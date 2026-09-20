#!/usr/bin/env python3
"""Manage the story collection: sqlite index (id, topic, theme) + stories/{id}.md.

Ids are plain numbers ("1", "2", ...), assigned sequentially. The requested topic
verbatim names the topic, e.g. "curl --basic"; the theme is the palette entry the
story was written under, e.g. "Migration".
"""

import argparse
import os
import re
import sqlite3
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "stories.db")
STORIES_DIR = os.path.join(ROOT, "stories")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS stories (
            id    TEXT PRIMARY KEY,
            topic TEXT NOT NULL,
            theme TEXT NOT NULL DEFAULT ''
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(stories)")}
    if "theme" not in columns:
        conn.execute("ALTER TABLE stories ADD COLUMN theme TEXT NOT NULL DEFAULT ''")
    conn.commit()


def story_path(story_id):
    return os.path.join(STORIES_DIR, story_id + ".md")


ID_RE = re.compile(r"^[1-9][0-9]*$")


def check_id(story_id):
    if not ID_RE.match(story_id):
        sys.exit("error: ids must be plain numbers (1, 2, ...): %s" % story_id)
    return story_id


def next_id(conn):
    """One past the highest id in the index or on disk, so ids never get reused."""
    used = {row[0] for row in conn.execute("SELECT id FROM stories")}
    if os.path.isdir(STORIES_DIR):
        used |= {n[:-3] for n in os.listdir(STORIES_DIR) if n.endswith(".md")}
    numbers = [int(u) for u in used if ID_RE.match(u)]
    return str(max(numbers) + 1 if numbers else 1)


def cmd_init(args):
    os.makedirs(STORIES_DIR, exist_ok=True)
    conn = connect()
    init_db(conn)
    conn.close()
    print("initialized %s and %s/" % (DB_PATH, STORIES_DIR))


def cmd_add(args):
    os.makedirs(STORIES_DIR, exist_ok=True)
    conn = connect()
    init_db(conn)
    story_title = args.story_title or args.topic
    story_id = check_id(args.id) if args.id else next_id(conn)
    if conn.execute("SELECT 1 FROM stories WHERE id = ?", (story_id,)).fetchone():
        sys.exit("error: id already exists: %s" % story_id)
    path = story_path(story_id)
    if os.path.exists(path):
        sys.exit("error: file already exists: %s" % path)
    conn.execute(
        "INSERT INTO stories (id, topic, theme) VALUES (?, ?, ?)",
        (story_id, args.topic, args.theme or ""),
    )
    conn.commit()
    conn.close()
    with open(path, "w") as f:
        f.write("# %s\n\n" % story_title)
        if args.theme:
            f.write("*Theme: %s*\n\n" % args.theme)
    print(story_id)
    print(path)
    if args.edit:
        subprocess.call([os.environ.get("EDITOR", "vi"), path])


def cmd_list(args):
    conn = connect()
    init_db(conn)
    rows = conn.execute(
        "SELECT id, topic, theme FROM stories ORDER BY CAST(id AS INTEGER)"
    ).fetchall()
    conn.close()
    for story_id, topic, theme in rows:
        mark = "" if os.path.exists(story_path(story_id)) else "  [MISSING FILE]"
        print("%-6s %-32s %s%s" % (story_id, topic, theme or "-", mark))


def cmd_retitle(args):
    conn = connect()
    init_db(conn)
    cur = conn.execute(
        "UPDATE stories SET topic = ? WHERE id = ?", (args.topic, args.id)
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        sys.exit("error: no such story: %s" % args.id)
    print("%s -> %s" % (args.id, args.topic))


def cmd_retheme(args):
    conn = connect()
    init_db(conn)
    cur = conn.execute("UPDATE stories SET theme = ? WHERE id = ?", (args.theme, args.id))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        sys.exit("error: no such story: %s" % args.id)
    print("%s -> %s" % (args.id, args.theme))


def cmd_rename(args):
    conn = connect()
    init_db(conn)
    check_id(args.new_id)
    if not conn.execute("SELECT 1 FROM stories WHERE id = ?", (args.id,)).fetchone():
        sys.exit("error: no such story: %s" % args.id)
    if conn.execute("SELECT 1 FROM stories WHERE id = ?", (args.new_id,)).fetchone():
        sys.exit("error: id already exists: %s" % args.new_id)
    old_path, new_path = story_path(args.id), story_path(args.new_id)
    if os.path.exists(new_path):
        sys.exit("error: file already exists: %s" % new_path)
    if os.path.exists(old_path):
        os.rename(old_path, new_path)
    conn.execute("UPDATE stories SET id = ? WHERE id = ?", (args.new_id, args.id))
    conn.commit()
    conn.close()
    print("%s -> %s" % (args.id, args.new_id))


def cmd_remove(args):
    conn = connect()
    init_db(conn)
    cur = conn.execute("DELETE FROM stories WHERE id = ?", (args.id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        sys.exit("error: no such story: %s" % args.id)
    path = story_path(args.id)
    print("removed %s from index (file kept: %s)" % (args.id, path))


def cmd_check(args):
    conn = connect()
    init_db(conn)
    indexed = {row[0] for row in conn.execute("SELECT id FROM stories")}
    conn.close()
    on_disk = {
        name[:-3]
        for name in os.listdir(STORIES_DIR)
        if name.endswith(".md")
    } if os.path.isdir(STORIES_DIR) else set()
    problems = 0
    for story_id in sorted(indexed | on_disk):
        if not ID_RE.match(story_id):
            print("id is not a plain number: %s" % story_id)
            problems += 1
    for story_id in sorted(indexed - on_disk):
        print("missing file: stories/%s.md" % story_id)
        problems += 1
    for story_id in sorted(on_disk - indexed):
        print("not indexed: stories/%s.md" % story_id)
        problems += 1
    if problems == 0:
        print("ok: %d stories, index and files agree" % len(indexed))
    else:
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="create the database and stories directory").set_defaults(
        func=cmd_init
    )

    p = sub.add_parser("add", help="add a new story")
    p.add_argument("topic", help='requested topic verbatim, stored in the database, e.g. "curl --basic"')
    p.add_argument(
        "-s", "--story-title", help="descriptive title written as the H1 of the .md file"
    )
    p.add_argument(
        "-t", "--theme", help='the palette theme the story is written under, e.g. "Migration"'
    )
    p.add_argument("--id", help="explicit numeric id (default: next unused number)")
    p.add_argument("-e", "--edit", action="store_true", help="open $EDITOR afterwards")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="list stories ordered by id")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("retitle", help="change a story's requested topic verbatim")
    p.add_argument("id")
    p.add_argument("topic")
    p.set_defaults(func=cmd_retitle)

    p = sub.add_parser("retheme", help="change the theme recorded for a story")
    p.add_argument("id")
    p.add_argument("theme")
    p.set_defaults(func=cmd_retheme)

    p = sub.add_parser("rename", help="change a story's numeric id (moves its file too)")
    p.add_argument("id")
    p.add_argument("new_id")
    p.set_defaults(func=cmd_rename)

    p = sub.add_parser("remove", help="remove a story from the index (keeps the file)")
    p.add_argument("id")
    p.set_defaults(func=cmd_remove)

    p = sub.add_parser("check", help="verify index and files agree")
    p.set_defaults(func=cmd_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
