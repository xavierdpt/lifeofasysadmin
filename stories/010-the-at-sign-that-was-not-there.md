# The At-Sign That Was Not There

The ticket came in at 16:40 on a Thursday, which is the worst time for a ticket to
come in. Early enough that nobody can claim it is tomorrow's problem, late enough
that everyone has spent their good hours already.

> **Subject:** metrics endpoint unreachable from the new sidecar\
> The exporter is running, `ss` shows it listening, but curl can't connect.\
> Nothing in the exporter logs. Please advise.

Attached was a terminal paste, which is more than most tickets get:

```
$ ss -xl | grep metrics
u_str LISTEN 0  5   @metrics.sock  1008939  * 0

$ curl --abstract-unix-socket @metrics.sock http://localhost/stats
curl: (7) Failed to connect to localhost port 80 after 0 ms: Couldn't connect to server
```

Emil, who had opened the ticket, had done the thing you want people to do. He had
checked that the thing was listening before claiming it wasn't. He had used the
right flag: the exporter binds an *abstract* Unix socket, one that lives in a
namespace of its own rather than on the filesystem, and `--abstract-unix-socket` is
exactly the option for that. He had even pasted the socket name straight out of
`ss` so as not to mistype it.

That last part was the bug.

## Why an abstract socket at all

Nobody chooses an abstract Unix socket by accident, and it is worth knowing what
the exporter's author was buying, because it explains why the failure was so
quiet.

The exporter runs in a container with a read-only root filesystem. The scraper is
the sidecar in Emil's subject line, and it shares the exporter's network
namespace. A pathname socket would have meant finding somewhere writable for the
socket file to live, mounting that somewhere into both containers, and then
getting the uid, gid and mode right on both sides — three moving parts to hold a
socket that never leaves the pod. It would also have meant the stale-socket dance:
a pathname socket is a file that "must be deleted by the caller when it is no
longer needed", as `unix(7)` puts it, so after a hard kill the file survives its
process and the next start has to `unlink()` it before binding, or fail with
`EADDRINUSE`.

An abstract socket has none of that. There is no file, so there is nothing to
mount, nothing to chmod and nothing to clean up: abstract sockets "automatically
disappear when all open references to the socket are closed". And the reachability
falls out for free, because network namespaces isolate the abstract socket
namespace along with everything else network-shaped. The sidecar sharing the
namespace could already see it; nothing outside the namespace could. For a metrics
endpoint that should be visible to exactly one neighbour, that is a tidy answer.

The bill comes in two parts. The first is a security footnote: `unix(7)` is blunt
that "socket permissions have no meaning for abstract sockets" — umask does
nothing, chmod does nothing — so the only thing standing between the exporter and
a client is the namespace boundary. Everything in that namespace can connect, full
stop. The second part is the one Emil paid. A pathname socket is a thing you can
`ls`. An abstract socket is a name with no representation anywhere except in the
kernel's tables and in whatever tool agrees to print it for you — and, as we were
about to find out, the tools do not agree.

## What the error says, and what it means

The message is a small masterpiece of misdirection. It names a host, `localhost`.
It names a port, `80`. Neither was ever contacted. When you point curl at a Unix
socket, the hostname and port in the URL are decoration — they fill in the `Host:`
header and nothing else — but the failure path doesn't know that. Deep in
`lib/connect.c`, after every connection attempt has failed, curl reaches for
`conn->host.name` and `conn->port` and prints them, because that is what it prints
for every other kind of connection in the world.

So the first thing I told Emil was to stop reading the last line. The last line is
a summary written by a function that has forgotten what it was doing. The line
above it is the one that knows:

```
$ curl -v --abstract-unix-socket @metrics.sock http://localhost/stats
*   Trying :0...
* Immediate connect fail for : Connection refused
* Failed to connect to localhost port 80 after 0 ms: Couldn't connect to server
```

`Connection refused`. Not `No such file or directory`, not a timeout. On a Unix
socket, `ECONNREFUSED` means the kernel looked up the address, found nothing
listening at it, and said no. Which is strange, because `ss` had just shown
something listening.

Unless it was listening at a *different* address than the one we were asking for.

## The empty address

Look again at that verbose output and you'll notice something that ought to be
unsettling:

```
*   Trying :0...
```

Trying *what*? There is no address there at all. The port is zero, which is fine —
Unix sockets don't have ports — but the address is empty, and it is empty in both
the successful and the failing case. That is not curl being coy. It is curl
printing a C string that begins with a NUL byte.

An abstract socket address is a `sockaddr_un` whose `sun_path` starts with a zero
byte; the name is the bytes *after* that zero, and its length comes from the
address length rather than from a terminator. `Curl_addr2string()` in
`lib/connect.c` formats `sun_path` with `%s`, so for an abstract socket it always
formats the empty string. Every abstract-socket connection curl has ever made, on
any machine, logs `Trying :0...` — and, a line later, `Connected to localhost ()
port 80`, with nothing between the parentheses. It is not a symptom. It is just
what that code path looks like, forever.

This matters because it removes the one diagnostic you would most like to have.
curl will not echo back the name it is actually using. You have to work that out
yourself.

## Two tools, two conventions

`ss` and `netstat` display abstract sockets with a leading `@`. That `@` is not
part of the name. It is a rendering of the leading NUL byte, a printable stand-in
for an unprintable one, invented so that abstract sockets do not appear in the
listing as blank lines.

curl's own documentation says so, in one sentence in
`docs/cmdline-opts/abstract-unix-socket.d`:

> Note: netstat shows the path of an abstract socket prefixed with '@', however
> the `<path>` argument should not have this leading character.

So when Emil copied `@metrics.sock` out of `ss` and handed it to curl, curl did
what it was told. It built an address consisting of a NUL byte followed by the
twelve characters `metrics.sock` — sorry, the thirteen characters `@metrics.sock`
— and asked the kernel for that. The exporter was listening on the NUL byte
followed by `metrics.sock`. Two different names. Nothing was listening at the one
we asked for. Connection refused, correctly, instantly.

Drop the `@` and it works:

```
$ curl -v --abstract-unix-socket metrics.sock http://localhost/stats
*   Trying :0...
* Connected to localhost () port 80
> GET /stats HTTP/1.1
> Host: localhost
...
< HTTP/1.1 200 OK
```

One character. Forty minutes.

## The neighbouring trap

While we were in there, Emil asked the reasonable follow-up: what would have
happened with `--unix-socket`, the filesystem variant, if he'd used the wrong one?

```
$ curl -v --unix-socket @metrics.sock http://localhost/stats
*   Trying @metrics.sock:0...
* Immediate connect fail for @metrics.sock: No such file or directory
```

Note the difference. Here the name *is* an ordinary C string, so curl prints it,
and the kernel goes looking for a file called `@metrics.sock` in the current
directory, doesn't find one, and says `ENOENT`. Same exit code — 7 — and a
completely different story underneath. `ENOENT` means "there is no such path".
`ECONNREFUSED` on a Unix socket means "that address exists as far as I'm
concerned, and nobody is home". If Emil had been on the filesystem variant, the
error would have pointed almost directly at the mistake. On the abstract variant
it pointed nowhere, because there was nothing to point at.

There is one more edge here, which I filed away for the runbook rather than
inflicting on anyone at 17:20. `sun_path` is 108 bytes. curl rejects a longer path
before it ever reaches the kernel:

```
$ curl --abstract-unix-socket "$(python3 -c 'print("a"*108)')" http://localhost/
curl: (6) Unix socket path too long: 'aaaaaaaa...'
```

Exit code 6 is `CURLE_COULDNT_RESOLVE_HOST`. No host was resolved, or could have
been. It is the code the Unix-socket path happens to return for a name it can't
use, and if you are reading exit codes out of a monitoring script rather than
reading the message, it will tell you your DNS is broken.

## What went into the runbook

Not "remember to drop the `@`". People don't remember that; they remember it for
two weeks. What went in was a shape:

- **Never paste a socket name from `ss` or `netstat` straight into curl.** Those
  tools render the leading NUL as `@`. Take the name from the code, the unit file,
  or the config that binds it.
- **Read the line above the summary.** curl's final `Failed to connect to <host>
  port <port>` names whatever was in the URL, which for a Unix socket is fiction.
  The `Immediate connect fail` line carries the real `errno`.
- **On an abstract socket, `Trying :0...` is normal.** The empty address is a
  formatting artefact, not evidence.
- **Distinguish the two failures.** `ENOENT` means the path is wrong.
  `ECONNREFUSED` means the name is right in form but nothing is bound to it —
  either the service is down, or you are asking for a name one character away from
  the one it took.

Emil added a fifth line himself, a week later, after it caught someone else:

- **The `@` you can see is the byte you can't.**
