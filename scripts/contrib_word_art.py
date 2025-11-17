"""
Draw the word NERDLIN on the GitHub contributions graph by creating backdated commits.

How it works
 - We render a 5x7 pixel font for each letter and compose the word across 52 weeks (columns).
 - For each ON pixel, we create N commits on the corresponding date within the last 52 weeks.
 - Commits are authored with backdated GIT_AUTHOR_DATE/GIT_COMMITTER_DATE so they appear on the heatmap.

Usage (locally):
  python scripts/contrib_word_art.py --apply --push --intensity 6 --name "Nerdlin" --email "<your_email_or_noreply>"

Notes
 - Commits count only if the author email is linked to your GitHub account. You can use the noreply email:
   <username>@users.noreply.github.com
 - The contributions board shows only the last 52 weeks, so we schedule this weekly to keep the word visible.
 - Run inside a dedicated repo (public recommended). Enable "Include private contributions" if using private.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess
from pathlib import Path


# 5x7 font (columns width=5, rows height=7, '1' = filled, '0' = empty)
FONT_5x7 = {
    "N": [
        "10001",
        "11001",
        "10101",
        "10011",
        "10001",
        "10001",
        "10001",
    ],
    "E": [
        "11111",
        "10000",
        "11110",
        "10000",
        "11111",
        "00000",
        "00000",
    ],
    "R": [
        "11110",
        "10001",
        "11110",
        "10100",
        "10010",
        "10001",
        "00000",
    ],
    "D": [
        "11110",
        "10001",
        "10001",
        "10001",
        "11110",
        "00000",
        "00000",
    ],
    "L": [
        "10000",
        "10000",
        "10000",
        "10000",
        "11111",
        "00000",
        "00000",
    ],
    "I": [
        "11111",
        "00100",
        "00100",
        "00100",
        "11111",
        "00000",
        "00000",
    ],
}


def compose_word(word: str, total_columns: int = 52, spacing: int = 1):
    # Build pixel matrix (7 rows x total_columns)
    rows, cols = 7, total_columns
    canvas = [[0 for _ in range(cols)] for _ in range(rows)]

    # Measure word width in columns
    width = 0
    letters = []
    for ch in word.upper():
        if ch not in FONT_5x7:
            continue
        letters.append(FONT_5x7[ch])
        width += 5
        width += spacing
    if letters:
        width -= spacing  # no trailing space

    start_col = max(0, (cols - width) // 2)
    c = start_col
    for glyph in letters:
        for r in range(7):
            for x in range(5):
                if glyph[r][x] == "1" and 0 <= c + x < cols:
                    canvas[r][c + x] = 1
        c += 5 + spacing

    return canvas


def sunday_of_current_week(today: dt.date) -> dt.date:
    # Python: Monday=0..Sunday=6
    days_since_sun = (today.weekday() + 1) % 7
    return today - dt.timedelta(days=days_since_sun)


def leftmost_sunday(today: dt.date) -> dt.date:
    return sunday_of_current_week(today) - dt.timedelta(weeks=51)


def plan_dates(canvas):
    today = dt.date.today()
    start = leftmost_sunday(today)
    dates = []
    for col in range(52):
        col_sun = start + dt.timedelta(weeks=col)
        for row in range(7):  # row 0 = Sunday
            if canvas[row][col]:
                dates.append(col_sun + dt.timedelta(days=row))
    return dates


def run(cmd, **kwargs):
    return subprocess.check_call(cmd, shell=True, **kwargs)


def make_commit_for_date(
    the_date: dt.date,
    author_name: str,
    author_email: str,
    message: str,
    file_path: Path,
    allow_empty: bool = False,
):
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("a", encoding="utf-8") as f:
        f.write(f"{the_date.isoformat()} - {message}\n")

    run(f"git add {file_path.as_posix()}")

    env = os.environ.copy()
    # Noon UTC for determinism
    date_str = f"{the_date.isoformat()} 12:00:00 +0000"
    env.update(
        {
            "GIT_AUTHOR_DATE": date_str,
            "GIT_COMMITTER_DATE": date_str,
            "GIT_AUTHOR_NAME": author_name,
            "GIT_AUTHOR_EMAIL": author_email,
            "GIT_COMMITTER_NAME": author_name,
            "GIT_COMMITTER_EMAIL": author_email,
        }
    )

    allow = " --allow-empty" if allow_empty else ""
    run(
        f'git commit -m "contrib-art: {message} ({the_date.isoformat()})"{allow}',
        env=env,
    )


def main():
    p = argparse.ArgumentParser(
        description="Render a word on GitHub contribution graph"
    )
    p.add_argument(
        "--word",
        default="NERDLIN",
        help="Word to render (letters supported: N,E,R,D,L,I)",
    )
    p.add_argument(
        "--intensity",
        type=int,
        default=6,
        help="Commits per lit cell (4-10 recommended)",
    )
    p.add_argument(
        "--apply", action="store_true", help="Create commits instead of dry-run"
    )
    p.add_argument("--push", action="store_true", help="Push after committing")
    p.add_argument("--name", default="Nerdlin", help="Author name to use for commits")
    p.add_argument(
        "--email",
        required=False,
        help="Author email (use your verified or <username>@users.noreply.github.com)",
    )
    p.add_argument("--file", default="art/log.txt", help="File to touch for commits")
    args = p.parse_args()

    canvas = compose_word(args.word)
    dates = plan_dates(canvas)
    print(
        f"Pixels lit: {len(dates)}; total commits planned: {len(dates) * args.intensity}"
    )

    if not args.apply:
        return

    author_email = args.email or os.environ.get("GIT_AUTHOR_EMAIL") or ""
    if not author_email:
        raise SystemExit("--email is required (or set GIT_AUTHOR_EMAIL)")

    # Ensure repo
    run("git rev-parse --is-inside-work-tree >NUL 2>&1")

    path = Path(args.file)
    for d in dates:
        for k in range(args.intensity):
            make_commit_for_date(
                d, args.name, author_email, message=f"{args.word} pixel", file_path=path
            )

    if args.push:
        run("git push")


if __name__ == "__main__":
    main()
