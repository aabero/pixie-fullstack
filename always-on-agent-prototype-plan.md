# Pixie: Always-on Agent Fork Implementation Plan

**Status:** Proposed implementation plan; no implementation changes made.
**Project owner:** Agustín Abero
**Agent name:** Pixie
**Command prefix:** `pixie`
**Baseline:** Fork of `jaredrhod/fullstack-agent`, with separately managed component repositories.
**Phase 0:** Persistent background assistant powered by Codex.
**Phase 1:** Spanish/English voice through an adapted Backtalk integration.

## 1. Goal and agreed priorities

Build a personal assistant that can carry out work between conversations, retain useful context, and eventually support natural spoken interaction in Spanish and English. Existing projects provide a starting point for our own implementation.

The agreed priorities are:

1. Use **Codex instead of Claude** as the agent backend.
2. Implement interactive text chat, persistent background tasks, Ubuntu service management, result delivery, and reproducible setup in **Phase 0**.
3. Implement voice in **Phase 1**, including bilingual interaction.
4. Treat the Jarvis-inspired visual interface as secondary. Reuse existing visuals before designing new ones.

This document describes changes to make to the fork and its components. It does not authorize deployment, installation on the owner's computer, or changes to existing personal notes.

## 2. Baseline and repository boundaries

Upstream fullstack-agent assembles separate projects: ai-memory-vault, Backtalk, ai-visualizer, and optional Barehands. It does not contain all their implementations. The installer and Backtalk currently depend on Claude Code.

| Repository / component | Intended responsibility | Planned treatment |
| --- | --- | --- |
| fullstack-agent fork | Setup, launchers, runtime integration, service installation, documentation | Primary integration repository; home of the new Phase 0 runtime initially |
| ai-memory-vault | Markdown knowledge, profile, daily notes, indexes, reusable job instructions | Adapt templates to Codex; preserve attribution and component licensing |
| Backtalk fork | Speech capture, transcription, playback, voice controls | Defer functional changes until Phase 1; replace Claude backend coupling |
| ai-visualizer | Animated conversation status | Optional reuse in Phase 1; no dependency for Phase 0 |
| Barehands | Webcam-based gesture board | Outside both phases unless explicitly added later |

Record upstream remotes and reviewed revisions. Configure installers and updates to use the intended forks rather than silently replacing adaptations with upstream versions. The owner's actual fork URLs remain to be supplied during implementation.

The reviewed fullstack-agent launcher is terminal-oriented and starts its components together. It is not a persistent task supervisor. The memory vault's reusable job notes are instructions, not an execution queue or scheduler.

## 3. Design principles

- Task execution and durable state belong to the background runtime, independently of text, voice, and visuals.
- Codex provides reasoning and tools. The application owns scheduling, permissions, task records, delivery, and recovery.
- Persistent knowledge and task execution records have different purposes. Use Markdown for inspectable knowledge and a transactional store for task state.
- Closing a client must not cancel an accepted task. Cancelling playback must not imply cancelling work.
- Keep credentials outside tracked files, prompts, result summaries, and logs.
- Model, reasoning effort, paths, and integrations must be configurable.
- Start with one user and one worker execution slot. Add concurrency only when needed and verified.
- Do not equate process restart with safe replay of an interrupted external action.

## 4. Phase 0: Persistent Codex assistant

### 4.1 Objective

Deliver Pixie as a non-voice personal assistant with interactive terminal chat and task-management commands. Both clients connect to the same persistent runtime, which executes manual and scheduled work through Codex, retains conversation references, task state, and results, and operates under Ubuntu service management.

### 4.2 Scope

Included: interactive text chat, task-management commands, Codex integration, identity and memory instructions, task persistence, basic scheduling, worker lifecycle, recovery, local result history, desktop notifications, deterministic setup, and operating documentation.

Excluded: microphone access, transcription, speech generation, Backtalk voice changes, custom visuals, gesture input, remote/mobile access, a public server, and broad email/calendar integrations. Validate one bounded local workflow before adding external integrations.

### 4.3 Work packages

| ID | Work package | Required changes | Completion evidence |
| --- | --- | --- | --- |
| P0-01 | Codex integration spike | Verify supported SDK/runtime versions, authentication, execution events, thread identifiers, interruption, permission behavior, and error handling | A bounded task runs from the intended service environment and returns a recorded result |
| P0-02 | Codex adapter | Introduce an application-owned execution interface; map supported Codex events into application events | Worker executes without Claude Code or the Claude Agent SDK |
| P0-03 | Identity and memory | Create AGENTS.md-based boot instructions; adapt vault pointers and task-note conventions | A new execution retrieves an approved preference and prior task context |
| P0-04 | Durable task store | Persist task definitions, attempts, states, schedules, events, and artifact references | Closing a client or restarting the worker preserves records |
| P0-05 | Scheduler and worker | Implement manual, one-off, and recurring triggers, leases, timeouts, and bounded retries | Scheduled work runs without an interactive terminal |
| P0-06 | Ubuntu services | Install a systemd user service, lifecycle commands, and useful logs | Runtime starts and restarts correctly under the documented lifecycle |
| P0-07 | Result delivery | Persist result history and delivery status; add optional desktop notifications | A finished task is discoverable even when notification delivery is unavailable |
| P0-08 | Reproducible setup | Replace Claude-only setup assumptions; configure forks, dependencies, paths, and services | A repeat installation preserves personal configuration and state |
| P0-09 | Verification and documentation | Add meaningful automated checks and an end-to-end runbook | Phase 0 acceptance scenarios pass with recorded limitations |
| P0-10 | Interactive text chat | Add `pixie chat` as a runtime client with streamed replies, follow-up context, task submission, status queries, and approval handling | The user converses with Pixie, delegates a task, closes chat, and returns to inspect its result |

### 4.4 Codex integration decision

Official OpenAI documentation currently describes a Codex SDK for programmatic automation, an app-server interface for richer clients, and non-interactive CLI execution. The Python SDK controls a local Codex app-server and published builds include a pinned runtime dependency. These are distinct from directly calling a general model API. [S1–S3]

**Proposed first choice:** evaluate the Python SDK because Backtalk is Python-based and a shared adapter may reduce Phase 1 integration work. This is a proposal, not a verified compatibility decision.

P0-01 must establish:

- The exact supported SDK/runtime versions and reproducible dependency installation.
- How a service running as the intended user authenticates without a terminal prompt.
- Whether the selected authentication route is subscription-based or API-billed; document actual account eligibility, limits, and billing. Do not promise unlimited or free execution.
- How to start execution, stream events, retain thread references, retrieve results, and interrupt an active run.
- How interactive chat remains responsive while the single task worker is busy, including status queries and approvals. Separate conversation handling from the worker queue and serialize turns within each conversation.
- How approval requests are surfaced. A worker without a connected user must wait or fail explicitly rather than hang or silently grant permission.
- How expired authentication, network failure, and usage limits become actionable task states.

Use the supported authentication mechanism. Do not implement token scraping or copy credential values into the fork. If the preferred SDK cannot meet a required behavior, record the limitation and choose another documented interface before implementing a workaround. [S4]

### 4.5 Adapter contract

Define application-level operations such as `submit`, `observe`, `request_cancel`, and `get_result`. These are proposed internal methods, not claims about Codex SDK method names.

Keep the mapping among task ID, execution-attempt ID, and Codex thread/turn references durable. A restored thread is context, not proof that an external action completed.

Use separate task contexts by default. Persist the mapping between chat conversations and their Codex thread references, and explicitly associate delegated tasks with their originating conversation. Carry only the relevant request and context into a task; do not merge every task into one global conversation. Share approved knowledge through the vault and serialize writes to shared knowledge in the initial single-worker implementation.

### 4.6 Task persistence and recovery

**Proposed storage:** SQLite for a single-user local runtime, with versioned migrations and transactional state transitions.

Minimum records:

- Conversation: ID, backend thread reference, task associations, and the history or context references required to resume text chat.
- Task: ID, request, originating conversation when applicable, creation time, workspace, permission profile, and current state.
- Schedule: trigger type, timezone, next due time, enabled status, and missed-run policy.
- Attempt: start/end times, backend references, lease/heartbeat, outcome, and error category.
- Event: timestamped state changes, approval requests, cancellation requests, and progress.
- Result: summary, artifact paths, completion status, and references to detailed output.
- Delivery: notification channel, attempt status, and last error.

Task states should distinguish `queued`, `running`, `awaiting_approval`, `blocked`, `succeeded`, `failed`, and `cancelled`. Store cancellation requests separately until the backend acknowledges the outcome.

On restart, reconcile stale running attempts. Retry bounded, repeatable work when safe. If an external action may already have happened, reconcile its outcome or require review. Do not claim exactly-once execution for arbitrary tools.

### 4.7 Scheduling and permissions

Start with manual execution, one-off schedules, and one simple recurring schedule format. Persist schedule definitions and calculate runs in an explicit timezone; default to America/Montevideo through configuration.

Define whether a missed occurrence is skipped or caught up, and prevent duplicate enqueueing of the same occurrence. Do not add unrestricted model-driven polling as the default.

Each task needs an explicit working directory and allowed actions. Begin with bounded local reads and result-file writes. External changes require an applicable preauthorization or an approval recorded for the exact operation. Credentials, permissions, and task history must remain separate concerns.

### 4.8 Ubuntu service management

**Proposed lifecycle:** `pixie-runtime.service`, a systemd user service for the persistent runtime, independent of terminal chat, Backtalk, and graphical clients.

- Use explicit executable and configuration paths; do not depend on interactive shell startup files.
- Provide start, stop, restart, status, and log-inspection instructions.
- Use restart-on-failure with backoff; expose configuration errors rather than restart endlessly.
- Handle shutdown by stopping new claims and recording in-flight work for reconciliation.
- Keep runtime state outside the checkout so updates do not remove it.
- Document that background availability still depends on the machine being powered on and awake.

To meet operation after logout and boot before login, evaluate user lingering and its system configuration implications. If unavailable, document the reduced lifecycle instead of claiming this requirement passes. Desktop notification delivery may require a graphical login even when execution continues.

### 4.9 Interactive text chat, task commands, and result delivery

**Interactive text chat is required in Phase 0.** `pixie chat` is the primary conversational interface. Task-management commands provide a direct way to inspect and control the same runtime without starting a conversation. Neither client owns the service lifecycle.

Proposed command surface (specification examples, not implemented commands):

```bash
pixie chat
pixie tasks list
pixie tasks show <task-id>
pixie results latest
pixie approvals list
pixie schedule list
pixie status
```

Also provide explicit operations to submit tasks directly, create or modify schedules, approve or deny pending actions, and cancel tasks. Their exact subcommand syntax remains an implementation decision.

Interactive chat must:

- Support natural-language conversation, streamed replies, and follow-up questions through Codex.
- Let the user delegate immediate or scheduled work, ask for status, and inspect results.
- Route scheduling and task mutations through structured runtime operations; a conversational promise alone must never count as task registration.
- Confirm acceptance only after durable persistence, returning a task ID and, for scheduled work, the interpreted schedule and timezone. Ask for clarification when scheduling intent is ambiguous.
- Present approval requests and record the decision against the exact pending operation; reuse the same approval mechanism as the task commands and later voice client.
- Preserve conversation references so the user can resume or explicitly start a new conversation. Make the selected conversation visible.
- Remain responsive to status and control requests while background work runs. If a model turn cannot start immediately, show its queued or waiting state explicitly.
- Treat closing chat as detaching the client, not cancelling accepted tasks or stopping the service. Distinguish cancelling an unfinished conversational turn from cancelling a persisted task.
- Report a stopped or unreachable service clearly rather than silently running a separate assistant process.

Use a local, user-restricted runtime connection; the exact transport is an implementation decision. The client must not bypass the runtime by spawning unmanaged background Codex tasks.

Persistent result history is authoritative. Save results before attempting notification delivery. Keep notification payloads brief and avoid sensitive content. If no desktop session exists, retain the result and delivery status for later review without marking task execution as failed.

When chat is connected, surface relevant task updates without losing the current conversation. After reconnecting, make unread results discoverable through chat and task history. Notifications are a convenience, not proof that the user received a result.

Example Phase 0 workflow:

1. Open `pixie chat` and request a bounded research task or recurring briefing.
2. Pixie persists the accepted task and reports its ID and any schedule details.
3. Close the terminal; the runtime continues the accepted work.
4. The runtime saves the result and attempts desktop notification delivery.
5. Reopen chat to ask about the task, or inspect it through `pixie tasks show <task-id>`.


### 4.10 Reproducible setup and updates

Provide a deterministic setup script or command; a conversational wizard may explain options but must not be the only definition of installation behavior.

- Remove Claude Code prerequisites and commands from the Phase 0 path.
- Add a project AGENTS.md for development rules and a separate template for Pixie's installed identity and memory pointers.
- Use Pixie as the assistant name, `pixie` as the command prefix, and `pixie-runtime.service` as the proposed service name. Install the terminal client alongside the runtime.
- Preserve the owner's instructions; do not copy upstream personality and operating rules wholesale or overwrite existing AGENTS.md files.
- Install only Phase 0 dependencies by default. Defer Backtalk models, audio packages, and visual components.
- Record component remotes, revisions, and compatible dependency versions.
- Keep tracked example configuration separate from personal configuration, state, and credentials.
- Make reruns idempotent and show configuration migrations before applying them.
- Make updates explicit and version-aware; do not pull every component's latest branch blindly.
- Keep upstream attribution and license notices; components have different licenses.

### 4.11 Proposed repository layout

This layout is illustrative and should be reconciled with the actual fork before coding:

```text
fullstack-agent/
  AGENTS.md
  README.md
  fullstack-agent.md
  pyproject.toml
  src/pixie_runtime/
    codex_adapter.py
    tasks.py
    store.py
    scheduler.py
    worker.py
    notifications.py
    cli.py
    chat.py
    client.py
  config/pixie.example.toml
  templates/agent/AGENTS.md
  systemd/pixie-runtime.service
  scripts/setup.sh
  scripts/doctor.sh
  tests/
  docs/operations.md
```

The original launch and update scripts need review and adaptation. Voice/visual launchers must never own the background runtime's lifecycle.

### 4.12 Phase 0 acceptance criteria

- [ ] The installed Phase 0 path runs through Codex without Claude installed.
- [ ] `pixie chat` provides streamed replies and coherent follow-up conversation through Codex.
- [ ] Natural-language task and schedule requests create durable runtime records and return their identifiers and interpreted schedule details.
- [ ] A bounded task can be submitted and inspected through the CLI.
- [ ] Chat and task commands show the same tasks, approvals, and results.
- [ ] Chat remains usable for status and approvals while the background worker executes a task.
- [ ] Closing and reopening chat preserves conversation references and accepted tasks; explicit new-conversation behavior is available.
- [ ] An approval can be reviewed and answered through chat and is enforced by the runtime.
- [ ] A scheduled task completes after the submitting terminal closes.
- [ ] Definitions, results, and history survive service restart.
- [ ] An interrupted attempt is reconciled without blindly replaying external actions.
- [ ] Authentication and usage-limit failures produce a clear blocked/error state.
- [ ] An approval-dependent task does not silently bypass its policy.
- [ ] A result remains available when desktop notifications cannot be delivered.
- [ ] Startup, failure restart, shutdown, logout, and reboot behavior are verified against the documented prerequisites.
- [ ] Re-running setup preserves configuration, knowledge, and state.
- [ ] A new task retrieves an approved preference from the configured vault.
- [ ] The documented end-to-end scenario passes: schedule a task through `pixie chat`, close the client, execute, deliver or retain the result, restart the service, and inspect history through chat and task commands.

## 5. Phase 1: Codex-backed bilingual voice

### 5.1 Objective and dependency

Add voice as another interface to Pixie by adapting Backtalk to the Phase 0 runtime. Reuse the text chat's conversation handling, task operations, approvals, and result history. Phase 1 depends on the execution interface and task lifecycle established in Phase 0; it must not create a second scheduler, task store, or competing memory system.

### 5.2 Work packages

| ID | Work package | Required changes | Completion evidence |
| --- | --- | --- | --- |
| P1-01 | Replace Claude coupling | Adapt Backtalk's brain integration to the Phase 0 Codex-backed runtime | A spoken request executes through Codex with no Claude Agent SDK dependency |
| P1-02 | Multilingual recognition | Replace the English-only default; validate multilingual local recognition | Spanish, English, and mixed technical vocabulary are captured correctly |
| P1-03 | Bilingual speech | Add Spanish/English output routing or select a verified bilingual speech engine | Responses use the requested language without repeated model initialization |
| P1-04 | Localized controls | Add Spanish and English commands, approval prompts, affirmative responses, denials, and cancellation behavior | Both languages control the same operations consistently |
| P1-05 | Interruption semantics | Separate playback stop, conversational correction, task cancellation, and client shutdown | Interrupting speech does not unintentionally interrupt durable work |
| P1-06 | Conversation continuity | Track pending references and selected task context across voice turns | Follow-up questions identify the correct task and result |
| P1-07 | Setup integration | Add optional voice dependencies and launch controls to the fork's setup | Phase 0 remains usable without audio dependencies |
| P1-08 | Existing visualizer | Optionally publish voice states and waveform signals to ai-visualizer | The selected existing face reflects actual state |

### 5.3 Existing Backtalk areas to adapt

- `brain.py`: replace Claude SDK session management with the runtime client/adapter boundary.
- `main.py`: revise turn routing, bilingual commands, approvals, and interruption semantics.
- `ears.py`: verify multilingual recognition and preserve useful transcription metadata if required.
- `mouth.py`: add language-aware synthesis, independent playback cancellation, and explicit fallback behavior.
- `config.py` and example configuration: expose languages, recognition model, speech engine, backend connection, and microphone settings.
- `signals.py`: preserve compatibility with the existing visualizer contract where practical.
- Package metadata and setup/launch scripts: remove Claude-specific dependencies and add only verified replacements.

The earlier reviewed Backtalk implementation uses `small.en` by default, selects one Kokoro language pipeline from the configured voice, and uses English-oriented built-in control phrases. Changing the recognition model alone will not complete bilingual support.

### 5.4 Interaction requirements

Begin with push-to-talk; hands-free listening, wake words, speaker recognition, and open-speaker echo cancellation are later enhancements unless separately prioritized.

- Respond in the requested language, otherwise follow the current conversation language.
- Accept language changes between turns and mixed-language technical requests.
- Keep Spanish and English activation/control phrases consistent in meaning.
- Keep approval intent explicit; transcription similarity alone must not authorize an action.
- Treat “stop speaking” and “cancel task” as different commands.
- Permit status questions while work continues, without exposing raw tool output as conversational speech.
- On client disconnect, retain accepted tasks and pending results in Phase 0.
- Do not replay a whole backlog of spoken notifications automatically when the user reconnects.

### 5.5 Phase 1 acceptance criteria

- [ ] Complete separate Spanish and English conversations through Codex.
- [ ] Switch languages between turns while preserving context.
- [ ] Correctly handle “Revisá el deployment y avisame si falla el health check.”
- [ ] Ask in Spanish for an answer in English, and the reverse.
- [ ] Confirm and deny an action in both languages.
- [ ] Interrupt speech, then ask about the task that continues in the background.
- [ ] Explicitly cancel a task and report its actual outcome, including any work already performed.
- [ ] Close and reopen voice without losing accepted tasks or stored results.
- [ ] Record end-of-utterance-to-first-audio latency, interruption delay, task accuracy, and resource usage on the target Ubuntu machine.
- [ ] Existing Phase 0 acceptance checks still pass with voice disabled and enabled.

## 6. Implementation order and verification

Implement Phase 0 in this order: integration spike; adapter and instructions; task and conversation persistence; worker and scheduler; shared runtime interface and interactive text chat; services and result delivery; setup and operations verification. P0-10 is part of Phase 0 despite its appended identifier. Then implement Phase 1 against the same runtime and interaction contracts.

Propose the test scope in each implementation plan before making behavior changes. Focus automated checks on state transitions, scheduling, safe recovery, delivery persistence, permission handling, adapter event mapping, chat-to-task registration, conversation resumption, and client detachment. Use bounded real Codex smoke tests for behavior that mocks cannot establish.

Voice requires human listening and representative recordings in addition to automated checks. No recognition quality, accent accuracy, latency, or service reliability has been established by the research alone.

## 7. Open implementation decisions

| Decision | Current position | Resolve by |
| --- | --- | --- |
| Fork URLs and component ownership | Not supplied | Before changing setup/update remotes |
| Codex interface and versions | Python SDK proposed; validate required behavior | P0-01 |
| Authentication and billing | Supported account route to be verified | P0-01 |
| Runtime language and task storage | Python and SQLite proposed | Phase 0 technical plan |
| Logout/boot lifecycle | systemd user service proposed; verify lingering | P0-06 |
| First real workflow | One bounded local task; exact use case not selected | Before end-to-end verification |
| Voice engine and recognition model | Local baseline first; decide from bilingual tests | Phase 1 technical plan |
| Visual design | Reuse existing face; no custom design commitment | P1-08 |

## 8. Sources and research boundaries

Sources establish upstream behavior and supported interfaces; proposed modules, contracts, storage choices, and acceptance criteria are project recommendations.

- [S1 — Official OpenAI documentation: Codex SDK](https://learn.chatgpt.com/docs/codex-sdk)
- [S2 — Official OpenAI documentation: Codex App Server](https://learn.chatgpt.com/docs/app-server)
- [S3 — Official OpenAI documentation: non-interactive execution](https://learn.chatgpt.com/docs/non-interactive-mode)
- [S4 — Official OpenAI documentation: authentication](https://learn.chatgpt.com/docs/auth?surface=cli)
- [S5 — fullstack-agent](https://github.com/jaredrhod/fullstack-agent)
- [S6 — Reviewed fullstack-agent launcher](https://github.com/jaredrhod/fullstack-agent/blob/5bb159f47dbd6fa8f108651d0532a43aef16346b/start.sh)
- [S7 — ai-memory-vault](https://github.com/jaredrhod/ai-memory-vault)
- [S8 — Reviewed Backtalk implementation](https://github.com/jaredrhod/backtalk/tree/84b3a6cd321060cabb74aad6ebe794621cf99bd3)
- [S9 — ai-visualizer](https://github.com/jaredrhod/ai-visualizer)

Recheck upstream and official documentation when implementation starts. This plan does not assume that future upstream revisions preserve the reviewed behavior.
