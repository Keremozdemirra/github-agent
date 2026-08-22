# backlog-groom on github-agent's own BACKLOG.md

Real input, not a toy: this repository's own `BACKLOG.md` as it stood before
this skill existed, captured here as `BACKLOG.md`. Running the check against
it is what exposed the need for the skill in the first place.

## Command

```bash
python3 scripts/groom.py --repo . --json
```

Output: `findings.json`.

## The one finding

```
[DUPLICATE] line 29 — portfolio-sweep: overlaps 100% with already-shipped
'repo-portfolio-audit' — read both before building this
```

Queue item **001 — portfolio-sweep** reads: "Audit every repository in one
pass and report only what changed since the last run: broken suites, missing
CI, secrets, .gitignore gaps, README tables that no longer match the
directories on disk, conventions a repository claims but no longer holds.
State file so a weekly run reports new findings rather than re-listing old
ones."

The Done section already carries **repo-portfolio-audit**, "shipped
2026-08-20. Written before this repository existed and published here as-is;
no queue item." Its own SKILL.md description: "Sweeps every repository in a
portfolio in one pass and reports only what changed since last time... Keeps a
state file so a weekly run reports new findings rather than re-listing the
same ones."

## Judgment

These are the same job. `repo-portfolio-audit` was written and published
before this BACKLOG.md existed, so it was never checked against the Queue
item that already described it — the note "no queue item" on the Done line
says exactly that. The 100% overlap score is not a coincidence of vocabulary;
it is two descriptions of one skill.

**Outcome: delete Queue item 001.** Nothing needs building — the thing it
asked for has existed since 2026-08-20. The existing Done line already
explains why it carries no item number, so no rewrite is needed there either.
This is the DUPLICATE outcome the skill's SKILL.md calls for when the overlap
is genuine rather than adjacent: tick nothing, build nothing, remove the
stale ask, leave the record of what shipped exactly as it was.

This is also why the skill matters beyond this one repository: the failure
mode is silent. Nothing broke. The Queue item would have sat there, correct
looking, until someone spent a day rebuilding a skill that already existed.
