---
name: repo-portfolio-audit
description: One health sweep over every repository in the portfolio, reporting only what changed since the last run: pull, tests, CI coverage, secret and dangerous-pattern scan, .gitignore, claimed conventions, README prose tells. Keeps a state file for weekly runs. Use for "repolarimi tara", "repo sagligi", "audit my github", "what needs fixing across my projects". Not for one app in depth; use pre-launch-security-audit.
---

# Repo portfolio audit

One pass over every repository that reports what is wrong, with no fixed-length
list per repo. The point of doing it across the whole portfolio at once is that
drift shows up as a pattern: five repos missing the same thing is one decision
to make, and the report presents it as one.

The failure mode to design against is a report nobody reads. That happens two
ways: it repeats last week's findings, or it reports things that are fine as
though they were problems. Both are handled below, and both matter more than
adding another check.

## Workflow

### 1. Establish the target list

Repos can come from a `repos.txt` (one clone URL or local path per line), from
what the user names, or from a GitHub account if a connector or `gh` is
available. If none of those exist, ask for the list once and write it to
`repos.txt` so the next run is unattended.

When the list comes from local clones (`git remote get-url origin` over every
`.git` under a root), strip userinfo before the URL reaches the transcript:
`git remote get-url origin | sed -E 's#//[^/@]*@#//#'`. A stale clone can carry
a token as `x-access-token` in its origin URL, and the transcript is itself
written to disk and synced, so an unfiltered print turns one exposure into two.
Treat `.git/config`, `.npmrc`, `.netrc` and `pip.conf` the same way: report how
many of them matched and keep their contents out of the output.

Note whether push access exists before doing any work. It changes the deliverable:
with push, a branch and PR per repo; without, patches the user applies. Finding
this out at the end wastes the pass.

### 2. Run the sweep

```bash
# $SKILL_DIR is not set in every runtime; locate the script directly.
SWEEP="$(find "$HOME/.claude/skills" "$HOME/agents" -name sweep.py -path '*repo-portfolio-audit*' -print -quit 2>/dev/null)"
python3 "$SWEEP" --repos repos.txt --workdir ./_audit
```

If `$SWEEP` comes back empty the skill lives somewhere these roots do not cover;
ask the user where it is installed.

Useful flags: `--only-new` compares against the state file and reports only
findings not seen last time; `--json` for machine-readable output; `--no-fetch`
to work against already-cloned copies.

It clones or pulls each repo, then per repo checks:

- **Tests**: discovers each project's suite and runs it, reporting pass counts
  and any failure with its output.
- **CI**: is there a workflow, does it run on push, and would it fail when the
  tests fail? A workflow that finds zero tests and exits green is worse than
  none, so that case is reported specifically.
- **Secrets and dangerous patterns**: delegates to the
  `pre-launch-security-audit` scanner when it is available. For a hand scan,
  enumerate with `find` and pipe into the matcher:
  `find REPO -type f -print0 | xargs -0 grep -lE 'ghp_|github_pat_|x-access-token'`.
  Plain `grep -r` on this machine is ugrep, which skips `.git` in recursive mode
  even when pointed straight at it, and `scan_secrets.py` filters by extension,
  so an extensionless `.git/config` escapes both. Check `.git/config`, `.npmrc`,
  `.netrc` and `pip.conf` by path.
- **`.gitignore` covers `.env`**, and `.env` is not in the git history.
- **Conventions**: LICENSE, README, BACKLOG present; and whether the root
  README's project table matches the directories on disk, which is the single
  most common drift in a numbered-projects layout.
- **README prose tells**: em dashes, "not X, but Y", emoji, checkmark bullets,
  hype verbs. Counts only; see the judgment note below.

Two checks the script leaves to you:

**Commit attribution.** GitHub credits a commit to an account only when the
author email matches one. A commit made with a fallback address such as
`<user>@<hostname>.local` pushes fine, shows in `git log` and on the web, and
adds nothing to the contribution graph; no warning exists anywhere. Check the
last few commits per repo:

```bash
gh api repos/OWNER/REPO/commits --jq '.[0:5][] | .author.login'
```

Flag any `null`, report the offending author email, and give the fix:
`git config --global user.email <id>+<login>@users.noreply.github.com`. Before
the sweep, confirm the machine has a global `user.email` at all
(`git config --global user.email`); an empty answer means every new commit is
mis-attributed by default.

**Read a verifier before running it.** Small projects fuse audit and build: a
script named `check`, which the README presents as the thing to trust, may call
the build step and rewrite the artefact it is checking. In a task that must
leave the sources untouched, grep the project's own verification command for
writes to the tree (a file opened for writing, a build or generator invocation)
before running it, and prefer the narrowest suite that gives the same evidence,
usually the per-project tests. The report names the command that ran and the
command that was refused, with the reason; without that a reader cannot tell
whether the numbers came from a mutating run.

### 3. Judge before reporting

The script produces candidates. Two kinds need a human-level decision and must
not go into the report as findings on the script's say-so:

**Prose tells are counts; the verdict needs a reader.** A README with seven em
dashes may be carefully written prose or may be LLM output; the number cannot
tell you which. Read the file. Deliberate prose stays. Only flag it when the
other markers are there too (emoji as icons, checkmark bullets,
"seamlessly / powerful / unlock", invented testimonials) or when the
"not X, but Y" construction appears several times in a short file.

**Skip what does not apply, and say you skipped it.** A pure library has no
rate limiting, no security headers and no og:image, and reporting their absence
is noise that costs the reader's attention for the rest of the report. Web
checks apply to things that serve requests; SEO checks apply to things with a
site. State the exclusion once rather than listing non-applicable items.

If a check produced a false positive, fix the check. A scanner that cries wolf
gets ignored within two runs, which is worse than not running it.

### 4. Report

Sort by consequence across the whole portfolio, mixing repos; the reader wants
to know what to do first:

```markdown
## Portfolio audit: <N> repos, <date>

**Headline:** <one sentence: the thing to fix first, and how widespread it is.>

### New since <last run date>
| Repo | Finding | Impact |
|---|---|---|

### Portfolio-wide patterns
<Things true of several repos. Each is one decision.>

### Healthy — checked and fine
<Test counts, clean scans, conventions held. This section is what makes the
report trustworthy: it shows the pass was thorough rather than lucky.>

### Not applicable here
<Which checks were skipped and why, in one line.>
```

Then offer fixes in priority order. Anything mechanical and repo-wide (a missing
`.gitignore` line, an absent CI workflow) can be applied across all repos in one
go; anything touching code gets its own review.

### 5. Deliver

With push access: a branch per repo, one focused commit, PR per repo. Without:
`git format-patch` per repo plus a one-page apply guide, and verify at least one
patch applies to a fresh clone and the tests still pass afterwards; a patch
that does not apply is not a deliverable.

Either way, write the state file so the next run can say "new since".

## Related skills

- `pre-launch-security-audit`: the deep pass on anything that serves requests.
- `vibecode-tech-audit`: for repos that publish a site or docs page.
- `de-ai-slop-ui`: the copy section, when README prose needs work.
- `new-project-scaffold`: when the audit finds a project that drifted from the
  layout, it encodes what the layout is.
