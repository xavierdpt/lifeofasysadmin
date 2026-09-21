# lifeofsysadmin

A collection of illustrative scenario stories about the life of a system administrator.

## Structure

```
stories.db             sqlite index: one row per story (numeric id, requested topic
                       verbatim, theme)
stories/{id}.md        the story content, one file per story (1.md, 2.md, … — do not read)
scripts/story.py       CLI to create and maintain stories
scripts/build_site.py  renders the collection into the GitHub Pages site
src/                   upstream package sources, for fact-checking stories (read-only)
aux/                   off-limits — do not read, modify, or reference
```

### The topic, the title and the theme

Each story has a **requested topic** and a **story title**, and they are deliberately
different:

- **Requested topic verbatim** — the `topic` column in `stories.db`. It names the
  *topic* the story is about, in the form the topic is actually written: `curl --basic`,
  `curl --aws-sigv4`. This is what `list` shows, and the site renders it as the
  subtitle under each entry in the index.
- **Story title** — the `# ` heading at the top of `stories/{id}.md`. Descriptive and
  written for a reader.

They are not expected to match. Never "fix" one to match the other.

Alongside them, the **theme** — the palette entry the story was written under, e.g.
`Migration` — is recorded in the `theme` column and named in the story itself. The
site prints it after the topic in the subtitle, on the index and on the story page.

The `id` is the link between them and is also the filename stem. It is a plain number
— `1`, `2`, `3` — carrying no meaning beyond identity and reading order. Because the
content lives in a file named after the id, either one can be rewritten without
touching the other.

### Database schema

```sql
CREATE TABLE stories (
    id    TEXT PRIMARY KEY,          -- a plain number, as text: "1", "2", ...
    topic TEXT NOT NULL,             -- requested topic verbatim, e.g. "curl --basic"
    theme TEXT NOT NULL DEFAULT ''   -- the palette theme, e.g. "Migration"
);
```

The `sqlite3` CLI is available (3.45.1) and is fine for ad-hoc queries against
`stories.db`. Make changes through `scripts/story.py`, though, so the index and the
files in `stories/` never drift apart.

## Commands

```bash
python3 scripts/story.py init                        # create stories.db and stories/
python3 scripts/story.py add "curl --cert" \
    -s "<story title>" -t "<theme>"                  # new row + stories/{id}.md stub
python3 scripts/story.py list                        # all stories, in reading order
python3 scripts/story.py retitle <id> "<new requested topic verbatim>"
python3 scripts/story.py retheme <id> "<theme>"
python3 scripts/story.py rename <id> <new-id>        # renumbers the row and the .md file
python3 scripts/story.py remove <id>                 # drops the row, keeps the file
python3 scripts/story.py check                       # index and files agree?
python3 scripts/build_site.py -o _site               # render the site locally
```

`add` assigns the next unused number as the id; pass `--id` to set it explicitly, and
`-e` to open `$EDITOR` on the new file. Without `-s`, the story title defaults to the
requested topic verbatim. `-t` records the theme and writes it into the stub.

## Conventions

- Ids are plain numbers (`1`, `2`, …) and the files are `stories/1.md`, `stories/2.md`,
  … — no slugs, no prefixes. The numeric id is also the reading order, so a story added
  later reads last unless it is renumbered with `rename`.
- The requested topic verbatim names the topic as it is written, e.g. `curl --basic`.
  It is not a sort key and takes no numeric prefix.
- Each `stories/{id}.md` begins with a single `# ` heading — the story title, followed
  by a `*Theme: <theme>*` line naming the theme the story was written under. The same
  theme goes in the `theme` column, spelled as the palette spells it.
- Don't build the story title on a negation or an absence: "nobody", "never",
  "no X can", "does not", "nothing but", "ignores". Stories often turn on something
  missing, and "the X that didn't Y" is the easy way to name that reveal, so the
  titles converged on it. The index lists them all together, and there it reads as a
  tic. Name something concrete from the story instead: an object, a moment, a
  number, a line of output.
- Add stories with `scripts/story.py add` rather than creating files by hand, so the
  index and the files never drift apart. Run `check` if in doubt.
- In commit messages, refer to a story by its id and requested topic verbatim
  (`Add story 6: acpid`, `Story 2: tighten the plugin section`), never by its title
  or a paraphrase of it. Commit subjects show up in `git log` and in the git status
  snapshot at the start of every session, so titles there put the earlier titles in
  context while the next one is being written. Older commits still carry titles; do
  not mine `git log` for them.

### Never read the existing stories

**Do not open, read, `cat`, `grep`, `head`, diff, or summarise any file under
`stories/`.** Not to match the house style, not to check the conventions, not to see
which themes are taken, not "just the first few lines", and not as a side effect of a
wildcard like `cat stories/*.md`. This holds even when writing a new story, which is
exactly when the temptation is strongest.

Everything you need to write a story is in this file: the topic-and-title rule, the
`# ` heading and `*Theme:*` line, the "show the feature in use and say why it exists"
requirement, and the themes palette. If something about the expected shape of a story is unclear, ask —
do not go and look at a neighbouring story to infer it.

The reason is voice. Stories written by someone who has just read the previous one
converge: the same rhythm, the same section headings, the same closing move, the same
narrator. The collection is meant to read as a set of separate accounts, and the only
reliable way to keep them separate is to write each one without the others in context.
Repetition that creeps in this way is invisible from inside a single story and obvious
when the collection is read end to end.

Two narrow exceptions, both of which are bookkeeping rather than reading:

- `scripts/story.py list` and `scripts/story.py check` are always fine. They report
  ids, requested topics verbatim and themes, never content.
- If the user explicitly asks you to read, edit, review or compare a specific story in
  that moment, do it. The instruction is about reaching for them unprompted.

To choose a requested topic verbatim, and to see which ids are taken, use `list`. To
propose themes, use the palette below and the topics `list` gives you — not the story
text.

### Show the feature in use, and say why it exists

The story exists to teach the topic. By the end the reader should know two things
about it: **what problem it solves** — why the feature was added at all, what was
painful or impossible without it — and **what it does**, concretely enough to use it.

Both come from an applied example, not from exposition. Show someone reaching for the
feature in a situation that actually calls for it: the command they type, the config
they write, the output they get back, and what they do with it. A paragraph explaining
the feature is not a substitute for a scene in which it earns its place. The reason it
exists is best shown by what the scene would look like without it — the workaround, the
manual step, the thing that silently went wrong before.

"Why does this exist" is a question about the feature, not about the local setup. Who
chose this host, this vendor or this directory layout is background at most; the
question the story answers is why the option, flag, protocol or policy was built and
what it is for.

That, alongside the theme the user picked from the palette below, is the whole
requirement.
There is no prescribed shape for it — no required section, heading, bullet list or
running order. Some stories will want a paragraph of history, some a line of
dialogue, some a single aside in the middle of the diagnosis. Work out each time
what that story needs, rather than reaching for the same structure or the same
vocabulary as the last one.

Ground the motivation the same way as the rest of the story: the man page, the
changelog, the source in `src/`. Why a feature exists is as checkable as an error
message, and inventing a plausible-sounding rationale is the same error as
inventing a plausible-sounding flag.

## Story themes

A working palette of scenarios for the collection. Not a checklist — a menu to pick
from so the stories stay varied instead of all being "prod broke at 3am".

### Propose three themes before writing

The division of labour is fixed: **the user supplies the topic, you supply the
themes.**

The topic the user names *is* the requested topic verbatim — record it as given (`curl
--basic`), do not reword, expand or prettify it, and do not invent a topic of your
own.

Then propose **three** themes from the palette below and let the user choose. Do not
pick one yourself and start writing. Each proposal is one or two lines: the theme,
and how that topic would play out under it — the same option reads completely
differently as a migration, a pentest finding or an onboarding conversation. Make the
three genuinely different from each other rather than three shades of "it broke";
varying the angle (first day versus tenth year, who caused it versus who found it) is
a legitimate way to make them differ.

Write only after the user picks one. Record the theme they picked with `add -t` (or
`retheme`), and name it in the story's `*Theme:*` line, so the site can show it next
to the topic.

### Incident and failure

- Production outage: the symptom, the wrong first hypothesis, the actual cause.
- Slow burn: degradation nobody noticed until a threshold was crossed.
- The one-character bug: a copied-and-pasted command that was subtly wrong.
- Cascading failure: a small dependency taking down something far away from it.
- Heisenbug: the problem that disappears while you are watching it.
- Failed rollback: the escape hatch that had never been tested.
- Post-incident review: what the timeline actually shows versus what people remember.

### Security

- Attack suspicion: an anomaly that may or may not be an intrusion, and the triage.
- Incident response: containment, evidence preservation, the call on when to pull the plug.
- Red team: stealth, persistence, lateral movement — from the operator's side.
- Blue team and detection engineering: writing the rule, then finding its blind spot.
- Pentest engagement: the finding, the writeup, and the "but it isn't exposed" reply.
- Hardening and least privilege: removing access without removing the ability to work.
- Secrets handling: the credential found in a place it should never have been.
- Supply chain: a dependency, image, or package that was not what it claimed to be.
- Isolation boundaries: containers, namespaces, and assumptions about what is "internal".

### Operations and change

- Migration: moving a service and discovering what was undocumented about it.
- Upgrade: a version bump with a behaviour change nobody read the changelog for.
- Deprecation: retiring something still in use by someone who never answered the email.
- Capacity and scaling: running out of a resource nobody was graphing.
- Performance investigation: where the time actually goes.
- Configuration drift: the host that was special and nobody knew why.
- Backup and restore: the restore drill and what it revealed.
- Disaster recovery and failover: the plan meeting reality.
- Cost: the bill that explains an architectural decision after the fact.

### Tools and craft

- Debugging with whatever is available: a stripped-down image, no usual toolbox.
- Reading the source or the manual to settle a question that memory got wrong.
- Automation: the script that saved hours, and the script that caused an outage.
- Observability: adding the signal that would have caught it, after it wasn't caught.
- Portability: the same command behaving differently on another OS or platform.
- Legacy archaeology: understanding a system whose authors are long gone.
- Testing in staging: why staging did not reproduce it.

### People and process

- On-call: the handover, the pager, the night that shaped a policy.
- Onboarding and mentoring: explaining a subtlety to someone encountering it first time.
- Communication under pressure: what to tell stakeholders while still diagnosing.
- Pushback: saying no to a change, or being overruled and documenting it.
- Compliance and audit: proving a control works, not just asserting it.
- Vendor and support: escalation, and the limits of someone else's runbook.
- Documentation: the runbook rewrite, and what makes a command copy-pasteable.
- Blameless culture: how the same incident reads with and without blame.

### Angle, not topic

Any theme above can be told from a different vantage point, which changes the story
more than the subject does: first day versus tenth year, the person who caused it
versus the person who found it, real time versus reconstructed afterwards, or the
same event told by the sysadmin and by the user who filed the ticket.

## src/ — reference sources

`src/` holds the unpacked upstream sources of the packages the stories talk about,
each as the Ubuntu source package plus its extracted tree (for example `curl` 8.5.0).
This is not an inventory: `ls src/` is the source of truth, and the list is not
meant to be kept up to date here. Whenever you need to check something in a package
that isn't there yet — including packages the story only touches in passing, not just
the one named in the topic — fetch it with `apt source <package>` from inside `src/`
at that moment, rather than falling back on memory. The directory is gitignored.

Use it to make the stories **true**: check actual option names, error messages, exit
codes, defaults and behaviour against the real documentation and source code rather
than from memory. When a story asserts something concrete about a tool, grep `src/`
for it first.

Treat `src/` as read-only reference material — never edit it, and don't let its files
show up in the story collection.

## aux/ — hands off

`aux/` is the user's own working area. Do not read, write, move, or reference anything
in it unless the user explicitly asks in that moment.

**Exception — pushing.** `aux/github.token` holds the GitHub PAT for this repo's
`origin`. Use it to authenticate pushes without asking each time. Feed it through a
one-off credential helper so the token never lands in argv, the remote URL, or
`.git/config`:

```bash
git -c credential.helper='!f() { echo username=x-access-token; echo password="$(tr -d "\n\r " < aux/github.token)"; }; f' push origin main
```

Never commit the token, echo it, or include it in command output.
