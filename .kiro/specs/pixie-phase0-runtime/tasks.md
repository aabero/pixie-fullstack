# Implementation Plan: Pixie Phase 0 Runtime

## Overview

The implementation language is Python 3.12+ (the design names it; target machine runs 3.14.4). All environments, installs and test runs use `uv` (D31): `uv sync`, `uv run pytest`, never stdlib `venv` or bare `pip`.

The plan is ordered so that the riskiest unknowns are resolved first and a thin end-to-end loop exists early:

1. The Requirement 1 spike runs first and gates everything (D2, D3, D5).
2. Early verification tasks (uv Python 3.14.4, V-1 cronsim, V-2 prompt_toolkit) run before the components that depend on them.
3. A thin slice (chat, persist task, disconnect, execute, reconnect, discuss the result) is built with the fake adapter, then the spike-selected adapter is added. Phase 0 builds only the selected Codex adapter plus the fake one.
4. Safety (permissions, approvals, cancellation, recovery), Vault, schedules, notifications, Doctor, setup, update, repository disposition, documentation and the verification record follow.

Tasks marked **SPIKE-DEPENDENT** rely on the outcome of the spike (D2 interface, D3 unattended subscription login, D5 lingering). Each states how it degrades. Test sub-tasks are optional (`*`); the core logic they validate is not optional. Property tests use Hypothesis (`max_examples >= 100`) and carry the tag `# Feature: pixie-phase0-runtime, Property N: <title>`; example tests are used for formatting and configuration checks. The automated tests use the fake adapter and need no network or Codex (19.8).

## Tasks

- [ ] 1. Requirement 1 spike (P0-01): validate the Codex integration
  - Gates all dependent work. Spike code lives under `spikes/p0-01/` (throwaway, not application code). Raw outputs are kept. If the spike shows unattended subscription login cannot work, stop and review scope with the Operator before continuing (Introduction, D3).
  - [x] 1.1 Create the spike harness and run one bounded task per candidate interface
    - Create a uv project under `spikes/p0-01/`; record `uv --version` and the Python version uv provides.
    - Try the Python SDK first, then app-server JSON-RPC, then `codex exec`; stop at the first that satisfies the needs, but record why earlier ones were rejected.
    - Run one bounded task from a transient `systemd-run --user` unit, finishing within 300 s; record outcome, input, final result, start and end timestamps.
    - Record the exact full version and the pinning method (`uv.lock` or pinned `uv pip` requirement), and the Python versions supported including whether 3.14.4 works.
    - Note: any Python version or `requires-python` set in the spike project is throwaway; the application value follows the result recorded by task 2.1.
    - _Requirements: 1.1, 1.2, 1.7, 1.10; Decisions: D2, D31_
  - [ ] 1.2 Spike streaming, thread references, results and interruption
    - Record mechanism and observed result for: starting execution, streaming events, retaining thread references, retrieving results.
    - Interrupt an active run; verify it stops within 10 s; record final state and whether the thread reference remains usable.
    - _Requirements: 1.3, 1.4; Decisions: D2_
  - [ ] 1.3 Spike unattended ChatGPT-subscription login from a user service
    - Create a dedicated `CODEX_HOME`, log in with the subscription (no API key), file-based credential store; run from a `systemd-run --user` unit with no terminal and no nvm-sourced PATH (absolute Codex path, `node` directory on a minimal PATH).
    - Record: subscription vs API billing, account eligibility, usage limits (units, period, shared with interactive use), terms for automated use, billing implications.
    - Record how expired login is detected (the observable signal).
    - Record whether the dedicated Codex_Home can hold a working unattended login.
    - _Requirements: 1.8, 1.9, 2.14, 9.11, 9.12; Decisions: D3, D29_
  - [ ] 1.4 Spike approval surfacing and failure signals
    - Trigger an approval request; record how it surfaces to application code and, with no user connected, the observed worker behavior and elapsed time.
    - Reproduce or simulate expired auth, network failure and usage limit; record the signal for each and whether thread state is preserved; mark anything not reproducible "not verified" with the reason.
    - _Requirements: 1.5, 1.6; Decisions: D2, D3_
  - [ ] 1.5 Spike permission profile enforcement and read confinement
    - Verify `read-only` and `workspace-write` enforcement through the backend sandbox configuration (sandbox mode, writable roots); record the mechanism and any profile that cannot be enforced.
    - Record whether reads can be confined to listed directories and whether the Codex_Home can be excluded from reads.
    - Run an out-of-bounds write attempt under a prompt demanding it; confirm it is blocked and that the sandbox is not silently doing nothing.
    - _Requirements: 1.11, 2.13, 8.12, 8.13, 8.16; Decisions: D2, D29, D30_
  - [ ] 1.6 Spike instruction discovery and model/effort selection
    - Record how instruction files are discovered (global file in Codex_Home, project-root chain, working directory) and which injection strategy works (`explicit`, `codex_home`, `inline`); confirm a working directory outside any Git repository avoids repository `AGENTS.md` inheritance.
    - Record how model and reasoning effort are set and which values the account accepts, or mark "not verified" with the reason.
    - _Requirements: 1.12, 1.13, 3.2, 3.16, 2.11; Decisions: D2_
  - [ ] 1.7 Spike natural-language delegation proof
    - Build a throwaway stub (small SQLite file under `spikes/`) exposing `create_task` and `propose_schedule`; prove through at least one executed run that a natural-language chat request invokes the structured operation and returns a persisted identifier present in the stub store.
    - Record whether delegation works through host tools (MCP or dynamic tools, verified against the exact pinned version), structured output, or only slash commands; slash-only is recorded as reduced conversational functionality; undemonstrated is "not verified" with the reason.
    - Operator ruling: the throwaway stub store under `spikes/` is an accepted reading of Requirement 1.14's "present in the Store" wording. The spike proves the mechanism and that the returned identifier is persisted in the stub; persistence in the real Store is covered by the thin end-to-end slice and its tests (6.9, 6.11).
    - _Requirements: 1.14, 12.1; Decisions: D2_
  - [ ] 1.8 Write the spike report and capability record
    - Write `docs/spike-p0-01-report.md` covering every item in Requirement 1, the selected backend (only this one gets built), the filled capability record (design `AdapterCapabilities` flags), the D2/D3 conclusions, and the D5 lingering observation (does the user service survive logout and start at boot; mark unverified if not testable).
    - List the design degradations that apply (design "Degradation by backend") and any requirements issue found (for example slash-only delegation).
    - _Requirements: 1.1 to 1.14, 9.7, 9.8; Decisions: D2, D3, D5_

- [ ] 2. Early verification tasks
  - [ ] 2.1 Verify uv can provide Python 3.14.4
    - Using `uv python list` and a throwaway `uv venv --python 3.14.4`, confirm availability on the Operator's machine.
    - Operator ruling: assume Python 3.14.4. If uv cannot provide it, the stated outcome is to default to Python 3.12; record the chosen version ("3.14.4" or "3.12") and the reason in `docs/spike-p0-01-report.md` and in the verification notes (task 19.6).
    - The version recorded here is authoritative: `requires-python` and the interpreter pin (4.1), the unit file (17.1), setup (17.2) and the documentation (19.2, 19.4) must use whichever version this task records.
    - _Requirements: 1.10, 16.13, 20.5; Decisions: D31_
  - [ ] 2.2 V-1: verify cronsim on Python 3.14.4
    - In a throwaway uv environment, install and check timezone-aware evaluation for `America/Montevideo` and a DST zone (for example `America/New_York`), spring-forward gap (fires once at first valid instant after the gap), fall-back overlap (fires once, first occurrence), strictly-after-reference results.
    - Record the result; failure means choosing another library behind `cron.py`, not changing the design. Must finish before task 14.1.
    - Run on the Python version recorded by task 2.1.
    - _Requirements: 6.1, 6.2, 6.3; Decisions: D14_
  - [ ] 2.3 V-2: verify prompt_toolkit for the Chat_Client
    - In a throwaway uv environment on Python 3.14.4 check: (a) text printed from a background task appears above the input line (`patch_stdout`); (b) while a reply streams, a task update appears within 2 s and `/status` and `/approve` typed mid-stream are answered within 2 s.
    - If it fails or is flaky, select the fallback (plain `input()` in a worker thread, updates printed from the event loop) and run the same checks (a) and (b) against it; record the result. If neither meets 2 s, record it as a requirements issue for 11.9 and 11.11.
    - _Requirements: 11.9, 11.11_

- [ ] 3. Checkpoint - spike gate
  - Confirm the spike report exists and names the selected backend. If D3 failed (no unattended login) stop and ask the user to review scope before continuing. Ensure all tests pass, ask the user if questions arise.

- [ ] 4. Project foundation, configuration and Store
  - [ ] 4.1 Create the project skeleton
    - Create `pyproject.toml` (`requires-python >=3.12`, script entry `pixie`, `dev` dependency group with pytest, pytest-asyncio, hypothesis), `uv.lock` via `uv lock`, package `src/pixie_runtime/`, `tests/{unit,property,integration,smoke}/`, a `Clock` interface, SPDX headers, and a documented single test command (`make test` wrapping `uv run pytest tests/unit tests/property tests/integration`).
    - Add `.gitignore` entries excluding an in-repo Runtime_Home (`.pixie-dev/`) and keep audio, transcription and visualizer dependencies out of the manifest.
    - Dependencies are added with exact pins via uv.
    - `requires-python` (and any interpreter pin) follows the version recorded by task 2.1 (3.14.4, or 3.12 if uv cannot provide 3.14.4).
    - _Requirements: 15.4, 16.13, 19.1, 20.6; Decisions: D31_
  - [ ] 4.2 Implement configuration and paths
    - Implement `config.py` and `paths.py`: Runtime_Home resolution (`PIXIE_HOME`, default `~/.pixie`), TOML load with unknown-key and range rejection naming the key, single authoritative Vault path entry, model and reasoning effort unset by default with no hardcoded model, secrets file loader, and `config/pixie.example.toml` with placeholders and commented model keys.
    - The `codex.interface` key is set from the spike report (**SPIKE-DEPENDENT**, D2; no degradation, value only).
    - _Requirements: 2.11, 3.15, 9.11, 15.1, 15.3, 15.6_
  - [ ] 4.3 Implement the Store schema and DB thread
    - Migration `0001` with all tables in the design (conversations, messages, turns, tasks, schedules, occurrences, schedule_proposals, attempts, attempt_turns, events, cancellation_requests, approvals, preauthorizations, results, deliveries, schema_migrations, runtime_state), constraints, indexes, the one-active-attempt partial unique index, terminal-state and append-only triggers.
    - Single dedicated DB thread, WAL, `synchronous=FULL`, `foreign_keys=ON`, commit deadline with rollback, Store located under the Runtime_Home.
    - _Requirements: 4.1, 4.4, 4.5, 4.7, 5.2, 7.1, 7.11, 8.1, 12.7_
  - [ ] 4.4 Implement migrate and startup schema checks
    - `migrate.py`: show pending migrations, verified SQLite backup under the Runtime_Home, each migration in its own transaction, rollback and error naming the failed version and backup on failure.
    - Startup check: initialize a missing Store automatically, refuse with exit 78 on pending migration (naming `pixie migrate`) or newer schema (reporting both versions) without modifying the Store.
    - _Requirements: 4.2, 4.3, 4.8, 9.5; Decisions: D26_
  - [ ] 4.5 Implement the lifecycle table and transitions
    - `lifecycle.py` as the single transition table of 5.13, repository functions committing State change and Event in one transaction, `INVALID_STATE` and `TERMINAL` errors with no Event on rejection.
    - _Requirements: 4.4, 4.6, 5.1, 5.2, 5.13_
  - [ ]* 4.6 Write property test for lifecycle closure
    - **Property 1: Lifecycle closure**
    - **Validates: Requirements 4.6, 5.1, 5.2, 5.13**
  - [ ]* 4.7 Write property test for transition atomicity
    - **Property 2: Transition atomicity**
    - **Validates: Requirements 4.4**
  - [ ]* 4.8 Write property test for Store round trip and crash durability
    - **Property 3: Store round trip and crash durability**
    - **Validates: Requirements 4.1, 4.5, 6.7, 14.6**
  - [ ]* 4.9 Write property test for migration safety
    - **Property 4: Migration safety**
    - **Validates: Requirements 4.2, 4.3, 4.8**
  - [ ]* 4.10 Write tests for configuration validation and passthrough
    - **Property 24: Configuration validation and passthrough**
    - Unknown key, out-of-range value and unsupported model are rejected naming the key; unset model and effort produce an execution request with no override (checked against the worker request builder once it exists); static check that no model identifier appears in the source.
    - **Validates: Requirements 2.11**

- [ ] 5. Redaction and adapter interface
  - [ ] 5.1 Implement redaction and leak detection
    - `redaction.py`: replace configured credential values and URL/base64 encodings with a placeholder, idempotent; leak detector rescans and on a hit discards the output and records `credential_leak_blocked` without the value; logging filter.
    - _Requirements: 15.2, 15.5, 15.6_
  - [ ] 5.2 Implement the adapter protocol, capability record and event mapper
    - `adapter/base.py`: `CodexAdapter` protocol, `AdapterCapabilities`, `ExecutionRequest`, `SandboxSpec`, `BackendRefs`, Application_Event kinds; `adapter/mapper.py`: table-driven total mapping (supported, `unmapped` with raw type, `parse_failure` with payload truncated to 10,000 characters), ordered per-attempt delivery within 1 s.
    - Callers reference no Codex or Claude type; `on_refs` persistence failure ends the attempt with no further submissions.
    - The capability flags are those named in the spike report (**SPIKE-DEPENDENT**, D2; unknown flags default to false so the system fails closed).
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_
  - [ ] 5.3 Implement the fake adapter
    - `adapter/fake.py`: scripted events, blockable approvals, ignorable cancellation, configurable liveness, all capability flags settable, injectable `on_refs` failure.
    - _Requirements: 19.8, 2.5, 2.6_
  - [ ]* 5.4 Write property test for event mapping
    - **Property 11: Adapter event mapping is total and ordered**
    - **Validates: Requirements 2.2, 2.3, 2.4**
  - [ ]* 5.5 Write property test for redaction and leak blocking
    - **Property 22: Redaction and leak blocking**
    - **Validates: Requirements 15.2, 15.5**

- [ ] 6. Thin end-to-end slice with the fake adapter
  - Goal: chat, persist task, disconnect, execute, reconnect, discuss the result.
  - [ ] 6.1 Implement Runtime process startup and shutdown
    - `runtime.py`, `sdnotify.py`: single-instance `flock` (exit 75 on second instance), new `instance_id` per start, config and Store checks from 4.4, `READY=1` after startup, SIGTERM handling that stops claims (attempt interruption recording is completed in 10.5), exit codes 75 and 78.
    - _Requirements: 7.10, 9.2, 9.3, 9.5, 4.2_
  - [ ] 6.2 Implement the RPC server, protocol and single client interface
    - `server.py`, `protocol.py`, `client.py`: Unix socket (dir 0700, socket 0600), `SO_PEERCRED` check closing foreign connections within 1 s, NDJSON framing, `hello{client_type}`, push events, error codes from the design, 10 s commit deadline, `UNSUPPORTED_OPERATION` for `voice`/`audio`/`transcription`/`speech` namespaces, `runtime.status`.
    - `client.py` is the only module clients use; Runtime-unavailable detection within 5 s.
    - _Requirements: 10.1, 10.2, 10.5, 12.3, 20.1, 20.2, 20.3, 20.4, 20.7_
  - [ ] 6.3 Implement task, result and unread-result services
    - `tasks.py`: create (absolute Project_Directory and Permission_Profile required, Results_Location assigned, nothing persisted on rejection, originating Conversation recorded), list, get, resume stub of lifecycle; `results.list/get/mark_read/unread_count` newest first; result file written by the Runtime for `read-only`.
    - _Requirements: 8.1, 8.10, 11.12, 12.4, 12.7, 13.4, 14.6_
  - [ ] 6.4 Implement prompt assembly and instruction isolation
    - `prompts.py`: read Agent_Instructions fresh per execution (unreadable gives `instructions_unavailable` failure and notice), provide them under the injection strategy from the capability record, first-prompt ordering, working directory under the Runtime_Home never inside a Git work tree, the repository, or the Project_Directory.
    - **SPIKE-DEPENDENT** (D2): injection strategy is `explicit`, `codex_home` or `inline` as recorded by the spike; degrades in that order.
    - _Requirements: 3.2, 3.3, 3.9, 3.16, 1.12_
  - [ ] 6.5 Implement the Worker with leases and result persistence
    - `worker.py`, `leases.py`: claim in one transaction (instance id, 60 s lease, model/effort recorded), heartbeat every 15 s only while the adapter reports the execution alive, one Attempt at a time, event persistence through the redactor, thread/turn mapping write-ahead, Result persisted before the terminal transition (separate transaction recording `persistence_error` if the Result fails).
    - Operator ruling (design wins over the literal text of 5.9): a persistent network failure ends in `blocked` with a `retry_review` Approval when a possible external action was recorded (design Worker section, Property 33, consistent with 7.6); otherwise it ends `failed` after max retries.
    - _Requirements: 2.5, 2.6, 2.9, 7.1, 7.2, 7.9, 14.1, 14.2, 2.11_
  - [ ] 6.6 Implement the conversation lane and slash commands
    - `conversations.py`: Conversation and message persistence, per-conversation turn ordering with a queued indicator, streamed deltas, partial replies marked `partial`, follow-up context (thread resume, else last N messages with a warning), turn cancellation touching no Task, delegated Task gets its own context holding only the request and selected messages (default delegating message plus six before).
    - Structured slash commands `/new /resume /task /tasks /status /results /quit`; acceptance confirmation with Task identifier generated by the Runtime only after commit.
    - _Requirements: 3.9, 10.6, 11.1, 11.3, 11.4, 11.5, 11.6, 11.7, 11.8, 11.10, 12.1, 12.2, 12.3, 12.4, 12.7, 12.8_
  - [ ] 6.7 Implement the Task_CLI core commands
    - `cli.py`: `pixie status`, `tasks list|show|submit`, `results latest|list|show`, `approvals list`; all through `client.py`; exit codes (0, 1, 69), empty-list message, not-found and malformed-argument errors, no direct Store reads, Runtime-unavailable error within 5 s.
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.8, 13.10, 10.3, 10.5_
  - [ ] 6.8 Implement the Chat_Client
    - `chat.py`: connect within 5 s (else error, no Conversation, non-zero exit), display the Conversation id before the first message, resume offer, streamed output, immediate Task update entries, unread-result count on reconnect, status and approval answers within 2 s while a Task runs.
    - Rendering uses prompt_toolkit or the threaded `input()` fallback, whichever V-2 (task 2.3) selected.
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.7, 11.9, 11.10, 11.11, 11.12_
  - [ ] 6.9 Wire and verify the end-to-end slice with the fake adapter
    - Integration test: start the Runtime, chat `/task`, receive confirmation with identifier, close the client, the Worker executes, reconnect, see the unread Result, ask about it in chat; assert the Task survived the disconnect and appears in both chat and `pixie tasks show`.
    - _Requirements: 10.4, 12.2, 13.3, 19.5_
  - [ ]* 6.10 Write property test for task creation validation
    - **Property 27: Task creation validation**
    - **Validates: Requirements 8.1**
  - [ ]* 6.11 Write property test for chat-to-task registration integrity
    - **Property 16: Chat-to-task registration integrity**
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4, 12.6, 12.7, 12.8, 13.4**
  - [ ]* 6.12 Write property test for turn ordering and client detachment
    - **Property 28: Conversation turn ordering and client detachment**
    - **Validates: Requirements 10.4, 11.8, 13.3, 20.4**
  - [ ]* 6.13 Write property test for unread results
    - **Property 29: Unread results**
    - **Validates: Requirements 11.12**
  - [ ]* 6.14 Write test for voice operations rejection
    - **Property 31: Voice operations are rejected without side effects**
    - **Validates: Requirements 20.7**
  - [ ]* 6.15 Write test for instruction presence and isolation
    - **Property 25: Instruction presence and isolation**
    - **Validates: Requirements 3.2, 3.16**
  - [ ]* 6.16 Write unit tests for Task_CLI and Chat_Client
    - Connect-time limits, unreachable error, queued indicator, streaming, resume offer, update rendering, 1,000-Task read under 2 s, mutation exit codes, empty list, unknown id.
    - _Requirements: 11.1, 11.2, 11.9, 11.10, 11.11, 13.1, 13.5, 13.6, 13.8_
  - [ ]* 6.17 Write test for Task context minimality and thread-as-context
    - **Property 26: Task context minimality and thread-as-context**
    - **Validates: Requirements 2.10, 3.9**

- [ ] 7. Checkpoint - thin slice works with the fake adapter
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 8. Selected Codex adapter (SPIKE-DEPENDENT)
  - [ ] 8.1 Implement the selected Codex adapter
    - **SPIKE-DEPENDENT (D2):** implement only the interface selected by the spike (SDK, else app-server JSON-RPC client for the used subset, else `codex exec`) in `adapter/<selected>.py`: submit, observe, request_cancel, get_result, thread resume, raw-event mapping table, dedicated `CODEX_HOME`, absolute executable path, no reading of Codex credential files, no write of credentials to the repository.
    - Degradation: SDK failing falls to app-server, then to `exec`; `exec` loses backend approvals and possibly host tools (design "Degradation by backend"); nothing above the adapter changes.
    - _Requirements: 2.1, 2.2, 2.5, 2.8, 2.14, 9.11; Decisions: D2_
  - [ ] 8.2 Implement authentication check, liveness, inactivity confirmation and model validation
    - **SPIKE-DEPENDENT (D2, D3):** `check_auth` within 30 s with a failure report free of credentials, `is_alive`, `confirm_inactive` (pid plus start time from `/proc`), `force_stop`, `list_models`, mapping of auth, usage-limit and network signals recorded by the spike, approval request and answer routing.
    - Degradation: without `auth_probe` expiry is detected on failure only; without `approval_requests` approvals exist only for Runtime-mediated operations and out-of-bounds operations are recorded as `sandbox_denied` (8.18); without `unattended_login` stop for scope review.
    - _Requirements: 2.9, 2.11, 5.7, 5.8, 7.4, 8.18, 1.6, 1.9; Decisions: D2, D3_
  - [ ] 8.3 Implement the host-tool bridge for chat delegation
    - **SPIKE-DEPENDENT (D2):** `hosttools.py` and `toolbridge.py` exposing `create_task`, `propose_schedule` (registered in task 14.3), `list_tasks`, `get_task`, `get_result` with per-turn tokens, executed by Runtime code, wired into the conversation lane.
    - Degradation: use schema-constrained structured output validated by the Runtime if `host_tools` is absent; if neither works, only slash commands and the Task_CLI create work and this is recorded as reduced conversational functionality for the Operator to review (requirements 12.5 and 12.6, 19.5).
    - _Requirements: 12.1, 12.5, 12.6, 3.9; Decisions: D2_
  - [ ] 8.4 Add bounded real Codex smoke tests
    - `tests/smoke/`, excluded from the default run, 120 s cap each, timeout counts as failure: bounded task from a transient user unit, streaming and thread retention, interrupt within 10 s, instruction isolation canary, delegation via the selected route, auth/usage-limit failure where safely inducible, same slice scenario as 6.9 against the real adapter.
    - _Requirements: 19.2, 1.1, 1.3, 1.4, 3.16, 1.14_

- [ ] 9. Checkpoint - real adapter loop works
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 10. Permissions, approvals, cancellation, failure handling and recovery
  - [ ] 10.1 Implement the Permission Planner
    - `permissions.py`: profile to `SandboxSpec` per the design table, realpath canonicalization with containment checks, fail-closed `blocked`/`permission_unenforceable` when the needed capability is absent, `read_confinement_unavailable` warning event, Codex_Home exclusion where supported (else `codex_home_exposure: yes` for status), 10 MB / 100 file quota audit after each Attempt and on file-change events (`limit_exceeded`), `git status` tripwire (`policy_violation`), chat-created Tasks limited to `projects.allowed_roots`.
    - **SPIKE-DEPENDENT (D2, D30):** capability flags decide which profiles can run; unconfined reads run with a warning, writes stay fail-closed.
    - _Requirements: 2.13, 8.1, 8.2, 8.10, 8.11, 8.12, 8.13, 8.16, 8.17; Decisions: D16, D29, D30_
  - [ ] 10.2 Implement the Approval Service and timeout accounting
    - `approvals.py`: canonical operation hash, one Approval per operation within 2 s with `awaiting_approval` in one transaction, preauthorization matching, consumption of grants, answering through one transaction for both clients (`ALREADY_RESOLVED`), resume within 5 s, denial to `failed`/`approval_denied`, no expiry without a client, single slot held during `awaiting_approval` with the stall shown in status and chat.
    - Attempt timeout stopwatch paused during `awaiting_approval`, continuation budget preserved, heartbeats continue.
    - `pixie approvals approve|deny` and chat `/approve /deny`.
    - **SPIKE-DEPENDENT (D2):** degrades to Runtime-mediated Approvals only (Vault edits, retry review) when the backend does not surface approvals.
    - _Requirements: 7.3, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9, 8.15, 8.18, 13.2, 13.7; Decisions: D16, D25_
  - [ ] 10.3 Implement cancellation
    - Cancellation request rows within 1 s, immediate `cancelled` for `queued`/`blocked`, pending request with unchanged State for active Attempts, withdrawn Approvals, adapter cancel, acknowledgment mapping to `cancelled`/`succeeded`/`failed` after recording work done, 30 s unacknowledged handling (State and request kept, shown pending), terminal rejection; `pixie tasks cancel` and chat `/cancel`.
    - _Requirements: 5.3, 5.4, 5.5, 5.6, 5.10, 5.11, 10.7, 13.2, 13.7_
  - [ ] 10.4 Implement failure handling, retry safety and resume
    - Authentication gives `blocked` plus the `auth_required` worker gate (queued Tasks wait), usage limit gives `blocked` with limit and reset time, network failure retried with 2 to 60 s backoff up to max retries then `failed` (but `blocked` with a `retry_review` Approval when a possible external action was recorded; Operator ruling: the design and Property 33 win over the literal text of 5.9, consistent with 7.6), timeout gives `failed`/`timeout`, invalid model gives `blocked`/`configuration`; single `retry_safety` decision in `recovery.py`; `retry_review` Approval and its grant/deny exits; `pixie tasks resume` and chat equivalent.
    - _Requirements: 2.11, 5.7, 5.8, 5.9, 5.14, 5.15, 5.16, 7.5, 7.6, 7.7, 7.3_
  - [ ] 10.5 Implement recovery, shutdown and watchdog
    - Startup reconciliation before any claim over all unreconciled Attempts of other instances (including shutdown-interrupted), inactivity confirmation first, pending-cancellation handling, awaiting-approval preservation, `reconciled_at` idempotency, shutdown interruption within 10 s, lease-expiry watchdog for hung Attempts, persistence-failure fault flag, conversation turns marked `failed(interrupted)` at restart.
    - _Requirements: 5.12, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 7.10, 7.11, 7.12, 11.4_
  - [ ] 10.6 Add the sandbox canary smoke test
    - Smoke test (and the probe routine reused by `pixie doctor --probe`) that tries an out-of-bounds write under a prompt demanding it for both profiles; the write must be blocked, and a silently disabled sandbox must be detected.
    - **SPIKE-DEPENDENT (D2):** if a profile cannot be enforced the test asserts the fail-closed refusal instead.
    - _Requirements: 8.14, 8.12, 8.13, 19.2_
  - [ ]* 10.7 Write property test for permission planning fails closed
    - **Property 13: Permission planning fails closed**
    - **Validates: Requirements 8.10, 8.11, 8.12, 8.13**
  - [ ]* 10.8 Write property test for path confinement
    - **Property 15: Path confinement**
    - **Validates: Requirements 8.2, 8.17**
  - [ ]* 10.9 Write property test for approval binding
    - **Property 12: Approval binding**
    - **Validates: Requirements 8.3, 8.4, 8.5, 8.6, 8.9**
  - [ ]* 10.10 Write property test for the single execution slot
    - **Property 8: Single execution slot**
    - **Validates: Requirements 7.1, 7.11, 8.15**
  - [ ]* 10.11 Write property test for timeout accounting
    - **Property 10: Timeout accounting**
    - **Validates: Requirements 7.3**
  - [ ]* 10.12 Write property test for cancellation
    - **Property 14: Cancellation as request and acknowledgment**
    - **Validates: Requirements 5.3, 5.4, 5.5, 5.10, 5.11, 10.6, 10.7**
  - [ ]* 10.13 Write property test for recovery policy and idempotency
    - **Property 9: Recovery policy and idempotency**
    - **Validates: Requirements 5.12, 7.4, 7.5, 7.6, 7.7, 7.11, 7.12**
  - [ ]* 10.14 Write property test for replay safety of recorded side effects
    - **Property 33: Replay safety of recorded side effects**
    - Include a fake Runtime tool write (stand-in for `vault_append`) with a crash injected at each point.
    - Operator ruling: assert the design behavior, not the literal text of 5.9. A persistent network failure with a recorded possible external action ends `blocked` with a `retry_review` Approval (consistent with 7.6), never an automatic retry or plain `failed`.
    - **Validates: Requirements 3.7, 5.9, 7.5, 7.6**

- [ ] 11. Checkpoint - safety and recovery
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 12. Vault and memory instructions
  - [ ] 12.1 Implement Vault reading
    - `vault.py` reader: single Vault path from config, preferences extracted only from the configured level-2 heading of the index, exact-match headings, missing/unreadable Vault runs without preferences with a `vault_unavailable` warning and notice and no change to the Vault, Doctor warning when the index "Vault location" differs from config.
    - _Requirements: 3.4, 3.5, 3.13, 3.15, 3.18_
  - [ ] 12.2 Write the Pixie identity template
    - `templates/agent/AGENTS.md`: original text (no CC BY-SA sentences), assistant name Pixie, neutral default tone and welcome line, Vault pointers, no interactive-only rules, approvals only through the system mechanism.
    - _Requirements: 3.1, 3.10, 3.11, 18.16; Decisions: D18_
  - [ ] 12.3 Implement the Vault writer and protected sections
    - Serialized FIFO plus file lock, 60 s start timeout (`VAULT_WRITE_TIMEOUT`, file unchanged), temp file, fsync, rename, hash re-check, `vault_append` and `vault_replace_section` host tools only, protected headings give no write plus one `protected_vault_edit` Approval for the exact change, `external_action_begin`/`end` recording for Attempt writes.
    - **SPIKE-DEPENDENT (D2):** without `host_tools` Tasks cannot write the Vault; only Operator-initiated writes work.
    - _Requirements: 3.7, 3.8, 3.14, 8.4; Decisions: J-18_
  - [ ] 12.4 Adapt the Vault_Template_Repo (sibling repository `pixie-ai-memory-vault`)
    - In the sibling repository (not this one): produce marker-free, interview-free, boot-file-free, Obsidian-free, interactive-rule-free index and daily-note templates carrying the level-2 headings `Vault location`, `Who I Am`, `My Preferences for Working with AI`, `Vault Rules for AI`; keep CC BY-SA 4.0 license and attribution to Jared Rhodenizer; set `upstream` remote to `https://github.com/jaredrhod/ai-memory-vault.git`; no template text copied into this repository.
    - _Requirements: 3.17, 18.14, 18.15, 18.18; Decisions: D7, D18, D19_
  - [ ] 12.5 Wire preferences into prompt assembly
    - Inject the extracted preferences block (labelled as style hints) into the first prompt of each new Task execution; no other Vault content.
    - _Requirements: 3.4, 3.13_
  - [ ]* 12.6 Write property test for Vault preference extraction
    - **Property 18: Vault preference extraction**
    - **Validates: Requirements 3.4, 3.5, 3.13**
  - [ ]* 12.7 Write property test for Vault write serialization and protection
    - **Property 19: Vault write serialisation and protection**
    - **Validates: Requirements 3.7, 3.8, 3.14**
  - [ ]* 12.8 Write the Vault template contract and installed-text checks
    - Example tests: required heading set, absence of fill-in markers, interview block, boot-file reference, Obsidian instructions and interactive-only phrases in installed templates and `templates/agent/AGENTS.md`.
    - _Requirements: 3.10, 3.17_

- [ ] 13. Checkpoint - Vault and memory
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Scheduling
  - [ ] 14.1 Implement the cron wrapper
    - `cron.py`: `next_after` and `between` behind the library chosen in V-1 (cronsim if it passed, otherwise the replacement), IANA zone handling, DST gap fires once after the gap, overlap fires once at the first occurrence, strictly-after results, default zone America/Montevideo.
    - Depends on task 2.2 (V-1); if cronsim failed, swap the library behind the wrapper only.
    - _Requirements: 6.1, 6.2, 6.3; Decisions: D14_
  - [ ] 14.2 Implement the Scheduler tick and missed-run policy
    - `scheduler.py`: three Schedule types, per-second tick, due Occurrence enqueue in one transaction with the (schedule, due time) primary key within 5 s, `skip` default and uncapped `catch_up` at startup in due order, creation only from Operator-created Schedules, persistence-failure rejection, execution with no client.
    - _Requirements: 6.1, 6.4, 6.5, 6.6, 6.7, 6.8, 6.9, 6.10; Decisions: D13_
  - [ ] 14.3 Implement schedule proposals
    - `schedule_proposals` service: persisted proposal with absolute expiry from `schedules.proposal_ttl_minutes`, at most 3 pending (code constant), `PROPOSAL_LIMIT`, single-use confirm in one transaction, preview recomputation with `PREVIEW_CHANGED`, past one-off rejection, confirm without id only when exactly one pending, `AMBIGUOUS_PROPOSAL`, discard frees a slot, list with expiry; `propose_schedule` host tool (degrades per 8.3) and RPC methods; ambiguous intents create nothing and prompt one clarifying question.
    - _Requirements: 6.11, 6.12, 6.13, 6.14, 6.15, 6.16, 12.5, 12.6; Decisions: D28_
  - [ ] 14.4 Add schedule commands to the Task_CLI and Chat_Client
    - `pixie schedule list|add|update|trigger`, chat `/schedule /confirm [P-n] /proposals /discard P-n`; previews show cron, IANA zone, next three run times (one for one-off), proposal id and expiry; acceptance message repeats the interpretation.
    - _Requirements: 12.5, 12.6, 13.1, 13.2, 6.16_
  - [ ]* 14.5 Write property test for cron next-due invariants
    - **Property 6: Cron next-due invariants across time zones**
    - **Validates: Requirements 6.1, 6.2**
  - [ ]* 14.6 Write property test for occurrence idempotency
    - **Property 5: Occurrence idempotency**
    - **Validates: Requirements 6.4, 6.5**
  - [ ]* 14.7 Write property test for missed-run policies
    - **Property 7: Missed-run policies**
    - **Validates: Requirements 6.6**
  - [ ]* 14.8 Write property test for the schedule proposal lifecycle
    - **Property 32: Schedule proposal lifecycle**
    - **Validates: Requirements 6.11, 6.12, 6.13, 6.14, 6.15, 6.16, 12.5**
  - [ ]* 14.9 Write test for schedule preview correctness
    - **Property 17: Schedule preview correctness**
    - **Validates: Requirements 12.5**

- [ ] 15. Checkpoint - scheduling
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 16. Result delivery
  - [ ] 16.1 Implement the notifier
    - `notifications.py`: `notify-send` with 10 s timeout, session bus detection, one attempt within 5 s of Result persistence, payload limits (title 80, body 200; Task id, final State, truncated summary only), `deliveries` row `delivered`/`failed` with last error.
    - _Requirements: 14.3, 14.4, 14.5; Decisions: D15_
  - [ ] 16.2 Wire Delivery into the Worker
    - After the Result commit only (never when persistence failed), create the Delivery; failure leaves Result and Task State unchanged; delivery status shown in `results` output after restart.
    - _Requirements: 14.1, 14.2, 14.4, 14.6_
  - [ ]* 16.3 Write property test for result-before-delivery
    - **Property 20: Result before delivery, and delivery failure is harmless**
    - **Validates: Requirements 14.1, 14.2, 14.4**
  - [ ]* 16.4 Write test for notification payload bounds
    - **Property 21: Notification payload bounds**
    - **Validates: Requirements 14.5**

- [ ] 17. Systemd unit, setup, Doctor and update
  - [ ] 17.1 Create the systemd unit template and renderer
    - The interpreter version used follows the version recorded by task 2.1.
    - `systemd/pixie-runtime.service.in`: `Type=notify`, absolute interpreter in the uv-managed environment, absolute Codex path, minimal `PATH` with the `node` directory, 30 s start and stop timeouts, `Restart=on-failure`, growing delay with `RestartSteps`/`RestartMaxDelaySec` when `systemctl --version` supports them else fixed `RestartSec`, start limit 5 in 300 s, `KillMode=control-group`; never invokes uv or a shell startup file.
    - _Requirements: 9.1, 9.2, 9.4, 9.5, 9.10, 9.11, 9.12, 9.13, 9.14; Decisions: D32_
  - [ ] 17.2 Implement the Setup_Script
    - `scripts/setup.sh`, `scripts/prereqs.py`, `setup.py`: check `uv` first (stop with install instructions, never auto-install), prerequisites named before any change, stop the running service (abort untouched if it cannot stop), `uv sync --locked --no-dev` into `<home>/venv`, create-only Runtime_Home, Codex_Home mode 0700/0600 with tightening reported, Agent_Instructions install (existing `AGENTS.md` left byte-for-byte, template beside it), deterministic Vault creation from the adapted templates with no interview and no Obsidian access, unit install and `daemon-reload`, ask before enabling lingering and before first enable, `install-manifest.json`, restart only per the Operator's choices with a report, versioned config migration shown and backed up first.
    - The Python version installed by uv follows the version recorded by task 2.1.
    - **SPIKE-DEPENDENT (D3, D5):** Codex login steps follow the spike; if lingering is declined or unavailable setup documents the reduced lifecycle.
    - _Requirements: 2.12, 3.1, 3.6, 3.12, 9.1, 9.7, 9.8, 16.1, 16.2, 16.3, 16.4, 16.5, 16.8, 16.9, 16.13, 16.14; Decisions: D5, D17, D31, D34_
  - [ ] 17.3 Implement the Doctor_Script
    - `doctor.py`: five checks (service, Store version, configuration, Codex authentication with `codex/` modes and exposure, Vault path), each pass/fail/skipped with a reason within 30 s, skipped "Runtime not running" never a pass, running Doctor is a read-only status client of the socket and never opens the Store, exit non-zero only on a failed check, informational lines (model/effort, lingering, `notify-send`, systemd version and restart mechanism, interpreter exists, read confinement), `--probe` canary only while the Runtime is stopped; no Obsidian check.
    - **SPIKE-DEPENDENT (D2, D3):** the authentication check and exposure line use the recorded probe and capability flags.
    - _Requirements: 2.13, 8.14, 13.9, 16.6, 16.7, 16.10, 9.14; Decisions: D33_
  - [ ] 17.4 Implement update and the version manifest
    - `components.toml` (remote, Reviewed_Revision, pinned revision, license hash for this repository and the Vault_Template_Repo), `update.py` with the ordered steps of 17.3 (stop, backup config and Store with integrity check, fetch from configured remotes only and show per-component commit lists and changed-file counts, explicit yes/no, apply pinned revisions `--ff-only`, `uv sync --locked`, migrate if needed, Doctor while stopped, restart, Doctor again), decline changes nothing, failure names component and reason and points to manual recovery, LICENSE and attribution preserved, uv-missing stops before any change.
    - Operator ruling (D33, 17.3): the first Doctor run, before the restart, is informational for the file-only checks. Check 1 (service active) failing there is expected and does not stop the update; a failure of any other check stops the update before the restart. The second Doctor run after the restart gives the reported outcome.
    - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 18.9, 18.17; Decisions: D33_
  - [ ] 17.5 Wire the offline tools into the `pixie` entry point
    - Add `pixie migrate`, `pixie doctor`, `pixie setup`, `pixie update` to the CLI entry point as Offline_Tools that never use the Runtime socket except the Doctor's read-only status calls.
    - _Requirements: 13.9, 4.2, 16.1, 16.6, 17.3_
  - [ ]* 17.6 Write property test for setup idempotency and preservation
    - **Property 23: Setup idempotency and preservation**
    - **Validates: Requirements 3.6, 3.12, 16.4, 16.5, 16.11, 17.5, 18.7**
  - [ ]* 17.7 Write property test for Doctor reporting
    - **Property 30: Doctor reports every check**
    - **Validates: Requirements 13.9, 16.6, 16.7**
  - [ ]* 17.8 Write unit tests for setup, unit file and update
    - Prerequisite failure leaves the tree unchanged, uv-missing stop, non-silent lingering prompt, rendered unit snapshot with absolute paths and restart-mechanism fallback, manifest content, Codex_Home mode repair, update against local bare repositories (confirmation, decline, ordered steps, failure message).
    - Doctor during update (Operator ruling, D33): the first Doctor run with the service stopped does not stop the update when only check 1 fails; a failure of any other check stops the update before the restart; the second Doctor run after the restart gives the reported outcome.
    - _Requirements: 9.1, 9.4, 9.7, 16.3, 16.8, 16.13, 17.2, 17.3, 17.6, 2.12_

- [ ] 18. Checkpoint - operations tooling
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. Repository disposition, documentation and verification record
  - [ ] 19.1 Apply legacy disposition and adapt root files
    - `git mv` unused Claude-oriented files and `start.bat`/`update.bat` into `legacy/` with a README stating they are retained pending the Operator's decision (copy `start.sh`/`update.sh` there before adapting); write root `AGENTS.md` (repository development rules only, separate from the installed template); adapt `start.sh` (prints service status and chat hint, never starts or stops the Runtime) and `update.sh` (shim to `pixie update`); no history rewrite; abort and report if any step would touch Operator_Content.
    - _Requirements: 18.1, 18.3, 18.4, 18.5, 18.7, 18.8, 18.10, 18.13_
  - [ ] 19.2 Rewrite README, TROUBLESHOOTING and CONTRIBUTING
    - State the Python version recorded by task 2.1.
    - Describe Pixie Phase 0, Codex and the Ubuntu service lifecycle; no Claude Code prerequisite or setup path; keep upstream attribution and Jared Rhodenizer's copyright.
    - _Requirements: 18.2, 18.4, 18.6_
  - [ ] 19.3 Record licensing, reviewed revisions and upstream remote
    - Add `docs/licensing.md` (AGPL-3.0-or-later runtime, CC BY-SA templates, not legal advice, qualified review advised), `docs/reviewed-revisions.md` (`5bb159f`, `659bba9`), add the `upstream` remote `jaredrhod/fullstack-agent` (never fetched automatically), keep the plan at `docs/always-on-agent-prototype-plan.md`, keep LICENSE byte-identical; no commit unless the Operator asks.
    - _Requirements: 18.6, 18.9, 18.11, 18.12, 18.14, 18.17_
  - [ ] 19.4 Write the operations runbook
    - Use the Python version recorded by task 2.1 in all commands and paths.
    - `docs/operations.md`: exact start/stop/restart/status/log commands with expected results, restart-delay mechanism in use with delay values and observed systemd version, lingering and suspend caveats, update and manual recovery procedure, end-to-end scenario as ordered steps with command and expected result.
    - _Requirements: 9.6, 9.8, 9.9, 9.14, 17.3, 17.6, 19.4_
  - [ ]* 19.5 Write static and repository checks
    - Example tests: no audio modules or dependencies, no hardcoded model identifier, no reading of Codex credential files, clients import only `client.py`, no tracked credential values, `.gitignore` covers an in-repo Runtime_Home, no Obsidian paths, no legacy-backend references outside `legacy/` and attribution, launchers never control the Runtime, LICENSE identical to the git blob, legacy originals identical to history.
    - _Requirements: 20.6, 2.11, 2.8, 10.3, 20.1, 15.1, 15.3, 15.4, 16.9, 18.3, 18.4, 18.5, 18.6, 18.10_
  - [ ] 19.6 Create the verification procedure and record
    - Record the Python version from task 2.1 (including the 3.12 fallback and its reason if it applied).
    - `docs/verification.md`: manual systemd procedure (start, stop, restart, failure backoff, logout, reboot, notification with and without a graphical session, socket permissions) with action, expected outcome and pass/fail/unverified field; an automated end-to-end scenario test (project-state summary, `read-only`, Runtime-written result file) reported as four separate items (executes after client close, delivers or retains, survives service restart, appears in chat and CLI history); spike-dependent and unmet-environment items recorded "unverified" with reasons, never counted as passed; failing items recorded with the overall outcome failed.
    - _Requirements: 19.1, 19.3, 19.5, 19.6, 19.7, 19.9, 9.7, 9.8; Decisions: D5, D6, D27_

- [ ] 20. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP; the core logic they validate is not optional.
- Each task references specific requirements (and decisions) for traceability.
- Checkpoints ensure incremental validation.
- Property tests validate universal correctness properties (Hypothesis, `max_examples >= 100`); example tests validate formats, configuration and edge cases.
- Real Codex smoke tests are excluded from the default run and each is capped at 120 s.
- Manual systemd, logout, reboot and notification checks in task 19.6 are performed by the Operator; this plan only creates the procedure and records.
- No task installs anything on the Operator's machine outside the documented setup flow.

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "1.5", "1.6", "2.1"] },
    { "id": 2, "tasks": ["1.7", "2.2", "2.3"] },
    { "id": 3, "tasks": ["1.8"] },
    { "id": 4, "tasks": ["4.1"] },
    { "id": 5, "tasks": ["4.2", "4.3", "5.1"] },
    { "id": 6, "tasks": ["4.4", "4.5", "5.2", "5.5"] },
    { "id": 7, "tasks": ["4.6", "4.7", "4.8", "4.9", "5.3", "5.4", "6.1", "6.4"] },
    { "id": 8, "tasks": ["6.2", "6.3"] },
    { "id": 9, "tasks": ["6.5", "6.6", "6.7", "6.10"] },
    { "id": 10, "tasks": ["4.10", "6.8", "6.11", "6.12", "6.13", "6.14", "6.15", "6.17"] },
    { "id": 11, "tasks": ["6.9", "6.16"] },
    { "id": 12, "tasks": ["8.1", "10.1"] },
    { "id": 13, "tasks": ["8.2", "8.3", "10.2", "10.7", "10.8"] },
    { "id": 14, "tasks": ["8.4", "10.3", "10.6", "10.9", "10.11"] },
    { "id": 15, "tasks": ["10.4", "10.12"] },
    { "id": 16, "tasks": ["10.5"] },
    { "id": 17, "tasks": ["10.10", "10.13", "10.14", "12.1", "12.2", "12.4", "14.1", "16.1", "17.1"] },
    { "id": 18, "tasks": ["12.3", "12.5", "12.6", "12.8", "14.2", "14.5", "16.2", "16.4", "17.2", "17.3"] },
    { "id": 19, "tasks": ["12.7", "14.3", "14.6", "14.7", "16.3", "17.4", "17.6", "17.7"] },
    { "id": 20, "tasks": ["14.4", "14.8", "14.9", "17.8"] },
    { "id": 21, "tasks": ["17.5"] },
    { "id": 22, "tasks": ["19.1", "19.2", "19.3", "19.4"] },
    { "id": 23, "tasks": ["19.5"] },
    { "id": 24, "tasks": ["19.6"] }
  ]
}
```
