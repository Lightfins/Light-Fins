#!/usr/bin/env bash
set -euo pipefail

# Ralph (Claude Code CLI edition)
# - Runs Claude repeatedly until all PRD items are complete
# - Each iteration is a fresh Claude invocation (fresh context)
# - Memory persists via git commits, prd.json, progress.txt, and AGENTS.md updates
#
# REQUIREMENTS:
# - git repo
# - jq installed
# - Claude Code CLI installed & authenticated
#
# USAGE:
#   chmod +x scripts/ralph/ralph_claude.sh
#   ./scripts/ralph/ralph_claude.sh 25
#
# OPTIONAL ENV:
#   CLAUDE_BIN="claude"
#   CLAUDE_FLAGS="--dangerously-skip-permissions"
#   RALPH_SLEEP_SECS=2
#   RALPH_BASE_BRANCH="main"   # or "master"
#   RALPH_DIR="scripts/ralph"  # override if you store elsewhere

MAX_ITERATIONS="${1:-10}"

CLAUDE_BIN="${CLAUDE_BIN:-claude}"
CLAUDE_FLAGS="${CLAUDE_FLAGS:---dangerously-skip-permissions}"
RALPH_SLEEP_SECS="${RALPH_SLEEP_SECS:-2}"
RALPH_DIR="${RALPH_DIR:-scripts/ralph}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "$(basename "$SCRIPT_DIR")" != "ralph" ]]; then
  # If invoked from elsewhere, still honor RALPH_DIR relative to repo root
  true
fi

# Resolve repo root
if ! git_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  echo "ERROR: Not inside a git repository."
  exit 1
fi

RALPH_PATH="$git_root/$RALPH_DIR"
PRD_JSON="$RALPH_PATH/prd.json"
PROGRESS_TXT="$RALPH_PATH/progress.txt"
PROMPT_MD="$RALPH_PATH/prompt.md"
PREFLIGHT_MD="$RALPH_PATH/preflight.md"

echo "🚀 Ralph (Claude) starting in: $git_root"
echo "📁 Ralph dir: $RALPH_PATH"
echo "🔁 Max iterations: $MAX_ITERATIONS"
echo

# Hard checks
command -v jq >/dev/null 2>&1 || { echo "ERROR: jq not found. Install jq."; exit 1; }
command -v "$CLAUDE_BIN" >/dev/null 2>&1 || { echo "ERROR: Claude CLI not found (CLAUDE_BIN=$CLAUDE_BIN)."; exit 1; }

[[ -f "$PROMPT_MD" ]] || { echo "ERROR: Missing $PROMPT_MD"; exit 1; }
[[ -f "$PREFLIGHT_MD" ]] || { echo "ERROR: Missing $PREFLIGHT_MD"; exit 1; }
[[ -f "$PRD_JSON" ]] || { echo "ERROR: Missing $PRD_JSON"; exit 1; }
[[ -f "$PROGRESS_TXT" ]] || { echo "ERROR: Missing $PROGRESS_TXT"; exit 1; }

# Extract branchName from prd.json
BRANCH_NAME="$(jq -r '.branchName // empty' "$PRD_JSON")"
if [[ -z "$BRANCH_NAME" || "$BRANCH_NAME" == "null" ]]; then
  echo "ERROR: prd.json missing branchName."
  exit 1
fi

# Determine base branch
if [[ -n "${RALPH_BASE_BRANCH:-}" ]]; then
  BASE_BRANCH="$RALPH_BASE_BRANCH"
else
  # Best effort: prefer main, then master, else current
  if git show-ref --verify --quiet refs/heads/main; then
    BASE_BRANCH="main"
  elif git show-ref --verify --quiet refs/heads/master; then
    BASE_BRANCH="master"
  else
    BASE_BRANCH="$(git branch --show-current)"
  fi
fi

echo "🌿 Base branch: $BASE_BRANCH"
echo "🌿 Feature branch (from prd.json): $BRANCH_NAME"
echo

# Ensure working tree clean (avoid Claude committing your uncommitted changes)
if [[ -n "$(git status --porcelain)" ]]; then
  echo "ERROR: Working tree not clean. Commit/stash changes before running Ralph."
  git status --porcelain
  exit 1
fi

# Create or checkout feature branch
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME"; then
  git checkout "$BRANCH_NAME" >/dev/null
else
  git checkout "$BASE_BRANCH" >/dev/null
  git checkout -b "$BRANCH_NAME" >/dev/null
fi

echo "✅ On branch: $(git branch --show-current)"
echo

# ---------------------------
# PREFLIGHT: agent must say YES/NO
# ---------------------------
echo "🧪 Preflight check: asking agent if it can use this loop (YES/NO)..."
PREFLIGHT_OUT="$(
  cat "$PREFLIGHT_MD" | "$CLAUDE_BIN" $CLAUDE_FLAGS 2>&1 || true
)"

# Extract first non-empty line
PREFLIGHT_FIRST_LINE="$(
  printf "%s\n" "$PREFLIGHT_OUT" | awk 'NF {print; exit}'
)"

if [[ "$PREFLIGHT_FIRST_LINE" != "YES" ]]; then
  echo
  echo "❌ Preflight failed. Agent did NOT confirm usability."
  echo "First line was: $PREFLIGHT_FIRST_LINE"
  echo
  echo "Full preflight output:"
  echo "----------------------"
  printf "%s\n" "$PREFLIGHT_OUT"
  echo "----------------------"
  exit 1
fi

echo "✅ Preflight: YES"
echo

# Helper: check completion by scanning prd.json
all_done() {
  local remaining
  remaining="$(jq '[.userStories[] | select(.passes == false)] | length' "$PRD_JSON")"
  [[ "$remaining" -eq 0 ]]
}

# Quick status
REMAINING="$(jq '[.userStories[] | select(.passes == false)] | length' "$PRD_JSON")"
echo "📌 Stories remaining: $REMAINING"
echo

if all_done; then
  echo "✅ Nothing to do. All stories already pass."
  exit 0
fi

# Run loop
LOG_DIR="$RALPH_PATH/logs"
mkdir -p "$LOG_DIR"

for i in $(seq 1 "$MAX_ITERATIONS"); do
  echo "════════════════════════════════════════"
  echo "═══ Iteration $i / $MAX_ITERATIONS"
  echo "════════════════════════════════════════"

  # Each iteration: fresh Claude invocation
  ITER_LOG="$LOG_DIR/iteration-$i.txt"

  set +e
  cat "$PROMPT_MD" | "$CLAUDE_BIN" $CLAUDE_FLAGS 2>&1 | tee "$ITER_LOG"
  CLAUDE_EXIT="${PIPESTATUS[1]}"
  set -e

  # Stop condition via explicit token
  if grep -q "<promise>COMPLETE</promise>" "$ITER_LOG"; then
    echo
    echo "✅ COMPLETE signal received."
    exit 0
  fi

  # Stop condition if prd.json shows all passes true
  if all_done; then
    echo
    echo "✅ All stories now pass (prd.json)."
    exit 0
  fi

  # If Claude errored, still continue (Ralph pattern), but show it.
  if [[ "$CLAUDE_EXIT" -ne 0 ]]; then
    echo
    echo "⚠️ Claude exited non-zero (code=$CLAUDE_EXIT). Continuing."
  fi

  sleep "$RALPH_SLEEP_SECS"
done

echo
echo "⚠️ Max iterations reached without completion."
echo "Check:"
echo "  - $PRD_JSON"
echo "  - $PROGRESS_TXT"
echo "  - $LOG_DIR/"
exit 1
