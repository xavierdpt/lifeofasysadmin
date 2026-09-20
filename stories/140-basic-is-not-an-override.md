# The Flag I Added To Be Safe

I am the person who broke it. That is the whole reason I am writing this down
rather than letting the timeline in the incident doc speak for itself: the
timeline makes it look like a server change, and it wasn't. It was me, on a
Tuesday, adding six characters to a line I had no business touching.

The six characters were `--basic`.

## What the job did

`archive-push` ran at 02:10 every night on the media ingest box. It rolled the
previous day's transcodes into a tarball and streamed the tarball into the
archive service:

```
tar -cf - /srv/ingest/$DAY \
  | curl -sS --fail --digest -u "$ARCHIVE_USER:$ARCHIVE_PASS" \
         -T - "https://archive.internal/vault/$DAY.tar"
```

Two things in there are deliberate and neither is obvious, so both deserve an
explanation before I get to how they collided.

## Why it streams from a pipe

The `-T -` is the older of the two decisions. The ingest box has a 40 GB root
volume and no separate scratch partition, because it was specced as a machine
that receives files, transforms them, and pushes them somewhere else — nothing
was ever supposed to *sit* there. A day of transcodes is routinely 15 to 30 GB.

Writing the tarball to a file first and then uploading it would mean holding a
second full copy of the day on a volume that cannot hold one, so whoever wrote
the job used the pipe. What it buys is exact and easy to name: no temp file, so
no 30 GB write, no disk-full at 02:15, no half-written `/tmp/$DAY.tar` left
behind by a killed job for the next run to trip over. curl reads stdin and
sends it as it arrives.

The tradeoff is the part nobody writes on the whiteboard. A pipe has no
beginning to return to. If curl ever needs to send the body a *second* time, it
has to ask the reader to go back to the start, and the curl tool implements that
by trying to `lseek()` the input fd (`src/tool_cb_see.c`). On a pipe that call
fails, and the callback returns `CURL_SEEKFUNC_CANTSEEK`, which is 2
(`include/curl/curl.h:371`). Non-zero. libcurl turns a non-zero seek return into
`failf(data, "seek callback returned error %d", ...)` and
`CURLE_SEND_FAIL_REWIND` (`lib/multi.c:1770`) — exit code 65.

So the job's standing bet is: the body will only ever need to be sent once.

## Why it used Digest

The archive service is internal, but "internal" here still means the request
crosses two racks and a load balancer that terminates TLS, and the audit control
we signed up to says the archive credential must not be recoverable from a
captured request on any hop. Basic fails that flatly: curl builds the header by
formatting `user:password` and base64-encoding it (`lib/http.c:379`, then
`Curl_base64_encode`), which is an encoding, not a secret. Digest sends a hash
over a server-supplied nonce instead, so what's on the wire isn't replayable
tomorrow.

What Digest costs is a round trip. There is no Digest header curl can send
cold — it needs the server's nonce first. So the first request goes out with no
credentials, comes back 401 with a `WWW-Authenticate: Digest` challenge, and
curl repeats the request with the answer.

For a 30 GB body that sounds fatal, and it isn't, because libcurl knows the
shape of this dance. When it has picked a method that takes multiple passes, it
sets `conn->bits.authneg` and sends the PUT as a *probe* with a content-length
of zero (`lib/http.c:941`). The body doesn't move until the auth is settled. The
pipe gets read exactly once. The two decisions fit together, and they fit
together for four years.

## What I changed

We were migrating the archive service, and the new one spoke Basic only. I was
working through the jobs that talked to it. I read the man page for `--basic`,
which says:

> Tells curl to use HTTP Basic authentication with the remote host. This is the
> default and this option is usually pointless, unless you use it to override a
> previously set option that sets a different authentication method (such as
> --ntlm, --digest, or --negotiate).

*Unless you use it to override a previously set option.* That is the sentence. I
had a previously set option, `--digest`, and I wanted to override it, so I added
`--basic` to the end of the line and left `--digest` alone, because removing it
felt like the change that needed a review and adding felt like the change that
didn't.

`--basic` does not override anything. In `src/tool_getparam.c`, the case for it
is:

```c
case 'n': /* --basic for completeness */
  if(toggle)
    config->authtype |= CURLAUTH_BASIC;
  else
    config->authtype &= ~CURLAUTH_BASIC;
```

An OR. `--digest` a few lines up is an OR too. What I actually built was not
"Basic instead of Digest", it was the two-bit mask `CURLAUTH_DIGEST |
CURLAUTH_BASIC` — a *set of methods curl is willing to use*, which is a
different kind of thing than a choice.

## The bill

libcurl has one line of comment that explains the entire outage, in
`Curl_http_output_auth`:

```c
  if(authhost->want && !authhost->picked)
    /* The app has selected one or more methods, but none has been picked
       so far by a server round-trip. Then we set the picked one to the
       want one, and if this is one single bit it'll be used instantly. */
    authhost->picked = authhost->want;
```

*If this is one single bit.* Everything downstream in `output_auth_headers()`
tests `authstatus->picked == CURLAUTH_BASIC`, `== CURLAUTH_DIGEST`, and so on —
equality, not a mask test. My two-bit value equals none of them. No branch ran,
no header was emitted, `auth` stayed NULL, and so `multipass` was set FALSE,
and so `conn->bits.authneg` was FALSE.

No probe. curl streamed all 22 GB of Tuesday's tarball to a server that had
never been told who was sending it, the server said 401 at the end of it, and
curl — now finally knowing what was on offer — picked a method, cloned the URL
to retry, and reached for the beginning of the pipe.

```
* Please rewind output before next send
curl: (65) seek callback returned error 2
```

Forty-one minutes to send, and then exit 65.

The second-order joke is that even if the pipe *had* been seekable, I would not
have got what I asked for. The new service, mid-migration, was still advertising
both methods in the 401, and the preference order in `pickoneauth()`
(`lib/http.c:451`) is Negotiate, Bearer, Digest, NTLM, then Basic. With both
bits set and both offered, curl picks Digest. The flag I added to force Basic
would have been outvoted by the flag I left in to be safe.

## What I took from it

The fix was a one-word diff — delete `--digest` — and it is not the useful part.

The useful part is that I added a flag *without removing one*, which felt like
the cautious move and was in fact the only way to reach a state neither flag can
produce on its own. Auth options in curl are bits in a mask. Adding a bit is not
replacing a bit, and the man page sentence I leaned on describes the effect the
author had in mind, not the operation the parser performs. Six characters, and
no review, because what is there to review about a flag that the documentation
itself calls "usually pointless"?
