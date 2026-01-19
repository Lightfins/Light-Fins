# Ralph Agent Instructions (Claude Code CLI)

You are an autonomous coding agent working inside a git repository.

## Hard rules
- You must complete EXACTLY ONE user story per iteration.
- Choose the highest priority story where `passes: false`.
- Do not attempt other stories in this iteration.
- If you must change extra files to make checks pass, do so (minimal necessary).
- Never leave the repo in a broken state after committing.

## Your tasks (in order)
1) Read `scripts/ralph/prd.json`
2) Read `scripts/ralph/progress.txt` (especially "Codebase Patterns" at the top)
3) Ensure you are on the branch from `prd.json.branchName`
4) Pick the single highest priority story where `passes: false`
5) Implement that ONE story
6) Run quality checks (choose what exists; prefer in this order):
   - `npm run typecheck` (or `pnpm -s typecheck` / `yarn -s typecheck` if repo uses that)
   - `npm test` (or repo equivalent)
   - Any repo-specific lint/build checks if present and fast
7) If you learned stable conventions/gotchas, update the nearest `AGENTS.md` in directories you touched
8) Commit changes with message: `feat: [ID] - [Title]`
9) Update `scripts/ralph/prd.json` to set that story `passes: true`
10) Append an entry to `scripts/ralph/progress.txt` using the format below

## Progress.txt append format (append at bottom)
## YYYY-MM-DD - [Story ID]
- Implemented:
  - (brief)
- Files changed:
  - path/to/file
- Checks run:
  - command -> result
- Learnings:
  - (short)
---

## Codebase Patterns (top of progress.txt)
If you discover durable patterns/gotchas that will help future iterations, add them under the "## Codebase Patterns" section near the top of progress.txt AND (when appropriate) also into AGENTS.md.

## Stop condition
If ALL stories in prd.json have `passes: true`, respond with exactly:
<promise>COMPLETE</promise>
