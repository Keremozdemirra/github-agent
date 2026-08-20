#!/usr/bin/env python3
"""Sweep a portfolio of repositories and report what needs attention.

Standard library only. Clones or pulls each repo, runs its tests, checks CI,
conventions and .env hygiene, delegates the secret scan to the
pre-launch-security-audit scanner when it is reachable, and counts LLM-writing
tells in README prose.

Usage:
    python3 sweep.py --repos repos.txt --workdir ./_audit
    python3 sweep.py --repos repos.txt --workdir ./_audit --only-new
    python3 sweep.py --repos repos.txt --workdir ./_audit --json

repos.txt: one clone URL or local path per line; blank lines and # comments
ignored.

The output is CANDIDATES. Two categories need your judgment before they go in a
report: prose-tell counts (read the file — deliberate prose is not slop) and
anything that does not apply to the kind of project at hand. See SKILL.md.
"""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

SEV_ORDER = {"FAIL": 0, "WARN": 1, "OK": 2, "INFO": 3}


def run(cmd, cwd=None, timeout=600):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError) as e:
        return 127, str(e)


class Repo:
    def __init__(self, name, path):
        self.name = name
        self.path = path
        self.findings = []          # (sev, check, message, detail)

    def add(self, sev, check, message, detail=""):
        self.findings.append((sev, check, message, detail))


# ------------------------------------------------------------------ acquire

def acquire(target, workdir, fetch=True):
    """Clone or pull; returns (name, path) or (name, None) on failure."""
    if os.path.isdir(target):
        return os.path.basename(os.path.abspath(target)), os.path.abspath(target)

    name = re.sub(r"\.git$", "", target.rstrip("/").rsplit("/", 1)[-1])
    dest = os.path.join(workdir, name)
    if os.path.isdir(os.path.join(dest, ".git")):
        if fetch:
            rc, out = run(["git", "-C", dest, "pull", "--ff-only", "-q"])
            if rc != 0:
                print(f"  ! pull failed for {name}: {out.strip()[:120]}",
                      file=sys.stderr)
        return name, dest
    if not fetch:
        return name, None
    os.makedirs(workdir, exist_ok=True)
    rc, out = run(["git", "clone", "-q", target, dest], timeout=900)
    if rc != 0:
        print(f"  ! clone failed for {name}: {out.strip()[:200]}", file=sys.stderr)
        return name, None
    return name, dest


# ------------------------------------------------------------------- checks

def check_tests(r):
    """Discover and run each project's unittest suite."""
    roots = []
    projects_dir = os.path.join(r.path, "projects")
    if os.path.isdir(projects_dir):
        for d in sorted(os.listdir(projects_dir)):
            p = os.path.join(projects_dir, d)
            if os.path.isdir(os.path.join(p, "tests")):
                roots.append(p)
    elif os.path.isdir(os.path.join(r.path, "tests")):
        roots.append(r.path)

    if not roots:
        has_py = any(f.endswith(".py")
                     for _, _, fs in os.walk(r.path) for f in fs)
        if has_py:
            r.add("FAIL", "tests", "Python code but no tests/ directory found")
        else:
            r.add("INFO", "tests", "No code to test", "documents only")
        return 0

    total = 0
    for root in roots:
        rel = os.path.relpath(root, r.path)
        rc, out = run([sys.executable, "-m", "unittest", "discover",
                       "-s", "tests", "-t", "."], cwd=root)
        m = re.search(r"^Ran (\d+) test", out, re.M)
        n = int(m.group(1)) if m else 0
        total += n
        if rc != 0:
            fail = "\n".join(l for l in out.splitlines()
                             if l.startswith(("FAIL:", "ERROR:")))[:400]
            r.add("FAIL", "tests", f"Test suite failing in {rel}",
                  fail or out.strip()[-400:])
        elif n == 0:
            r.add("WARN", "tests", f"{rel} has a tests/ dir but ran 0 tests")
    if total:
        r.add("OK", "tests", f"{total} tests pass across {len(roots)} project(s)")
    return total


def check_ci(r, test_count):
    wf_dir = os.path.join(r.path, ".github", "workflows")
    files = ([f for f in sorted(os.listdir(wf_dir))
              if f.endswith((".yml", ".yaml"))] if os.path.isdir(wf_dir) else [])
    if not files:
        if test_count:
            r.add("FAIL", "ci", f"No CI — {test_count} tests, nothing runs them",
                  "a suite nobody runs decays silently")
        else:
            r.add("INFO", "ci", "No CI", "nothing to run yet")
        return

    blob = ""
    for f in files:
        try:
            blob += open(os.path.join(wf_dir, f), encoding="utf-8",
                         errors="ignore").read() + "\n"
        except OSError:
            pass

    if not re.search(r"^\s*(push|pull_request)\s*:", blob, re.M):
        r.add("WARN", "ci", "Workflow does not trigger on push or pull_request")
    if not re.search(r"unittest|pytest|nose|go test|npm (?:run )?test|cargo test",
                     blob):
        r.add("WARN", "ci", "No test runner found in the workflow",
              "CI exists but may not be testing anything")
    # A workflow that finds nothing and exits 0 reports a green check on zero
    # tests, which reads as "the suite passed" when nothing ran.
    loops = re.search(r"for\s+\w+\s+in\s+\S*projects/\*", blob)
    if loops and not re.search(r"ran\s*(?:-eq|==)\s*0|exit 1|::error", blob):
        r.add("WARN", "ci", "Workflow loops over projects with no empty-set guard",
              "if discovery finds nothing it will pass green")
    r.add("OK", "ci", f"CI present ({', '.join(files)})")


def check_hygiene(r):
    gi_path = os.path.join(r.path, ".gitignore")
    gi = ""
    if os.path.exists(gi_path):
        gi = open(gi_path, encoding="utf-8", errors="ignore").read()
    else:
        r.add("WARN", "hygiene", "No .gitignore")
    if not re.search(r"^\s*\.env", gi, re.M):
        r.add("WARN", "hygiene", ".gitignore does not cover .env",
              "a local secrets file can be committed by accident")

    if os.path.isdir(os.path.join(r.path, ".git")):
        rc, out = run(["git", "-C", r.path, "log", "--all", "--full-history",
                       "--oneline", "--", "*.env", "*.env.*"])
        if out.strip():
            r.add("FAIL", "hygiene", ".env appears in git history",
                  f"{len(out.strip().splitlines())} commit(s) — rotate every key")
        rc, out = run(["git", "-C", r.path, "ls-files"])
        tracked = [l for l in out.splitlines()
                   if re.search(r"(^|/)\.env", l)
                   and not re.search(r"\.(example|sample|template)$", l)]
        for t in tracked:
            r.add("FAIL", "hygiene", ".env is tracked in git", t)

    for f, sev in (("LICENSE", "WARN"), ("README.md", "FAIL"),
                   ("CLAUDE.md", "INFO")):
        if not os.path.exists(os.path.join(r.path, f)):
            r.add(sev, "conventions", f"No {f}")


def check_project_table(r):
    """Does the root README's project table match the directories on disk?

    The most common drift in a numbered-projects layout: a project is added and
    the table is not updated, so the repo's own index is wrong.
    """
    projects_dir = os.path.join(r.path, "projects")
    readme = os.path.join(r.path, "README.md")
    if not (os.path.isdir(projects_dir) and os.path.exists(readme)):
        return
    on_disk = {d for d in os.listdir(projects_dir)
               if os.path.isdir(os.path.join(projects_dir, d))
               and re.match(r"\d{3}-", d)}
    if not on_disk:
        return
    text = open(readme, encoding="utf-8", errors="ignore").read()
    missing = sorted(d for d in on_disk
                     if d.split("-", 1)[1] not in text and d not in text)
    if missing:
        r.add("WARN", "conventions",
              "Root README does not mention every project directory",
              ", ".join(missing))

    backlog = os.path.join(r.path, "BACKLOG.md")
    if os.path.exists(backlog):
        btext = open(backlog, encoding="utf-8", errors="ignore").read()
        unlisted = sorted(d for d in on_disk
                          if d.split("-", 1)[1] not in btext)
        if unlisted:
            r.add("WARN", "conventions",
                  "BACKLOG.md does not mention every project directory",
                  ", ".join(unlisted))


PROSE_TELLS = {
    "em dash": r"—",
    "'not X, but Y'": r"(?i)\bnot (?:just |only |merely )?[\w ]{2,30}[—,-]{1,2} (?:it'?s |but )",
    "checkmark bullet": r"(?m)^\s*[-*]?\s*[✅✓☑]",
    "emoji": r"[\U0001F300-\U0001FAFF✨⚡\U0001F680]",
    "hype verb": r"(?i)\b(?:seamless(?:ly)?|effortless(?:ly)?|unlock|supercharge|"
                 r"revolutioni[sz]e|game.chang\w*|cutting.edge)\b",
}


def check_prose(r):
    """Count LLM-writing tells. Counts only — the judgment is yours.

    A README with several em dashes may be careful prose or may be machine
    output. Flag it only when the harder markers show up too.
    """
    hard = 0
    soft = 0
    where = []
    for dirpath, dirnames, filenames in os.walk(r.path):
        dirnames[:] = [d for d in dirnames if d not in (".git", "node_modules")]
        for fn in filenames:
            if fn.lower() != "readme.md":
                continue
            path = os.path.join(dirpath, fn)
            try:
                t = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            hits = {k: len(re.findall(p, t)) for k, p in PROSE_TELLS.items()}
            hits = {k: v for k, v in hits.items() if v}
            if not hits:
                continue
            h = sum(v for k, v in hits.items()
                    if k in ("emoji", "checkmark bullet", "hype verb"))
            s = sum(v for k, v in hits.items()
                    if k in ("em dash", "'not X, but Y'"))
            hard += h
            soft += s
            where.append(f"{os.path.relpath(path, r.path)}: " +
                         ", ".join(f"{k} x{v}" for k, v in hits.items()))
    if hard:
        r.add("WARN", "prose", "README prose shows hard AI-writing markers",
              "; ".join(where[:6]))
    elif soft:
        r.add("INFO", "prose", "README prose tells counted — read before judging",
              "; ".join(where[:6]) + " | em dashes and 'not X, but Y' alone are "
              "not evidence of machine writing; deliberate prose uses both")


def check_secrets(r, scanner):
    if not scanner or not os.path.exists(scanner):
        r.add("INFO", "secrets", "Secret scan skipped",
              "pre-launch-security-audit scanner not found; pass --scanner PATH")
        return
    rc, out = run([sys.executable, scanner, r.path], timeout=600)

    def section(level):
        """Lines belonging to one severity block of the scanner's output."""
        m = re.search(rf"^-- {level} \((\d+)\) --$(.*?)(?=^-- |\Z)",
                      out, re.M | re.S)
        if not m:
            return None, ""
        body = "\n".join(l.strip() for l in m.group(2).splitlines() if l.strip())
        return int(m.group(1)), body

    n_crit, crit_body = section("CRITICAL")
    n_high, high_body = section("HIGH")
    if n_crit:
        r.add("FAIL", "secrets", f"{n_crit} critical security finding(s)",
              crit_body[:600])
    if n_high:
        r.add("WARN", "secrets", f"{n_high} high security finding(s)",
              high_body[:400])
    if not n_crit and not n_high:
        r.add("OK", "secrets", "No secrets or dangerous patterns found")
    if "No HTTP surface detected" in out:
        r.add("INFO", "secrets", "Web checks not applicable",
              "no HTTP surface — rate limiting, headers and request validation "
              "skipped")


# ------------------------------------------------------------------- state

def finding_key(repo, sev, check, message):
    return hashlib.sha1(f"{repo}|{check}|{message}".encode()).hexdigest()[:12]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", required=True,
                    help="file with one clone URL or path per line")
    ap.add_argument("--workdir", default="./_audit")
    ap.add_argument("--state", default=None,
                    help="state file (default: <workdir>/state.json)")
    ap.add_argument("--scanner", default=None,
                    help="path to pre-launch-security-audit scan_secrets.py")
    ap.add_argument("--only-new", action="store_true")
    ap.add_argument("--no-fetch", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    targets = []
    with open(args.repos, encoding="utf-8") as fh:
        for line in fh:
            line = line.split("#", 1)[0].strip()
            if line:
                targets.append(line)
    if not targets:
        print("no repos listed", file=sys.stderr)
        return 2

    workdir = os.path.abspath(args.workdir)
    state_path = args.state or os.path.join(workdir, "state.json")
    os.makedirs(workdir, exist_ok=True)

    scanner = args.scanner
    if not scanner:
        guess = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "..", "..", "pre-launch-security-audit",
                             "scripts", "scan_secrets.py")
        scanner = guess if os.path.exists(guess) else None

    previous = {}
    if os.path.exists(state_path):
        try:
            previous = json.load(open(state_path, encoding="utf-8"))
        except ValueError:
            previous = {}
    seen_before = set(previous.get("findings", []))

    repos = []
    for t in targets:
        name, path = acquire(t, workdir, fetch=not args.no_fetch)
        r = Repo(name, path or "")
        if not path:
            r.add("FAIL", "acquire", "Could not clone or reach the repository", t)
            repos.append(r)
            continue
        n = check_tests(r)
        check_ci(r, n)
        check_hygiene(r)
        check_project_table(r)
        check_prose(r)
        check_secrets(r, scanner)
        repos.append(r)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    all_keys = []
    payload = []
    for r in repos:
        for sev, check, msg, detail in r.findings:
            key = finding_key(r.name, sev, check, msg)
            all_keys.append(key)
            payload.append({"repo": r.name, "severity": sev, "check": check,
                            "message": msg, "detail": detail, "key": key,
                            "new": key not in seen_before})

    shown = [f for f in payload
             if (not args.only_new or f["new"] or f["severity"] == "FAIL")]

    if args.json:
        print(json.dumps({"generated": now, "previous_run": previous.get("generated"),
                          "findings": shown}, indent=2))
    else:
        print(f"\n=== Portfolio audit — {len(repos)} repos — {now} ===")
        if previous.get("generated"):
            print(f"    previous run: {previous['generated']}"
                  + ("  (showing new + all failures)" if args.only_new else ""))
        for sev in ("FAIL", "WARN", "OK", "INFO"):
            rows = [f for f in shown if f["severity"] == sev]
            if not rows:
                continue
            print(f"\n-- {sev} ({len(rows)}) --")
            for f in rows:
                flag = " [NEW]" if f["new"] and previous else ""
                print(f"  {f['repo']:22} {f['message']}{flag}")
                if f["detail"]:
                    for line in f["detail"].splitlines()[:6]:
                        print(f"      {line}")
        fails = sum(1 for f in payload if f["severity"] == "FAIL")
        warns = sum(1 for f in payload if f["severity"] == "WARN")
        news = sum(1 for f in payload if f["new"]) if previous else 0
        print(f"\n{fails} failing, {warns} worth fixing"
              + (f", {news} new since last run." if previous else "."))
        print("Judgment still required: prose counts are not verdicts, and "
              "checks that do not apply to a library should be stated as "
              "skipped rather than listed. See SKILL.md.")

    with open(state_path, "w", encoding="utf-8") as fh:
        json.dump({"generated": now, "findings": all_keys}, fh, indent=2)

    return 1 if any(f["severity"] == "FAIL" for f in payload) else 0


if __name__ == "__main__":
    sys.exit(main())
