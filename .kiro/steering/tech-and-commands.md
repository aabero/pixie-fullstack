---
inclusion: always
---

# Tech stack and commands

Applies while building the `pixie-phase0-runtime` spec. The spec documents win if anything here conflicts with them.

## Python and environments

- All Python environments, installs and runs go through `uv` (decision D31). Never use bare `pip`, `python -m venv` or `virtualenv`.
- Add dependencies with `uv add` (runtime) or `uv add --dev` (test tooling), and keep `uv.lock` committed. Pin exact versions through the lock file.
- Do not install `uv` or any system package yourself. If `uv` is missing, stop and tell the Operator.
- Python version: 3.14.4, or 3.12 if task 2.1 recorded that uv cannot provide it. Use the version recorded in `docs/spike-p0-01-report.md`. Do not choose a version on your own.
- Keep audio, transcription and visualizer dependencies out of the manifest.

## Layout

- Application code: `src/pixie_runtime/`.
- Tests: `tests/unit`, `tests/property`, `tests/integration`, `tests/smoke`.
- Spike code and raw outputs: `spikes/p0-01/` (throwaway, never imported by application code).
- Config example: `config/pixie.example.toml` (placeholders only, model and reasoning effort commented out).
- Runtime_Home for development: `PIXIE_HOME`, or `.pixie-dev/` inside the repo (git-ignored). Never use the Operator's real `~/.pixie` in tests.

## Commands

- Run tests: `uv run pytest tests/unit tests/property tests/integration`. Once task 4.1 adds it, `make test` wraps the same command.
- Run one file: `uv run pytest tests/unit/test_<name>.py`.
- Smoke tests (`tests/smoke`) are run separately and may need the real backend; do not run them unless the task asks.
- No lint or type-check tool is named in the spec. Do not add one unless a task says so.
- Do not run long-lived processes (the Runtime, a watcher) in the foreground. Tell the Operator the exact command instead.
- The systemd unit runs the environment's interpreter by absolute path and never invokes `uv`.

## Test conventions

- Test runner: pytest with pytest-asyncio (or anyio). Property tests use Hypothesis with `max_examples >= 100`.
- Tag every property test with `# Feature: pixie-phase0-runtime, Property N: <title>`.
- Use example tests for formatting and configuration checks.
- Tests use the fake adapter and an injected `Clock`. Never use real time sleeps or the real Codex backend in unit, property or integration tests.
- Optional test sub-tasks (marked `*`) may be skipped, but the logic they validate must be implemented.

## Code conventions

- Every new source file starts with the SPDX header the task 4.1 skeleton defines. The project is AGPL-3.0-or-later; keep LICENSE and attribution intact.
- Code talks to Codex only through the adapter interface. Callers never use Codex types.
- Never log secrets or credential values. Pass anything user-visible through the redaction helpers once they exist.
- Exit codes for the CLI: 0 success or empty list, 1 operation error, 69 Runtime unavailable.
