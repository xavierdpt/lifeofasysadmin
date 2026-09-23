#!/usr/bin/env python3
"""Draw themes from themes.txt at random, weighted against the ones already used.

A theme's weight is 1 / (1 + uses) ** power, where uses is the number of stories in
stories.db recorded under that subtheme. An unused theme weighs 1, a theme used once
weighs 1/4 with the default power of 2, twice 1/9, and so on: used themes stay
possible, just less likely. The draw is without replacement, so the lines printed
are distinct. Output is the chosen lines of themes.txt, verbatim.
"""

import argparse
import os
import random
import re
import sqlite3
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(ROOT, "stories.db")
THEMES_PATH = os.path.join(ROOT, "themes.txt")

LINE_RE = re.compile(r"^\[[^\]]*\]\s*(.+)$")


def subtheme(line):
    """The part between the bracket and the colon; the whole rest if there is no gloss."""
    m = LINE_RE.match(line)
    if not m:
        return None
    return m.group(1).split(":", 1)[0].strip().rstrip(".")


def usage_counts():
    if not os.path.exists(DB_PATH):
        return {}
    conn = sqlite3.connect(DB_PATH)
    try:
        rows = conn.execute(
            "SELECT theme, COUNT(*) FROM stories WHERE theme != '' GROUP BY theme"
        ).fetchall()
    finally:
        conn.close()
    return dict(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-n", type=int, default=3, help="how many themes to draw (default 3)")
    parser.add_argument(
        "-p", "--power", type=float, default=2.0,
        help="how hard to penalise used themes; 0 disables weighting (default 2)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="print each drawn theme's use count and weight to stderr",
    )
    args = parser.parse_args()

    with open(THEMES_PATH, encoding="utf-8") as f:
        lines = [l.rstrip("\n") for l in f if l.strip()]
    counts = usage_counts()

    pool = []
    for line in lines:
        name = subtheme(line)
        if name is None:
            sys.exit(f"draw_themes: cannot parse themes.txt line: {line!r}")
        uses = counts.get(name, 0)
        pool.append((line, uses, 1.0 / (1 + uses) ** args.power))

    if args.n > len(pool):
        sys.exit(f"draw_themes: asked for {args.n} themes, palette has {len(pool)}")

    rng = random.SystemRandom()
    for _ in range(args.n):
        i = rng.choices(range(len(pool)), weights=[w for _, _, w in pool])[0]
        line, uses, weight = pool.pop(i)
        print(line, flush=True)
        if args.verbose:
            print(f"  uses={uses} weight={weight:.3f}", file=sys.stderr)


if __name__ == "__main__":
    main()
