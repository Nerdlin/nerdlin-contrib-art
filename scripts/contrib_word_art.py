"""
Draw the word NERDLIN on the GitHub contributions graph by creating backdated commits.

How it works
 - We render a 5x7 pixel font for each letter and compose the word across 52 weeks (columns).
 - For each ON pixel, we create N commits on the corresponding date within the last 52 weeks.
 - Commits are authored with backdated GIT_AUTHOR_DATE/GIT_COMMITTER_DATE so they appear on the heatmap.

Usage (locally):
  python scripts/contrib_word_art.py --apply --push --intensity 60 --name "Nerdlin" --email "<ID>+<username>@users.noreply.github.com"

Notes
 - Commits count only if the author email is linked to your GitHub account. You can use the noreply email:
   <ID>+<username>@users.noreply.github.com
 - The history is rebuilt from scratch on every run (no smearing); --push force-pushes it.
 - The contributions board shows only the last 52 weeks, so we schedule this weekly to keep the word visible.
 - Run inside a dedicated repo (public recommended). Enable "Include private contributions" if using private.
"""

from __future__ import annotations

import argparse
import datetime as dt
import os
import subprocess


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
    return subprocess.check_call(cmd, **kwargs)


def build_history(dates, intensity, name, email, word, branch):
    """Rebuild the branch from scratch as an orphan history via git fast-import.

    Re-rendering on top of old commits makes the word smear: the window moves
    one column per week, so every run would add a shifted copy. Rebuilding the
    history each time keeps exactly one copy of the word.
    """
    stream = []
    mark = 0
    readme = f"Contribution word art: {word}\nHistory is rebuilt by scripts/contrib_word_art.py\n"
    for d in sorted(dates):
        ts = int(dt.datetime(d.year, d.month, d.day, 12, tzinfo=dt.timezone.utc).timestamp())
        for _ in range(intensity):
            mark += 1
            msg = f"contrib-art: {word} pixel ({d.isoformat()})"
            ident = f"{name} <{email}> {ts} +0000"
            stream.append(f"commit refs/heads/{branch}")
            stream.append(f"mark :{mark}")
            stream.append(f"author {ident}")
            stream.append(f"committer {ident}")
            stream.append(f"data {len(msg.encode())}")
            stream.append(msg)
            if mark > 1:
                stream.append(f"from :{mark - 1}")
            else:
                stream.append(f"M 100644 inline README.md")
                stream.append(f"data {len(readme.encode())}")
                stream.append(readme)
            stream.append("")
    subprocess.run(
        ["git", "fast-import", "--quiet", "--force"],
        input="\n".join(stream).encode(),
        check=True,
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
        default=60,
        help="Commits per lit cell (must outweigh your normal daily activity)",
    )
    p.add_argument(
        "--apply", action="store_true", help="Build the history instead of dry-run"
    )
    p.add_argument(
        "--push", action="store_true", help="Force-push the rebuilt history"
    )
    p.add_argument("--name", default="Nerdlin", help="Author name to use for commits")
    p.add_argument(
        "--email",
        required=False,
        help="Author email (ID+<username>@users.noreply.github.com)",
    )
    p.add_argument("--branch", default="art-build", help="Local branch to build")
    p.add_argument(
        "--target", default="main", help="Remote branch to overwrite on --push"
    )
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

    run(["git", "rev-parse", "--is-inside-work-tree"], stdout=subprocess.DEVNULL)
    build_history(dates, args.intensity, args.name, author_email, args.word, args.branch)

    if args.push:
        run(["git", "push", "--force", "origin", f"{args.branch}:{args.target}"])


if __name__ == "__main__":
    main()
