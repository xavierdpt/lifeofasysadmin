# lifeofsysadmin

A collection of illustrative scenario stories about the life of a system administrator.

## Structure

```
stories.db          sqlite index: one row per story (numeric id, technical title)
stories/{id}.md     the story content, one file per story (1.md, 2.md, … — do not read)
scripts/story.py    CLI to create and maintain stories
src/                upstream package sources, for fact-checking stories (read-only)
aux/                off-limits — do not read, modify, or reference
```

### The two titles

Each story has **two** titles, and they are deliberately different:

- **Technical title** — the `title` column in `stories.db`. It names the *topic* the
  story is about, in the form the topic is actually written: `curl --basic`,
  `curl --aws-sigv4`. This is the title `list` shows, and the site renders it as the
  subtitle under each entry in the index.
- **Story title** — the `# ` heading at the top of `stories/{id}.md`. Descriptive and
  written for a reader (e.g. `The Backup Nobody Had Ever Restored`).

They are not expected to match. Never "fix" one to match the other.

The `id` is the link between them and is also the filename stem. It is a plain number
— `1`, `2`, `3` — carrying no meaning beyond identity and reading order. Because the
content lives in a file named after the id, either title can be rewritten without
touching the other.

### Database schema

```sql
CREATE TABLE stories (
    id    TEXT PRIMARY KEY, -- a plain number, as text: "1", "2", ...
    title TEXT NOT NULL      -- technical title: the topic, e.g. "curl --basic"
);
```

There is no `sqlite3` CLI on this machine; use `scripts/story.py` (Python `sqlite3`)
for all database access.

## Commands

```bash
python3 scripts/story.py init                        # create stories.db and stories/
python3 scripts/story.py add "curl --cert" \
    -s "The Certificate That Expired on a Sunday"    # new row + stories/{id}.md stub
python3 scripts/story.py list                        # all stories, in reading order
python3 scripts/story.py retitle <id> "<new technical title>"
python3 scripts/story.py rename <id> <new-id>        # renumbers the row and the .md file
python3 scripts/story.py remove <id>                 # drops the row, keeps the file
python3 scripts/story.py check                       # index and files agree?
```

`add` assigns the next unused number as the id; pass `--id` to set it explicitly, and
`-e` to open `$EDITOR` on the new file. Without `-s`, the story title defaults to the
technical title.

## Conventions

- Ids are plain numbers (`1`, `2`, …) and the files are `stories/1.md`, `stories/2.md`,
  … — no slugs, no prefixes. The numeric id is also the reading order, so a story added
  later reads last unless it is renumbered with `rename`.
- The technical title names the topic as it is written, e.g. `curl --basic`. It is not a
  sort key and takes no numeric prefix.
- Each `stories/{id}.md` begins with a single `# ` heading — the story title.
- Add stories with `scripts/story.py add` rather than creating files by hand, so the
  index and the files never drift apart. Run `check` if in doubt.

### Never read the existing stories

**Do not open, read, `cat`, `grep`, `head`, diff, or summarise any file under
`stories/`.** Not to match the house style, not to check the conventions, not to see
which themes are taken, not "just the first few lines", and not as a side effect of a
wildcard like `cat stories/*.md`. This holds even when writing a new story, which is
exactly when the temptation is strongest.

Everything you need to write a story is in this file: the two-title rule, the `# `
heading, the "show it in use and say why it was built that way" requirement, and the
themes palette. If something about the expected shape of a story is unclear, ask —
do not go and look at a neighbouring story to infer it.

The reason is voice. Stories written by someone who has just read the previous one
converge: the same rhythm, the same section headings, the same closing move, the same
narrator. The collection is meant to read as a set of separate accounts, and the only
reliable way to keep them separate is to write each one without the others in context.
Repetition that creeps in this way is invisible from inside a single story and obvious
when the collection is read end to end.

Two narrow exceptions, both of which are bookkeeping rather than reading:

- `scripts/story.py list` and `scripts/story.py check` are always fine. They report
  ids and technical titles, never content.
- If the user explicitly asks you to read, edit, review or compare a specific story in
  that moment, do it. The instruction is about reaching for them unprompted.

To choose a technical title, and to see which ids are taken, use `list`. To propose
themes, use the palette below and the titles `list` gives you — not the story text.

### Show the thing in use, and answer "why was it built that way"

A story that only shows *what* broke reads like a bug report. Somewhere before the
diagnosis, say why the thing being debugged was set up the way it was: who chose it,
what they were buying, and what the choice cost them later.

The story must also put the thing to work. Show a concrete scenario in which someone
actually uses it — the command they run, the config they write, the situation that
called for it — not just an explanation of what it does. The reader should come away
knowing both what it is for and what using it looks like.

That, alongside the theme the user picked from the palette below, is the whole
requirement.
There is no prescribed shape for it — no required section, heading, bullet list or
running order. Some stories will want a paragraph of history, some a line of
dialogue, some a single aside in the middle of the diagnosis. Work out each time
what that story needs, rather than reaching for the same structure or the same
vocabulary as the last one.

It applies to whatever the story leans on: a non-obvious option, flag, protocol,
topology or policy. If the reader would ask "why was it like that?", answer it.

Ground the answer the same way as the rest of the story: the man page, the
changelog, the source in `src/`. The motivation is as checkable as the error
message, and inventing a plausible-sounding rationale is the same error as
inventing a plausible-sounding flag.

## Story themes

A working palette of scenarios for the collection. Not a checklist — a menu to pick
from so the stories stay varied instead of all being "prod broke at 3am".

### Propose three themes before writing

The division of labour is fixed: **the user supplies the topic, you supply the
themes.**

The topic the user names *is* the technical title — record it as given (`curl
--basic`), do not reword, expand or prettify it, and do not invent a topic of your
own.

Then propose **three** themes from the palette below and let the user choose. Do not
pick one yourself and start writing. Each proposal is one or two lines: the theme,
and how that topic would play out under it — the same option reads completely
differently as a migration, a pentest finding or an onboarding conversation. Make the
three genuinely different from each other rather than three shades of "it broke";
varying the angle (first day versus tenth year, who caused it versus who found it) is
a legitimate way to make them differ.

Write only after the user picks one.

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

`src/` holds the unpacked upstream sources of the packages the stories talk about
(currently `curl` 8.5.0, as the Ubuntu source package plus its extracted tree). More
packages will be added there over time.

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
