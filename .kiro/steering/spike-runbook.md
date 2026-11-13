---
inclusion: manual
---

# Spike runbook (task 1, P0-01)

Attach with `#spike-runbook` when running any of tasks 1.1 to 1.8, and task 2.1, which writes its result to the spike report. The spec wins if anything here conflicts with it.

## Ground rules

- The spike gates all dependent work. If unattended ChatGPT-subscription login cannot work (D3), stop and review scope with the Operator. Do not start task 4 or later.
- Spike code lives only under `spikes/p0-01/`. It is throwaway and is never imported by application code.
- Keep raw outputs under `spikes/p0-01/raw/`, redacted first (see below). The report summarizes them and links to them.
- Try interfaces in this order and stop at the first that meets the needs: Python SDK, then app-server JSON-RPC, then `codex exec`. For each one you reject, record why (Requirement 1.7). Name another documented interface before implementing any workaround.
- Use a dedicated `CODEX_HOME` for the spike. Never use `~/.codex`. API keys are not an authentication route here; use the ChatGPT subscription login.
- If a login step needs the Operator (browser, device code), stop and ask. Do not try to automate around it.

## Running things safely

- Run each bounded task from a transient user unit: `systemd-run --user` with a unit name starting `pixie-spike-`. No terminal, no nvm-sourced PATH: use the absolute Codex path and put only the `node` directory plus system binary directories on `PATH`.
- Every bounded run finishes within 300 s. Set an explicit timeout and record timeout as an outcome, not as a retry.
- Stop and clean up every `pixie-spike-*` unit when you finish (`systemctl --user stop`, then `reset-failed` if needed). Do not touch any other unit.
- Do not enable lingering or reboot or log out. For D5 (does the user service survive logout and start at boot), record what is observable without doing that, and mark the rest "not verified" with the reason. The Operator runs those checks.
- Do not install Codex, Node or uv. Record versions found with `codex --version`, `uv --version` and similar.
- Run no long-lived process in the foreground.

## What counts as a recorded observation

For every item, write: mechanism used, exact input, observed result, and the run it came from (command plus start and end timestamps). Then:

- Use "not verified" plus the reason whenever you could not reproduce or test something. Never fill a gap with an assumption, documentation claims, or what you expect to be true.
- Record exact full version identifiers (SDK, app-server or CLI) and the pinning method (`uv.lock` or a pinned `uv pip` requirement).
- Record Python versions supported, and whether 3.14.4 works, or "not verified" with the reason.
- For interruption, record the time to stop (must be within 10 s), the final state and whether the thread reference is still usable.
- For approvals with no user connected, record what the worker did (waits, denies or fails) and the elapsed time.
- For expired auth, network failure and usage limit, record the observable signal and whether thread state survives. Simulate where you cannot reproduce, and say it was simulated.
- For the sandbox canary: run an out-of-bounds write under a prompt that demands it, confirm it is blocked, and confirm the sandbox is not silently doing nothing (the same write must succeed inside the allowed root).
- For instruction discovery, check from a working directory outside any Git repository to confirm repository `AGENTS.md` is not inherited.
- For delegation (1.14), the proof must come from an executed run: a natural-language request invokes `create_task` or `propose_schedule` and returns an identifier present in the stub store. Record whether it works through host tools, structured output or slash commands only. Slash-only is "reduced conversational functionality".

## Redaction before saving

Remove or replace before anything is written to `spikes/`, `docs/` or `docs/dev-log.md`: tokens, API keys, auth and refresh values, device codes, account emails and names, organization or account IDs, and any content of the Codex credential file. Keep the key names and structure. If unsure whether a value is secret, redact it.

## Report skeleton: `docs/spike-p0-01-report.md`

Use one section per item, in this order, so nothing from Requirement 1 is missed:

1. Bounded task run (1.1): outcome, input, result, timestamps
2. Versions and pinning (1.2), including Python versions and 3.14.4 (1.10)
3. Mechanisms and observed results (1.3): start, stream, thread refs, results, interrupt, delegation
4. Interruption (1.4)
5. Approval surfacing and unattended behavior (1.5)
6. Failure signals: expired auth, network, usage limit (1.6)
7. Limitations and interface chosen, with reasons earlier ones were rejected (1.7)
8. Authentication route, eligibility, usage limits, terms, billing (1.8)
9. Unattended login from a user service and expiry detection (1.9)
10. Permission profiles and read confinement (1.11)
11. Instruction discovery and injection strategy (1.12)
12. Model and reasoning effort (1.13)
13. Natural-language delegation proof (1.14)
14. Selected backend (only this one is built)
15. Filled capability record (the design's `AdapterCapabilities` flags)
16. D2, D3 and D5 conclusions, including the lingering observation
17. Design degradations that apply, and any requirements issue found (for example slash-only delegation)
18. Python version decision from task 2.1 (3.14.4, or 3.12 with the reason)

Each section ends with a status: `verified`, `partly verified` or `not verified`, plus the reason. Do not edit `requirements.md` or `design.md`. If a finding contradicts them, list it under item 17 and tell the Operator.
