# The Bucket That Became a Service

We had rotated the access keys on the Tuesday. So when the archive uploads started
failing on the Wednesday with `SignatureDoesNotMatch`, nobody spent even a minute
looking anywhere else. There is a particular kind of incident where the evidence is
so agreeable that it takes you three hours to notice it never actually said
anything.

The job is a nightly one. A retention worker rolls up the previous day's audit
events into a single gzipped file and pushes it to object storage, where legal's
tooling picks it up. It runs in a distroless image — no shell, no package manager,
no Python — and the entire upload is one command:

```
curl --fail-with-body -sS \
     --aws-sigv4 "aws:amz" \
     --user "$AK:$SK" \
     -T /work/audit-2026-09-15.jsonl.gz \
     "https://audit-archive-prod.s3.eu-west-1.amazonaws.com/2026/09/audit-2026-09-15.jsonl.gz"
```

The response body, which `--fail-with-body` helpfully keeps instead of throwing
away, was this:

```xml
<Error><Code>SignatureDoesNotMatch</Code><Message>The request signature we calculated does not match the signature you provided. Check your key and signing method.</Message></Error>
```

"Check your key." We had just changed the key. Case closed, allegedly.

## Why curl and not the SDK

It is worth saying why a signed S3 upload is being done by a command-line HTTP
client at all, because the answer is not laziness and it explains exactly which
failure was available to us.

The retention worker is in scope for the audit that the audit events exist to
satisfy, which means its image gets reviewed, and the review is easier the less is
in it. The official SDK route meant a Python runtime, `boto3`, and the transitive
set underneath it, in an image whose entire job is to read a file and send it
somewhere. Every one of those is a thing to patch, a thing to scan, and a thing to
explain in the review. `--aws-sigv4` collapses that to a flag on a binary that was
already present.

What it buys is precise. SigV4 is not a protocol you can improvise: it is a
canonical request, a hashed canonical request, a four-stage HMAC key derivation,
and an `Authorization` header with the signed header list in it. Getting that wrong
by one byte of whitespace is indistinguishable from getting the password wrong.
`lib/http_aws_sigv4.c` does the whole thing — including the canonicalisation nobody
gets right by hand, like the sort in `canon_query()` that reorders query pairs and
uppercases percent-escapes — and it has done since 7.75.0. One flag, no runtime.

The tradeoff is that curl implements the *signing*, not the SDK. There is no
credential chain, no instance-role refresh, no endpoint resolver. Those are all
things you now do yourself, and we knew about all of them, because they are the
kind of missing feature that announces itself the first time you need it.

The one we did not know about is the one that does not announce itself: curl still
needs a region and a service to build the credential scope, and if you do not give
it either, it will work them out from the hostname. The man page mentions this, in
the mildest possible phrasing — the region is used "when the region name is omitted
from the endpoint", the service likewise. What it does not say anywhere is *how*
it reads the endpoint. That is the bill, and it came due the day someone changed a
URL.

## Three hours on the key

I want to record the wrong path honestly, because it was not stupid, it was just
well-supported.

We re-issued the key pair. Same error. We checked for a trailing newline in the
secret, which is the classic way to break this, since the secret is fed straight
into the derivation:

```c
  secret = curl_maprintf("%s4%s", provider0,
                         data->state.aptr.passwd ?
                         data->state.aptr.passwd : "");
```

Anything in `passwd` is signed with, including a newline you cannot see. Ours was
clean. We tried the same credentials from a laptop with the AWS CLI and they worked
on the first attempt, which should have been the moment the key hypothesis died,
and instead became "so it is something about the container".

What broke the loop was the dullest possible move. We took the `-sS` off and put
`-v` on.

```
* aws_sigv4: picked service audit-archive-prod from host
* aws_sigv4: picked region s3 from host
```

curl had been printing the cause every single night, to a stream we had explicitly
suppressed.

## First dot, second dot

The inference is about twenty lines, and once you have read them the behaviour is
not surprising at all — it is the only thing the code could possibly do.

```c
  if(!service[0]) {
    char *hostdot = strchr(hostname, '.');
    ...
    strncpy(service, hostname, len);
    service[len] = '\0';

    infof(data, "aws_sigv4: picked service %s from host", service);

    if(!region[0]) {
      const char *reg = hostdot + 1;
      const char *hostreg = strchr(reg, '.');
      ...
      strncpy(region, reg, len);
      region[len] = '\0';
      infof(data, "aws_sigv4: picked region %s from host", region);
    }
  }
```

The service is everything before the first dot. The region is everything between
the first dot and the second. That is the whole algorithm, and against the endpoint
it was written for it is exactly right:

```
s3.eu-west-1.amazonaws.com
└service┘ └─region─┘
```

Our URL was not that one any more. Two weeks earlier, a platform change had moved
our buckets from path-style to virtual-host-style addressing — `https://s3.eu-west-1.amazonaws.com/audit-archive-prod/...`
became `https://audit-archive-prod.s3.eu-west-1.amazonaws.com/...`. There were good
reasons for it and it was done carefully; it broke nothing that anyone could see,
because every other consumer of those buckets used an SDK, and an SDK resolves the
region from configuration rather than from string-scanning the hostname.

Put the new URL through those twenty lines and the bucket name is in the service
slot:

```
audit-archive-prod.s3.eu-west-1.amazonaws.com
└────service──────┘ └region┘
```

So curl built a credential scope of
`20260916/s3/audit-archive-prod/aws4_request`, derived a key down that path, and
signed with it. S3 derived a key down `eu-west-1/s3` and got a different answer.
Every byte of the request was correct except the two strings nobody had typed.

And the error message is not wrong, exactly. The signature really did not match.
"Check your key and signing method" even names the actual category — it is the
signing method — but the sentence has a key in the first half, and after a key
rotation that is the only half anyone reads.

## The second failure, hiding behind the first

Fixing it is one edit. Name the two fields instead of letting them be guessed:

```
--aws-sigv4 "aws:amz:eu-west-1:s3"
```

What interests me is what that edit *also* fixed, silently, which we only found
because someone asked whether the upload had ever been fully correct.

There is a second place in `Curl_output_aws_sigv4()` that reads the service name:

```c
  sign_as_s3 = (strcasecompare(provider0, "aws") &&
                strcasecompare(service, "s3"));
```

That flag decides how the request payload gets hashed. For an ordinary service,
curl hashes what is in `postfields`:

```c
  result = Curl_sha256it(sha_hash, (const unsigned char *) post_data,
                         post_data_len);
```

`-T` does not use `postfields`. It streams a file. So `post_data` is NULL, the
length is zero, and what gets signed as the payload hash is the SHA-256 of an
empty buffer — for a request whose body is a 40 MB gzip. When `sign_as_s3` is true
the code takes a different branch entirely, `calc_s3_payload_hash()`, which sees a
request method and a payload it cannot hash in advance and substitutes S3's
documented escape hatch:

```c
#define S3_UNSIGNED_PAYLOAD "UNSIGNED-PAYLOAD"
```

then attaches it as `x-amz-content-sha256`, so the signature covers a declaration
that the payload is deliberately not signed, which is a thing both sides can agree
on.

With `service` inferred as `audit-archive-prod`, `sign_as_s3` was false. So the
broken scope was not our only problem: we were also signing an empty-payload hash
with no `x-amz-content-sha256` header at all. Two independent defects from one
misread hostname, arriving as one error message. Had we somehow fixed only the
scope, we would have got the identical `SignatureDoesNotMatch` and concluded the
fix had not worked.

The libcurl page says this part out loud, in the notes for `CURLOPT_AWS_SIGV4`:

> A sha256 checksum of the request payload is used as input to the signature
> calculation. For POST requests, this is a checksum of the provided
> CURLOPT_POSTFIELDS. Otherwise, it's the checksum of an empty buffer. For
> requests like PUT, you can provide your own checksum in an HTTP header named
> x-provider2-content-sha256.

"Otherwise, it's the checksum of an empty buffer" is a sentence I had read as a
description of GET.

## What we changed

- **The service and region are written down.** `--aws-sigv4 "aws:amz:eu-west-1:s3"`.
  Not because inference is wrong, but because the inference is a function of a
  hostname, and a hostname is something another team is allowed to change without
  telling us. The pinned form is immune to URL restructuring; the inferred form is
  a coupling between our auth and somebody else's DNS layout.
- **`-v` goes to the job log, always.** This is the change I would keep above the
  others. `infof()` is not debug output in the sense of being for developers; it is
  curl telling you what it decided. We had been discarding the tool's reasoning and
  keeping only its verdict, and then spending three hours trying to reconstruct the
  reasoning from the verdict.
- **The verification step uploads and then reads back.** A HEAD on the object,
  comparing size, after the PUT. Not because it caught this — this failed loudly —
  but because the empty-buffer discovery made the point that a signed request can
  be accepted for reasons unrelated to its body.
- **We wrote down which parts of SigV4 curl does.** Signing: yes, completely.
  Credential sourcing, endpoint resolution, retries, multipart: no. That list is
  now three lines at the top of the job, so the next person does not have to infer
  the boundary from an outage.

## The shape of it

The thing I keep turning over is not the parsing rule. It is that we chose a tool
for what it would not do — no SDK, no runtime, no dependency tree — and then were
surprised by the one thing it did do on our behalf without being asked.

A default that reads its input from somewhere else in your system is not a default
you have accepted. It is a dependency you have not noticed. Ours was on the
position of a dot in a hostname, and the day someone moved the dot, the tool did
precisely what it says it does, printed precisely what it had decided, and we
were not listening.
