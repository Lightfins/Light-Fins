# Ralph Agent Instructions (Claude Code CLI)

## Rules
- Complete exactly ONE user story per iteration: the highest-priority story where `passes: false`.
- Keep the diff minimal; touch other files only to make the checks pass.
- Commit only when every check passes (green-to-green).

## Steps
1. Read `scripts/ralph/prd.json`, then `scripts/ralph/progress.txt` (start with "Codebase Patterns").
2. Implement the chosen story.
3. Run the checks CI runs (`.github/workflows/ci.yml`). Today that is, from `frontend/`: `npm ci` (if `node_modules/` is missing), `npx tsc --noEmit`, `npm run build`.
4. Set that story's `passes: true` in `prd.json`.
5. Append a progress entry (format below). Add durable conventions and gotchas to "Codebase Patterns" at the top of `progress.txt`.
6. Commit all of this iteration's changes, including `prd.json` and `progress.txt`, as one Conventional Commit: `feat: [ID] - [Title]`.

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

## Stop condition
If ALL stories in prd.json have `passes: true`, respond with exactly:
<promise>COMPLETE</promise>
