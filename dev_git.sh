#!/usr/bin/env bash
# Branch/PR workflow commands (Phase 9C). Sourced by dev.sh.
#
# Native-GitHub model: one branch = one PR = many commits, squash-merged.
#   jbranch "name"  -> start: pull fresh main, create+switch a branch
#   jsave "msg"     -> commit (auto-push if a PR exists for the branch)
#   jpr "title"     -> push branch + open a PR
#   jprstatus       -> show the PR + its CI checks
#   jland [--f]     -> CI-gated squash-merge + delete branch + back to fresh main
#   jprco <N>       -> checkout an existing PR (by number) to resume work
#
# Once `main` is branch-protected on GitHub, direct pushes to main are rejected, so
# this PR flow is the only path. jgit (direct-to-main) is kept for the rare unprotected op.
# Needs the gh CLI (brew install gh && gh auth login) for jpr/jland/jprstatus/jprco.

_JH_GIT_ROOT="${JH_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]:-${(%):-%x}}")" && pwd)}"

# --- helpers ---------------------------------------------------------------

# Is the working tree dirty (uncommitted tracked changes or staged)?
_jh_dirty() { [ -n "$(git -C "$_JH_GIT_ROOT" status --porcelain)" ]; }

# Prompt to handle a dirty tree before switching branches. Returns 0 to proceed.
_jh_handle_dirty() {
  if ! _jh_dirty; then return 0; fi
  echo -e "${YELLOW:-}  You have uncommitted changes:${NC:-}"
  git -C "$_JH_GIT_ROOT" status --short | sed 's/^/    /'
  echo -n "  [s]tash / [c]ommit-here / [a]bort? "
  read -r ans
  case "$ans" in
    s|S) git -C "$_JH_GIT_ROOT" stash push -u -m "jh-auto-stash" && echo "  ✓ stashed (restore: git stash pop)" ;;
    c|C) echo "  → run jsave first, then retry"; return 1 ;;
    *)   echo "  aborted"; return 1 ;;
  esac
}

# The PR number for the current branch, if one is open (empty otherwise).
_jh_current_pr() {
  gh pr view --json number --jq .number 2>/dev/null
}

# --- commands --------------------------------------------------------------

# jbranch "name" — start fresh: clean dirty tree, pull main, create+switch branch.
jbranch() {
  local name="$1"
  [ -z "$name" ] && { echo -e "${RED:-}✗ usage: jbranch \"branch-name\"${NC:-}"; return 1; }
  cd "$_JH_GIT_ROOT" || return 1
  _jh_handle_dirty || return 1
  echo -e "${BLUE:-}=== jbranch: $name ===${NC:-}"
  git checkout main >/dev/null 2>&1 || { echo -e "${RED:-}✗ can't switch to main${NC:-}"; return 1; }
  git pull --ff-only origin main 2>&1 | tail -1
  git checkout -b "$name" 2>&1 | tail -1 || return 1
  echo -e "${GREEN:-}✓ on '$name' (off fresh main)${NC:-}"
}

# jsave "msg" — commit current work; auto-push if a PR already exists.
jsave() {
  local msg="$1"
  [ -z "$msg" ] && { echo -e "${RED:-}✗ usage: jsave \"commit message\"${NC:-}"; return 1; }
  cd "$_JH_GIT_ROOT" || return 1
  local branch; branch="$(git branch --show-current)"
  if [ "$branch" = "main" ]; then
    echo -e "${YELLOW:-}  ⚠ you're on main. jsave is for branch work — run jbranch first,${NC:-}"
    echo -e "${YELLOW:-}    or use jgit for an intentional direct-to-main commit.${NC:-}"
    return 1
  fi
  git add -A
  if git diff --cached --quiet; then echo "  nothing to commit"; return 0; fi
  git commit -m "$msg" 2>&1 | tail -1 || return 1
  local n; n="$(git rev-list --count main..HEAD 2>/dev/null)"
  echo -e "${GREEN:-}✓ committed ($n commit(s) on '$branch')${NC:-}"
  # if a PR exists, push so it updates
  if [ -n "$(_jh_current_pr)" ]; then
    git push 2>&1 | tail -1 && echo "  ✓ pushed (PR updated)"
  fi
}

# jpr "title" — push the branch and open a PR.
jpr() {
  local title="$1"
  cd "$_JH_GIT_ROOT" || return 1
  local branch; branch="$(git branch --show-current)"
  [ "$branch" = "main" ] && { echo -e "${RED:-}✗ on main — jbranch first${NC:-}"; return 1; }
  if _jh_dirty; then echo -e "${YELLOW:-}  uncommitted changes — jsave first${NC:-}"; return 1; fi
  # already a PR?
  local existing; existing="$(_jh_current_pr)"
  if [ -n "$existing" ]; then
    echo -e "${GREEN:-}✓ PR #$existing already open:${NC:-} $(gh pr view --json url --jq .url 2>/dev/null)"
    return 0
  fi
  [ -z "$title" ] && title="$branch"
  git push -u origin "$branch" 2>&1 | tail -1
  gh pr create --base main --head "$branch" --title "$title" --body "Opened via jpr." 2>&1 | tail -1
  echo -e "${GREEN:-}✓ PR opened — CI will run${NC:-}"
}

# jprstatus — show the current PR + its CI checks.
jprstatus() {
  cd "$_JH_GIT_ROOT" || return 1
  local pr; pr="$(_jh_current_pr)"
  [ -z "$pr" ] && { echo "  no open PR for this branch"; return 0; }
  echo -e "${BLUE:-}=== PR #$pr ===${NC:-}"
  gh pr view --json title,url,state --jq '"  \(.title)\n  \(.url)\n  state: \(.state)"' 2>/dev/null
  echo "  checks:"
  gh pr checks 2>/dev/null | sed 's/^/    /' || echo "    (no checks yet — CI lands in 9D)"
}

# jland [--f] — squash-merge the PR (CI-gated), delete the branch, back to fresh main.
jland() {
  cd "$_JH_GIT_ROOT" || return 1
  local force=false; [ "$1" = "--f" ] && force=true
  local pr; pr="$(_jh_current_pr)"
  [ -z "$pr" ] && { echo -e "${RED:-}✗ no open PR for this branch${NC:-}"; return 1; }
  # CI gate (client-side; branch protection also enforces server-side once it exists)
  if ! $force; then
    local checks; checks="$(gh pr checks 2>/dev/null)"
    if echo "$checks" | grep -qiE "fail|error"; then
      echo -e "${RED:-}✗ CI not green:${NC:-}"; echo "$checks" | sed 's/^/    /'
      echo "  fix, or jland --f to override"
      return 1
    fi
  fi
  echo -e "${BLUE:-}=== jland: merge PR #$pr ===${NC:-}"
  gh pr merge "$pr" --squash --delete-branch 2>&1 | tail -2 || return 1
  git checkout main >/dev/null 2>&1
  git pull --ff-only origin main 2>&1 | tail -1
  echo -e "${GREEN:-}✓ landed PR #$pr → main; on fresh main${NC:-}"
}

# jprco <N> — check out an existing PR's branch to resume work.
jprco() {
  local num="$1"
  [ -z "$num" ] && { echo -e "${RED:-}✗ usage: jprco <PR-number>${NC:-}"; return 1; }
  cd "$_JH_GIT_ROOT" || return 1
  _jh_handle_dirty || return 1
  gh pr checkout "$num" 2>&1 | tail -2 && echo -e "${GREEN:-}✓ on PR #$num's branch${NC:-}"
}
