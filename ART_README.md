Contributions Word Art (NERDLIN)

What this does

- Draws the word NERDLIN on the GitHub contribution heatmap using backdated commits (last 52 weeks).
- Keeps the word visible via a weekly scheduled workflow.

Quick start

1. Create a separate public repo (recommended), e.g. `nerdlin-contrib-art` and copy these files:
   - `scripts/contrib_word_art.py`
   - `.github/workflows/contrib-word-art.yml`
2. Edit the workflow and set your email:
   - Prefer `<username>@users.noreply.github.com` or a verified email on your account.
3. Push to GitHub. Run the workflow manually once (Actions tab -> Contrib Word Art -> Run).
4. Wait a few minutes and refresh your profile. The board shows only the last 52 weeks; the job runs every Sunday to maintain the word.

Local run (optional)

- Ensure you run inside that repo and your git remote is set.
- Example (PowerShell):
  python scripts/contrib_word_art.py --apply --push --intensity 6 --name "Nerdlin" --email "<username>@users.noreply.github.com"

FAQ

- Can I make it stay forever? The contributions graph is a rolling 52-week window. The scheduled workflow recreates the pattern each week so it effectively persists.
- Is this allowed? Commits are real; they must be authored by you. Consider doing this in a separate sandbox repo so it doesn’t confuse viewers of your main activity.
- Will empty commits count? This script appends to `art/log.txt` to avoid empty commits.
