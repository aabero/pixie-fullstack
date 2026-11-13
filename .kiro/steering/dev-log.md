---
inclusion: always
---

# Developer log

This file is a project rule for spec task work. To adjust it, edit this file. To turn it off, delete this file.

## When it applies

Whenever you finish a spec task (a task from any `tasks.md` under `.kiro/specs/`), append one entry to `docs/dev-log.md` before you report the task as done. Do this for every task, including spike, verification and checkpoint tasks. Do not write an entry for ordinary chat questions or for tasks you did not complete.

If a task is only partly done or is blocked, still append an entry and set the status to `partial` or `blocked`.

## File rules

- The single log file is `docs/dev-log.md`. Create it with the heading `# Developer log` if it does not exist.
- Append only. Never rewrite, reorder or delete earlier entries.
- Newest entry goes at the end of the file.
- Keep each entry short: 5 to 15 lines. Link to files by path instead of pasting code or long output.
- Never put secrets, tokens, credential values or personal data in the log.

## Entry format

```markdown
## Task <number> - <task title> (<YYYY-MM-DD>)

- Status: done | partial | blocked
- Spec: <feature-name>
- Requirements: <requirement and decision numbers from the task>
- What changed: <files and behavior, in a few bullets>
- Decisions: <choices you made that the spec did not dictate, or "none">
- Deviations from the design: <where you differed from design.md and why, or "none">
- Tests: <command run, for example `uv run pytest tests/...`, and the result; or "not run" with the reason>
- Follow-ups: <open issues, spike-dependent degradations that applied, or "none">
```

## Content guidance

- Use the task number exactly as written in `tasks.md` (for example `6.5`).
- If a task is marked SPIKE-DEPENDENT, state which spike outcome you relied on and whether the degradation path applied.
- Record deviations honestly, including small ones. If a deviation contradicts `requirements.md` or `design.md`, say so here and do not edit those documents.
- For optional test sub-tasks you skipped, write `skipped (optional)` under Tests.
- Take the date from the environment's current date, not from memory.
