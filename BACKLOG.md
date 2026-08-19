# Backlog

Working queue. The next unchecked item is the one being built. An item stays
unchecked and picks up a `status:` note if it spans more than one working
session — finishing something half-built takes priority over starting the next
one.

Rules of thumb applied to every item:

- one job per skill, done properly, rather than a bundle of half-features
- a skill earns its place only if it beats writing the instruction out by hand;
  if a good prompt does the same job, the skill is overhead
- the `description` frontmatter is the whole trigger mechanism — write it so the
  skill fires on how the work is actually asked for, including in Turkish
- every skill carries a worked example on real input, not a toy
- no claim about a framework, standard, regulation or method without a citation
  and a vintage
- an agent gets its own file only when it needs a different judgement, not a
  different topic

---

## Done

Nothing yet.

## Queue

- [ ] **001 — portfolio-sweep** · Audit every repository in one pass and report only what changed since the last run: broken suites, missing CI, secrets, .gitignore gaps, README tables that no longer match the directories on disk, conventions a repository claims but no longer holds. State file so a weekly run reports new findings rather than re-listing old ones.
- [ ] **002 — backlog-groom** · Read a BACKLOG against the code that now exists. Tick what shipped, delete what the design outgrew, re-rank what the last three items changed, and flag every entry that has sat unchanged long enough to be a decision nobody made.
- [ ] **003 — pr-review** · Review a pull request against the repository's own stated standard rather than a generic checklist — the rules in its BACKLOG, the conventions in its sibling projects, the voice of its existing README.
- [ ] **004 — daily-loop-runbook** · The runbook the scheduled loop follows, versioned here rather than in the loop repository, so the instruction and the agents that carry it out stay together.
- [ ] **005 — repo-scaffold** · Create a repository that matches the house conventions from the first commit: README with a 'what this is not' section, BACKLOG with the standing rules block, LICENSE, .gitignore, and the layout its kind of work uses.
- [ ] **006 — stale-pr-triage** · Find open pull requests that have gone quiet, work out whether each is waiting on a decision, a conflict or nothing, and say which to close.
- [ ] **007 — release-notes** · Write the release note from what the commits actually changed, not from their subject lines, and say plainly what a user has to do differently.
- [ ] **008 — ci-bootstrap** · Add the smallest CI that would actually have caught the last three things that broke, rather than the standard matrix nobody reads.
- [ ] **009 — secret-sweep** · Scan history as well as the working tree, and say what to do about a secret that is already in a published commit — rotation first, rewriting second.
- [ ] **010 — convention-drift** · Check whether a repository still holds the conventions its own README claims, and report the gap as a diff rather than a complaint.
