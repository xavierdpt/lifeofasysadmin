# The Flag That Was Ignored by Some SFTP Servers

The migration took forty minutes. I know because I put the maintenance window in the
calendar as an hour and closed the ticket early, which is a thing I have stopped
doing since.

What we moved was the smallest, dullest transfer we own: a settlement journal that
goes out once a day to a clearing partner. One file, appended to daily, one file per
month. It had been going out over FTP since before I was hired. The partner was
sunsetting FTP on 2026-02-28, so on the 17th I changed `ftp://` to `sftp://`, added
a key, ran it by hand, watched it exit zero, and went to lunch.

It kept exiting zero for seven weeks. That is the part I want to be honest about up
front: nothing failed. Nothing retried. Nothing paged. The job was green every single
night while the file on the far end was quietly wrong in a way that no exit code in
curl's table describes.

## The job

Here is the whole thing, minus the key path and the hostname:

```
curl --fail-with-body -sS \
     --upload-file /var/spool/settle/journal.batch \
     --append \
     --key /etc/settle/id_ed25519 \
     sftp://sftp.partner.example/inbound/journal-2026-04.dat
```

`--append` is `-a`. It is old — `Added: 4.8` in `docs/cmdline-opts/append.d`, which
puts it somewhere around 1999, older than most of the things it is being used to
talk to. The tool's man page says:

> (FTP SFTP) When used in an upload, this option makes curl append to the target file
> instead of overwriting it. If the remote file does not exist, it is created. Note
> that this flag is ignored by some SFTP servers (including OpenSSH).

I want to be clear that this sentence was in `curl.1` the whole time. It is four
lines long and the fourth line is the entire incident. I had read that page. I had
read it looking for whether `--append` worked over SFTP at all, found "FTP SFTP" in
the protocol list, and stopped reading at the good news.

## Why we were appending in the first place

Nobody would design this today, so it is worth saying who designed it and what they
were buying, because they were not being careless.

The partner's ingest is a batch job on their side that wakes at 06:00, reads exactly
one file per month at a fixed path, and reconciles it against their own ledger. It
does not list a directory. It does not glob. It does not accept a manifest. When our
predecessors onboarded in the FTP era, the partner's integration guide gave them two
options: upload a complete cumulative file every night, or append the day's delta.

The motivation was the month-end file size. By the 28th the cumulative journal is
around 900 MB, and the link to the partner's DMZ was, in the year this was designed,
a very tired one. Re-uploading 900 MB every night to add 30 MB was not a stylistic
objection; it was a nightly transfer that ran past the ingest window and got the
whole file rejected as incomplete.

What appending buys is specific and real: the bytes on the wire each night are the
bytes that are new, the transfer finishes in two minutes instead of fifty, and the
remote file is never in a half-written state that the 06:00 job could pick up. That
last one matters more than the bandwidth. A cumulative re-upload has a window —
between the first byte and the last — where the file at the fixed path is a truncated
prefix of the month. Appending never produces a file shorter than the one that was
there before.

The tradeoff is the one every append-based protocol has: the client no longer knows
what the file contains. With a cumulative upload, the local file is the truth and the
remote is a copy, so you can compare them. With an append, the remote file is the
only copy of the aggregate, and correctness depends entirely on the append having
actually been an append. Under FTP that dependency was visible. Under SFTP it stopped
being visible, and that is the bill, arriving seven years later on a Thursday.

## What FTP was doing that I did not appreciate

Over FTP, `--append` is not a flag in any meaningful sense. It selects a verb.

In `lib/ftp.c`, at the bottom of the upload setup, there is exactly one line that
cares:

```c
  result = Curl_pp_sendf(data, &ftpc->pp, append?"APPE %s":"STOR %s",
                         ftpc->file);
```

`APPE` instead of `STOR`. That is a command the server has to answer. If the server
does not implement `APPE`, or will not do it on that path, it says so with a 5xx, and
`ftp_state_stor_resp()` turns that into:

```c
  if(ftpcode >= 400) {
    failf(data, "Failed FTP upload: %0d", ftpcode);
```

and returns `CURLE_UPLOAD_FAILED`, which is exit code 25 — "Failed starting the
upload. For FTP, the server typically denied the STOR command." A refusal to append
was a refusal to transfer. There was no version of the FTP job that uploaded the
bytes *and* failed to append them. The two outcomes were the same outcome.

I had internalised that so thoroughly that I did not know I had internalised it.
"Exit zero means it appended" was not a belief I held; it was a belief I was standing
on.

## Seven weeks later

The call came from the partner's reconciliation team on 2026-04-09, and the complaint
was almost too strange to act on. They were seeing March transactions in the April
file. Not duplicated April ones — March ones, from specific dates, in a contiguous
run at the end of the file.

My first hypothesis was theirs: that we were writing the wrong month's path. We were
not; the path is built from `date +%Y-%m` and the April file was named for April.

My second hypothesis was that our local spool had stale content. It did not.

Then I did the thing I should have done on 2026-02-17, which was look at the remote
file instead of the exit code. I pulled it down and diffed it against what the month
should have been, and the shape of it is what finally made sense of everything:

- The first N bytes were that night's batch. Correct records, correct order.
- Everything after byte N was untouched older content, ending mid-record.

The file was not appended. It was also not overwritten. It was *overlaid* — each
night's batch painted over the front of whatever was there, and whatever was longer
than that night's batch survived off the end like the bottom of a poster under a
smaller poster.

## The three flags

The answer is nine lines in `lib/vssh/libssh2.c`, in the SFTP upload path:

```c
      if(data->set.remote_append)
        /* Try to open for append, but create if nonexisting */
        flags = LIBSSH2_FXF_WRITE|LIBSSH2_FXF_CREAT|LIBSSH2_FXF_APPEND;
      else if(data->state.resume_from > 0)
        /* If we have restart position then open for append */
        flags = LIBSSH2_FXF_WRITE|LIBSSH2_FXF_APPEND;
      else
        /* Clear file before writing (normal behavior) */
        flags = LIBSSH2_FXF_WRITE|LIBSSH2_FXF_CREAT|LIBSSH2_FXF_TRUNC;
```

Read the branches as a set and the failure mode falls out of them without needing a
packet capture.

With `--append`, curl opens the remote file `WRITE|CREAT|APPEND`. Note what is *not*
in that list: `TRUNC`. Truncation appears only in the third branch, the ordinary one.
That is correct and deliberate — you must not truncate a file you are about to append
to.

But the append semantics live entirely in `LIBSSH2_FXF_APPEND`, and that flag is a
request to the server. An SFTP write carries its own offset, so a server that does
not honour the append bit simply writes where it is told, starting at zero. Drop
`APPEND` from that first branch and what remains is `WRITE|CREAT`: open it, don't
truncate it, write from the top. Which is precisely the file I was holding.

So the flag we depended on was, on this server, the only one of the three with no
effect, and the one that was silently dropped was the one carrying all of the
meaning. Everything else about the transfer was a complete success. All the bytes we
sent arrived, in order, at the offsets curl asked for. Exit code zero was not a lie.
It was answering a narrower question than I was asking it.

## The manual I should not have trusted

There is a second, smaller trap here, and I fell in it while I was already digging.
When I went to check whether this was a curl bug, I read the library page rather than
the tool page, and `docs/libcurl/opts/CURLOPT_APPEND.3` says:

```
.SH DESCRIPTION
A long parameter set to 1 tells the library to append to the remote file
instead of overwrite it. This is only useful when uploading to an FTP site.
.SH PROTOCOLS
FTP
```

FTP only. Which, for about ten minutes, had me believing our SFTP job was passing an
option that libcurl ignored outright — a clean story, and the wrong one. The code
above is right there in the SFTP handler; `remote_append` is read and acted on. The
tool's own page lists `FTP SFTP` and carries the OpenSSH warning. Two pages in the
same tarball, one of them stale, and I picked the stale one because it was the one
that sounded like a lower level of the stack.

Grepping the source settled in thirty seconds what two man pages disagreed about. I
should have started there. The habit I am trying to build is: when the documentation
is load-bearing for a production decision, read the code it documents.

## What we changed

We stopped appending remotely. The partner's ingest still reads one fixed path, so we
could not switch to per-day files, but we could stop asking the far end to do arithmetic
for us:

- The month's journal is now assembled locally, where appending is a filesystem
  operation we can verify.
- Each night uploads the complete file to `journal-2026-04.dat.part`, then issues a
  rename into place via `--quote` once the transfer has exited zero. The fixed path is
  never a partial file, which was the real thing the original append design was
  protecting. The bandwidth objection that justified the append died with the link
  upgrade in 2021 and nobody had revisited the design since.
- After the rename, a separate step stats the remote file and compares the size to the
  local one. A transfer that lies about its results cannot lie about the file it left
  behind, so the check is on the artefact, not the exit code.

The third bullet is the one I would keep if I could only keep one. Not because size
comparison is clever — it is the least clever check available — but because for seven
weeks we had a nightly job whose only output was its own opinion of itself.

## What I tell people now

`--append` over FTP is a verb the server must answer. `--append` over SFTP is a
request the server may decline in silence, and curl has no way to tell you it was
declined, because nothing failed. The man page has said so since long before I
touched this, in one sentence I had read and filed as a footnote.

The general shape, though, is bigger than one flag. When a transfer moves to a new
protocol, the flags come along unchanged and look like they mean what they used to
mean. Some of them stop being enforceable on the way. It is worth asking, of every
option on a command line that survived a migration: on the old protocol, who was
responsible for making this true — and on the new one, is anybody?
