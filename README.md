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
so they are available in every session and every folder. Re-run it whenever one of
these repositories ships something new — it pulls rather than re-clones.

Then simply ask. Each skill's `description` frontmatter is written to match how
the request actually gets phrased, in English or Turkish, so you do not name the
skill and generally should not have to think about which one applies.

**If nothing fires**, that is a defect in the skill rather than in how you
asked. The description was written for the wrong phrasing. Say what you asked
and what you expected, and it gets fixed — that feedback is more valuable than
working around it.

**What is actually built** is listed under Contents below and in the Done
section of [BACKLOG.md](BACKLOG.md). Everything under Queue is planned and does
not exist yet.

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

`examples/` is empty so far.

## Roadmap

See [BACKLOG.md](BACKLOG.md). The first unchecked item is the one being built.

## Contents

| Skill | What it does |
| --- | --- |
| [repo-portfolio-audit](skills/repo-portfolio-audit) | Audit every repository in one pass and report only what changed since the last run. |

| Agent | What it does |
| --- | --- |
| [hata-avcisi](agents/hata-avcisi.md) | Finds a bug's root cause from evidence rather than guesswork. |
| [kod-review](agents/kod-review.md) | Reviews a change the way a senior engineer would, before it is committed. |

These arrived already written and in daily use, rather than being built against the queue below — which is why most carry no item number. Some have Turkish bodies: they were written in the language they are used in, and translating them is a queue item rather than a blocker.

Everything still under Queue in [BACKLOG.md](BACKLOG.md) does not exist
yet.
## Licence

MIT. See [LICENSE](LICENSE).
