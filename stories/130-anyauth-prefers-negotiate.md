# The Server Learned a Word Our Scripts Could Not Say

I did not write `pull-bundle`. I want to be clear about that up front, not to duck
anything, but because it matters to how long this took: I spent the first hour of the
incident treating a nine-year-old shell script as a black box that had always worked,
which is exactly the frame of mind in which you do not read the flags.

## Tuesday, 06:40

The page said `fleet-agent: policy bundle rejected on 3 hosts`. Three is a bad number.
One is a host problem. All two hundred is an obvious problem. Three is the kind of
number that makes you look for what is special about those three, and there is always
something special about any three hosts you care to examine.

What was special about those three was that they had rebooted overnight. The agent
reloads its policy bundle from disk on start. Everything else in the fleet was still
running on a bundle it had loaded days ago and had no reason to re-read.

The bundle on disk was 412 bytes. A healthy one is about 90 kilobytes. I ran `head`
on it and got an HTML document whose `<title>` was `401 Unauthorized`.

So: the nightly pull had been writing a 401 error page over the policy bundle, on
every host in the fleet, and had been doing it for — this is the part I did not want
to find out — nine days. The reboots were not the failure. The reboots were the
first thing that had bothered to look.

## The script

```sh
#!/bin/sh
set -e
tmp=$(mktemp /var/lib/fleet/.bundle.XXXXXX)
curl -sS --anyauth -u "$SVC_USER:$SVC_PASS" \
     -o "$tmp" \
     --max-time 120 \
     "https://artifacts.corp.example/fleet/policy/current.json"
mv "$tmp" /var/lib/fleet/bundle.json
```

`set -e`, so the `mv` only runs if curl succeeds. Curl had been succeeding. Exit code
0, nine nights running, writing a 401 page into the temp file and then renaming it
into place with the confidence of a job well done.

## Why it said --anyauth

The script is from 2017 and the flag was not a shrug. I went and found the person who
wrote it, who now works two floors up on something else entirely, and she remembered
the reasoning immediately, which tells you it had cost her some thought at the time.

The constraint was that `pull-bundle` was never pointed at one service. It was the
one artifact-fetching primitive in the base image, and in 2017 the things it fetched
from were three different systems with three different ideas about authentication.
The inventory service, which was a Perl CGI, wanted Basic. The artifact store, which
was somebody's Nexus, wanted Digest. The wiki that the build notes lived on was
behind a Kerberised Apache and wanted Negotiate. Each of these was operated by a
different team and none of them were going to change for her.

The obvious design is a table: endpoint to auth method, consulted before the fetch.
She did not want the table, and her reason was specific and correct. A table is a
second thing that has to be right. It has to be updated when a service changes, by
someone who notices that a service has changed, and the failure mode of a stale table
is an authentication error at three in the morning on a host nobody can log into.
She wanted the fetch primitive to have no configuration at all beyond a URL and a
credential.

`--anyauth` buys exactly that. Curl issues the request without credentials, reads the
`WWW-Authenticate` headers off the 401, and picks a method from what the server says
it accepts. The documentation is honest about the price — *this is done by first
doing a request and checking the response-headers, thus possibly inducing an extra
network round-trip* — and an extra round-trip on a nightly job is not a price at all.
Adding a fourth endpoint required changing nothing. That is a real property and it
held for nine years.

The tradeoff, which is written down in the curl documentation but not in our runbook,
is that you have handed the choice of authentication method to the server. Not to the
server's operator on the day you wrote the script — to the server, on every request,
forever. And curl's choice among the offers is not negotiable either. `pickoneauth()`
walks a fixed preference order, and the comment above it says what it is doing:

```c
/* The order of these checks is highly relevant, as this will be the order
   of preference in case of the existence of multiple accepted types. */
if(avail & CURLAUTH_NEGOTIATE)
  pick->picked = CURLAUTH_NEGOTIATE;
```

Negotiate first, then Bearer, Digest, NTLM, NTLM_WB, Basic, and AWS SigV4 last. There
is no knob. If a server offers two methods, curl takes the one higher in that list,
and the list encodes a judgement about cryptographic strength that has nothing to do
with whether the client is in a position to use it.

## What changed on the other side

Nine days earlier, the artifacts team had put `artifacts.corp.example` behind the new
SSO-aware ingress. This was a good change, competently executed, and announced in a
channel I am in. Staff hitting the artifact store in a browser now get single sign-on
instead of a password prompt. The ingress does that by adding one offer to the
challenge it returns on an unauthenticated request:

```
HTTP/1.1 401 Unauthorized
WWW-Authenticate: Negotiate
WWW-Authenticate: Basic realm="artifacts"
```

Basic still worked. They kept it precisely so that scripts would not break. The
service account `svc-fleet` had a password, the password was still correct, and if you
ran the fetch by hand with `--basic` it returned ninety kilobytes of policy bundle
exactly as it always had.

But our curl no longer asked for Basic. It read both headers, `avail` came out as
`CURLAUTH_NEGOTIATE | CURLAUTH_BASIC`, and `pickoneauth()` did what it says on the
tin. The fleet hosts have no keytab and no ticket cache. They are not Kerberos
clients in any sense. Curl picked Negotiate on a machine that had never held a
Kerberos credential in its life.

## Why it picked a method the host could not perform

This was the part I got wrong for an hour, because my mental model was that curl
would discover it had no ticket and fall back. That is not how availability is
decided. When curl reads `Negotiate` in the challenge, the question it asks is
`Curl_auth_is_spnego_supported()`, and in the GSS-API build that function is:

```c
bool Curl_auth_is_spnego_supported(void)
{
  return TRUE;
}
```

It is a build-time fact, not a runtime one. It means *this binary was linked against
GSS-API*, which the Ubuntu packaging arranges for every flavour — `debian/rules`
passes `--with-gssapi=/usr` in the configure arguments shared by all of them — and it
says nothing whatsoever about whether there is a credential cache on the box.
`curl -V` had been listing `GSS-API Kerberos SPNEGO` in its features line on every
host in the fleet since the image was built, and the answer to "can this host do
Kerberos" had been yes, in the only sense curl means by it, the whole time.

## Why it then gave up silently

Having picked Negotiate, curl retried the request and tried to produce an
`Authorization: Negotiate` header. `gss_init_sec_context()` failed, because there is
no ticket. What happens next is the whole incident, and it is eleven lines in
`lib/http_negotiate.c`:

```c
result = Curl_input_negotiate(data, conn, proxy, "Negotiate");
if(result == CURLE_AUTH_ERROR) {
  /* negotiate auth failed, let's continue unauthenticated to stay
     compatible with the behavior before curl-7_64_0-158-g6c6035532 */
  authp->done = TRUE;
  return CURLE_OK;
}
```

Read what that does. The Kerberos handshake could not be started, so curl marks host
authentication **done** and returns success. Not "done" as in authenticated — "done"
as in stop trying. The second request went out with no `Authorization` header at all.
The server, entirely reasonably, returned 401 again. And curl, having already decided
it was finished authenticating, did not go back and consider Basic, which was sitting
right there in the challenge and which would have worked.

The comment explains itself: this is bug-compatibility with the behaviour before a
2019 change, kept so that a curl which cannot do Kerberos against a server that
merely mentions it degrades to an unauthenticated request rather than an error. For
a client fetching a public resource from a server that offers optional SSO, that is
the kind thing to do. For us it converted a credential failure into a 401 page.

And the diagnostic for the failure is `infof()`:

```
* gss_init_sec_context() failed: No Kerberos credentials available
  (default cache: FILE:/tmp/krb5cc_0)
```

`infof()` is verbose-only output. The script ran `curl -sS`. `-S` promotes error
messages past `-s`, and this is not an error message; it is an informational one, and
it had never once been printed on any host in the fleet. The one line that named the
problem in plain language was written to a stream that was not enabled.

## The exit code

The last thing to explain is why `set -e` did not save us, and the answer is that
curl really did succeed.

Curl decides whether an HTTP status is fatal in `http_should_fail()`, and the rule
for 401 is not "401 is an error". The rule is: if we were not asked to fail on
errors, nothing is fatal; and even when we were, a 401 is only fatal if there is no
user name configured, or if `data->state.authproblem` is set. We had a user name.
`authproblem` does eventually get set — the second 401 comes back, curl tries the
challenge again with Negotiate now firmly picked, fails again, and that path does set
it — and `Curl_http_auth_act()` then returns

```c
return data->set.http_fail_on_error ? CURLE_HTTP_RETURNED_ERROR : CURLE_OK;
```

The entire difference between exit 22 and exit 0 is whether `-f` was on the command
line. It was not. So curl wrote the 401 body to `-o`, returned 0, `set -e` was
satisfied, and `mv` put it where the agent would find it.

I will note that the curl manual does not hide this. `--fail` says, in its own
documentation: *This method is not fail-safe and there are occasions where
non-successful response codes slip through, especially when authentication is
involved (response codes 401 and 407).* We were not even at the level of being
tripped up by that footnote. We had not reached it.

## The fix

The immediate fix was one flag, and it is the flag I would not have found without
reading `tool_getparam.c`:

```sh
curl -sS --anyauth --no-negotiate --fail -u "$SVC_USER:$SVC_PASS" ...
```

The manual presents these as alternatives to each other — *this is used instead of
setting a specific authentication method, which you can do with --basic, --digest,
--ntlm, and --negotiate* — and I had read "instead of" as meaning the last one wins.
It does not. Underneath, the tool keeps a single bitmask, and the options are not all
the same shape:

```c
case 'o': /* --anyauth, let libcurl pick it */
  if(toggle)
    config->authtype = CURLAUTH_ANY;
```

`--anyauth` *assigns* every bit. `--no-negotiate` *clears* one:

```c
case 'l': /* --negotiate */
  if(!toggle)
    config->authtype &= ~CURLAUTH_NEGOTIATE;
```

So `--anyauth --no-negotiate` means "any method except Negotiate", which is precisely
what we want and is documented nowhere. Order matters and is not commutative:
`--no-negotiate --anyauth` clears the bit and then sets every bit back, and does
nothing at all. I tested both before I believed it.

`--fail` went in at the same time, so that if any of this goes wrong again the script
stops at curl instead of at a reboot nine days later.

The longer fix is the table she did not want to write, and I have come round to her
side of it rather than mine. A table would not have helped here. The table would have
said `artifacts.corp.example: basic`, which is what we now effectively say, but the
table would have been written in 2017 and would have been just as ignorant of the
ingress change as `--anyauth` was — it would simply have been ignorant in a way that
happened to keep working. That is luck, not design. What we actually lacked was any
check that the thing we downloaded was the thing we wanted. `pull-bundle` now pipes
the result through a schema check before the `mv`, and the 412-byte HTML page fails
it in a way that no amount of cleverness about authentication would have.

## Footnotes for whoever reads this next

- There is a `CURLAUTH_ANYSAFE` in libcurl, which is every method except Basic, for
  the opposite problem: `--anyauth` will send your password in clear text to any
  server that asks for Basic over plain HTTP, and `libcurl-security.3` says so in as
  many words. The curl command-line tool does not expose `ANYSAFE`. From the shell
  you get `--anyauth`, or you assemble the mask you want out of `--no-` toggles.
- With `--anyauth` on a GET, the cost is one wasted round trip. On a POST or a PUT it
  can be the entire body, twice. The empty `Content-Length: 0` probe request that
  curl uses for authentication negotiation is only armed when a *single* method is
  already picked; with `--anyauth` the first request carries the real payload, gets
  the 401, and then has to rewind and send it again. If more than about 2 KB remains
  unsent when the 401 arrives, curl gives up on the connection entirely —
  `streamclose(conn, "Mid-auth HTTP and much data left to send")` — and opens a new
  one.
- Which is why the manual warns you off `--anyauth` with uploads from stdin: stdin
  cannot be rewound. When the tool sets up an upload from stdin it counts the bits in
  your auth mask, and if there is more than one it prints *Using --anyauth or
  --proxy-anyauth with upload from stdin involves a big risk of it not working. Use a
  temporary file or a fixed auth type instead.* A warning, not a refusal.
- If Negotiate had succeeded, there would have been a second surprise waiting:
  Negotiate and NTLM are connection-bound, and when curl picks NTLM it logs *Forcing
  HTTP/1.1 for NTLM* and closes the HTTP/2 connection. A change in a server's
  challenge header can quietly change your protocol version.
- The challenge parser matches each offer by prefix and requires the next character
  to be a space, a comma, or end of string. A header reading `Negotiate-Lite` is not
  Negotiate. I checked, because at 08:20 I was willing to believe anything.
- `--anyauth` does nothing at all without `--user`. With no user name and no bearer
  token, curl marks both host and proxy authentication done before it starts and
  never looks at a `WWW-Authenticate` header. The flag in a credential-less command
  line is decoration.
