# lifeofsysadmin

A collection of illustrative scenario stories about the life of a system administrator.

## Structure

```
stories.db          sqlite index: one row per story (id, title)
stories/{id}.md     the story content, one file per story
scripts/story.py    CLI to create and maintain stories
src/                upstream package sources, for fact-checking stories (read-only)
aux/                off-limits — do not read, modify, or reference
```

### The two titles

Each story has **two** titles, and they are deliberately different:

- **Technical title** — the `title` column in `stories.db`. Structured for sorting and
  quick bulk edits (e.g. `020-backup-restore-drill`). This is the title used when
  listing or ordering stories.
- **Story title** — the `# ` heading at the top of `stories/{id}.md`. Descriptive and
  written for a reader (e.g. `The Backup Nobody Had Ever Restored`).

They are not expected to match. Never "fix" one to match the other.

The `id` is the link between them and is also the filename stem. Because the content
lives in a file named after the id, either title can be rewritten without touching the
other.

### Database schema

```sql
CREATE TABLE stories (
    id    TEXT PRIMARY KEY,
    title TEXT NOT NULL      -- technical title
);
```

There is no `sqlite3` CLI on this machine; use `scripts/story.py` (Python `sqlite3`)
for all database access.

## Commands

```bash
python3 scripts/story.py init                        # create stories.db and stories/
python3 scripts/story.py add "030-the-cert-expiry" \
    -s "The Certificate That Expired on a Sunday"    # new row + stories/{id}.md stub
python3 scripts/story.py list                        # all stories, sorted by technical title
python3 scripts/story.py retitle <id> "<new technical title>"
python3 scripts/story.py rename <id> <new-id>        # renames the row and the .md file
python3 scripts/story.py remove <id>                 # drops the row, keeps the file
python3 scripts/story.py check                       # index and files agree?
```

`add` derives the id from the technical title (slugified, de-duplicated with a numeric
suffix); pass `--id` to set it explicitly, and `-e` to open `$EDITOR` on the new file.
Without `-s`, the story title defaults to the technical title.

## Conventions

- Technical titles start with a zero-padded numeric prefix (`010-`, `020-`, …) so the
  sorted listing reflects the intended reading order; leave gaps for insertions.
- Each `stories/{id}.md` begins with a single `# ` heading — the story title.
- Add stories with `scripts/story.py add` rather than creating files by hand, so the
  index and the files never drift apart. Run `check` if in doubt.

### Answer the "why was it built that way" question

A story that only shows *what* broke reads like a bug report. Somewhere before the
diagnosis, say why the thing being debugged was set up the way it was: who chose
it, what they were buying, and what the choice cost.

This applies to any topic, not just the one a given story happens to use. Whenever
a story leans on a non-obvious option, flag, protocol, topology or policy, it owes
the reader a short section covering:

- **The motivation.** The constraint that made the ordinary choice awkward — a
  read-only filesystem, a shared namespace, an audit requirement, a bill.
- **What it buys.** The specific problems it removes, named concretely rather than
  as "simplicity" or "performance".
- **The tradeoff.** What is given up, including the security or operability
  footnote that only bites later.
- **The bill, when it comes due.** Tie the tradeoff to the incident, so the context
  is doing work in the plot rather than sitting there as background.

Ground each claim the same way as the rest of the story: the man page, the
changelog, the source in `src/`. The motivation is as checkable as the error
message, and inventing a plausible-sounding rationale is the same error as
inventing a plausible-sounding flag.

## Story themes

A working palette of scenarios for the collection. Not a checklist — a menu to pick
from so the stories stay varied instead of all being "prod broke at 3am".

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
