# Writing style

The house rules for the prose of the stories in `stories/`. `CLAUDE.md` is the rest
of the project: the topic-and-title rule, the themes, the `src/` checking, and the
rule against reading the existing stories. Read this file before writing or revising
a story.

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

  The same goes for the folksy tag that personifies software — "one argument per
  line, the way the init script wants them". An init script does not want
  anything, and the clause only re-asserts that the format is mandatory, which the
  first half already said.

  Fix these by deleting them, not by writing a better one. A replacement aside,
  chosen more carefully, is the next tic.

  Attitude is also where unchecked facts hide. A throwaway clause does not feel
  like an assertion, so it does not get grepped for the way the error message and
  the exit code do — and that init script turned out to be a systemd unit, and the
  format belonged to the launcher's config file rather than to either. Anything
  named in an aside gets verified against `src/` on the same terms as the rest.

  When one of these comes out, cut it and stop. The repair is not a true fact in
  the same slot: "the way the init script wants them" became "Systemd started them
  by instance name, `anytun@pop-ams`", which is correct, checked, and does nothing
  — no later scene touches the service manager, the instance name is visible in the
  config path named eight words earlier, and the paragraph now ends on its dullest
  noun. That sentence is there to spend the research that went into it. Verifying
  something does not entitle it to a place; the sentence before it was already
  finished.

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
