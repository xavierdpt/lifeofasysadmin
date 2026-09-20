#!/usr/bin/env python3
"""Manage the story collection: sqlite index (id, technical title) + stories/{id}.md."""

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
            title TEXT NOT NULL
        )
        """
    )
    conn.commit()


def story_path(story_id):
    return os.path.join(STORIES_DIR, story_id + ".md")


def slugify(text):
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "story"


def unique_id(conn, base):
    candidate, n = base, 2
    while True:
        row = conn.execute("SELECT 1 FROM stories WHERE id = ?", (candidate,)).fetchone()
        if row is None and not os.path.exists(story_path(candidate)):
            return candidate
        candidate = "%s-%d" % (base, n)
        n += 1


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
    story_title = args.story_title or args.technical_title
    story_id = args.id or unique_id(conn, slugify(args.technical_title))
    if conn.execute("SELECT 1 FROM stories WHERE id = ?", (story_id,)).fetchone():
        sys.exit("error: id already exists: %s" % story_id)
    path = story_path(story_id)
    if os.path.exists(path):
        sys.exit("error: file already exists: %s" % path)
    conn.execute(
        "INSERT INTO stories (id, title) VALUES (?, ?)", (story_id, args.technical_title)
    )
    conn.commit()
    conn.close()
    with open(path, "w") as f:
        f.write("# %s\n\n" % story_title)
    print(story_id)
    print(path)
    if args.edit:
        subprocess.call([os.environ.get("EDITOR", "vi"), path])


def cmd_list(args):
    conn = connect()
    init_db(conn)
    rows = conn.execute("SELECT id, title FROM stories ORDER BY title").fetchall()
    conn.close()
    for story_id, title in rows:
        mark = "" if os.path.exists(story_path(story_id)) else "  [MISSING FILE]"
        print("%-40s %s%s" % (title, story_id, mark))


def cmd_retitle(args):
    conn = connect()
    init_db(conn)
    cur = conn.execute(
        "UPDATE stories SET title = ? WHERE id = ?", (args.technical_title, args.id)
    )
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        sys.exit("error: no such story: %s" % args.id)
    print("%s -> %s" % (args.id, args.technical_title))


def cmd_rename(args):
    conn = connect()
    init_db(conn)
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
    p.add_argument("technical_title", help="sortable title stored in the database")
    p.add_argument(
        "-s", "--story-title", help="descriptive title written as the H1 of the .md file"
    )
    p.add_argument("--id", help="explicit id (default: slug of the technical title)")
    p.add_argument("-e", "--edit", action="store_true", help="open $EDITOR afterwards")
    p.set_defaults(func=cmd_add)

    p = sub.add_parser("list", help="list stories ordered by technical title")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("retitle", help="change a story's technical title")
    p.add_argument("id")
    p.add_argument("technical_title")
    p.set_defaults(func=cmd_retitle)

    p = sub.add_parser("rename", help="change a story's id (moves its file too)")
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
