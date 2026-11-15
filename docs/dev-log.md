# Developer log

## Task 1.1 - Create the spike harness and run one bounded task per candidate interface (2026-11-15)

- Status: blocked
- Spec: pixie-phase0-runtime
- Requirements: 1.1, 1.2, 1.7, 1.10; Decisions D2, D31
- What changed: new uv project `spikes/p0-01/` (pyproject, uv.lock, harness `run_sdk_bounded.py`, `NOTES-1.1.md`, redacted `raw/`), dedicated empty CODEX_HOME `spikes/p0-01/.codex-home` (git-ignored).
- Decisions: spike project pinned to Python 3.14.4 (uv uses system /usr/bin/python3.14); SDK `openai-codex==0.169.0` pinned via uv.lock, bundles `openai-codex-cli-bin==0.169.0`. Imports OK on 3.12, 3.13, 3.14.4.
- Deviations from the design: none
- Tests: bounded run in unit pixie-spike-sdk-2 (16 s) returned HTTP 401, no credentials in the dedicated CODEX_HOME. No completed task, so no final result.
- Follow-ups: Operator must log in to the dedicated CODEX_HOME (see spikes/p0-01/NOTES-1.1.md), then re-run the bounded task. App-server and `codex exec` not tried (SDK not yet rejected). No pixie-spike-* units remain.

## Task 1.1 - Create the spike harness and run one bounded task per candidate interface (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.1, 1.2, 1.7, 1.10; Decisions D2, D31
- What changed: re-ran the bounded SDK task after the Operator's device-auth login; added `spikes/p0-01/raw/sdk-run-3.redacted.json` and `sdk-run-3.stderr.txt`; updated `spikes/p0-01/NOTES-1.1.md`.
- Decisions: stopped at the Python SDK (interface 1); app-server and `codex exec` not tried because the SDK met the needs. Run in unit pixie-spike-sdk-3, 2026-11-15T21:29:42Z to 21:29:47Z (4.57 s), outcome completed, result "PONG".
- Deviations from the design: none
- Tests: no pytest run (spike task). Bounded run succeeded; CLI 0.167.2 credentials accepted by bundled 0.169.0 binary. 3.14.4 works; 3.12/3.13 import-only.
- Follow-ups: tasks 1.2 onward not started; report not written. No pixie-spike-* units remain.

## Task 1.2 - Spike streaming, thread references, results and interruption (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.3, 1.4; Decision D2
- What changed: added `spikes/p0-01/run_sdk_stream_interrupt.py`, `spikes/p0-01/NOTES-1.2.md`, `spikes/p0-01/raw/sdk-run-4.redacted.json` and `sdk-run-4.stderr.txt`.
- Decisions: stayed on the Python SDK (no limitation found for 1.2); ran with read-only sandbox, deny_all approvals and tool-free prompts. Run in unit pixie-spike-sdk-4, 2026-11-15T21:40:21Z to 21:40:38Z.
- Deviations from the design: none
- Tests: no pytest run (spike task). Streaming, thread ids, TurnResult and thread_resume worked; interrupt stopped in 0.006 s, final state `interrupted`, thread usable in the same and a new client.
- Follow-ups: interrupt during tool execution or approval wait, and app-server crash recovery, not verified. No pixie-spike-* units remain. Task 1.3 not started.
