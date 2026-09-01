---
name: backlog-groom
description: Reads a repository's BACKLOG.md against the code that now exists — ticks off Queue items that already shipped under a different name, flags Done items whose file no longer exists on disk, and surfaces Queue items nobody has touched in weeks so they read as a decision rather than an oversight. Use this skill whenever the user wants to groom, tidy, prune, reconcile or sanity-check a backlog or roadmap file, asks "does this backlog still match reality", "hangi maddeler zaten yapılmış", "backlog'u temizle", "bu liste güncel mi", or is about to pick the next item from a Queue and wants to know it is not already done; and periodically on any repository whose BACKLOG.md is more than a few items deep, since drift here is silent — nothing breaks, it just wastes the next person's day.
---

# Backlog groom

A BACKLOG.md drifts the same way any index does: the thing it points at keeps
moving and the index does not follow. Two failure modes matter here, and they
look nothing alike from inside the file.

The first is a Queue item that already shipped. It happens when work lands
under a name nobody chose in advance — a skill gets built, published, and given
a better name than the one sitting in the Queue — and the two are never
reconciled. Nobody notices until the Queue item is picked up and half-built
before the duplication surfaces. The second is a Done item whose file was later
deleted, renamed past recognition, or never actually committed — the backlog
now asserts something false about the repository's own state.

A third thing is not a failure exactly, but worth surfacing: a Queue item that
has sat on the same line, unedited, for longer than everything around it. That
is not evidence it is wrong. It is evidence nobody has looked at it recently
enough to say whether it is still right — which is a decision, made or not.

## Workflow

### 1. Run the check

```bash
python3 "$SKILL_DIR/scripts/groom.py" --repo path/to/repo
```

`--stale-days N` (default 21) sets how long a Queue line sits before it counts
as stale. `--dup-threshold F` (default 0.55) sets the keyword-overlap
coefficient between a Queue item's text and something already shipped — lower
it if a repository's BACKLOG entries are written tersely enough that real
duplicates score below the default.

It parses the Done and Queue sections, reads what actually exists on disk
(`skills/`, `agents/`, `projects/NNN-*`) and the root README's Contents table,
and reports three kinds of candidate:

- **DUPLICATE** — a Queue item whose words overlap heavily with something
  already in Done or in the README table. The overlap score is reported so you
  can judge it rather than trust it.
- **MISSING** — a Done item whose name matches nothing on disk.
- **STALE** — a Queue item whose line in BACKLOG.md has not been touched (via
  `git blame`) in at least `--stale-days`. An item carrying an inline
  `status:` note is exempt — that is the file's own way of saying it is
  mid-flight, not forgotten.

### 2. Judge before editing

Every finding is a candidate, not a verdict, for the same reason
`repo-portfolio-audit` states it plainly: a script that reports things that are
fine as though they were problems gets ignored within two runs.

**DUPLICATE** — read the Queue item and whatever it overlaps with, in full. A
high score can mean genuine duplication (tick the Queue item, or delete it and
point to the shipped thing from its Done entry) or it can mean two things that
are adjacent but not the same job — a sweep skill and a triage skill share a
lot of vocabulary without being the same tool. Say which, in the commit or PR
that edits BACKLOG.md.

**MISSING** — check by hand before deleting the Done line. A rename the script
does not recognise is more likely than work that vanished; fix the Done entry's
name to match rather than erasing the record that it shipped.

**STALE** — this is not "delete it". Read the item against what shipped since
it was written. Three outcomes: it is still right and just hasn't come up yet
(leave it, nothing to do); the repository outgrew it (delete it, and say why in
the same place `run-through` notes go); or it should move up because recent
work made it more relevant, not less (re-rank it, one line, no rewrite of
neighbouring entries).

### 3. Edit BACKLOG.md

Match the file's own voice — the Rules-of-thumb block at the top and the Done
entries already there are the model. A Done line ticked by this skill gets the
same `· shipped <date>.` form as every other Done entry, plus one clause saying
what it turned out to be, if the name changed. A deleted Queue item leaves no
trace; BACKLOG.md is a working queue, not a changelog, and the commit that
removed it is the record.

Do not re-rank or reword anything the check did not flag. Grooming a backlog
and rewriting it are different jobs — this skill is the first one only.

## Related skills

- `repo-portfolio-audit` — the wider sweep this skill's DUPLICATE and MISSING
  checks borrow their "candidates, not verdicts" discipline from; run it first
  if you also want test, CI and convention findings across the same repository.
- `new-project-scaffold` — updates BACKLOG.md when a new project is scaffolded,
  which is the moment this skill's MISSING check has nothing to catch.
