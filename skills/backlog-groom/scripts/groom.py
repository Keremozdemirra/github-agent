#!/usr/bin/env python3
"""Check a BACKLOG.md against the repository it actually describes.

Standard library only. Parses the Done and Queue sections, then flags three
things a BACKLOG drifts into once nobody rereads it end to end:

- a Queue item that already shipped, usually under a different name than the
  one it was queued under
- a Done item whose file no longer exists on disk
- a Queue item that has sat on the same line, untouched, longer than anything
  else in the file — not wrong on its own, but worth a decision

Usage:
    python3 groom.py --repo path/to/repo
    python3 groom.py --repo path/to/repo --stale-days 30 --json

The output is CANDIDATES, the same discipline as repo-portfolio-audit: a
keyword overlap between a Queue item and something already shipped is a
reason to go read both, not a verdict that they are the same thing. See
SKILL.md.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

STOPWORDS = {
    "that", "this", "with", "from", "into", "when", "what", "where", "which",
    "would", "could", "should", "have", "has", "its", "are", "was", "were",
    "been", "being", "not", "but", "one", "two", "three", "across", "each",
    "every", "only", "than", "then", "also", "more", "most", "some", "such",
    "own", "per", "via", "over", "under", "after", "before", "about",
    "against", "between", "without", "within", "rather", "instead",
    "itself", "their", "them", "they", "your", "does", "did", "done",
    "already", "still", "just", "much", "many", "given", "actually",
    "actual", "real", "genuinely", "same", "there", "these", "those", "here",
    "will", "and", "for", "the",
}


def words(text):
    return {w for w in re.findall(r"[a-z]{4,}", text.lower())
            if w not in STOPWORDS}


def overlap(a, b):
    """Overlap coefficient: |a n b| / min(|a|, |b|). 0 if either is empty."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


# ------------------------------------------------------------------- parse

ITEM_RE = re.compile(
    r"^-\s\[( |x)\]\s\*\*(?:(\d+)\s*[—-]\s*)?([^*]+?)\*\*\s*(?:\xb7|-)?\s*(.*)$"
)


def parse_backlog(path):
    """Return (done_items, queue_items). Each item is a dict with line_no."""
    done, queue = [], []
    section = None
    with open(path, encoding="utf-8") as fh:
        for i, raw in enumerate(fh, start=1):
            line = raw.rstrip("\n")
            if line.startswith("## "):
                heading = line[3:].strip().lower()
                section = heading if heading in ("done", "queue") else None
                continue
            m = ITEM_RE.match(line)
            if not m or section is None:
                continue
            checked, number, label, rest = m.groups()
            item = {
                "line_no": i,
                "number": number,
                "label": label.strip(),
                "text": rest.strip(),
                "in_progress": "status:" in rest.lower(),
                "raw": line,
            }
            (done if section == "done" else queue).append(item)
    return done, queue


# --------------------------------------------------------------- disk state

def slugs_on_disk(repo):
    """Names of things actually built, from every layout these repos use."""
    found = set()
    for base in ("skills", "agents"):
        d = os.path.join(repo, base)
        if not os.path.isdir(d):
            continue
        for name in os.listdir(d):
            found.add(re.sub(r"\.md$", "", name).lower())
    projects = os.path.join(repo, "projects")
    if os.path.isdir(projects):
        for name in os.listdir(projects):
            found.add(re.sub(r"^\d+-", "", name).lower())
    return found


def readme_contents_table(repo):
    """(name, description) rows from the root README's Contents table."""
    path = os.path.join(repo, "README.md")
    if not os.path.exists(path):
        return []
    rows = []
    row_re = re.compile(r"^\|\s*\[([^\]]+)\]\([^)]*\)\s*\|\s*(.*?)\s*\|\s*$")
    for line in open(path, encoding="utf-8", errors="ignore"):
        m = row_re.match(line.strip())
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows


def name_match(label, disk_slugs):
    key = re.sub(r"[^a-z0-9]+", "-", label.lower()).strip("-")
    return key in disk_slugs or any(key in s or s in key for s in disk_slugs)


# ------------------------------------------------------------------- git age

def line_age_days(repo, path, line_no, now):
    """Days since the commit that last touched this line, via git blame."""
    try:
        p = subprocess.run(
            ["git", "-C", repo, "blame", "--line-porcelain",
             "-L", f"{line_no},{line_no}", "--", os.path.relpath(path, repo)],
            capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if p.returncode != 0:
        return None
    m = re.search(r"^committer-time (\d+)$", p.stdout, re.M)
    if not m:
        return None
    commit_time = datetime.fromtimestamp(int(m.group(1)), tz=timezone.utc)
    return (now - commit_time).days


# ---------------------------------------------------------------- findings

def check_duplicates(queue, done, readme_rows, dup_threshold):
    candidates = []
    reference = [(d["label"], d["text"]) for d in done if d["text"]]
    reference += readme_rows
    for q in queue:
        if q["in_progress"] or not q["text"]:
            continue
        qw = words(q["text"])
        best = None
        for label, text in reference:
            score = overlap(qw, words(text))
            if score >= dup_threshold and (best is None or score > best[1]):
                best = (label, score)
        if best:
            candidates.append({
                "kind": "DUPLICATE",
                "item": q["label"],
                "line": q["line_no"],
                "message": f"overlaps {best[1]:.0%} with already-shipped "
                           f"'{best[0]}' — read both before building this",
            })
    return candidates


def check_missing(done, disk_slugs):
    candidates = []
    for d in done:
        if not name_match(d["label"], disk_slugs):
            candidates.append({
                "kind": "MISSING",
                "item": d["label"],
                "line": d["line_no"],
                "message": "marked done but nothing on disk matches this name",
            })
    return candidates


def check_stale(repo, backlog_path, queue, stale_days, now):
    candidates = []
    for q in queue:
        if q["in_progress"]:
            continue
        age = line_age_days(repo, backlog_path, q["line_no"], now)
        if age is not None and age >= stale_days:
            candidates.append({
                "kind": "STALE",
                "item": q["label"],
                "line": q["line_no"],
                "message": f"untouched for {age} days — a decision nobody made",
            })
    return candidates


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="path to the repository")
    ap.add_argument("--stale-days", type=int, default=21)
    ap.add_argument("--dup-threshold", type=float, default=0.55)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    repo = os.path.abspath(args.repo)
    backlog_path = os.path.join(repo, "BACKLOG.md")
    if not os.path.exists(backlog_path):
        print(f"no BACKLOG.md in {repo}", file=sys.stderr)
        return 2

    done, queue = parse_backlog(backlog_path)
    disk_slugs = slugs_on_disk(repo)
    readme_rows = readme_contents_table(repo)
    now = datetime.now(timezone.utc)

    findings = []
    findings += check_duplicates(queue, done, readme_rows, args.dup_threshold)
    findings += check_missing(done, disk_slugs)
    findings += check_stale(repo, backlog_path, queue, args.stale_days, now)
    findings.sort(key=lambda f: f["line"])

    if args.json:
        print(json.dumps(findings, indent=2))
    else:
        print(f"Done: {len(done)}  Queue: {len(queue)}  "
              f"({sum(1 for q in queue if q['in_progress'])} in progress)")
        if not findings:
            print("Nothing flagged — read it anyway before trusting that.")
        for f in findings:
            print(f"[{f['kind']}] line {f['line']} — {f['item']}: {f['message']}")
        print("\nCandidates, not verdicts. See SKILL.md before editing BACKLOG.md.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
