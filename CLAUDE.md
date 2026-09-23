# lifeofsysadmin

A collection of illustrative scenario stories about the life of a system administrator.

## Structure

```
stories.db             sqlite index: one row per story (numeric id, requested topic
                       verbatim, theme, summary)
stories/{id}.md        the story content, one file per story (1.md, 2.md, … — do not read)
scripts/story.py       CLI to create and maintain stories
scripts/build_site.py  renders the collection into the GitHub Pages site
themes.txt             the palette: one line per subtheme, `[theme] subtheme: gloss`
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

When the user writes the topic as `[x] y`, it means **the program `y` shipped by the
binary package `x`** — `[akonadi-backend-mysql] mysqld-akonadi` is the `mysqld-akonadi`
program from the `akonadi-backend-mysql` package. The bracket is there because the
program name alone does not say where it comes from: it disambiguates programs that
several packages could plausibly ship, and points at which package to `apt source` when
checking the story against `src/`. Record the whole thing, brackets included, as the
requested topic verbatim; the story is about `y`, and `x` is how you find it.

When the user gives the package alone, as `[x]` with no program after it, the choice is
left to you: pick whichever program that package ships that the story wants, or write
about the package itself if that serves better. Don't ask which one. The requested topic
verbatim is still what the user typed — `[alsa-utils]`, bare brackets and nothing after
them — whichever program the story ends up using.

The **summary** — the `summary` column — is a hook, not an abstract. It sets up the
story's situation (who, where, what just went wrong or needs doing, the stakes) so a
reader wants to open it, and stops there. It does not explain the topic and does not
reveal the diagnosis, the cause, the fix or the ending. The site renders it (as inline
markdown) under the subtitle on the index. Write it once the story is finished, with
`summarize`, and keep it to roughly 40–60 words. The title and writing-style rules
apply to it too.

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
    theme TEXT NOT NULL DEFAULT '',  -- the palette theme, e.g. "Migration"
    summary TEXT NOT NULL DEFAULT '' -- one-paragraph summary shown on the site index
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
python3 scripts/story.py summarize <id> "<summary>"  # one paragraph, inline markdown ok
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
  theme goes in the `theme` column, spelled as `themes.txt` spells it.
- Don't build the story title on a negation or an absence: "nobody", "never",
  "no X can", "does not", "nothing but", "ignores". Stories often turn on something
  missing, and "the X that didn't Y" is the easy way to name that reveal, so the
  titles converged on it. The index lists them all together, and there it reads as a
  tic. That is the whole rule — beyond it, title the story however it wants to be
  titled.
- Add stories with `scripts/story.py add` rather than creating files by hand, so the
  index and the files never drift apart. Run `check` if in doubt.
- In commit messages, refer to a story by its id and requested topic verbatim
  (`Add story 6: acpid`, `Story 2: tighten the plugin section`), never by its title
  or a paraphrase of it. Commit subjects show up in `git log` and in the git status
  snapshot at the start of every session, so titles there put the earlier titles in
  context while the next one is being written. Older commits still carry titles; do
  not mine `git log` for them.

### Writing style

- Don't close a description with an exclusivity flourish: "and nothing else",
  "nothing more", "that's all it does", "no X, no Y, just Z". It adds emphasis
  without adding information, and it had become a verbal tic across the stories. Say
  what the thing does. If what it *doesn't* do is the point (the kernel reports the
  power button but doesn't shut down), name that specific thing in its own sentence.

- Don't call anything "load-bearing". It isn't how the thing is described in IT, and
  as a metaphor it says only "this matters" while sounding like it explained why. Say
  what depends on it and what breaks when it goes: which process reads the file, which
  startup the symlink survives, what the next login does without it.

- Reserve "broke it" (and "broken") for things that are actually broken: a service
  that won't start, a file that won't parse, a permission that stops the job running.
  Don't use it for a theory that turned out wrong, a mystery that finally yielded or a
  habit someone dropped — say what actually happened to the thing.

- Don't end on a summarising epigram. The tempting last sentence counts up what the
  story contained and states its moral — "three names, one binary, and the only one
  that mattered was the one nobody had typed" — and it lands as a punchline that tells
  the reader what they just read. Finish on something concrete instead and let the
  reader draw the conclusion: the last command run, the line of output, how the ticket
  was closed, what the person did next.

- Don't hang a wry aside off a fact. The shape is a concrete detail, a comma, and a
  relative clause that reframes it knowingly — "the flow records came in on Mondays,
  and Marit read them on Mondays, which was the only part of the arrangement anyone
  had ever written down". It is texture added for its own sake: it invokes a history
  ("the arrangement") the story does not have and never uses, its wit is built on an
  absence, and the knowingness is generic enough to fit any team anywhere. The
  variants are all the same move — `which was the only X anyone had ever Y`, `not
  that anyone had asked`, `for reasons nobody could reconstruct`. Stop at the fact.
  If the history behind it matters, the story can go and find out what it was; if it
  doesn't, the aside is a promise the story never pays.

  Fix these by deleting them, not by writing a better one. A replacement aside,
  chosen more carefully, is the next tic.

- Don't announce the next move before the scene makes it. "She did not know what
  2342 was. That was the first thing to fix." — the verdict sentence says what the
  story is about to do, and then the section heading says it again, and then the
  scene does it. One is enough, and it should be the scene. The tell is a short flat
  statement followed by a short verdict, alone in its own paragraph at a section
  seam: a cadence borrowed to make a beat land, with no second fact in it. The verb
  usually gives it away too, reaching for a brisk register and mis-picking — nobody
  *fixes* not knowing what a port is, they go and find out. Cut the verdict, keep
  the fact, and let the next paragraph start.

- Don't label a section with its function. "What the port is for" announces that an
  explanation is coming, which turns a scene — someone asking, someone answering on
  a call — into a lecture before it has said anything, and hands over the shape of
  the answer ahead of the person who finds it. The test is whether the heading could
  be pasted into any other story in the collection: "What the port is for", "The
  investigation", "The fix", "Background" all could, so they name nothing and only
  mark a slot. A set of them is worse than one, because setup / explanation /
  resolution is the generic shape of a write-up rather than anything the incident
  had, and headings are where that shape becomes visible.

  A story is usually better off with fewer headings than it first wants, or none: a
  blank line carries a scene break. Where one stays, it should name something only
  this story has — the port number, a line of the output, the word someone
  remembered wrong.

### Never read the existing stories

**Do not open, read, `cat`, `grep`, `head`, diff, or summarise any file under
`stories/`.** Not to match the house style, not to check the conventions, not to see
which themes are taken, not "just the first few lines", and not as a side effect of a
wildcard like `cat stories/*.md`. This holds even when writing a new story, which is
exactly when the temptation is strongest.

Everything you need to write a story is in this file: the topic-and-title rule, the
`# ` heading and `*Theme:*` line, the "show the feature in use and say why it exists"
requirement, and the themes in `themes.txt`. If something about the expected shape of
a story is unclear, ask — do not go and look at a neighbouring story to infer it.

The reason is voice. Stories written by someone who has just read the previous one
converge: the same rhythm, the same section headings, the same closing move, the same
narrator. The collection is meant to read as a set of separate accounts, and the only
reliable way to keep them separate is to write each one without the others in context.
Repetition that creeps in this way is invisible from inside a single story and obvious
when the collection is read end to end.

Two narrow exceptions, both of which are bookkeeping rather than reading:

- `scripts/story.py list` and `scripts/story.py check` are always fine. They report
  ids, requested topics verbatim and themes, never content. The `summary` column *is*
  content: `list` does not print it, and ad-hoc `sqlite3` queries should not select it
  (no `SELECT *`) unless you are writing or revising that story's summary.
- If the user explicitly asks you to read, edit, review or compare a specific story in
  that moment, do it. The instruction is about reaching for them unprompted.

To choose a requested topic verbatim, and to see which ids are taken, use `list`. The
themes come out of `themes.txt` at random — never from the story text.

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

That, alongside the theme the user picked from the three drawn from `themes.txt`, is
the whole requirement.
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

The palette of scenarios lives in `themes.txt`, one line per subtheme, in the form
`[theme] subtheme: gloss` — the broad theme in brackets, then the specific subtheme and
a line on what it is. It keeps the stories varied instead of all being "prod broke at
3am".

### Draw three themes before writing

The division of labour is fixed: **the user supplies the topic, `themes.txt` supplies
the themes.**

The topic the user names *is* the requested topic verbatim — record it as given (`curl
--basic`), do not reword, expand or prettify it, and do not invent a topic of your
own. That includes the `[x] y` form: it is written to the `topic` column exactly as
the user typed it, brackets and all.

Then draw three themes at random, **before reading anything in `src/`**:

```bash
sort -R themes.txt | tail -3
```

The order matters. Reading the sources first leaves you with one or two facts about
the topic already in mind — the flag that looked interesting, the error string that
jumped out — and the three pitches then come out as the same material dressed three
ways: the same option, the same output, the same reveal, with a migration, a pentest
and an onboarding wrapped around it. The user is then choosing a costume, not a story.
Draw the themes while you still know nothing but the topic's name, so each one sends
you looking for something different.

With the three themes in hand, go to `src/` once per theme and find that theme its own
material: a different part of the topic's surface — another option, another code path,
another default, another error message, another line of the man page or changelog —
whichever part of the topic that particular theme would actually run into. A migration
meets the compatibility behaviour and the deprecated spelling; a pentest finding meets
what the feature reveals on the wire or in a log; a first day meets the default nobody
set. If two of the three themes lead you to the same fact, keep looking for one of
them: three pitches resting on one detail is the failure this ordering exists to
prevent.

Offer those three and let the user choose. Take the draw as it comes: don't swap in a
theme that suits the topic better, don't re-roll a draw that looks awkward, and don't
pick one yourself and start writing. For each of the three, say in one or two lines how
that topic would play out under it, naming the concrete thing from `src/` that theme
would be built on — the same option reads completely differently as a migration, a
pentest finding or an onboarding conversation, and an unlikely pairing is usually the
interesting one. Varying the angle (first day versus tenth year, who caused it versus
who found it) is part of that work.

Once the user picks, the rest of the checking happens as usual: the chosen theme's
detail is the story's starting point, not its limit, and everything the story asserts
still gets verified against `src/` before it is written down.

Write only after the user picks one. Record the theme they picked with `add -t` (or
`retheme`), and name it in the story's `*Theme:*` line, so the site can show it next
to the topic. What gets recorded is the subtheme — the part between the bracket and the
colon, `Migration`, `Heisenbug` — not the bracketed theme and not the gloss after the
colon.

### Angle, not topic

Any theme in the file can be told from a different vantage point, which changes the
story more than the subject does: first day versus tenth year, the person who caused it
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

Timing: the first visit to `src/` for a new story comes *after* the three themes are
drawn, and is made once per theme, looking for a different part of the topic for each
— see "Draw three themes before writing".

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
