---
inclusion: manual
---

# Legacy disposition and licensing checklist

Attach with `#legacy-and-licensing` when running tasks 12.2, 12.4, 19.1, 19.2 or 19.3. The spec wins if anything here conflicts with it (Requirements 18.1 to 18.18, 3.10, 3.17).

## Before any move or rewrite

- Run `git status` and confirm what is tracked, modified or untracked. Do not proceed over unrelated uncommitted work without telling the Operator.
- Operator_Content is any Operator-authored config, credential, Vault note or existing Store record. If any step would delete, overwrite or move it, abort that step, leave the content unchanged and report the file and the step (18.7, 18.13).
- Do not commit, push or switch branches. The Operator commits. Report what to include, such as the plan-file move (18.11).

## Legacy files (task 19.1)

- Use `git mv` only. No history rewrite, squash, amend or force push (18.8).
- Move into `legacy/`: unused Claude-oriented files (`CLAUDE.md`, `fullstack-agent.md`) and `start.bat` and `update.bat`. Originals stay byte-identical to their content in history (18.10).
- `start.sh` and `update.sh`: copy the originals into `legacy/` first, then adapt the root versions in place.
  - `start.sh` prints service status and a chat hint, and never starts, stops or restarts the Runtime (18.3).
  - `update.sh` is a shim to `pixie update`, with no blind pull-latest (18.5).
- Add `legacy/README.md` saying the files are retained pending the Operator's removal decision. Do not delete anything from `legacy/`.
- No Claude Code prerequisite and no `claude "set me up"` path may remain in the Phase 0 flow. A search for "claude" outside `legacy/` and upstream attribution must return zero matches (18.4).
- Also gone from the Phase 0 flow: the Desktop launcher flow, the blind pull-latest update, and Claude-specific wiring such as `backtalk.json` (18.5).

## Two different AGENTS.md files

- Root `AGENTS.md`: repository development rules only, written for people and agents working on this repo. Requirement 18.1 says to adapt `CLAUDE.md` and `fullstack-agent.md` into it. Take only the development-rule substance. Drop the installer wizard role and the Claude Code boot path.
- `templates/agent/AGENTS.md`: Pixie's identity and memory instructions, installed by setup (task 12.2). Never merge it with the root file, and never let task executions inherit the root file (3.16, 18.1).
- The identity template uses a neutral default name, tone and welcome line in place of Jarvis (18.16). It has no interactive-only rules, no fill-in markers and no interview block. Approvals go only through the system mechanism.

## Licensing

- `LICENSE` stays byte-identical to the git blob. Confirm with `git diff --stat -- LICENSE` and `git hash-object LICENSE` against `HEAD:LICENSE` (18.6).
- Keep Jared Rhodenizer's copyright notice and upstream attribution in every adapted file.
- Runtime code is AGPL-3.0-or-later. Vault templates and adapted Vault text are CC BY-SA 4.0 and stay only in the Vault_Template_Repo, with their own separate license file (18.14).
- `templates/agent/AGENTS.md` in this repository is original text. It may borrow ideas from Vault templates but never sentences. Do not paste or paraphrase closely from Vault template or upstream text (3.1, 18.14).
- Do not copy any Vault_Template_Repo template text into this repository.
- `docs/licensing.md` states the mixed licensing (AGPL runtime, CC BY-SA templates), that it is not legal advice, and that a qualified review is advised before publishing or selling (18.14). Do not invent legal conclusions.

## Sibling repository (task 12.4)

- Work in `pixie-ai-memory-vault`, not in this repository. If it is not available locally, stop and ask the Operator where it is. Do not clone it without being asked.
- The index and daily-note templates carry no fill-in markers, interview block, boot-file reference, Obsidian instructions or interactive-only rules, and carry the level-2 headings `Vault location`, `Who I Am`, `My Preferences for Working with AI` and `Vault Rules for AI` (3.17).
- Keep the CC BY-SA 4.0 license and attribution to Jared Rhodenizer. Set the `upstream` remote to `https://github.com/jaredrhod/ai-memory-vault.git` (18.18). Never fetch it automatically.

## Remotes and revisions (task 19.3)

- Add the `upstream` remote for this repository pointing to `jaredrhod/fullstack-agent`. Never fetch it automatically (18.9).
- `docs/reviewed-revisions.md` records `5bb159f` (this fork) and `659bba9` (Vault_Template_Repo fork) (18.17).
- Keep the plan at `docs/always-on-agent-prototype-plan.md`. Never delete it (18.11, 18.12).

## Done check

Before reporting the task done, confirm and state in the dev-log entry: legacy originals identical to history, LICENSE unchanged, zero "claude" matches outside `legacy/` and attribution, no Operator_Content touched, and nothing committed.
