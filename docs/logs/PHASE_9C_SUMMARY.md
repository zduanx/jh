# Phase 9C: Branch/PR Workflow (`dev.sh` commands)

**Status**: 📋 Planning
**Date**: June 24, 2026
**Goal**: Replace direct-to-`main` commits (`jgit`) with a native-GitHub branch→PR→merge workflow, wrapped in short `dev.sh` commands — so every change goes through a reviewable, CI-gateable PR.

> Independent of **9A** (Terraform migration) — pure local git/PR tooling, no secrets, no
> AWS, no production. The CI *gate* lights up in **9D**; 9B's commands are built to no-op
> gracefully until then. (Phase 9: 9A Terraform → 9B PR flow → 9C CI → 9D CD → 9E secrets.)

---

## Overview

The project currently commits straight to `main` via `jgit`. That works solo but has no review
gate and no place for CI to block bad changes. 9C introduces the **native-GitHub model**
(Option A, chosen over Meta-style stacked diffs for solo simplicity): **one branch = one PR =
many commits**, squash-merged together. The commits stack incrementally on a branch; the PR is
the reviewable unit; merge folds them into `main` as one clean commit.

This is a deliberate translation of the Meta muscle-memory workflow (grab dev → commit → submit →
land) onto GitHub primitives — *not* stacked PRs (which need extra tooling like Sapling/Graphite
and don't pay off for a single developer).

The commands wrap `git` + the GitHub CLI (`gh`). They are guarded and idempotent (safe to
re-run), match the existing `dev.sh` conventions (color vars, `JH_ROOT`, status echoes), and
**never silently lose uncommitted work** — `jbranch`/`jprco` dirty-check and offer
stash/commit/abort before switching.

**Included in this phase**:
- `jbranch "name"` — dirty-check → pull fresh `main` → create+switch branch
- `jsave "msg"` — commit (auto-push if a PR already exists for the branch)
- `jpr "title"` — push branch + open a PR (`gh pr create`)
- `jprstatus` — show the PR + its CI checks (the signal; no-ops cleanly pre-9C)
- `jland [--f]` — CI-gated squash-merge + delete branch + back to fresh `main`
- `jprco <N>` — checkout an existing PR (by number) to resume work on it
- Update `DEV_SHORTCUTS.md`

**Explicitly excluded**:
- Stacked PRs / Sapling / Graphite (Meta-style per-commit diffs) — deferred; not worth it solo
- Branch *protection* setup (a one-time GitHub UI step) — documented in 9C where the CI gate exists
- Auto-deploy on merge — that's 9D

---

## Key Achievements (planned)

### 1. The lifecycle commands
| Command | Wraps | Role (Meta analogue) |
|---------|-------|----------------------|
| `jbranch "name"` | `git checkout main && pull && checkout -b` | grab a dev / start work |
| `jsave "msg"` | `git add -A && commit` (+ push if PR exists) | commit (incrementally) |
| `jpr "title"` | `git push -u` + `gh pr create` | submit for review |
| `jprstatus` | `gh pr view` + `gh pr checks` | watch the CI signal |
| `jland [--f]` | `gh pr merge --squash --delete-branch` + sync main | land / ship |
| `jprco <N>` | `gh pr checkout N` | resume an existing PR |

### 2. Safety: never lose uncommitted work
- `jbranch` / `jprco` run `git status --porcelain` first; if dirty → prompt **stash / commit / abort**
- Untracked files are flagged (carried along by git, but warned so they don't sneak into a PR)
- `--f` on `jland` is an explicit override; without it, a non-green PR is refused client-side (and
  branch protection refuses it server-side once 9D lands)

### 3. Graceful pre-CI behavior
- `jprstatus` + `jland`'s gate degrade cleanly when **no checks exist** (before 9D) — they don't
  error; `jland` simply merges (same as today). The gate logic is present, waiting for 9D's CI to
  produce checks.

---

## Highlights

- **`jsave` is separate from `jpr`** — matches the real lifecycle (commit repeatedly, submit once),
  and fixes the ordering trap of "open a PR before there's anything to merge."
- **`jsave` auto-pushes once a PR exists** → the PR updates automatically (the "amend" need, handled
  without a separate command). New commits on the branch *are* the PR update.
- **`jland` squash-merges** → the branch's N WIP commits collapse into one clean `main` commit
  ("ship everything together," the Meta "land" semantics).
- **One branch = one PR.** Not "multiple stacked diffs" — that's a different (Phabricator/Sapling)
  model. On native GitHub, the branch is the unit and its commits merge as a whole.
- **Prereq: `gh` CLI** (`brew install gh && gh auth login`) — the `jpr`/`jland`/`jprstatus`/`jprco`
  commands wrap it. `jbranch`/`jsave` are pure git and work without it.

---

## Testing & Validation (planned)

**Manual** (end-to-end loop on a throwaway branch):
- [ ] `jbranch test/x` off a clean tree → on new branch, branched from fresh main
- [ ] `jbranch` with a dirty tree → prompts stash/commit/abort (no silent carry)
- [ ] `jsave "wip"` ×2 → two commits on the branch
- [ ] `jpr "Test"` → PR opened, URL printed; re-running reports the existing PR (idempotent)
- [ ] `jsave` after `jpr` → auto-pushes, PR updates
- [ ] `jprstatus` → shows the PR (and "no checks" pre-9C, without erroring)
- [ ] `jprco <N>` from a clean tree → checks out that PR
- [ ] `jland` → squash-merges, deletes branch, returns to fresh main
- [ ] Switching branches never touches the root `.env.local` (9A win, re-verified)

---

## Next Steps → Phase 9D

The CI workflow (`.github/workflows/ci.yml`) — runs the test suites on every push/PR. Once it
exists, `jprstatus` shows real check results and `jland`'s gate (plus branch protection) actually
blocks merging red PRs. The commands built here need no changes — the CI just populates the
checks they already read.

---

## File Structure (planned)

```
jh/
└── dev.sh    # jbranch, jsave, jpr, jprstatus, jland, jprco
                (+ existing jgit kept for quick main-direct work)
DEV_SHORTCUTS.md  # commands table updated
```

**Key files**:
- [dev.sh](../../dev.sh) — the new branch/PR commands (matching existing `j*` conventions)
- [DEV_SHORTCUTS.md](../../DEV_SHORTCUTS.md) — reference table

---

## Key Learnings

- **Branch vs PR:** a branch is an independent line of commits (pure git); a PR is a GitHub request
  to merge one branch into another, wrapping it with a diff + CI + review. The branch *holds* the
  work; the PR is the reviewed doorway into `main`.
- **Meta vs GitHub models differ.** Meta = "commit = diff, diffs stack, land the stack" (needs
  Sapling/Graphite to replicate on GitHub). Native GitHub = "branch = PR (many commits), merge one
  PR." 9C chooses the native model and collapses a "stack" into one squash-merged PR.
- **The commands must never silently misplace WIP** — the dirty-check + stash bridge is the core of
  safe branch-switching.

---

## References

- GitHub CLI (`gh`): https://cli.github.com/manual/
- `gh pr create` / `gh pr merge`: https://cli.github.com/manual/gh_pr
# 9C flow verified 05:31
