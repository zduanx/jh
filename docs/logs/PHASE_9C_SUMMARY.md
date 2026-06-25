# Phase 9C: Branch/PR Workflow (`dev.sh` commands) + branch-protected `main`

**Status**: ✅ Completed
**Date**: June 25, 2026
**Goal**: Replace direct-to-`main` commits (`jgit`) with a native-GitHub branch→PR→merge workflow, wrapped in short `dev.sh` commands — and **protect `main`** (merge-only) so every change goes through a reviewable, CI-gateable PR.

> Pure local git/PR tooling + a one-time GitHub branch-protection setting. The CI *gate*
> lights up in **9D** (commands no-op gracefully until then). Phase 9: 9A Terraform →
> 9B secrets → **9C PR flow** → 9D CI → 9E CD.

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

## Key Achievements

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
  branch protection refuses it server-side once 9D's CI lands)

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

## What was built / done

- **6 commands** in `dev_git.sh` (sourced by `dev.sh`): `jbranch`, `jsave`, `jpr`,
  `jprstatus`, `jland`, `jprco` — guarded, idempotent; `jsave` refuses on `main`.
- **`main` branch-protected** (merge-only) via the GitHub API:
  `gh api -X PUT repos/zduanx/jh/branches/main/protection` →
  *Require a pull request before merging*; `enforce_admins=false` (admin escape hatch kept).
  Web equivalent: github.com/zduanx/jh/settings/branches.
- **`jgit` retained** as the (now admin-only, pre-protection) direct-to-main escape hatch.

## Testing & Validation

**Verified end-to-end** (dogfooded — these PRs were the first real uses):
- ✅ `jbranch` → off fresh main; dirty-tree prompt (stash/commit/abort)
- ✅ `jsave` → commits on a branch; **refuses on main** (suggests jbranch/jgit)
- ✅ `jpr` → opened **PR #1**; idempotent (re-run reports the existing PR)
- ✅ `jprstatus` → showed the PR + checks
- ✅ `jland` → squash-merged **PR #1** and **PR #2** into protected `main`, deleted branch,
  returned to fresh main — proving merge-only `main` works (PR merge passes; direct push blocked)
- ✅ **Bonus:** opening a PR triggers **Vercel's preview deploy**, and merging triggers
  Vercel's **production** deploy — frontend CD is already live via Vercel's GitHub integration

---

## Next Steps → Phase 9D

The CI workflow (`.github/workflows/ci.yml`) — runs the test suites on every push/PR. Once it
exists, `jprstatus` shows real check results and `jland`'s gate (plus branch protection) actually
blocks merging red PRs. The commands built here need no changes — the CI just populates the
checks they already read.

---

## File Structure

```
jh/
├── dev_git.sh   # jbranch, jsave, jpr, jprstatus, jland, jprco
└── dev.sh       # sources dev_git.sh (+ jgit kept as admin escape hatch)
```

**Key files**:
- [dev_git.sh](../../dev_git.sh) — the branch/PR commands (matching existing `j*` conventions)

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
