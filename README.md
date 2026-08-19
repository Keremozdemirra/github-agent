# github-agent

Agents and skills for running a repository portfolio rather than a repository.

Running one repository is a solved problem. Running fifteen is a
different job, and it is mostly attention allocation: which repository has gone
quiet, which backlog has drifted from what the code actually does, which pull
request has been open long enough to have become a merge conflict, which README
describes a project that no longer exists.

This repository holds the agents and skills for that job. It is the pack behind
the daily loop that advances the rest of the portfolio, and the first place a
change to how that loop behaves should land.

It exists because the work is genuinely repeatable. The same audit, the same
grooming pass, the same release note, the same "this repository claims a
convention it no longer holds" check — written once, run everywhere.

## What this is not

It is not a CI system and does not replace one. It reads the state
of a repository and acts on judgement; a test suite is what tells you whether
the code works.

It is not a GitHub API wrapper. Where `gh` already does the job, these skills
call `gh` rather than reimplementing it.

It does not merge anything. Every skill here stops at the pull request.

## How to use this

These are skills for Claude, not a command-line tool. There is nothing to
install and nothing to import — you describe the work and the matching skill
fires on its own.

**In Claude Code or Cowork**, once the skills are on your machine:

```bash
bash ~/Desktop/agent/_setup/sync-skills.sh
```

That clones every agent repository and links its `skills/` into `~/.claude/skills`,
so they are available in every session and every folder. Re-run it whenever the
daily loop ships something new — it pulls rather than re-clones.

Then simply ask. Each skill's `description` frontmatter is written to match how
the request actually gets phrased, in English or Turkish, so you do not name the
skill and generally should not have to think about which one applies.

**If nothing fires**, that is a defect in the skill rather than in how you
asked. The description was written for the wrong phrasing. Say what you asked
and what you expected, and it gets fixed — that feedback is more valuable than
working around it.

**What is actually built** is the Done section of [BACKLOG.md](BACKLOG.md).
Everything under Queue is planned and does not exist yet. The daily loop builds
one item a day; the table above is the intended shape, not the current state.

## Layout

```
agents/
  <name>.md           one specialist, its brief and its boundaries
skills/
  <name>/
    SKILL.md          the instruction, with triggering description frontmatter
    scripts/          only where deterministic code beats instruction
examples/
  <name>/             worked example on real input, with the output committed
```

## Roadmap

See [BACKLOG.md](BACKLOG.md). The first unchecked item is the one being built.

## Planned contents

Nothing here is built yet. This table is the intended shape, and the daily loop
fills it in one item at a time.

| # | Skill | What it does |
| --- | --- | --- |
| 001 | [portfolio-sweep](skills/portfolio-sweep) | Audit every repository in one pass and report only what changed since the last run: broken suites, missing CI, secrets, . |
| 002 | [backlog-groom](skills/backlog-groom) | Read a BACKLOG against the code that now exists. |
| 003 | [pr-review](skills/pr-review) | Review a pull request against the repository's own stated standard rather than a generic checklist — the rules in its BACKLOG, the conventions in its sibling projects, the voice of its existing README. |
| 004 | [daily-loop-runbook](skills/daily-loop-runbook) | The runbook the scheduled loop follows, versioned here rather than in the loop repository, so the instruction and the agents that carry it out stay together. |
| 005 | [repo-scaffold](skills/repo-scaffold) | Create a repository that matches the house conventions from the first commit: README with a 'what this is not' section, BACKLOG with the standing rules block, LICENSE, . |
| 006 | [stale-pr-triage](skills/stale-pr-triage) | Find open pull requests that have gone quiet, work out whether each is waiting on a decision, a conflict or nothing, and say which to close. |
| 007 | [release-notes](skills/release-notes) | Write the release note from what the commits actually changed, not from their subject lines, and say plainly what a user has to do differently. |
| 008 | [ci-bootstrap](skills/ci-bootstrap) | Add the smallest CI that would actually have caught the last three things that broke, rather than the standard matrix nobody reads. |
| 009 | [secret-sweep](skills/secret-sweep) | Scan history as well as the working tree, and say what to do about a secret that is already in a published commit — rotation first, rewriting second. |
| 010 | [convention-drift](skills/convention-drift) | Check whether a repository still holds the conventions its own README claims, and report the gap as a diff rather than a complaint. |

## Licence

MIT. See [LICENSE](LICENSE).
