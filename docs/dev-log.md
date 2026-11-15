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

## Task 1.3 - Spike unattended ChatGPT-subscription login from a user service (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.8, 1.9, 2.14, 9.11, 9.12; Decisions D3, D29
- What changed: added `spikes/p0-01/run_login_probe.py`, `spikes/p0-01/NOTES-1.3.md`, `spikes/p0-01/raw/login-probe-1.redacted.json`, `login-probe-1.stderr.txt`, `login-probe-2.redacted.json`, `login-probe-2.stderr.txt`.
- Decisions: used the existing Operator login (no new login); simulated "not logged in" with an empty temp CODEX_HOME; second run without `--pipe` because `--pipe` forwarded a tty. Runs: pixie-spike-login-1 21:44:50Z-21:45:10Z, pixie-spike-login-2 21:45:20Z-21:45:39Z.
- Deviations from the design: none
- Tests: no pytest run (spike task). Unit run with no tty and minimal PATH completed the bounded task ("PONG"); `codex login status` gives exit 0 / exit 1 for logged in / not logged in; empty home gives 401 on SDK run.
- Follow-ups: D3 holds for the observed window. Not verified: real token expiry/refresh, default credential-store value (set `file` explicitly), account plan, whether the Terms permit unattended personal use, lingering/boot (D5). No pixie-spike-* units remain. Task 1.4 not started.
## Task 1.4 - Spike approval surfacing and failure signals (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.5, 1.6; Decisions D2, D3
- What changed: added `spikes/p0-01/run_approval_probe.py`, `run_failure_probe.py`, `NOTES-1.4.md` and redacted raw outputs `raw/approval-*.redacted.json`, `raw/failure-*.redacted.json` (plus stderr files).
- Decisions: used the low-level SDK client (`approvalsReviewer=user`, custom approval handler) because the public API only has deny_all/auto_review; simulated network failure with a closed-port `chatgpt_base_url` and a proxy env; simulated usage limit with a loopback fake provider returning 429 (dummy key, real login not sent).
- Deviations from the design: none
- Tests: no pytest run (spike task). Findings: approval arrives as server request `item/commandExecution/requestApproval`, worker waits (verified 240 s, no timeout), a blocking handler stalls the SDK reader so `interrupt` hangs, default handler auto-accepts; network failure = `will_retry` errors then turn `failed` (~12.5 s), thread survives; usage limit = typed `usageLimitExceeded`, turn `failed`.
- Follow-ups: not verified: real token expiry, real usage limit, thread state after auth failure, cross-client resume after a usage-limit failure, approve path, wait beyond 240 s. No pixie-spike-* units remain. Task 1.5 not started.
## Task 1.5 - Spike permission profile enforcement and read confinement (2026-11-15)
- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.11, 2.13, 8.12, 8.13, 8.16; Decisions D2, D29, D30
- What changed: added `spikes/p0-01/run_sandbox_probe.py`, `run_sandbox_unit.sh`, `NOTES-1.5.md` and redacted `raw/sandbox-{ro,ww,prof,profdeny,profdeny2,nosb}.redacted.json` (+ stderr files).
- Decisions: used low-level `thread_start` with explicit `approvalPolicy=never` and `config` (sandbox_workspace_write / permissions profiles) because the public `Sandbox` enum has no writable roots; simulated "sandbox cannot be applied" with the unit property `RestrictNamespaces=user` (no system change); stand-in "fakehome" dir for the Codex_Home exclusion test.
- Deviations from the design: none
- Tests: no pytest run (spike task). read-only and workspace-write (writable roots) enforced by bwrap, blocked writes are command failures (turn still `completed`); legacy modes do not confine reads; a named permission profile does (unlisted dirs invisible, explicit `deny` gives Permission denied); `:workspace` keeps /tmp writable; sandbox failure is fail-closed per command with no start-up signal.
- Follow-ups: not verified: real Codex_Home as deny target, deny globs, apply_patch/file-change enforcement, network enforcement, real-host causes of sandbox failure (AppArmor etc.), paths a real task needs under a confined profile. Model refuses on seen policy, so only neutral-script results count as enforcement. No pixie-spike-* units remain. Task 1.6 not started.
## Task 1.6 - Spike instruction discovery and model/effort selection (2026-11-15)
- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.12, 1.13, 3.2, 3.16, 2.11; Decision D2
- What changed: added `spikes/p0-01/run_instruction_probe.py`, `run_instruction_unit.sh`, `NOTES-1.6.md` and redacted `raw/instr-*.redacted.json` (plus empty stderr files).
- Decisions: used `thread_start.instructionSources` plus canary markers in temp dirs as evidence; tested the Codex_Home route with a credential-less throwaway CODEX_HOME (removed afterwards), so model visibility of the global file is not verified.
- Deviations from the design: none. Finding that contradicts the task's expectation: outside a Git repo, ancestor AGENTS.md files are still loaded. Config `project_root_markers=[]` (cwd file only) or `project_doc_max_bytes=0` (none) switched it off in the canary runs. This repo has no root AGENTS.md, so that case used a canary parent. Needs a note in report item 17 (Requirement 3.16).
- Tests: no pytest run (spike task). explicit (developerInstructions/baseInstructions) and inline work; codex_home discovery works, delivery not verified; model/effort set via thread/turn params or config keys, invalid values fail the turn (modelNotFound, 400 unsupported_value), not at start.
- Follow-ups: not verified: global file reaching the model, global file vs `project_doc_max_bytes=0`, walk-up beyond the temp parent, turn-level effort echo, each model/effort pair. No pixie-spike-* units remain. Task 1.7 not started.

## Task 1.7 - Spike natural-language delegation proof (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.14, 12.1; D2
- What changed: added `spikes/p0-01/stub/` (SQLite stub store plus a dependency-free stdio MCP server), `run_delegation_probe.py`, `run_delegation_unit.sh`, `NOTES-1.7.md`, redacted `raw/deleg-*`, and `stub/*.db` in the spike `.gitignore`.
- Decisions: tried host tools (MCP) first and stopped there; dynamic tools, structured output and slash commands were not tried. Set `default_tools_approval_mode="approve"` on the stub server because run 1 failed with approvalPolicy=never.
- Deviations from the design: none.
- Tests: no pytest (spike). Executed runs: task -> `task-aeae2a74` and propose_schedule -> `sched-9bd59551`, both read back from SQLite; negative case made no call (weak: prompt said not to set anything up). Run 1 without pre-approval failed, as recorded.
- Follow-ups: MCP calls need pre-approval or an approval handler; MCP servers run outside the thread sandbox; determinism and a neutral negative case not verified. Dynamic tools and structured output not verified (not needed).
