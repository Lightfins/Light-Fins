# Agent Instructions

> Mirrored across CLAUDE.md, AGENTS.md, and GEMINI.md so every AI environment loads the same rules. Edit all three identically; CI fails when they differ.

You are the orchestration layer of a 3-layer architecture. It pushes deterministic work into code because LLM errors compound per step (90% accuracy per step ≈ 59% success over 5 steps).

## The 3 Layers

| Layer | Lives in | Role |
|-------|----------|------|
| 1. Directives | `directives/*.md` | SOPs: goal, inputs, scripts, outputs, edge cases, learnings |
| 2. Orchestration | you | Read the directive, run its scripts in order, handle errors, ask when inputs are ambiguous, record learnings |
| 3. Execution | `execution/*.py` | Deterministic, commented Python for API calls, data processing, files, and databases. Secrets come from `.env` |

Example: to fill an application PDF, read `directives/generate_pdf_application.md`, then run `execution/fill_sanlam_pdf.py` with the inputs it names.

## Operating Principles

1. **Reuse before you write.** Check `execution/` for a script that fits; write a new one only when none does.
2. **Self-anneal on failure:** read the stack trace → root-cause → fix the script → re-run it → record the learning in the directive's `## Learnings`. Ask the user before re-running anything that spends paid tokens or credits.
3. **Directives are living runbooks.** Edit existing directives in place to add learnings (API limits, timing, edge cases). Ask before creating a new directive or rewriting one.
4. **Skills** live in `.claude/skills/*/SKILL.md`. Claude Code loads them by description; other agents read the SKILL.md whose `description` matches the task.

## Files

- **Deliverables:** what the user receives: the filled application PDF, or a Google Doc when they run `/save-to-google-docs`.
- **Intermediates:** `.tmp/` holds scratch data. It is gitignored and safe to delete and regenerate.
- **Secrets:** `.env`, `credentials.json`, `token.json` are gitignored. Read them at runtime and keep them local.
