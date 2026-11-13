---
inclusion: always
---

# Safety boundaries

Applies while building the `pixie-phase0-runtime` spec. These add project-specific limits to your normal safety behavior.

## Credentials and secrets

- Never read, print, copy or commit anything under a `codex/` Codex_Home directory, credential files, token files, `.env`-style files or the Runtime secrets file. Refer to them by path or key name only.
- Never fall back to the shared `~/.codex` (Requirement 2.14). Use only the dedicated `CODEX_HOME` the task specifies.
- Spike output may contain tokens or account details. Redact before saving it under `spikes/` or `docs/`, and before writing it to `docs/dev-log.md`.
- Never put real account names, emails or API keys in code, tests, fixtures or docs. Use placeholders.

## System and service changes

- Only manage the user systemd unit `pixie-runtime.service`, and only with `systemctl --user`. Do not touch system-level units.
- Do not enable lingering (`loginctl enable-linger`), enable the unit at boot or install files outside the repo and the Runtime_Home unless the task says so and the Operator has agreed in this session.
- Transient `systemd-run --user` units used by the spike must be stopped and cleaned up when you finish.
- Do not install packages, `uv`, Node or Codex yourself. If a prerequisite is missing, stop and tell the Operator what is needed.
- Treat the Operator's Vault and any existing Store as Operator_Content. Never delete, overwrite or move it. Tests use temporary directories only.

## Git

- Do not commit, push, rewrite history or switch branches unless the Operator asks. The working branch is `kiro-phase0`.
- Legacy files (`CLAUDE.md`, `fullstack-agent.md`, `start.*`, `update.*`) are only moved or adapted by task 19.1, and only with `git mv`, with no history rewrite.
- Do not touch the sibling Vault_Template_Repo from this repository's tasks. Task 12.4 covers it separately.

## Spec documents

- Do not edit `requirements.md` or `design.md` during implementation. If you find a contradiction, record it in `docs/dev-log.md` and tell the Operator.
- Do not start work past the spike gate (task 3) unless `docs/spike-p0-01-report.md` exists and records that unattended login works, or the Operator has approved the scope.
- For SPIKE-DEPENDENT tasks, follow the degradation path the task states for the recorded spike outcome. Do not invent one.

## Runtime behavior to preserve

- Task executions must not inherit the repository development rules or the root `AGENTS.md` (Requirement 3.16).
- Write bounds are fail-closed. If the backend cannot enforce a Permission_Profile, do not run the Task with writes (Requirement 8.13). Never rely on prompt instructions alone for confinement.
- The Doctor never opens the Store and never starts a Codex execution, except `pixie doctor --probe` while the Runtime is stopped.
