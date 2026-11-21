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

## Task 1.8 - Write the spike report and capability record (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.1 to 1.14, 9.7, 9.8; Decisions D2, D3, D5
- What changed: added `docs/spike-p0-01-report.md` (18 sections per the spike runbook, each with a status), built only from `spikes/p0-01/NOTES-1.1.md` to `NOTES-1.7.md` and `spikes/p0-01/raw/`.
- Decisions: backend A (Python SDK `openai-codex` 0.169.0, Python 3.14.4) recorded as selected; `output_schema` and `backend_pid_report` marked not verified (no evidence in notes); D5 logout/boot marked not verified with Operator follow-ups; section 18 left "pending task 2.1".
- Deviations from the design: none in the work. Report item 17 lists findings that contradict or are missing from requirements/design: 3.16 ancestor AGENTS.md, approval handler model vs async `answer_approval`, read confinement vs `SandboxSpec`, interrupt blocked by a pending approval handler.
- Tests: not run (documentation task, no new experiments).
- Follow-ups: Operator runs lingering, logout and reboot checks (D5); Operator reads the Terms of Use on automated use; task 2.1 decides the Python version.

## Task 2.1 - Verify uv can provide Python 3.14.4 (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: none listed; Decision D31 (uv), Operator ruling to assume 3.14.4
- What changed: `spikes/p0-01/NOTES-2.1.md` (new, command and result table); `docs/spike-p0-01-report.md` section 18 now records the chosen version 3.14.4 instead of "pending".
- Decisions: Python 3.14.4, no 3.12 fallback. `uv python list` shows 3.14.4 installed at `/usr/bin/python3.14`; `uv venv --python 3.14.4` in a temp dir succeeded (exit 0) and reported 3.14.4. Temp dir removed.
- Deviations from the design: none
- Tests: not run (verification task; no code)
- Follow-ups: the interpreter is the system one; uv lists only 3.14.10 as downloadable, so a managed 3.14.4 is not verified as obtainable. Operator should keep the system python3.14 at 3.14.4 or revisit the pin.
## Task 2.2 - V-1: verify cronsim on Python 3.14.4 (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: none listed; Decision D14 (cron library behind `cron.py`)
- What changed: new throwaway uv project `spikes/v1-cronsim/` (`pyproject.toml`, `uv.lock`, `check_cronsim.py`, `raw-output.txt`, `raw-observations-wildcard-hourly.txt`, `NOTES.md`, `.gitignore`). Not part of the project manifest.
- Decisions: Montevideo has no DST now, so its gap and overlap checks use the 2014 tzdata transitions; the New_York checks use 2026.
- Deviations from the design: none
- Tests: `cd spikes/v1-cronsim && uv run python check_cronsim.py` on CPython 3.14.4, cronsim 2.8: 9 of 9 pass (gap fires once at 03:00, fixed-hour overlap fires once at first occurrence, results strictly after the reference).
- Follow-ups: cronsim passed, so no replacement library is needed. Wildcard-hour expressions (`0 * * * *`) fire in both overlap hours; task 14.1 should decide whether to suppress that. Not verified: `between`, naive datetimes, DOM/DOW combinations, tzdata version.
## Task 2.3 - V-2: verify prompt_toolkit for the Chat_Client (2026-11-15)

- Status: partial
- Spec: pixie-phase0-runtime
- Requirements: 11.9, 11.11
- What changed: new throwaway uv project `spikes/v2-prompt-toolkit/` (`pt_client.py`, `fb_client.py`, `driver.py`, `raw-pt.txt`, `raw-fallback.txt`, `NOTES.md`, `uv.lock`). Not in the project manifest.
- Decisions: no human terminal was available, so the clients ran under a stdlib pty read through the pyte emulator. Results are labelled pty-based in the notes.
- Deviations from the design: none
- Tests: `uv run python driver.py pt_client.py 8` on CPython 3.14.4, prompt_toolkit 3.0.53: (a) 8/8 update above prompt with partial input kept; (b) update <=0.005 s, `/status` <=0.13 s, `/approve` <=0.09 s. Fallback (`fb_client.py`, 8 runs): (b) within 2 s but (a) fails 8/8 (output overwrites the prompt line).
- Follow-ups: prompt_toolkit chosen, no requirements issue for 11.9/11.11. Not verified: real terminal emulator behaviour, resize, paste, long wrapped lines, higher stream rates. Operator commands are in `spikes/v2-prompt-toolkit/NOTES.md`.

## Task 3 - Checkpoint - spike gate (2026-11-15)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: none listed; gate on Decisions D2, D3
- What changed: only this entry. No code, spec or report edits.
- Decisions: none. Open items for the Operator are listed in the task 3 report (17b items, task 2.1 python pin, 2.2 wildcard-hour DST, 2.3 manual terminal check).
- Deviations from the design: none
- Tests: not run. No `tests/` directory exists yet (created by task 4.1).
- Follow-ups: gate passes. `docs/spike-p0-01-report.md` exists, names backend A (Python SDK `openai-codex` 0.169.0), has no pending sections, and records unattended login working (D3 not failed). No `pixie-spike-*` units remain. `.codex-home` is git-ignored and untracked. Secret scan of `spikes/` and `docs/` (excluding `.codex-home`) found no emails, JWT-like, sk-/ghp_-style strings. Long-string matches (40+ hex, 48+ char runs) are in a few files, see report. Task 4 not started.

## Planning - spike-gate decisions recorded in tasks.md (2026-11-20)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: spike report section 17b; decisions D2, D3, D5, D14, D31
- What changed: `tasks.md` annotated with the Operator's gate decisions (tasks 2.1, 4.1, 5.2, 6.4, 6.8, 8.1 to 8.3, 10.1 to 10.3, 10.6, 14.1, 14.5, 17.1 to 17.3, 19.2, 19.4, 19.6); new non-optional sub-task 3.1 (non-blocking approvals spike) added before task 4, dependency graph now waves 0 to 25; Overview reworded so it pins no Python version.
- Decisions: confirmed 17b-1, 3, 4, 5, 6, 7, 9, 12; Python `>=3.14.4,<3.15` (system python3.14, patch mismatch warns); cron overlap rule (a repeated local time fires once, so an hourly wildcard fires 24 times on a 25-hour day); cronsim and prompt_toolkit kept; D5 deferred to unit 17.1.
- Deviations from the design: `SandboxSpec` gains `read_roots`; design line 25 (instruction discovery) is contradicted by spike section 11; J-16 and the setup prerequisite say Python 3.12 or newer. Design and requirements not edited. The cron rule matches design line 513 and Property 6, so it is not a deviation.
- Tests: not run (planning edit); `validate_spec_format` passed on tasks.md.
- Follow-ups: open until 3.1 (17b-2, 17b-10); open until 8.1 (17b-11); Operator actions: read the Terms of Use (17b-8), check prompt_toolkit in a real terminal (V-2), logout/boot checks (D5).

## Task 3.1 - Pre-execution record, before starting (2026-11-20)

- Status: not started (readiness record only)
- Spec: pixie-phase0-runtime
- Requirements: 1.4, 1.5, 8.3, 8.4, 8.15; Decisions D2, D25
- State checked: 3.1 is the next unchecked task (task 3 is checked, task 4 is blocked behind 3.1); no `pixie-spike-*` units are running; `spikes/p0-01/.codex-home` and its `auth.json` are git-ignored; `git status` shows only `tasks.md` and `docs/dev-log.md` modified.
- Open items 3.1 must resolve: 17b-2 (approval handler blocks the SDK reader thread) and 17b-10 (10 s interrupt bound during an approval wait). 17b-11 is deferred to 8.1.
- Questions 3.1 must answer: (a) a non-blocking way to answer approvals through the SDK, (b) a direct app-server client where the Runtime owns the read loop, (c) the `accept` path and whether the command then runs, (d) `CodexClient(config, approval_handler=...)` without private attributes, (e) interrupt during a pending approval within 10 s.
- Stop rule: if a pending approval and a working interrupt cannot coexist, stop and ask the Operator to choose between changing Requirement 8.15 / D25 and a deny-and-resume model.
- After 3.1: remind the Operator of the design amendment batch (read_roots, design line 25, J-16 and setup prerequisite, and 8.15/D25 if needed) before task 4.

## Task 3.1 - Spike non-blocking approvals (2026-11-21)

- Status: done
- Spec: pixie-phase0-runtime
- Requirements: 1.4, 1.5, 8.3, 8.4, 8.15; Decisions D2, D25
- What changed: new `spikes/p0-01/run_approval_nb_probe.py`, `run_approval_nb_unit.sh`, `NOTES-3.1.md`, raw `raw/nb-*.redacted.json`; addenda appended to sections 5 and 17b-2 of `docs/spike-p0-01-report.md` (existing text unchanged).
- Result: a pending approval and a working interrupt coexist when the Runtime owns the read loop (direct JSON-RPC client: interrupt 0.009 s; patched SDK reader loop: 0.013 s). Unmodified SDK (handler, thread hand-off, AsyncCodex) does not meet 10 s. Accept runs the command outside the sandbox. `CodexClient(config, approval_handler=...)` works without private attributes. Interrupt cancels the pending approval (`serverRequest/resolved`).
- Decisions: used a minimal own JSON-RPC client in the probe; no choice made about the adapter backend interface.
- Deviations from the design: none new; confirms the design's async `answer_approval` needs a non-SDK reader loop.
- Tests: spike runs only, six transient units, all completed; units cleaned up. No unit tests (spike).
- Follow-ups: design amendment batch still pending (Operator's call); task 5.2 interface decision; not verified: waits >240 s, file-change approvals, network after accept.
