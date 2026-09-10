#!/usr/bin/env python3
"""Regenerate the project list in index.html from the GitHub API.

Run manually:
    python3 scripts/generate_index.py

Runs automatically via .github/workflows/update-index.yml (daily + on demand).
Only touches the block between the REPO-LIST and REPO-COUNT marker comments
in index.html — everything else in the file is left untouched.
"""
import html
import json
import re
import sys
import urllib.request
from pathlib import Path

USERNAME = "andrewpono"
SELF_REPO = f"{USERNAME}.github.io"
INDEX_PATH = Path(__file__).resolve().parent.parent / "index.html"

LIST_START = "<!-- REPO-LIST:START -->"
LIST_END = "<!-- REPO-LIST:END -->"
COUNT_START = "<!-- REPO-COUNT -->"
COUNT_END = "<!-- /REPO-COUNT -->"


def fetch_repos():
    url = f"https://api.github.com/users/{USERNAME}/repos?per_page=100&sort=pushed"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USERNAME, "Accept": "application/vnd.github+json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def build_item_html(repo):
    name = html.escape(repo["name"])
    link = html.escape(repo["html_url"])
    desc = html.escape(repo["description"] or "No description yet.")
    lang = repo.get("language")
    tag_html = f'\n            <span class="repo-tag">{html.escape(lang)}</span>' if lang else ""
    return (
        "      <li>\n"
        f'        <a class="repo" href="{link}">\n'
        '          <div class="repo-row">\n'
        f'            <span class="repo-name">{name}</span>{tag_html}\n'
        "          </div>\n"
        f'          <p class="repo-desc">{desc}</p>\n'
        "        </a>\n"
        "      </li>"
    )


def replace_between(text, start_marker, end_marker, new_inner):
    pattern = re.compile(re.escape(start_marker) + r".*?" + re.escape(end_marker), re.DOTALL)
    if not pattern.search(text):
        raise ValueError(f"Markers {start_marker!r} / {end_marker!r} not found in index.html")
    return pattern.sub(f"{start_marker}{new_inner}{end_marker}", text, count=1)


def main():
    repos = fetch_repos()
    originals = [r for r in repos if not r["fork"] and r["name"] != SELF_REPO]
    originals.sort(key=lambda r: r["pushed_at"], reverse=True)

    if not originals:
        print("No original (non-fork) repos found — leaving index.html untouched.", file=sys.stderr)
        return

    items_html = "\n" + "\n".join(build_item_html(r) for r in originals) + "\n"
    count_text = f'{len(originals)} repo{"s" if len(originals) != 1 else ""}'

    text = INDEX_PATH.read_text(encoding="utf-8")
    text = replace_between(text, LIST_START, LIST_END, items_html)
    text = replace_between(text, COUNT_START, COUNT_END, count_text)

    original_text = INDEX_PATH.read_text(encoding="utf-8")
    if text != original_text:
        INDEX_PATH.write_text(text, encoding="utf-8")
        print(f"Updated index.html with {len(originals)} repo(s).")
    else:
        print("No changes needed.")


if __name__ == "__main__":
    main()
