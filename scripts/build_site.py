#!/usr/bin/env python3
"""Render the story collection into a static site for GitHub Pages.

The requested topic, the theme and the summary come from stories.db; the story title and the prose
come from stories/{id}.md. Reading order is the numeric id; the index lists the newest
(highest id) first, PER_PAGE stories to a page. Topic and title stay separate: the index
shows the story title as the link, and the topic followed by the theme as its subtitle,
followed by the summary.
"""

import argparse
import html
import json
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
# Absolute URLs are needed for canonical links, Open Graph and the sitemap.
BASE_URL = "https://xavierdpt.github.io/lifeofasysadmin/"
AUTHOR = {"@type": "Person", "name": "Xavier Dupont", "url": "https://xavierdpt.github.io/"}
ISSUES_URL = "https://github.com/xavierdpt/lifeofasysadmin/issues"
# Stories per index page. Page 1 is index.html; page n is page/n.html.
PER_PAGE = 10
# Shown in the footer of every page, under that page's own footer line.
NOTE = (
    "These stories are written by an AI, checked against the actual source code, and "
    "read by a human before publication. Sorry for the occasional poor writing style "
    '\u2014 <a href="%s">feedback is welcome</a>.' % ISSUES_URL
)

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>%(title)s</title>
<meta name="description" content="%(description)s">
<link rel="canonical" href="%(url)s">
<meta property="og:type" content="%(og_type)s">
<meta property="og:site_name" content="%(site_title)s">
<meta property="og:title" content="%(og_title)s">
<meta property="og:description" content="%(description)s">
<meta property="og:url" content="%(url)s">
<script type="application/ld+json">%(jsonld)s</script>
<link rel="stylesheet" href="%(root)sstyle.css">
<script data-goatcounter="https://xavierdpt.goatcounter.com/count"
        async src="//gc.zgo.at/count.js"></script>
</head>
<body>
<header class="site">
  <a class="brand" href="%(root)s">%(site_title)s</a>
</header>
<main>
%(body)s
</main>
<footer>
  <p>%(footer)s</p>
  <p class="note">%(note)s</p>
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
  --card-bg: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #16171a;
    --fg: #e6e4df;
    --muted: #9b978c;
    --rule: #2e3035;
    --accent: #e4926f;
    --code-bg: #212327;
    --card-bg: #1c1e22;
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
ol.stories li {
  border: 1px solid var(--rule);
  border-radius: 8px;
  background: var(--card-bg);
  padding: 1em 1.1em;
  margin-bottom: 1em;
}
ol.stories a { font-size: 1.15rem; text-decoration: none; font-weight: 600; }
ol.stories a:hover { text-decoration: underline; }
.meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: baseline;
  gap: .3em 1.5em;
  margin-top: .55em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .8rem;
}
.meta .topic { color: var(--muted); }
.meta .theme { color: var(--accent); margin-left: auto; }
ol.stories p.summary { margin: .7em 0 0; font-size: .95rem; }
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
footer p.note { margin-top: .8em; font-size: .75rem; }
.nav { margin-top: 3em; font-size: .9rem; }
nav.pager {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: baseline;
  gap: .4em .9em;
  margin-top: 2em;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: .85rem;
  color: var(--muted);
}
nav.pager a { text-decoration: none; }
nav.pager a:hover { text-decoration: underline; }
nav.pager .current { color: var(--fg); font-weight: 600; }
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


def strip_theme(text):
    """Drop the `*Theme: ...*` line; the page prints the theme from the index."""
    return re.sub(r"\A\s*\*Theme:[^\n]*\*[ \t]*\n", "", text, count=1)


def subtitle(topic, theme):
    """The index and story subtitle: the requested topic, then the theme it was written under."""
    out = html.escape(topic)
    if theme:
        out += ' <span class="theme">%s</span>' % html.escape(theme)
    return out


def inline_markdown(md, text):
    """Render one paragraph of markdown without its wrapping <p>."""
    md.reset()
    out = md.convert(text).strip()
    return re.sub(r"\A<p>(.*)</p>\Z", r"\1", out, flags=re.S)


def plain_text(md, text):
    """Inline markdown flattened to plain text, for meta descriptions."""
    out = re.sub(r"<[^>]+>", "", inline_markdown(md, text))
    return " ".join(html.unescape(out).split())


def render(title, body, root, footer, url, description, og_type, jsonld, head_title=None):
    """`title` is the page's own name; `head_title` is the <title>, if it differs."""
    return PAGE % {
        "title": html.escape(head_title or title),
        "og_title": html.escape(title),
        "site_title": html.escape(SITE_TITLE),
        "description": html.escape(description),
        "url": html.escape(url),
        "og_type": og_type,
        # "</" would end the <script> element early.
        "jsonld": json.dumps(dict(jsonld, **{"@context": "https://schema.org"}), ensure_ascii=False).replace("</", "<\\/"),
        "body": body,
        "root": root,
        "footer": html.escape(footer),
        "note": NOTE,
    }


def page_path(n):
    """Where index page n lives, relative to the site root."""
    return "index.html" if n == 1 else "page/%d.html" % n


def page_url(n):
    return BASE_URL if n == 1 else BASE_URL + page_path(n)


def pager(n, pages, root):
    """Newer / numbered / older links between index pages; empty for a single page."""
    if pages == 1:
        return ""

    def href(k):
        return root if k == 1 else root + page_path(k)

    parts = []
    if n > 1:
        parts.append('<a href="%s" rel="prev">&larr; Newer</a>' % href(n - 1))
    for k in range(1, pages + 1):
        if k == n:
            parts.append('<span class="current" aria-current="page">%d</span>' % k)
        else:
            parts.append('<a href="%s">%d</a>' % (href(k), k))
    if n < pages:
        parts.append('<a href="%s" rel="next">Older &rarr;</a>' % href(n + 1))
    return '<nav class="pager" aria-label="Pages">\n  %s\n</nav>\n' % "\n  ".join(parts)


def sitemap(urls):
    items = "\n".join("  <url><loc>%s</loc></url>" % html.escape(u) for u in urls)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n%s\n</urlset>\n' % items
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--out", default=os.path.join(ROOT, "_site"))
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT id, topic, theme, summary FROM stories ORDER BY CAST(id AS INTEGER)"
    ).fetchall()
    conn.close()

    out = args.out
    if os.path.isdir(out):
        shutil.rmtree(out)
    os.makedirs(os.path.join(out, "stories"))
    os.makedirs(os.path.join(out, "page"))

    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "sane_lists"])

    entries = []
    missing = []
    for story_id, topic, theme, summary in rows:
        path = os.path.join(STORIES_DIR, story_id + ".md")
        if not os.path.exists(path):
            missing.append(story_id)
            continue
        with open(path, encoding="utf-8") as f:
            text = f.read()
        title = story_title(text, topic)
        md.reset()
        body = md.convert(strip_theme(strip_title(text)))
        page = "<article>\n<h1>%s</h1>\n<p class=\"slug\">%s</p>\n%s\n</article>\n" % (
            html.escape(title),
            subtitle(topic, theme),
            body,
        )
        page += '<p class="nav"><a href="../">&larr; All stories</a></p>\n'
        url = BASE_URL + "stories/%s.html" % story_id
        description = plain_text(md, summary) if summary else "%s: %s." % (SITE_TITLE, topic)
        jsonld = {
            "@type": "Article",
            "headline": title,
            "description": description,
            "url": url,
            "author": AUTHOR,
            "isPartOf": {"@type": "WebSite", "name": SITE_TITLE, "url": BASE_URL},
        }
        with open(os.path.join(out, "stories", story_id + ".html"), "w", encoding="utf-8") as f:
            f.write(render(
                title, page, "../", "Built from stories/%s.md" % story_id,
                url, description, "article", jsonld,
                head_title="%s – %s" % (title, SITE_TITLE),
            ))
        entries.append((story_id, topic, theme, title, summary))

    # Newest first on the index; the story ids themselves keep reading order.
    newest = entries[::-1]
    pages = max(1, -(-len(newest) // PER_PAGE))
    for n in range(1, pages + 1):
        root = "./" if n == 1 else "../"
        items = "\n".join(
            '  <li><a href="%sstories/%s.html">%s</a>\n'
            '    <span class="meta"><span class="topic">%s</span>'
            '<span class="theme">%s</span></span>%s</li>'
            % (
                root,
                html.escape(story_id),
                html.escape(title),
                html.escape(topic),
                html.escape(theme),
                '\n    <p class="summary">%s</p>' % inline_markdown(md, summary) if summary else "",
            )
            for story_id, topic, theme, title, summary in newest[(n - 1) * PER_PAGE:n * PER_PAGE]
        )
        index = (
            "<h1>%s</h1>\n<p class=\"tagline\">%s</p>\n<ol class=\"stories\">\n%s\n</ol>\n%s"
            % (html.escape(SITE_TITLE), html.escape(SITE_TAGLINE), items, pager(n, pages, root))
        )
        with open(os.path.join(out, page_path(n)), "w", encoding="utf-8") as f:
            f.write(render(
                SITE_TITLE, index, root, "%d stories." % len(entries),
                page_url(n), SITE_TAGLINE, "website",
                {"@type": "WebSite", "name": SITE_TITLE, "description": SITE_TAGLINE,
                 "url": BASE_URL, "author": AUTHOR},
                head_title=SITE_TITLE if n == 1 else "Page %d – %s" % (n, SITE_TITLE),
            ))

    # The site root's robots.txt points crawlers here; a project site cannot serve its own.
    with open(os.path.join(out, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap(
            [page_url(n) for n in range(1, pages + 1)]
            + [BASE_URL + "stories/%s.html" % e[0] for e in entries]
        ))

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
