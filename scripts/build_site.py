#!/usr/bin/env python3
"""Render the story collection into a static site for GitHub Pages.

The requested topic and the theme come from stories.db; the story title and the prose
come from stories/{id}.md. Reading order is the numeric id. Topic and title stay
separate: the index shows the story title as the link, and the topic followed by the
theme as its subtitle.
"""

import argparse
import html
import os
import re
import sqlite3
import shutil
import sys

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "stories.db")
STORIES_DIR = os.path.join(ROOT, "stories")

SITE_TITLE = "Life of a Sysadmin"
SITE_TAGLINE = "Scenario stories from the other side of the pager."

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<link rel="stylesheet" href="%(root)sstyle.css">
</head>
<body>
<header class="site">
  <a class="brand" href="%(root)sindex.html">%(site_title)s</a>
</header>
<main>
%(body)s
</main>
<footer>
  <p>%(footer)s</p>
</footer>
</body>
</html>
"""

STYLE = """:root {
  --bg: #fbfaf7;
  --fg: #1d1c1a;
  --muted: #6a675f;
  --rule: #e2ded4;
  --accent: #8a3324;
  --code-bg: #f1eee6;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16171a;
    --fg: #e6e4df;
    --muted: #9b978c;
    --rule: #2e3035;
    --accent: #e4926f;
    --code-bg: #212327;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: var(--bg);
  color: var(--fg);
  font: 17px/1.65 Georgia, "Iowan Old Style", "Times New Roman", serif;
  -webkit-text-size-adjust: 100%;
}
header.site {
  border-bottom: 1px solid var(--rule);
  padding: 18px 16px;
}
header.site .brand {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: 14px;
  letter-spacing: .08em;
  text-transform: uppercase;
  color: var(--muted);
  text-decoration: none;
}
header.site .brand:hover { color: var(--accent); }
main {
  max-width: 42rem;
  margin: 0 auto;
  padding: 40px 16px 64px;
}
h1 { font-size: 2rem; line-height: 1.2; margin: 0 0 .4em; }
h2 { font-size: 1.25rem; margin-top: 2.2em; border-bottom: 1px solid var(--rule); padding-bottom: .2em; }
h3 { font-size: 1.05rem; margin-top: 1.8em; }
a { color: var(--accent); }
p.tagline { color: var(--muted); font-style: italic; margin-top: 0; }
ol.stories { list-style: none; padding: 0; margin: 2.5em 0 0; }
ol.stories li { border-top: 1px solid var(--rule); padding: 1.1em 0; }
ol.stories a { font-size: 1.15rem; text-decoration: none; font-weight: 600; }
ol.stories a:hover { text-decoration: underline; }
.slug {
  display: block;
  margin-top: .3em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .8rem;
  color: var(--muted);
}
.slug .theme { color: var(--accent); }
.slug .theme::before { content: " \u00b7 "; color: var(--muted); }
pre, code { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }
code { background: var(--code-bg); padding: .1em .35em; border-radius: 3px; font-size: .85em; }
pre {
  background: var(--code-bg);
  padding: 14px 16px;
  border-radius: 6px;
  overflow-x: auto;
  font-size: .82rem;
  line-height: 1.5;
}
pre code { background: none; padding: 0; font-size: inherit; }
blockquote {
  margin: 1.4em 0;
  padding: .2em 0 .2em 1.1em;
  border-left: 3px solid var(--rule);
  color: var(--muted);
}
table { border-collapse: collapse; width: 100%; font-size: .9rem; }
th, td { border: 1px solid var(--rule); padding: .4em .6em; text-align: left; }
hr { border: 0; border-top: 1px solid var(--rule); margin: 2.5em 0; }
footer {
  border-top: 1px solid var(--rule);
  padding: 20px 16px 48px;
  text-align: center;
}
footer p {
  max-width: 42rem;
  margin: 0 auto;
  font-size: .8rem;
  color: var(--muted);
}
.nav { margin-top: 3em; font-size: .9rem; }
"""


def story_title(text, fallback):
    """The story title is the first `# ` heading of the file."""
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def strip_title(text):
    """Drop the H1 so it is not rendered twice."""
    return re.sub(r"\A\s*#\s+.*\n", "", text, count=1)


def subtitle(topic, theme):
    """The index and story subtitle: the requested topic, then the theme it was written under."""
    out = html.escape(topic)
    if theme:
        out += ' <span class="theme">%s</span>' % html.escape(theme)
    return out


def render(title, body, root, footer):
    return PAGE % {
        "title": html.escape(title),
        "site_title": html.escape(SITE_TITLE),
        "body": body,
        "root": root,
        "footer": html.escape(footer),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", default=os.path.join(ROOT, "_site"))
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, topic, theme FROM stories ORDER BY CAST(id AS INTEGER)"
    ).fetchall()
    conn.close()

    out = args.out
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "stories"))

    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists"])

    entries = []
    missing = []
    for story_id, topic, theme in rows:
        path = os.path.join(STORIES_DIR, story_id + ".md")
        if not os.path.exists(path):
            missing.append(story_id)
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        title = story_title(text, topic)
        md.reset()
        body = md.convert(strip_title(text))
        page = "<article>\n<h1>%s</h1>\n<p class=\"slug\">%s</p>\n%s\n</article>\n" % (
            html.escape(title),
            subtitle(topic, theme),
            body,
        )
        page += '<p class="nav"><a href="../index.html">&larr; All stories</a></p>\n'
        with open(os.path.join(out, "stories", story_id + ".html"), "w", encoding="utf-8") as f:
            f.write(render(title, page, "../", "Built from stories/%s.md" % story_id))
        entries.append((story_id, topic, theme, title))

    items = "\n".join(
        '  <li><a href="stories/%s.html">%s</a><span class="slug">%s</span></li>'
        % (html.escape(story_id), html.escape(title), subtitle(topic, theme))
        for story_id, topic, theme, title in entries
    )
    index = (
        "<h1>%s</h1>\n<p class=\"tagline\">%s</p>\n<ol class=\"stories\">\n%s\n</ol>\n"
        % (html.escape(SITE_TITLE), html.escape(SITE_TAGLINE), items)
    )
    with open(os.path.join(out, "index.html"), "w", encoding="utf-8") as f:
        f.write(render(SITE_TITLE, index, "", "%d stories, in reading order." % len(entries)))

    with open(os.path.join(out, "style.css"), "w", encoding="utf-8") as f:
        f.write(STYLE)

    # Pages otherwise hands the tree to Jekyll, which skips files it does not like.
    open(os.path.join(out, ".nojekyll"), "w").close()

    print("built %d stories into %s" % (len(entries), out))
    if missing:
        print("warning: indexed but no file: %s" % ", ".join(missing), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
