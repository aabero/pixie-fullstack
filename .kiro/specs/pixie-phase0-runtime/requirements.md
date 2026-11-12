# Requirements Document

## Introduction

Phase 0 of Pixie turns this fork of `jaredrhod/fullstack-agent` into a persistent, Codex-powered personal assistant. Pixie accepts work through an interactive text chat and task commands, executes that work in a background runtime that outlives any client, retains tasks, schedules, conversation references, and results, and runs under Ubuntu systemd user-service management.

Pixie is an always-on personal assistant built within this fork. Phase 0 must demonstrate the complete loop: converse, persist delegated work, execute after the client closes, save results, and return and discuss them. Voice follows in Phase 1 through the same Runtime.

The source of these requirements is `docs/always-on-agent-prototype-plan.md` (sections 1-4, 6, and 7), covering work packages P0-01 to P0-10 and the section 4.12 acceptance criteria. Phase 1 (bilingual voice) is out of scope and appears only as a forward-compatibility constraint.

Repository findings that shape the requirements:

- The fork (origin `git@github.com:aabero/pixie-fullstack.git`) currently contains no application code. It holds a Claude Code installer boot file (`CLAUDE.md`), a conversational setup wizard (`fullstack-agent.md`), terminal launchers (`start.sh`, `start.bat`), update scripts (`update.sh`, `update.bat`), and documentation. The Python runtime, Codex adapter, SQLite store, scheduler, worker, CLI, chat client, systemd unit, setup/doctor scripts, and tests are net-new.
- No `upstream` remote is configured on this fork, the working branch is `kiro-phase0`, and the plan file now lives at `docs/always-on-agent-prototype-plan.md` (moved from the repository root; originally committed at the root in ac88532).
- The code is licensed AGPL-3.0-or-later, copyright Jared Rhodenizer. The license and attribution must be preserved.

Platform scope: Phase 0 is Linux-only (Ubuntu with systemd user services), and the backend is Codex authenticated with the Operator's ChatGPT subscription (no API key). The existing macOS and Windows scripts stay untouched or are marked legacy. User-facing names change now (`pixie` command, `pixie-runtime.service`, assistant name Pixie); repository and directory names are kept. The Operator's machine is an Ubuntu laptop (native Ubuntu 26.04, Python 3.14.4, the `codex` CLI installed through nvm under Node 26, user lingering currently off). If the spike (Requirement 1) shows that the subscription route cannot support unattended execution, the scope is reviewed with the Operator before dependent work continues.

This document is a specification only. Nothing in it authorizes implementation, installation on the owner's computer, or changes to the owner's existing notes.

## Glossary

- **Pixie**: The assistant produced by this project; also the command prefix of its command-line tools.
- **Runtime**: The persistent background process (`pixie-runtime.service`) that owns task execution, scheduling, persistence, approvals, and result delivery, independent of any client.
- **Worker**: The Runtime component that claims queued attempts and executes them through the Codex_Adapter. Phase 0 provides one execution slot.
- **Scheduler**: The Runtime component that evaluates schedules and enqueues due occurrences.
- **Codex_Adapter**: The application-owned execution interface that wraps the selected Codex integration (SDK, app-server, or non-interactive CLI) and maps its events to Application_Events.
- **Application_Event**: A Runtime-defined, timestamped event record (progress, state change, approval request, cancellation request, result).
- **Store**: The SQLite database holding Conversations, Tasks, Schedules, Attempts, Events, Results, Deliveries, and Approvals.
- **Task**: A persisted unit of work with a request, Project_Directory, Results_Location, Permission_Profile, and State.
- **State**: The lifecycle state of a Task: `queued`, `running`, `awaiting_approval`, `blocked`, `succeeded`, `failed`, or `cancelled`.
- **Attempt**: One execution try of a Task, with start and end times, backend references, a lease, a heartbeat, an outcome, and an error category.
- **Schedule**: A persisted trigger definition (manual, one-off, or recurring) with a timezone, next due time, enabled flag, and missed-run policy.
- **Occurrence**: One due instance of a Schedule, identified by the Schedule and its due time.
- **Conversation**: A chat session with a persisted mapping to a Codex thread reference and associated Tasks.
- **Chat_Client**: The `pixie chat` terminal client that connects to the Runtime.
- **Task_CLI**: The non-conversational `pixie` subcommands for inspecting and controlling the Runtime.
- **Approval**: A persisted request for user permission to perform an exact operation, together with its decision. Its kinds are `backend_operation`, `protected_vault_edit`, and `retry_review` (a request for the Operator to allow a `blocked` Task to be retried).
- **Project_Directory**: The configured absolute directory that a Task may read, within the bounds of Requirement 8.
- **Results_Location**: A designated per-Task results directory, managed by the Runtime under the Runtime_Home, where results are written by default.
- **Permission_Profile**: A named set of allowed actions attached to a Task (`read-only` or `workspace-write`), applied relative to the Task's Project_Directory and Results_Location.
- **Result**: The persisted summary, artifact paths, completion status, and output references of a finished Task.
- **Delivery**: A persisted record of an attempt to notify the user of a Result, with channel, status, and last error.
- **Vault**: The Markdown knowledge directory (adapted from ai-memory-vault) holding profile, preferences, daily notes, and job instructions.
- **Vault_Template_Repo**: The adapted fork of `jaredrhod/ai-memory-vault` (`aabero/pixie-ai-memory-vault`), a prompts-and-templates repository without code, adapted in place and licensed CC BY-SA 4.0. It supplies the Vault templates (index, daily note, memory). The optional personalization interview is deferred out of Phase 0.
- **Protected_Section**: A Vault section (profile bio, preferences, vault rules) that a Task may modify only with a granted Approval.
- **Agent_Instructions**: The `AGENTS.md`-based boot instructions defining Pixie's identity and Vault pointers, installed from the separate template `templates/agent/AGENTS.md` to the configured Agent_Instructions location. They are distinct from the repository development rules in the root `AGENTS.md`.
- **Operator_Content**: Operator-authored configuration values, credentials, Vault notes, and existing Store records.
- **Setup_Managed_File**: A file owned by the Setup_Script, such as the systemd unit file and the version manifest.
- **Runtime_Home**: The directory outside the repository checkout where the Runtime keeps configuration, state, logs, and the Store.
- **Setup_Script**: The deterministic script that installs and configures Phase 0.
- **Doctor_Script**: The script that checks the installation and reports problems.
- **Installer_Wizard**: The legacy conversational setup file (`fullstack-agent.md`) and its boot file. Phase 0 provides no Installer_Wizard; the original files are retained only under `legacy/` and in git history (Requirements 16.1, 18.10).
- **Offline_Tool**: An Operator maintenance command (`pixie migrate`, `pixie doctor`, `pixie setup`, `pixie update`) that runs outside the Runtime process, opens files directly while the Runtime is stopped, and is not a general client of the Runtime. Exceptions: the Doctor_Script may act as a read-only Runtime socket client while the Runtime runs, and `pixie setup` stops and restarts the service (Requirements 13.9, 16.14).
- **Schedule_Proposal**: A persisted, single-use, expiring record of a Schedule interpreted from a chat message, awaiting Operator confirmation (identified as `P-n`).
- **Codex_Home**: The dedicated Codex configuration and login directory `codex/` under the Runtime_Home, used only by Pixie.
- **Upstream**: The original repository `jaredrhod/fullstack-agent`.
- **Reviewed_Revision**: A recorded commit identifier of an upstream repository or component that was inspected for this project.
- **Operator**: The single human owner of the Pixie installation.
- **Target_Platform**: Ubuntu Linux with systemd user services.

## Requirements

### Requirement 1: Codex integration spike

**User Story:** As the Operator, I want the Codex integration validated before dependent work begins, so that the Runtime is built on a documented, working interface.

#### Acceptance Criteria

1. WHEN the spike (P0-01) is executed, THE Codex_Adapter SHALL run one bounded task from the intended service environment, complete it within 300 seconds, and record the outcome (success, failure, or timeout), the task input, the final result, and the start and end timestamps in the spike report.
2. THE spike report SHALL record the exact Codex SDK, app-server, or CLI version used (full version identifier) and the dependency pinning method (the mechanism that fixes that exact version, expressed through `uv`, for example a `uv.lock` file or a pinned `uv pip` requirement; decision D31).
3. THE spike report SHALL record, for each of the following, the mechanism used and the observed result from at least one executed run: starting execution, streaming events, retaining thread references, retrieving results, interrupting an active run, and delegating work from a natural-language chat request (criterion 14).
4. WHEN the spike interrupts an active run, THE Codex_Adapter SHALL stop the run within 10 seconds and the spike report SHALL record the run's final state and whether the thread reference remains usable afterward.
5. WHEN the spike triggers an approval request, THE spike report SHALL record how the request surfaces to the Runtime, and, WHILE no user is connected, THE spike report SHALL record the observed worker behavior (waits, denies, or fails) and the elapsed time before that behavior occurs.
6. IF expired authentication, network failure, or a usage limit is reproduced or simulated during the spike, THEN THE spike report SHALL record for each condition how it appears to the Runtime (the observable signal or error indication) and whether the thread state is preserved. IF a condition cannot be reproduced or simulated, THEN THE spike report SHALL mark it "not verified" with the reason.
7. IF the preferred integration cannot provide a required behavior listed in criteria 3 through 6, THEN THE spike report SHALL document the limitation and name another documented interface before any workaround is implemented.
8. THE spike report SHALL record whether the chosen authentication route is subscription-based or API-billed, the account eligibility requirements, the usage limits (with units and period, including whether they are shared with interactive use), the terms applicable to automated use, and the billing implications (cost model and who is billed).
9. THE spike report SHALL record whether login with a ChatGPT subscription works unattended from a systemd user service, and how the Codex_Adapter detects that login has expired.
10. THE spike report SHALL record the Python versions supported by the chosen Codex integration (SDK, app-server client, or CLI wrapper), including whether it supports Python 3.14.4 as installed on the Operator's machine, and SHALL mark the Python 3.14.4 support "not verified" with the reason if it cannot be established.
11. THE spike report SHALL verify whether the chosen integration can enforce the `read-only` and `workspace-write` Permission_Profiles of Requirement 8 through the backend's sandbox or permission configuration (for example sandbox mode and writable roots), SHALL record how each profile is enforced, SHALL record any profile that cannot be enforced, and SHALL record whether reads can be confined to listed directories and whether a path (such as the Codex_Home) can be excluded from reads.
12. THE spike report SHALL record how the chosen Codex integration discovers instruction files, so that the Runtime can ensure that Task executions do not inherit the repository development rules (Requirement 3.16).
13. THE spike report SHALL record how the Codex model and reasoning effort are set through the chosen integration and which values the account accepts, and SHALL mark them "not verified" with the reason if they cannot be established.
14. WHEN the spike sends a natural-language chat request that delegates work, THE spike SHALL demonstrate in at least one executed run that the request invokes a structured Runtime operation (`create_task` or `propose_schedule`) and that the Runtime returns a persisted task identifier (or, for `propose_schedule`, a persisted Schedule_Proposal identifier) that is present in the Store, and THE spike report SHALL record whether delegation works through host tools, structured output, or only slash commands. IF delegation works only through slash commands, THEN THE spike report SHALL record the outcome as reduced conversational functionality. IF the delegation cannot be demonstrated, THEN THE spike report SHALL mark it "not verified" with the reason.

### Requirement 2: Codex execution adapter

**User Story:** As the Operator, I want task execution to go through an application-owned interface, so that the Runtime does not depend on Claude Code and the Codex integration can be replaced.

#### Acceptance Criteria

1. THE Codex_Adapter SHALL expose application-level operations to submit a Task for execution, subscribe to Application_Events for a submitted Task, request cancellation of a submitted Task, and retrieve the final result of a Task, without requiring callers to reference any Codex-specific or Claude-specific type.
2. WHEN Codex emits an event of a supported type, THE Codex_Adapter SHALL map it to exactly one Application_Event, preserving the event order in which Codex emitted it, and deliver it to subscribers within 1 second of receipt.
3. WHEN Codex emits an event of an unsupported type, THE Codex_Adapter SHALL record an unmapped Application_Event containing the raw type name and continue execution of the Task without changing the Task state.
4. WHEN Codex emits an event that is malformed and cannot be parsed, THE Codex_Adapter SHALL record an Application_Event indicating a parse failure, retain the raw payload truncated to 10,000 characters, and continue execution of the Task.
5. WHEN an Attempt starts, THE Codex_Adapter SHALL persist the mapping among Task identifier, Attempt identifier, Codex thread reference, and Codex turn reference, and SHALL update the turn reference each time a new turn begins.
6. IF persisting the mapping fails, THEN THE Codex_Adapter SHALL report the failure to the Runtime, mark the Attempt as failed, and make no further Codex submissions for that Attempt.
7. THE Worker SHALL execute Tasks while neither Claude Code nor the Claude Agent SDK is installed in the runtime environment.
8. THE Codex_Adapter SHALL authenticate through the supported Codex authentication mechanism without reading tokens from Codex credential stores and without writing credential values to any repository file.
9. IF Codex authentication is missing, expired, or rejected, THEN THE Codex_Adapter SHALL fail the submission within 30 seconds, report an authentication failure to the Runtime without including credential values, and make no further submission for that Attempt. The Task State that results from the failure is governed by Requirement 5.7 and 5.16, and Requirement 2.9 governs the timing and content of the failure report.
10. WHEN a stored Codex thread is restored, THE Runtime SHALL treat the thread contents as context only and SHALL NOT mark any external action as completed unless a recorded Application_Event or verification result for that action exists independently of the thread.
11. THE Codex model and reasoning effort SHALL be Runtime_Home configuration values, and THE Runtime source SHALL NOT hardcode any model identifier or effort level. WHERE the model or reasoning effort is unset, THE Runtime SHALL use the Codex integration's own default. IF a configured model or reasoning effort value is unknown or unsupported, THEN THE Runtime SHALL reject it with an error naming the configuration key and SHALL NOT lose any accepted Task. THE Runtime SHALL record the model and reasoning effort used on each Attempt, THE Doctor_Script SHALL report the configured values, and THE example configuration shipped in the repository SHALL carry these keys commented or empty with no hardcoded default model.
12. WHEN the Setup_Script runs, THE Setup_Script SHALL create the Codex_Home with directory mode 0700 and its credential file with mode 0600, and, IF either has a looser mode, THEN THE Setup_Script SHALL tighten it and report the change.
13. THE Doctor_Script SHALL fail the permissions line of the Codex authentication check IF the Codex_Home directory is looser than mode 0700 or its credential file is looser than mode 0600. WHERE the backend cannot exclude the Codex_Home from reads by Task executions (including when reads cannot be confined), THE Doctor_Script SHALL report the exposure as a known risk and THE `pixie status` output SHALL show `codex_home_exposure: yes`.
14. THE Runtime SHALL use only the Codex_Home for Codex login material and SHALL NOT fall back to a shared `~/.codex`. IF the Codex_Home cannot hold a working unattended login, THEN the scope SHALL be reviewed with the Operator as stated in the Introduction.

### Requirement 3: Identity and memory instructions

**User Story:** As the Operator, I want Pixie to load its identity and my approved preferences on every execution, so that it behaves consistently across tasks.

#### Acceptance Criteria

1. WHEN the Setup_Script runs, THE Setup_Script SHALL install Agent_Instructions from the separate template `templates/agent/AGENTS.md` (not from the root `AGENTS.md`, Requirement 18.1) to the configured Agent_Instructions location, and that template defines the assistant name Pixie and the Vault pointers, and that template SHALL be original text written for this repository, so that no CC BY-SA text from the Vault templates is copied into any file of this repository.
2. WHEN a new execution starts, THE Runtime SHALL provide the Agent_Instructions to Codex before Codex processes the first Task prompt of that execution.
3. IF the Agent_Instructions cannot be read when a new execution starts, THEN THE Runtime SHALL NOT start the execution, SHALL mark the Task as failed, and SHALL notify the Operator with an error indicating that the Agent_Instructions are unavailable.
4. WHEN a new Task is executed, THE Runtime SHALL make approved preferences from the configured Vault available to that execution before Codex processes the first Task prompt.
5. IF the configured Vault is missing or unreadable when a new Task is executed, THEN THE Runtime SHALL start the execution without preferences, SHALL notify the Operator with a warning indicating that the Vault is unavailable, and SHALL leave the Vault contents unchanged.
6. IF an `AGENTS.md` file already exists at the installation target, THEN THE Setup_Script SHALL leave the existing file byte-for-byte unchanged and SHALL write the Pixie template to a separate path distinct from the installation target.
7. WHEN an execution requests a write to shared Vault knowledge while another execution holds the Vault write, THE Runtime SHALL queue the request and SHALL begin it only after the earlier write completes, so that no two executions write the Vault at the same time.
8. IF a queued Vault write has not started within 60 seconds, THEN THE Runtime SHALL abandon the write, SHALL leave the Vault contents unchanged, and SHALL report a failure indicating a Vault write timeout to the requesting execution.
9. WHEN a Task is created from a Conversation, THE Runtime SHALL start a Codex context that is separate from the contexts of all other Tasks and SHALL provide to it only the request text and the Conversation messages selected through the structured task-creation operation, where the default selection is the delegating message and the six messages preceding it.
10. THE Agent_Instructions and the Vault templates installed by the Setup_Script SHALL contain no interactive-only rules, including rules that require stopping after asking a question, waiting for confirmation before editing, never suggesting to stop, or ending a reply with a forward question.
11. THE Runtime SHALL handle every request for permission to act only through the Approval mechanism defined in Requirement 8, and THE Agent_Instructions SHALL NOT define any other approval path.
12. WHEN the Setup_Script runs, THE Setup_Script SHALL create the Vault folder structure, index notes, templates, and frontmatter conventions deterministically and without any interview, and THE Setup_Script SHALL NOT include the personalization interview, which is deferred out of Phase 0 and, if added later, SHALL remain optional and SHALL NOT be authoritative for any Vault content or Runtime configuration.
13. WHEN a new Task is executed, THE Runtime SHALL read approved preferences only from the designated preferences section of the Vault index.
14. IF a Task attempts to modify a Protected_Section of the Vault without a granted Approval, THEN THE Runtime SHALL block the modification, create an Approval for the exact change under Requirement 8, and leave the Protected_Section unchanged.
15. THE Runtime SHALL read the Vault path from exactly one authoritative configuration entry in the Runtime_Home configuration, and every other consumer of the Vault path (Setup_Script, Doctor_Script, Agent_Instructions, and Task_CLI) SHALL derive the path from that entry.
16. THE Runtime SHALL NOT let Task executions inherit the repository development rules from the root `AGENTS.md`, and THE Runtime SHALL provide Pixie's Agent_Instructions explicitly to each execution, using the instruction discovery behavior recorded by the spike (Requirement 1.12).
17. THE Vault_Template_Repo SHALL supply index and daily-note templates that contain no fill-in markers, no interview instruction block, no reference to a Claude boot file, no Obsidian-specific instructions, and no interactive-only rules (criterion 10), and that carry the level-2 headings `Vault location`, `Who I Am`, `My Preferences for Working with AI`, and `Vault Rules for AI` used by criteria 13 and 14. An automated check SHALL verify this heading set and the absence of those items.
18. WHEN the Setup_Script creates the Vault from the templates, THE Setup_Script SHALL fill the "Vault location" entry from the single configuration entry of criterion 15, and IF the path found in the Vault index differs from that entry, THEN THE Doctor_Script SHALL report a warning.

### Requirement 4: Durable task store

**User Story:** As the Operator, I want tasks, schedules, and results to survive client closure and restarts, so that accepted work is never lost.

#### Acceptance Criteria

1. THE Store SHALL persist Conversations, Tasks, Schedules, Attempts, Events, Results, Deliveries, and Approvals in SQLite.
2. WHEN the Runtime starts and no Store exists, THE Runtime SHALL initialize the Store at the current schema version automatically. IF the Runtime starts and the Store has a pending schema migration, THEN THE Runtime SHALL NOT apply the migration, SHALL refuse to start, and SHALL tell the Operator which migrate step to run. WHEN the Operator invokes the migrate step on an existing Store, THE migrate step SHALL show the pending migrations, take a verified SQLite backup under the Runtime_Home, and apply each migration in ascending version order within its own transaction, recording the applied schema version after each migration succeeds.
3. IF a schema migration fails, THEN THE migrate step SHALL roll back that migration, leave the recorded schema version unchanged, leave the backup in place, and report an error identifying the failed migration version and the backup location.
4. WHEN a State transition is requested and permitted by the lifecycle, THE Store SHALL commit the State change and the corresponding Event in a single transaction, so that either both are persisted or neither is.
5. WHEN the Runtime restarts, whether after a normal shutdown, client closure, or abnormal termination, THE Store SHALL retain all records committed before the restart, with no partial State transitions visible.
6. IF a requested State transition is not permitted by the lifecycle, THEN THE Store SHALL reject the transition, return an error indicating the current State and the requested State, leave the Task unchanged, and record no Event for the transition.
7. THE Runtime SHALL keep the Store under the Runtime_Home, outside the repository checkout.
8. IF the Store schema version is newer than the highest version the Runtime supports, THEN THE Runtime SHALL refuse to start without modifying the Store, and report an error indicating both the Store schema version and the highest supported version.

### Requirement 5: Task lifecycle

**User Story:** As the Operator, I want clear task states, so that I can tell what Pixie is doing and why.

#### Acceptance Criteria

1. THE Runtime SHALL represent every Task in exactly one State from `queued`, `running`, `awaiting_approval`, `blocked`, `succeeded`, `failed`, and `cancelled` at any point in time.
2. WHEN a Task reaches `succeeded`, `failed`, or `cancelled`, THE Runtime SHALL treat the Task as terminal, reject any further State transition request for that Task, leave the Task State unchanged, and return an error to the caller indicating the Task is terminal.
3. WHEN the Operator requests cancellation of a Task that is not terminal, THE Store SHALL record the cancellation request, including the request time, separately from the Task State, within 1 second of the request.
4. IF the Operator requests cancellation of a Task that is already terminal, THEN THE Runtime SHALL reject the request, leave the Task State unchanged, and return an error to the Operator indicating the Task is terminal.
5. WHEN the backend acknowledges the cancellation outcome, THE Runtime SHALL set the Task State to `cancelled` if the work was stopped, or to `succeeded` or `failed` if the Task completed before cancellation took effect, and THE Store SHALL record the work already performed before the State changes.
6. IF the backend does not acknowledge a cancellation request within 30 seconds, THEN THE Runtime SHALL keep the Task in its current State, retain the recorded cancellation request, and surface to the Operator that cancellation is pending.
7. IF Codex authentication has expired, THEN THE Runtime SHALL set the affected Task to `blocked` with an error category of `authentication` and a message telling the Operator that re-authentication is required.
8. IF a usage limit prevents execution, THEN THE Runtime SHALL set the affected Task to `blocked` with an error category of `usage_limit` and a message telling the Operator which limit was reached and, when known, when it resets.
9. IF a network failure prevents execution and the failure persists after the configured maximum number of retries (Requirement 7.5, default 3), THEN THE Runtime SHALL set the affected Task to `failed` with an error category of `network` and a message telling the Operator the action to take, and THE Store SHALL retain the Task's recorded progress.
10. WHEN cancellation is requested for a Task with no active Attempt (State `queued` or `blocked`), THE Runtime SHALL set the Task to `cancelled` immediately and SHALL record any possible-external-action note from earlier Attempts.
11. WHEN cancellation is requested for a Task with an active Attempt (State `running` or `awaiting_approval`), THE Runtime SHALL keep the Task State unchanged while the request is pending, SHALL ask the Codex_Adapter to cancel the Attempt, SHALL mark any pending Approval of that Task as withdrawn, and SHALL change the State only under criterion 5 when the backend outcome is known (`cancelled`, or `succeeded` or `failed` if the Task finished first). THE Chat_Client and Task_CLI SHALL show a pending cancellation request while it is pending.
12. IF the Runtime restarts while a cancellation request is pending, THEN THE Runtime SHALL honor the request during reconciliation (Requirement 7), SHALL NOT re-queue the Task, SHALL confirm that the previous backend execution is no longer active, and SHALL then set the Task to `cancelled`, recording whether an external action may have occurred.
13. THE Runtime SHALL permit exactly the following State transitions and no others: `queued` to `running` or `cancelled`; `running` to `awaiting_approval`, `succeeded`, `failed`, `blocked`, `queued`, or `cancelled`; `awaiting_approval` to `running`, `queued`, `failed`, `succeeded`, `blocked`, or `cancelled`; `blocked` to `queued`, `failed`, or `cancelled`; and no transition out of `succeeded`, `failed`, or `cancelled`. This table is the lifecycle referred to in Requirements 4.4 and 4.6.
14. WHEN the Operator requests `pixie tasks resume <task-id>` (or the equivalent chat command) for a `blocked` Task, THE Runtime SHALL set the Task to `queued`, and IF the Task is not `blocked`, THEN THE Runtime SHALL reject the request with an error indicating the current State and leave the Task unchanged.
15. WHEN the Operator answers a `retry_review` Approval, THE Runtime SHALL set the Task from `blocked` to `queued` if the answer is grant, and from `blocked` to `failed` if the answer is deny.
16. WHILE Codex authentication is unresolved after a failure under criterion 7, THE Worker SHALL keep other queued Tasks in `queued` without claiming them, until a successful authentication check or an Operator resume.

### Requirement 6: Scheduling

**User Story:** As the Operator, I want Pixie to run work at scheduled times without an open terminal, so that recurring briefings and checks happen on their own.

#### Acceptance Criteria

1. THE Scheduler SHALL support exactly three Schedule types: manual (runs only when the Operator triggers it), one-off (runs once at a single specified date and time), and recurring (runs repeatedly according to a single standard 5-field cron expression evaluated in the Schedule's explicit IANA timezone).
2. THE Scheduler SHALL compute each Occurrence's due time in the Schedule's explicit timezone, using IANA timezone identifiers, including correct handling of daylight-saving transitions.
3. WHERE the Operator does not specify a timezone for a Schedule, THE Scheduler SHALL use the configured default timezone, which defaults to America/Montevideo.
4. WHEN an Occurrence becomes due, THE Scheduler SHALL enqueue exactly one Task for that Occurrence within 5 seconds of its due time while the Runtime is running.
5. IF the Scheduler evaluates the same Occurrence more than once, THEN THE Scheduler SHALL enqueue a Task for it only once and SHALL NOT create duplicate Tasks.
6. WHEN the Runtime starts after downtime, THE Scheduler SHALL apply each Schedule's missed-run policy to Occurrences that were due during the downtime, where the policy "skip" enqueues no Task for missed Occurrences and the policy "catch up" enqueues exactly one Task per missed Occurrence, in due-time order.
7. THE Scheduler SHALL persist Schedules, including their type, recurrence rule, timezone, missed-run policy, and the record of Occurrences already enqueued, so that they survive Runtime restarts without loss.
8. IF the Scheduler fails to persist a Schedule, THEN THE Scheduler SHALL reject the create or update request, SHALL indicate the failure to the Operator with an error stating the Schedule was not saved, and SHALL leave previously saved Schedules unchanged.
9. WHEN a scheduled Task becomes due, THE Worker SHALL execute it without a terminal or client connected.
10. THE Scheduler SHALL create recurring and one-off Occurrences only from Schedules the Operator created and SHALL NOT invoke the model on its own initiative outside of executing a Task enqueued from an Operator-created Schedule.
11. WHEN the Runtime interprets a Schedule from a chat message, THE Scheduler SHALL persist a Schedule_Proposal in the Store with an absolute expiry time equal to its creation time plus the configured proposal lifetime (default 30 minutes, allowed range 1 to 1440 minutes), so that proposals and their expiry times survive a Runtime restart unchanged, and a change of the configured lifetime SHALL apply only to proposals created afterwards.
12. IF 3 unexpired Schedule_Proposals are pending when a further proposal is requested, THEN THE Scheduler SHALL reject the request with an error telling the Operator to confirm or discard one, SHALL create no proposal, and SHALL leave every existing proposal unchanged.
13. WHEN the Operator confirms a Schedule_Proposal, THE Scheduler SHALL, in a single transaction, mark the proposal consumed and create the Schedule, so that each proposal creates at most one Schedule.
14. IF the Operator confirms a Schedule_Proposal that is unknown, discarded, consumed, or whose expiry time has been reached, THEN THE Scheduler SHALL reject the confirmation with an error naming the reason and SHALL create no Schedule.
15. WHEN the Operator confirms a Schedule_Proposal, THE Scheduler SHALL recompute the run times of the preview, and IF they differ from the preview the Operator was shown, THEN THE Scheduler SHALL create no Schedule, SHALL return the recomputed preview, and SHALL leave the proposal pending with its original expiry. IF a one-off run time has already passed at confirmation, THEN THE Scheduler SHALL reject the confirmation and create no Schedule.
16. WHEN the Operator confirms without naming a proposal, THE Scheduler SHALL confirm the only pending proposal, and IF several are pending, THEN THE Scheduler SHALL reject the confirmation with an error listing their identifiers and create no Schedule. WHEN the Operator discards a pending proposal, THE Scheduler SHALL mark it discarded so that it no longer counts toward the limit of criterion 12, and THE Chat_Client SHALL be able to list pending proposals with their expiry times.

### Requirement 7: Worker execution and recovery

**User Story:** As the Operator, I want the worker to run one task at a time and recover safely after interruptions, so that crashes do not cause lost or duplicated external actions.

#### Acceptance Criteria

1. THE Worker SHALL execute at most one Attempt at a time.
2. WHEN the Worker claims an Attempt, THE Worker SHALL record a lease with an expiry of 60 seconds from the claim time and SHALL refresh the heartbeat every 15 seconds only while the Codex_Adapter reports the backend execution alive, extending the lease expiry to 60 seconds from each refresh, until the Attempt reaches a terminal outcome.
3. IF an Attempt's active execution time exceeds its configured timeout (default 300 seconds, allowed range 1 to 3600 seconds), THEN THE Worker SHALL request cancellation of the Attempt, record the Attempt outcome as `timed_out`, and preserve all data recorded by the Attempt up to that point. WHILE the Task is `awaiting_approval`, THE Worker SHALL pause the timeout measurement, and WHEN the Approval is granted, THE Worker SHALL resume it with the remaining budget preserved. THE Worker SHALL continue lease heartbeats while the Task is `awaiting_approval`.
4. WHEN the Runtime starts, THE Runtime SHALL, before claiming any Attempt, identify every Attempt in a running or awaiting-approval state that belongs to a different Runtime instance than the current one, regardless of whether its lease has expired, mark each as stale, and reconcile each one according to criteria 5, 6, 7, 11, and 12. WHILE a Runtime instance is running, lease expiry SHALL detect a hung Attempt of that instance, which is reconciled in the same way.
5. WHEN a stale Attempt is repeatable and has no recorded external action, THE Runtime SHALL, after confirming or forcing that the previous backend execution is no longer active, re-queue its Task as a new Attempt, provided the number of retries already performed is below the configured maximum retries (default 3, allowed range 0 to 10).
6. IF a stale Attempt may have performed an external action (an external action is recorded, or the Attempt is not repeatable), THEN THE Runtime SHALL set the Task to `blocked`, record the reason as possible external action, not re-queue the Task, and prevent any retry until the Operator has explicitly approved it by granting a `retry_review` Approval that THE Runtime SHALL create for that Task (Requirements 5.14 and 5.15 define the exit from `blocked`).
7. IF the number of retries performed for a Task equals the configured maximum retries when reconciliation or failure handling would otherwise re-queue it, THEN THE Runtime SHALL set the Task to `failed`, record the error category of the last failed Attempt, and not create a further Attempt.
8. WHEN the Runtime receives a shutdown signal, THE Worker SHALL stop claiming new Attempts immediately, and SHALL record any in-flight Attempt as interrupted for reconciliation within 10 seconds of receiving the signal, so that the next start reconciles it under criteria 4 to 7 by instance identifier without waiting for lease expiry.
9. IF recording the lease, a heartbeat refresh, or a reconciliation outcome fails, THEN THE Worker SHALL stop executing the current Attempt, SHALL NOT claim a new Attempt, and SHALL report an error indicating the persistence failure to the Operator.
10. THE Runtime SHALL generate a unique instance identifier at each process start and record it on every Attempt it claims, and THE Runtime SHALL hold a single-instance lock in the Runtime_Home so that a second Runtime process refuses to start while the lock is held.
11. IF the Runtime cannot confirm that the previous backend execution of a stale Attempt is no longer active, THEN THE Runtime SHALL set the Task to `blocked` for Operator review through a `retry_review` Approval and SHALL NOT re-queue it. THE Runtime SHALL NOT allow two active Attempts for one Task or two concurrent Attempts overall.
12. WHEN a stale Attempt belongs to a Task in `awaiting_approval`, THE Runtime SHALL close the interrupted Attempt as `interrupted`, SHALL keep the Task's pending Approval and State, and SHALL NOT re-run the Task before the Approval is answered. WHEN the Approval is granted, THE Runtime SHALL give the new Attempt the grant bound to the exact operation; WHEN it is denied, Requirement 8.8 applies. IF an external action may have been recorded, THEN criterion 6 still applies and the Task is set to `blocked`.

### Requirement 8: Permissions and approvals

**User Story:** As the Operator, I want Pixie to ask before taking consequential actions, so that background work stays within limits I set.

#### Acceptance Criteria

1. WHEN a Task is created, THE Runtime SHALL attach to the Task one Project_Directory expressed as an absolute path and exactly one Permission_Profile, SHALL assign the Task's Results_Location, and SHALL reject creation of a Task that lacks a Project_Directory or a Permission_Profile with an error indicating which value is missing, leaving no Task persisted.
2. THE Runtime SHALL permit, by default, reads only within the configured Project_Directory (and within the Vault for approved preferences, Requirement 3) and writes only within the Task's Results_Location, as upper bounds that the Permission_Profiles of criteria 10 and 11 may narrow (for example, the `read-only` profile permits no agent writes), with a maximum size of 10 MB per file and a maximum of 100 files per Task audited under criterion 17, and THE Runtime SHALL canonicalize paths so that symbolic links and `..` segments cannot escape these bounds.
3. IF a Task attempts a read or write outside the bounds of criterion 2 or beyond its limits and the operation is not covered by its Permission_Profile or a recorded preauthorization, THEN THE Runtime SHALL block the operation, create an Approval for the exact operation, and set the Task to `awaiting_approval`.
4. WHEN a Task requires an external change not covered by its Permission_Profile or a recorded preauthorization, THE Runtime SHALL, within 2 seconds, create exactly one Approval that identifies the exact operation (operation type, target, and parameters), set the Task to `awaiting_approval`, and not perform the operation until the Approval is granted.
5. WHEN the Operator answers an Approval with grant or deny, THE Runtime SHALL record the decision, the answering client type, and the timestamp against that exact Approval, apply the decision only to the operation named in that Approval, and, if granted, resume the Task within 5 seconds.
6. IF an Approval has already been answered and a further answer is submitted for it, THEN THE Runtime SHALL reject the further answer with an error indicating the Approval is already resolved and SHALL keep the original decision unchanged.
7. WHILE no Chat_Client or Task_CLI is connected to answer an Approval, THE Runtime SHALL keep the Task in `awaiting_approval`, SHALL keep the Approval pending with no time-based expiry, and SHALL NOT grant the Approval.
8. IF an Approval is denied, THEN THE Runtime SHALL NOT perform the operation, SHALL record the denial as a Task Event that references the Approval, and SHALL set the Task to `failed` with error category `approval_denied` within 5 seconds; Phase 0 does not continue a Task with other work independent of the denied operation. For a `retry_review` Approval, denial is governed by Requirement 5.15.
9. THE Runtime SHALL process Approval answers from Chat_Client and Task_CLI through the same Approval mechanism, such that an identical answer from either client produces the same recorded decision and the same Task state transition.
10. WHERE a Task has the `read-only` Permission_Profile, THE Runtime SHALL permit reads within the Project_Directory and the Vault, SHALL permit no agent writes anywhere, and SHALL itself persist the Task's Result and write the result file into the Results_Location from the agent's final output.
11. WHERE a Task has the `workspace-write` Permission_Profile, THE Runtime SHALL permit the same reads as `read-only` and agent writes only inside the Results_Location, and SHALL require an explicit preauthorization or an Approval for any write inside the Project_Directory or elsewhere.
12. THE Runtime SHALL enforce the write bounds of criteria 2, 10, and 11 (and the read bounds where the backend supports read confinement, criterion 16) through the backend's sandbox or permission configuration (for example sandbox mode and writable roots), set per Task from its Permission_Profile, and SHALL NOT rely on prompt instructions alone.
13. IF the chosen Codex integration cannot enforce the Permission_Profile of a Task (Requirement 1.11), THEN THE Runtime SHALL fail closed by not running the Task with writes and SHALL report the reason to the Operator.
14. THE project SHALL include a smoke test (the sandbox canary) showing that an out-of-bounds write attempt is blocked regardless of the prompt. THE Doctor_Script MAY run the sandbox canary only through `pixie doctor --probe` and only WHILE the Runtime is stopped; WHILE the Runtime is running, THE Doctor_Script SHALL NOT run the canary, so that a running Doctor stays within the status-only limit of Requirement 13.9.
15. WHILE a Task is `awaiting_approval`, THE Runtime SHALL keep the Task's Attempt in the single execution slot so that no execution overlaps, SHALL keep queued Tasks waiting, and SHALL show the stall in status output and chat (decision D25).
16. IF the backend cannot confine reads to the Project_Directory and the Vault, THEN THE Runtime SHALL still run the Task, SHALL record a `read_confinement_unavailable` warning Event on every Attempt, and THE Doctor_Script SHALL report the limitation; write bounds remain fail-closed under criterion 13.
17. WHEN an Attempt ends or a file-change Event is received, THE Runtime SHALL audit the Results_Location against the per-file and per-Task limits of criterion 2, because the backend sandbox cannot enforce those limits; IF a limit is exceeded, THEN THE Runtime SHALL end the Attempt with error category `limit_exceeded` and retain the files for review.
18. WHERE the backend does not surface approval requests, THE Runtime SHALL create Approvals only for Runtime-mediated operations (Vault edits and retry review), SHALL record an operation the sandbox denies as a `sandbox_denied` Event, and SHALL record in the verification result that Tasks needing external changes are unsupported with that backend.

### Requirement 9: Ubuntu service management

**User Story:** As the Operator, I want Pixie to run as a managed service, so that it starts, restarts, and stops predictably.

#### Acceptance Criteria

1. WHEN the Operator runs the Setup_Script, THE Setup_Script SHALL install `pixie-runtime.service` as a systemd user service whose unit file specifies absolute paths for the Runtime executable, the working directory, and the configuration file, where the `ExecStart` command SHALL invoke the Python interpreter or entry point of the `uv`-managed virtual environment by absolute path, and SHALL NOT depend on `uv`, `PATH` lookups, or shell activation at service start (decision D31).
2. WHEN systemd starts `pixie-runtime.service`, THE service SHALL start the Runtime without reading any interactive shell startup file, and the Runtime SHALL reach a running state within 30 seconds.
3. THE Runtime SHALL start, run, and stop without requiring the Chat_Client, the Task_CLI, or any graphical client to be running, and stopping or crashing any of those clients SHALL leave the Runtime process running.
4. IF the Runtime process exits with a non-zero status or is terminated by a signal other than an Operator-issued stop, THEN THE service SHALL restart the Runtime after a delay that grows from about 2 seconds up to a maximum of 60 seconds on consecutive failures. Approximate growth is acceptable when the installed systemd lacks exact doubling or `RestartSteps`, and a fixed `RestartSec` is an acceptable fallback for older systemd versions, provided the fallback in use is documented (criterion 14).
5. IF the Runtime exits because of a configuration error, or because it refuses to start with a pending Store schema migration (Requirement 4.2), THEN THE service SHALL write a log entry identifying the invalid or missing configuration item or, for a pending migration, the migrate step to run, and SHALL stop restarting after 5 consecutive failed starts within 300 seconds, leaving the service in a failed state visible in the status command output.
6. THE documentation SHALL list the exact commands to start, stop, restart, show status, and follow logs for `pixie-runtime.service`, and SHALL state the expected observable result of each command.
7. WHERE user lingering is enabled, THE Runtime SHALL start at boot without any user login and SHALL keep running after the Operator logs out of all sessions. THE Setup_Script SHALL ask the Operator before enabling user lingering, because it is a system change, and SHALL NOT enable it silently.
8. IF user lingering is unavailable or the Operator declines to enable it, THEN THE documentation SHALL state the reduced lifecycle (the Runtime stops at logout and does not start until the Operator logs in), AND the verification result SHALL record the logout-persistence and boot-before-login criteria as not met, with the reason.
9. THE documentation SHALL state that background availability requires the machine to be powered on and not suspended or hibernated.
10. WHEN the Operator issues the stop command, THE service SHALL terminate the Runtime within 30 seconds, and the service SHALL NOT restart it.
11. THE unit file of `pixie-runtime.service` SHALL specify an explicit absolute path to the Codex executable, and THE Runtime SHALL NOT resolve the Codex executable through nvm, the `PATH` set by shell startup files, or any other shell startup file.
12. WHERE the Codex executable is a launcher that requires `node`, THE unit file SHALL set a minimal `PATH` consisting of the directory of the `node` executable found at setup time followed by the system binary directories, and THE Setup_Script SHALL record that directory in the configuration.
13. IF the Runtime fails to start 5 consecutive times within 300 seconds for any cause, THEN THE service SHALL stop restarting and remain in a failed state visible in the status command output.
14. THE documentation SHALL state which restart-delay mechanism the installed systemd supports (growing delay with `RestartSteps` and `RestartMaxDelaySec`, or the fixed `RestartSec` fallback for older systemd), the delay values in effect, and the systemd version on which this was observed.

### Requirement 10: Local runtime transport and client detachment

**User Story:** As the Operator, I want clients to connect to a single runtime securely, so that closing a client never cancels my work.

#### Acceptance Criteria

1. THE Runtime SHALL accept client connections only through a local transport (a Unix domain socket with owner-only permissions) that is accessible solely to the Operator's operating system user and is not reachable from any network interface.
2. IF a connection attempt originates from a different operating system user or from a network interface, THEN THE Runtime SHALL reject the connection within 1 second and SHALL NOT process any request from it.
3. THE Chat_Client and Task_CLI SHALL perform all task operations through the Runtime and SHALL NOT start unmanaged Codex executions.
4. WHEN a client disconnects or closes, whether normally or abnormally, THE Runtime SHALL continue every accepted Task without changing its state and SHALL retain its recorded progress and results.
5. IF the Runtime is stopped or unreachable, THEN THE Chat_Client and Task_CLI SHALL report within 5 seconds an error indicating the Runtime is unavailable, SHALL exit Task_CLI with a non-zero exit code, and SHALL NOT run a separate assistant process.
6. WHEN the Operator requests cancellation of an unfinished conversational turn, THE Runtime SHALL stop only that turn and SHALL leave every persisted Task unchanged.
7. WHEN the Operator requests cancellation of a persisted Task by its identifier, THE Runtime SHALL handle the request under the cancellation request and acknowledgment lifecycle of Requirement 5 (criteria 3 to 6 and 10 to 12), SHALL NOT mark a running Task `cancelled` before the actual execution outcome is established, and SHALL NOT alter any conversational turn or any other Task.

### Requirement 11: Interactive text chat

**User Story:** As the Operator, I want to converse with Pixie in a terminal, so that I can ask questions and delegate work naturally.

#### Acceptance Criteria

1. WHEN the Operator runs `pixie chat`, THE Chat_Client SHALL connect to the Runtime within 5 seconds, open or resume a Conversation, and display the identifier of the selected Conversation before accepting the first message.
2. IF the Chat_Client cannot connect to the Runtime within 5 seconds, THEN THE Chat_Client SHALL display an error indicating the Runtime is unreachable, create no Conversation, and exit with a non-zero exit code.
3. WHEN the Operator sends a message, THE Chat_Client SHALL display the reply incrementally as each streamed segment is received from Codex, with the first segment shown within 1 second of its receipt by the Chat_Client.
4. IF the reply stream from Codex fails or is interrupted before completion, THEN THE Chat_Client SHALL retain the partial reply already displayed, display an error indicating the reply was incomplete, and accept the next Operator message.
5. WHEN the Operator sends a follow-up message, THE Runtime SHALL generate the reply using the prior messages of the same Conversation as context.
6. WHEN the Operator asks to start a new Conversation, THE Chat_Client SHALL create a new Conversation with a distinct identifier, display that identifier, and leave all earlier Conversations and their messages unchanged.
7. WHEN the Operator runs `pixie chat` and a previous Conversation with a persisted thread reference exists, THE Chat_Client SHALL offer to resume that Conversation and SHALL resume it only if the Operator accepts.
8. THE Runtime SHALL process turns within a single Conversation one at a time in the order received, and SHALL NOT start a turn until the preceding turn in that Conversation has completed or failed.
9. WHILE the Worker is executing a Task, THE Chat_Client SHALL accept Operator input and respond to status requests and Approval answers, with each response displayed within 2 seconds of the request.
10. IF a conversational turn cannot start immediately, THEN THE Chat_Client SHALL display a queued or waiting indicator, including the turn's position in the queue where known, within 1 second, and SHALL remove the indicator when the turn starts.
11. WHEN a Task update arrives while chat is connected, THE Chat_Client SHALL display the update as a distinct entry within 2 seconds, without removing or altering any message already displayed and without interrupting a reply that is streaming.
12. WHEN the Operator reconnects, THE Chat_Client SHALL display the count of unread Results and a way to list them, and SHALL mark a Result as read only after the Operator has viewed it.

### Requirement 12: Chat-to-task registration

**User Story:** As the Operator, I want Pixie's confirmation of a task to mean it is really saved, so that I can trust delegated work.

#### Acceptance Criteria

1. WHEN the Operator sends a chat message that delegates work, THE Runtime SHALL create the Task or Schedule through a structured Runtime operation and SHALL NOT create it from free-text reply content.
2. WHEN the Store has committed the Task or Schedule record, THE Chat_Client SHALL display a confirmation of acceptance within 2 seconds of the commit.
3. IF the Store fails to commit the Task or Schedule record, or the commit is not confirmed within 10 seconds, THEN THE Chat_Client SHALL display an error indicating the work was not registered, SHALL NOT display a confirmation of acceptance, and THE Runtime SHALL leave no partial record in the Store.
4. WHEN a Task is accepted, THE Chat_Client SHALL display its Task identifier in the same message as the confirmation of acceptance.
5. WHEN the Runtime interprets a recurring Schedule from a chat message, THE Chat_Client SHALL display the cron expression, the IANA timezone name, and the next three run times in that timezone, and THE Runtime SHALL create the Schedule only after the Operator confirms that preview, consistent with criterion 6 and with the Schedule_Proposal rules of Requirements 6.11 to 6.16. WHEN a one-off Schedule is interpreted, THE Chat_Client SHALL display the run time and the IANA timezone name, and THE Runtime SHALL create the one-off Schedule only after the Operator confirms that preview in the same way. WHEN the Chat_Client displays a preview, THE Chat_Client SHALL display the proposal identifier and its expiry time. WHEN the Schedule is accepted, THE Chat_Client SHALL display that interpretation in the same message as the confirmation of acceptance.
6. IF the scheduling intent is ambiguous (the message lacks a resolvable time, recurrence, or timezone, or admits more than one interpretation), THEN THE Chat_Client SHALL ask one clarifying question, THE Runtime SHALL NOT create a Schedule, and THE Store SHALL contain no new Schedule record for that message.
7. WHEN the Runtime creates a delegated Task, THE Runtime SHALL store the identifier of the originating Conversation on the Task record, and every delegated Task SHALL have exactly one originating Conversation.
8. IF a conversational reply states that a Task or Schedule was registered and the Store contains no corresponding committed record, THEN THE Runtime SHALL be considered non-conforming, and automated tests SHALL fail when this condition occurs.

### Requirement 13: Task commands

**User Story:** As the Operator, I want direct commands to inspect and control Pixie, so that I can manage work without a conversation.

#### Acceptance Criteria

1. WHEN the Operator runs `pixie status`, `pixie tasks list`, `pixie tasks show <task-id>`, `pixie results latest`, `pixie approvals list`, or `pixie schedule list`, THE Task_CLI SHALL request the data from the Runtime through the local transport (Requirement 10.1), which reads it from the Store, print it to standard output, and exit with status zero within 2 seconds when the Store holds up to 1,000 Tasks.
2. WHEN the Operator runs a Task_CLI command to submit a Task, create or modify a Schedule, approve or deny a pending Approval, cancel a Task, or resume a `blocked` Task (`pixie tasks resume <task-id>`, Requirement 5.14), THE Task_CLI SHALL request the change from the Runtime through the local transport and exit with status zero after the Runtime reports that the Store has committed it, where for a cancellation of a Task with an active Attempt the committed change is the cancellation request and the Task_CLI SHALL report that cancellation is pending until the State changes (Requirement 5.11).
3. THE Task_CLI and Chat_Client SHALL show identical Tasks, Approvals, and Results, with identical field values, when each queries the Runtime at the same point in time.
4. WHEN the Operator submits a Task through the Task_CLI, THE Task_CLI SHALL display its Task identifier only after the Store has committed the Task.
5. IF the Operator names a Task identifier that does not exist, THEN THE Task_CLI SHALL print an error message indicating the Task was not found, make no change to the Store, and exit with a non-zero status.
6. IF a Task_CLI command fails because the Store is unavailable to the Runtime, a commit fails, or an argument is missing or malformed, THEN THE Task_CLI SHALL print an error message indicating the cause, leave the Store unchanged, and exit with a non-zero status.
7. IF the Operator approves, denies, or cancels an Approval or Task that is not in a state permitting that action (for example, an Approval already decided or a Task already completed), THEN THE Task_CLI SHALL print an error message indicating the current state, leave the Store unchanged, and exit with a non-zero status.
8. IF a list command finds no matching records, THEN THE Task_CLI SHALL print a message indicating that no records exist and exit with status zero.
9. THE Offline_Tools (`pixie migrate`, `pixie doctor`, `pixie setup`, `pixie update`) SHALL NOT be clients of the Runtime for the purposes of Requirements 10.3, 13, and 20.3, and SHALL be run by the Operator while the Runtime is stopped, except that (a) WHILE the Runtime is running, THE Doctor_Script MAY act as a read-only client of the Runtime socket, limited to status and health queries, and (b) `pixie setup` stops and restarts the service itself under Requirement 16.14. This exception does not make the Doctor_Script a general client of the Runtime, and THE Doctor_Script SHALL NOT read or open the Store directly while the Runtime runs. WHEN the Runtime is not running, THE Doctor_Script SHALL skip the checks that require the Runtime and report each as "Runtime not running" (Requirement 16.6).
10. IF the Runtime is stopped or unreachable when the Operator runs a Task_CLI command, THEN THE Task_CLI SHALL behave as stated in Requirement 10.5 and SHALL NOT read the Store directly.

### Requirement 14: Result delivery

**User Story:** As the Operator, I want results saved and surfaced reliably, so that I can find them even if a notification fails.

#### Acceptance Criteria

1. WHEN a Task finishes, THE Runtime SHALL persist the Result to durable storage and confirm the write succeeded before attempting any Delivery.
2. IF persisting the Result fails, THEN THE Runtime SHALL skip all Delivery attempts, record a persistence error indicating the failure cause on the Task, and set the Task to the State that the finish produces without altering it because of the persistence failure.
3. WHERE desktop notifications are enabled and a graphical session is available, THE Runtime SHALL attempt one desktop notification within 5 seconds of Result persistence and record the Delivery status as either delivered or failed.
4. IF notification delivery fails, a graphical session is unavailable, or the notification attempt does not complete within 10 seconds, THEN THE Runtime SHALL keep the Result unchanged, record the Delivery status as failed together with the last error text, and leave the Task State unchanged.
5. THE Runtime SHALL limit each notification payload to a title of at most 80 characters and a body of at most 200 characters, and SHALL limit the body to the Task identifier, the final Task State, and a truncated Result summary that excludes Task input, file contents, credentials, and environment values.
6. WHEN the Runtime restarts, THE Runtime SHALL make all previously persisted Results and their Delivery statuses retrievable through chat and Task_CLI, listed in order of Result creation time from newest to oldest.

### Requirement 15: Secrets handling

**User Story:** As the Operator, I want credentials kept out of tracked files and logs, so that they do not leak.

#### Acceptance Criteria

1. THE Runtime SHALL store credentials only in the Runtime_Home and SHALL NOT write credential values to any file tracked by the repository.
2. WHEN the Runtime builds a prompt, produces a Result summary, emits an Event, or writes a log entry, THE Runtime SHALL replace every configured credential value appearing in that output with a redaction placeholder before the output is stored, transmitted, or displayed.
3. THE repository SHALL track only example configuration files that contain placeholder values in place of credentials, and SHALL keep personal configuration, state, and credentials in the Runtime_Home.
4. WHERE the Runtime_Home resides within the repository checkout during development, THE `.gitignore` SHALL exclude all files and subdirectories of the Runtime_Home so that `git status` lists none of them as untracked or modified.
5. IF a credential value is detected in a prompt, Result summary, Event, or log entry after redaction has been applied, THEN THE Runtime SHALL discard the unredacted output, SHALL record an error indicating that a credential leak was blocked without including the credential value, and SHALL leave the stored credential unchanged.
6. IF the Runtime cannot read a required credential from the Runtime_Home, THEN THE Runtime SHALL refuse to start the dependent operation, SHALL report an error naming the missing credential key but not its value, and SHALL NOT fall back to reading the credential from a tracked repository file.

### Requirement 16: Reproducible setup

**User Story:** As the Operator, I want a deterministic, repeatable installation, so that I can rebuild or update Pixie without losing data.

#### Acceptance Criteria

1. THE Setup_Script (`scripts/setup.sh`) SHALL be the only installation entry point and SHALL define all installation steps, and THE Phase 0 flow SHALL NOT include a conversational Installer_Wizard (consistent with Requirement 18.1 and decision D19).
2. THE Setup_Script SHALL install only Phase 0 dependencies by default and SHALL NOT install Backtalk models, audio packages, or visual components.
3. WHEN the Setup_Script completes an installation, THE Setup_Script SHALL record, for each installed component, its remote location, its Reviewed_Revision, and the exact version of each dependency installed (as resolved by `uv`, for example in `uv.lock`).
4. WHEN the Setup_Script is run on an existing installation, THE Setup_Script SHALL NOT delete, overwrite, or move existing Operator_Content, and the only permitted changes SHALL be creating missing files and folders (initialization), updating Setup_Managed_Files, and applying displayed, versioned migrations after a backup. Normal Runtime writes (Store records, and Vault notes written by Tasks under Requirements 3 and 8) are not violations of this criterion.
5. WHEN a configuration migration is required, THE Setup_Script SHALL display the full list of configuration changes (each key added, changed, or removed, with old and new values, and credential values redacted under Requirement 15) before applying any change, SHALL make a backup copy of the affected files under the Runtime_Home before the change, and SHALL version each configuration migration.
6. WHEN the Operator runs the Doctor_Script, THE Doctor_Script SHALL check the Runtime service, Store version, configuration, Codex authentication state, and Vault path, and SHALL report a result of pass, fail, or skipped with a reason for each of the five checks within 30 seconds, where a skipped result is never counted as a pass. WHILE the Runtime is running, THE Doctor_Script SHALL obtain Runtime-dependent information (for example the Store version) only as a read-only client of the Runtime socket and SHALL NOT read the Store directly (Requirement 13.9). WHILE the Runtime is not running, THE Doctor_Script SHALL skip each check that requires the Runtime and report it as "Runtime not running", which is a skipped result and not a pass; checks that need only files (configuration, Codex_Home permissions, Vault path) and the service state SHALL still run. THE Doctor_Script SHALL exit with a non-zero status only WHEN at least one check fails, so a result consisting only of passes and skipped checks exits with status zero.
7. IF one or more Doctor_Script checks fail, THEN THE Doctor_Script SHALL still report the result of every remaining check and SHALL exit with a non-zero status. A skipped check alone SHALL NOT cause a non-zero exit (criterion 6).
8. IF a Setup_Script prerequisite is missing, THEN THE Setup_Script SHALL stop before modifying any file, name each missing prerequisite, and exit with a non-zero status.
9. THE Setup_Script SHALL NOT install, register, or configure Obsidian, and SHALL NOT read or modify any Obsidian configuration, including `obsidian.json` and any `.obsidian` folder.
10. THE Vault SHALL be usable as plain Markdown files without Obsidian, and THE Doctor_Script SHALL NOT require Obsidian to be present and SHALL NOT fail any check because Obsidian is absent.
11. WHILE the Runtime is stopped and no migration is pending, WHEN the Setup_Script is re-run, THE preservation check SHALL show Operator-owned configuration files, credential files, and Vault notes content-identical by hash comparison, and all pre-existing Store records logically unchanged by row-level comparison (SQLite file bytes are not compared, because checkpoints and journaling alter them).
12. WHILE the Runtime is running, THE preservation check SHALL be limited to records and files that the Runtime does not write.
13. THE Setup_Script SHALL create the Python virtual environment and install all Python dependencies with `uv` (for example `uv venv`, `uv sync`, or `uv pip`), and SHALL NOT use the stdlib `venv` module or bare `pip`. WHEN the Setup_Script runs, THE Setup_Script SHALL check that `uv` is present, and IF `uv` is missing, THEN THE Setup_Script SHALL stop before modifying any file, print a clear instruction for installing `uv`, exit with a non-zero status, and SHALL NOT install `uv` without the Operator's explicit consent (decision D31; Requirement 16.8).
14. WHEN `pixie setup` runs and `pixie-runtime.service` is running, THE Setup_Script SHALL stop the service before applying any change, and SHALL start it again at the end, respecting the Operator's lingering and enable choices (Requirements 9.7 and 9.8; a service that was not running, or that the Operator chose not to enable, is not started or enabled against that choice). THE Setup_Script SHALL report what it did (whether it stopped the service, whether it restarted it, and why it did not restart it where applicable). IF the service cannot be stopped, THEN THE Setup_Script SHALL stop before modifying any file and exit with a non-zero status.

### Requirement 17: Version-aware updates

**User Story:** As the Operator, I want updates to be explicit and recoverable by a documented procedure, so that my adaptations are not silently replaced.

#### Acceptance Criteria

1. WHEN the Operator starts an update, THE update procedure SHALL fetch only from the configured forks and SHALL apply only the component versions recorded in the version manifest.
2. IF an update would move any component to a version different from its recorded version, THEN THE update procedure SHALL display the component name, the current version, and the target version, and SHALL wait for explicit Operator confirmation (yes/no) before applying that change.
3. THE documented update and recovery procedure SHALL consist of these ordered steps: stop the service; back up the Runtime_Home configuration and the Store; show the incoming changes from the configured remotes; apply only the pinned revisions after explicit Operator confirmation; synchronize the Python environment with `uv` (for example `uv sync`) from the pinned lock; run the migrate step if needed (Requirement 4.2); run the Doctor_Script while the Runtime is still stopped (Runtime-dependent checks are skipped and reported as "Runtime not running", Requirement 16.6); restart the service; run the Doctor_Script a second time with the Runtime running. IF the Operator declines confirmation, THEN the procedure SHALL apply no change and leave all recorded versions unchanged. The Phase 0 components SHALL be this repository and the Vault_Template_Repo only.
4. WHEN an update is available, THE update procedure SHALL display the list of changed components and, for each one, the commit list between the current and target versions (with a count of changed files) before applying anything.
5. WHEN an update is applied, THE update procedure SHALL NOT delete, overwrite, or move existing Operator_Content, subject to the permitted changes and the preservation checks of Requirement 16.4, 16.11, and 16.12.
6. IF an update fails, THEN THE update procedure SHALL stop, SHALL report an error that identifies the failed component and the reason, and SHALL point to the documented manual recovery procedure, which restores the backup taken in criterion 3 and checks out the previously recorded revisions. THE recovery SHALL be a documented manual procedure and SHALL NOT be automatic.
7. WHEN an update is applied, THE update procedure SHALL leave all upstream attribution and license notice files and headers present and with unmodified content in every updated component.

### Requirement 18: Repository disposition

**User Story:** As the maintainer, I want a defined plan for each existing file, so that the fork is adapted without losing its provenance or the Operator's data.

#### Acceptance Criteria

1. THE project SHALL adapt `CLAUDE.md` and `fullstack-agent.md` into a root `AGENTS.md` that contains repository development rules only, SHALL keep Pixie's installed identity and memory instructions in a separate template `templates/agent/AGENTS.md` (as in section 4.11 of the source plan) that the Setup_Script installs to the configured Agent_Instructions location, SHALL NOT merge the two files, and SHALL remove the Claude Code installer boot path from the Phase 0 flow.
2. THE project SHALL adapt `README.md`, `TROUBLESHOOTING.md`, and `CONTRIBUTING.md` so that each file describes Pixie Phase 0, Codex, and the Ubuntu service lifecycle, and so that none of them references Claude Code as a prerequisite or setup path.
3. THE project SHALL adapt `start.sh` and `update.sh` so that no voice, face, or hands launcher starts, stops, or restarts the Runtime, and so that the Runtime lifecycle is controlled only by the Ubuntu service.
4. THE project SHALL remove the Claude Code prerequisite and the `claude "set me up"` setup path from the Phase 0 flow, so that a search of the Phase 0 documentation and scripts for "claude" outside the legacy location and upstream attribution returns zero matches.
5. THE project SHALL replace the Desktop launcher flow, the blind pull-latest update, and the Claude-specific wiring (for example `backtalk.json` wiring) in the Phase 0 flow, so that the Phase 0 flow contains zero references to each of them and the update path fetches and shows the incoming changes to the Operator before applying any of them.
6. THE project SHALL preserve the AGPL-3.0-or-later `LICENSE` file byte-for-byte, the copyright notice of Jared Rhodenizer, and upstream attribution in every adapted file.
7. THE project SHALL NOT delete, overwrite, or move any existing Operator_Content during adoption, install, or update, and the only permitted changes SHALL be those defined in Requirement 16.4.
8. THE project SHALL preserve the separate license file of each component and the complete git history of the fork, with no history rewrite, squash, or force push of existing commits.
9. THE project SHALL add a git remote named `upstream` pointing to `jaredrhod/fullstack-agent`, and SHALL record in a version-controlled file the Reviewed_Revision (git commit hash) of each reviewed repository, including `5bb159f` for this fork.
10. THE project SHALL retain each original Claude-oriented file, in unmodified form, either in git history or in a directory named `legacy`, with a README in that directory stating the files are retained pending the Operator's removal decision, until the Operator decides to remove them.
11. THE project SHALL keep the plan file at `docs/always-on-agent-prototype-plan.md`, the move from the repository root having been done at the Operator's request, and WHEN the Operator asks for a commit, THE project SHALL record the move in that commit.
12. IF the move of the plan file to `docs/` is not yet committed, THEN THE project SHALL leave the file at `docs/always-on-agent-prototype-plan.md` and SHALL NOT delete it.
13. IF an adaptation step would delete, overwrite, or move existing Operator_Content, THEN THE project SHALL abort that step, leave the content unchanged, and report to the Operator an error identifying the file and the step.
14. THE project SHALL keep Vault_Template_Repo templates and any adapted Vault text licensed under CC BY-SA 4.0 with attribution to Jared Rhodenizer and share-alike preserved, SHALL keep them in their own license file separate from the AGPL-3.0-or-later license of the Runtime, and SHALL document the mixed licensing (AGPL Runtime, CC BY-SA templates) in the repository documentation. Vault-derived templates SHALL remain only in the Vault_Template_Repo under CC BY-SA 4.0, and the Pixie identity template in this repository SHALL be original text that borrows ideas but not sentences from them. THE documentation SHALL state that this is not legal advice and that a qualified review is advised before publishing or selling.
15. THE project SHALL replace, in the Phase 0 flow, the following Claude-specific Vault parts: the `templates/MEMORY.md` redirect, the `~/.claude/projects` memory migration, the Claude-as-executor framing of the wizard, the shipped Jarvis identity (name, tone, and welcome line), the `[FILL IN]` markers and AI interview block of the index template, the Claude boot-file reference, and the Obsidian-specific advice, as specified in Requirement 3.17.
16. THE project SHALL provide a Pixie identity block with a neutral default name, tone, and welcome line in place of the Jarvis identity, located in the separate template `templates/agent/AGENTS.md` (Requirement 18.1).
17. THE project SHALL record in a version-controlled file the Reviewed_Revisions `5bb159f` (fullstack-agent fork) and `659bba9` (Vault_Template_Repo fork).
18. THE project SHALL adapt the Vault_Template_Repo in place as a template repository, and SHALL configure a git remote named `upstream` in that repository pointing to `https://github.com/jaredrhod/ai-memory-vault.git`.

### Requirement 19: Verification and documentation

**User Story:** As the maintainer, I want an automated and documented verification path, so that Phase 0 acceptance can be demonstrated.

#### Acceptance Criteria

1. THE project SHALL include automated tests covering every area listed in the Test Scope section, runnable from a single documented command that exits with code 0 when all tests pass and a non-zero code when any test fails.
2. THE project SHALL include real Codex smoke tests for behavior that mocks cannot establish, each with a maximum runtime of 120 seconds, and each reporting a timeout as a failure instead of hanging.
3. THE project SHALL include a manual verification procedure covering systemd service start, stop, and restart, user logout, and host reboot, where each step states the action to perform, the expected observable outcome, and a pass/fail recording field.
4. THE project SHALL provide an operations runbook (`docs/operations.md`) that describes the end-to-end scenario as an ordered list of steps, each with the command to run and the expected observable result.
5. WHEN the end-to-end scenario runs, THE scenario SHALL use as its workflow a summary of the state of a development project, reading the Project_Directory read-only under the `read-only` Permission_Profile and having the Runtime write the summary as a result file into the Results_Location (Requirement 8.10), WHERE the Operator chooses which project through configuration, AND THE verification result SHALL show, as separate pass/fail items, that a task scheduled through `pixie chat` executes after the client closes, delivers its Result or retains it when delivery is not possible, survives a service restart without losing the task or its Result, and appears in both chat history and Task_CLI history.
6. IF a criterion cannot be verified or a known limitation exists, THEN THE verification result SHALL record that criterion as "unverified" or list it under known limitations, with the reason, and SHALL NOT count it as passed.
7. IF an automated test, smoke test, or end-to-end scenario step fails, THEN THE verification result SHALL record the overall outcome as failed, identify the failing item, and retain the results of the items that did run.
8. THE automated tests SHALL use the fake Codex_Adapter and SHALL NOT require network access or an installed Codex.
9. IF an environment criterion is not met where verification ran, THEN THE verification result SHALL record that criterion as "unverified" with the reason, and SHALL NOT count it as passed.

### Requirement 20: Phase 1 forward compatibility

**User Story:** As the maintainer, I want Phase 0 to leave room for voice, so that Phase 1 reuses the same runtime without rework.

#### Acceptance Criteria

1. THE Runtime SHALL expose Conversation handling, task operations (create, list, get, request cancellation under Requirement 5), approvals (list pending, approve, reject), and Result history (list, get) through a single client interface that the Phase 0 text client uses for 100% of its Runtime interactions.
2. THE Runtime SHALL accept every operation listed in criterion 1 from any client that implements the client interface, without requiring changes to Runtime scheduler, Store, or memory code.
3. THE Runtime SHALL remain the only process that reads or writes the scheduler state, the Store, and memory in all phases, and no client SHALL access them directly.
4. WHEN two clients are connected to the Runtime at the same time, THE Runtime SHALL apply operations from both clients to the same scheduler, Store, and memory, and return results for each operation to the client that issued it.
5. THE Phase 0 installation SHALL install, start, and complete all Phase 0 acceptance tests on a machine that has no microphone, no audio output device, and no transcription or speech libraries installed.
6. THE Phase 0 Runtime source and dependency manifest SHALL contain zero modules, dependencies, or configuration options for audio capture, audio playback, transcription, speech synthesis, or visualizers.
7. IF a client calls a voice, audio, transcription, or speech operation in Phase 0, THEN THE Runtime SHALL reject the call with an error indicating the operation is unsupported and leave the scheduler, Store, and memory unchanged.

## Assumptions and Unresolved Decisions

The following items are assumptions or decisions. Items marked RESOLVED are settled; every other item must be resolved or confirmed by the stated point, and the design phase SHALL NOT silently choose a value for them.

| ID | Item | Current position | Resolve by |
| --- | --- | --- | --- |
| D1 | Component fork URLs and ownership (ai-memory-vault, Backtalk, ai-visualizer, Barehands) | PARTIALLY RESOLVED. Vault fork exists at `aabero/pixie-ai-memory-vault` (HEAD 659bba9, `upstream` set to `jaredrhod/ai-memory-vault`, nothing fetched). Backtalk, ai-visualizer, and Barehands will be forked in Phase 1 from the reviewed revision (Backtalk 84b3a6c per the plan); they are not needed in Phase 0. | Phase 1 |
| D2 | Codex interface: Python SDK, app-server, or non-interactive CLI, and pinned versions | OPEN, resolved by the Requirement 1 spike. Python SDK proposed (first candidate; `openai-codex`, controls the local Codex app-server over JSON-RPC with a pinned runtime, requires Python 3.10+), fallbacks app-server directly, then `codex exec`. The spike records the supported Python versions (Requirement 1.10). Open questions for the spike: unattended login with a ChatGPT subscription from a systemd service; how approval requests surface to application code; cancellation/interruption and error signals; usage limits shared with interactive use. | Requirement 1 spike (P0-01) |
| D3 | Authentication route and billing (subscription or API-billed) | OPEN. The Operator has a ChatGPT subscription (no API key). Whether it supports unattended use, its limits, and its terms for automated use are verified by the spike (Requirements 1.8, 1.9). | Requirement 1 spike (P0-01) |
| D4 | Runtime language and storage | RESOLVED: Python and SQLite. | Resolved |
| D5 | Logout and boot lifecycle | OPEN. Aim for user lingering so the Runtime starts at boot and survives logout; setup asks before enabling it (Requirements 9.7, 9.8). Actual behavior is verified and recorded as met, not met, or unverified. | Manual verification |
| D6 | First bounded real workflow for end-to-end verification | RESOLVED: a summary of the state of a development project, read-only on the Project_Directory under the `read-only` Permission_Profile, with the result file written into the Results_Location by the Runtime, not by the agent. The Operator chooses which project through configuration (Requirement 19.5). | Resolved |
| D7 | Vault location and whether ai-memory-vault is adapted in place or vendored | RESOLVED for adaptation: adapted in place as a template repository (Vault_Template_Repo). The Vault location itself is set in Runtime_Home configuration (Requirement 3.15). | Resolved |
| D8 | Platform scope: Phase 0 targets Ubuntu with systemd, while existing scripts also support macOS and Windows | RESOLVED: Phase 0 is Linux-only (Ubuntu, systemd). The macOS and Windows scripts remain untouched or marked legacy. Listed as out of scope and reflected in the Introduction and Requirement 18. | Resolved |
| D9 | Rename of the repository, directories, and references from `fullstack-agent` to Pixie | RESOLVED: keep repository and directory names. Only user-facing names change now (`pixie` command, `pixie-runtime.service`, assistant name Pixie). A full rename may be revisited later. | Resolved |
| D10 | Disposition of `always-on-agent-prototype-plan.md` | RESOLVED and DONE: moved to `docs/` at the Operator's request (staged, uncommitted); committing it awaits the Operator's request (Requirement 18.11, 18.12). | Resolved |
| D11 | Local runtime transport (Unix domain socket or other user-restricted channel) | RESOLVED: Unix domain socket with owner-only permissions (Requirement 10.1). | Resolved |
| D12 | Handling of pre-existing Claude-era artifacts on the Operator's machine (a `CLAUDE.md` in a parent folder, existing vault) | RESOLVED: setup never edits a parent `CLAUDE.md` or an existing vault (Requirement 18.7). | Resolved |
| D13 | Default values: timeouts, retry limit, heartbeat interval, backoff, missed-run default policy | RESOLVED: use the defaults in the detailed criteria: 60 s lease, 15 s heartbeat, 300 s timeout, 3 retries, 2-60 s backoff (Requirements 7 and 9). Default missed-run policy: skip. The `catch_up` policy is uncapped, as Requirement 6.6 states; the Operator accepts the risk of many Tasks after a long outage with a frequent cron. | Resolved |
| D14 | Recurring schedule format (cron-like, interval, or other) | RESOLVED: recurring schedules use standard 5-field cron plus an explicit IANA timezone (default America/Montevideo); the evaluation library is a design choice. One-off remains its own Schedule type. Cron limits: it cannot express a one-off run or an even every-N-hours cadence beyond the day. See Requirements 6.1 and 12.5. | Resolved |
| D15 | Desktop notification mechanism on Ubuntu | RESOLVED: libnotify `notify-send` is the optional mechanism and must not block execution (Requirements 14.3, 14.4). | Resolved |
| D16 | Permission_Profile model and preauthorization format | RESOLVED: named Permission_Profiles, the first two being `read-only` (reads in Project_Directory and Vault, Runtime writes the result file) and `workspace-write` (same reads, agent writes only in the Results_Location), enforced through the backend sandbox (Requirement 8.10 to 8.13). Preauthorizations are stored as explicit entries naming the exact operation (Requirement 8). | Resolved |
| D17 | Role of Obsidian | RESOLVED: optional in Phase 0, never installed, registered, or configured by setup (Requirement 16.9, 16.10). | Resolved |
| D18 | License compatibility between the AGPL-3.0-or-later Runtime and CC BY-SA 4.0 templates | RESOLVED (Option A): Pixie's `templates/agent/AGENTS.md` identity template is written from scratch in this AGPL repository as original text, borrowing ideas but not sentences from the CC BY-SA vault templates. Vault-derived templates stay only in the vault fork under CC BY-SA 4.0 (Requirements 3.1, 18.14). This is not legal advice; a qualified review is advised before publishing or selling. | Resolved |
| D19 | Whether the optional personalization interview wizard is kept for Codex in Phase 0 or deferred | RESOLVED: deferred out of Phase 0 (Requirement 3.12, Out of Scope). | Resolved |
| D25 | Execution slot during approval waits | RESOLVED: in Phase 0 a Task in `awaiting_approval` keeps its Attempt and the single execution slot, queued Tasks wait behind it, and the stall is visible in status output and chat (Requirement 8.15). Parking the Attempt to free the slot is explicitly deferred to a later phase. | Resolved |
| D26 | Store schema migration timing | RESOLVED: migrating an existing Store to a newer schema is an explicit Operator-invoked step that shows pending migrations, takes a verified SQLite backup, and applies each migration in its own transaction. Initialization of a missing Store is automatic. The Runtime refuses to start while a migration is pending and tells the Operator which step to run (Requirements 4.2, 4.3, 9.5). | Resolved |
| D27 | Permission_Profile of the project-summary workflow | RESOLVED: the project-summary workflow runs under the `read-only` Permission_Profile, and the Runtime persists the Result and writes the result file into the Task's Results_Location from the agent's final output. `workspace-write` remains available for future workflows that need agent-written artifacts (Requirements 8.10, 8.11, 19.5; D6). | Resolved |
| D28 | Schedule proposal behavior (J-25, J-26) | RESOLVED: proposals are persisted with an absolute expiry (default 30 minutes), at most 3 pending, single-use confirmation, preview recomputed at confirm time, applied to one-off and recurring Schedules (Requirements 6.11 to 6.16, 12.5). | Resolved |
| D29 | Codex home permissions and exposure (J-28) | RESOLVED: a dedicated Codex_Home with directory mode 0700 and credential file mode 0600, enforced by setup and checked by the Doctor_Script; exposure to Task sandboxes is reported as a known risk where it cannot be excluded; no fallback to a shared `~/.codex` (Requirements 2.12 to 2.14). | Resolved |
| D30 | Read confinement when the backend cannot provide it (RI-4) | RESOLVED by the Operator: Tasks still run with a recorded warning; write bounds stay fail-closed (Requirement 8.16). | Resolved |
| D31 | Python environment and dependency tooling | RESOLVED by the Operator: virtual environments and dependency installation use `uv` (`uv venv`, `uv sync`, `uv pip`), not the stdlib `venv` module or bare `pip`. Setup checks for `uv` and, if missing, stops with a clear instruction and does not auto-install it without Operator consent (Requirements 1.2, 9.1, 16.3, 16.13, 17.3). | Resolved |
| D32 | Restart backoff precision | RESOLVED: the growing restart delay (about 2 s up to 60 s) is approximate; a fixed `RestartSec` is an acceptable documented fallback on older systemd (Requirements 9.4, 9.14). | Resolved |
| D33 | Doctor_Script as read-only socket client and skipped-result semantics | RESOLVED by the Operator: a running Doctor_Script is a read-only, status-and-health-only client of the Runtime socket and never reads the Store directly; the sandbox canary runs only via `pixie doctor --probe` while the Runtime is stopped. Each check reports pass, fail, or skipped; skipped is never a pass; the exit status is non-zero only when a check fails (Requirements 8.14, 13.9, 16.6, 16.7, 17.3). | Resolved |
| D34 | Setup stops and restarts the service | RESOLVED: `pixie setup` stops a running `pixie-runtime.service` before changing anything and restarts it at the end, respecting the Operator's lingering and enable choices; if the stop fails, setup aborts before modifying any file (Requirements 13.9, 16.14). | Resolved |

## Test Scope

Test scope SHALL be proposed again in each implementation plan before behavior changes are made. The categories below define the baseline.

### Automated checks (no real Codex)

The Codex_Adapter is replaced by a fake that emits scripted events. These checks need no network access or Codex installation (Requirement 19.8).

- State transitions: the lifecycle permits only valid transitions and terminal states reject further changes (Requirement 5).
- Scheduling: timezone handling for America/Montevideo, one-off and recurring due-time computation, missed-run skip and catch-up policies, and no duplicate enqueue of the same Occurrence (Requirement 6).
- Restart recovery: stale lease reconciliation, bounded retry, and blocked state for possible external actions (Requirement 7).
- Immediate-restart reconciliation with unexpired leases, instance identifiers, and the single-instance lock (Requirement 7.4, 7.10 to 7.12).
- Attempt timeout paused during an approval wait and resumed with the remaining budget (Requirement 7.3).
- Cancellation request and acknowledgment lifecycle, including restart with a pending cancellation (Requirement 5.10 to 5.12).
- Backend-enforced permission bounds with an out-of-bounds negative case that is blocked regardless of the prompt (Requirement 8.12 to 8.14).
- Store migration: backup, refusal to start with a pending migration, and rollback of a failed migration (Requirement 4.2, 4.3).
- Preservation checks under the stated conditions: hash comparison of Operator-owned files and row-level comparison of Store records (Requirement 16.11, 16.12).
- Model and reasoning effort configuration validation (Requirement 2.11).
- Delivery persistence: a Result is saved before Delivery, and a failed Delivery leaves the Task State unchanged (Requirement 14).
- Permission and approval enforcement: no silent grant, exact-operation binding, denial behavior, and the no-client case (Requirement 8).
- Adapter event mapping: each supported event maps to one Application_Event, and unsupported events are recorded (Requirement 2).
- Chat-to-task registration: confirmation follows a committed record, and ambiguous schedules create nothing (Requirement 12).
- Conversation resumption and serialization of turns (Requirement 11).
- Client detachment: disconnecting a client leaves accepted Tasks running (Requirement 10).
- Setup idempotency: running the Setup_Script twice with no pending migration leaves Operator_Content unchanged under the conditions of Requirement 16.11 and 16.12.
- Store migrations and schema version refusal (Requirement 4).

### Property-based testing candidates

- Lifecycle state machine: for any sequence of transition requests, the Task State is always one of the seven States, and terminal States never change.
- Scheduler idempotency: evaluating the same set of Schedules at the same instant any number of times enqueues each Occurrence exactly once.
- Scheduler timezone invariant: the computed next due time is later than the reference time and is stable under repeated evaluation.
- Recovery idempotency: running restart reconciliation twice produces the same Store state as running it once.
- Setup idempotency: Setup_Script applied twice equals applied once on the resulting configuration.
- Round trip: serializing and deserializing Application_Events, Schedules, and configuration files returns an equivalent object.
- Event mapping: for any generated supported event, mapping is total and produces exactly one Application_Event.
- Approval binding: for any generated pending Approvals and decisions, a decision affects only its own Approval.
- Single active Attempt: at most one active Attempt exists overall at any instant, including across restarts.
- Timeout accounting: time spent in `awaiting_approval` never counts toward the Attempt timeout.

### Bounded real Codex smoke tests

- A bounded task runs from the service environment and returns a recorded Result (Requirement 1).
- Streaming, thread reference retention, and interruption behave as recorded in the spike.
- An authentication or usage-limit failure produces the expected blocked or failed state, where it can be induced safely.
- A new Task retrieves an approved preference from the configured Vault.

Smoke tests are few, bounded in cost, and excluded from default test runs. 

### Manual and systemd verification

- Service start, failure restart with backoff, shutdown, and log inspection.
- Behavior after logout and reboot, with and without user lingering (Requirement 9.7, 9.8).
- Desktop notification delivery with and without a graphical session.
- The end-to-end runbook scenario (Requirement 19), using the project-state summary workflow (read-only project directory, result file output, project configurable by the Operator).

Verification that cannot be performed SHALL be recorded as unverified and not reported as passed, including environment criteria unmet on the machine where verification ran (Requirement 19.9).

## Out of Scope

The following items are excluded from Phase 0:

- Voice: microphone access, transcription, speech generation, Spanish and English voice interaction, and any Backtalk changes. Only the forward-compatibility constraint in Requirement 20 applies.
- The ai-visualizer and any custom visual design.
- Barehands and gesture input.
- Remote or mobile access and any public server.
- Email, calendar, and other broad external integrations. Phase 0 validates one bounded local workflow only.
- Deployment or installation on the Operator's computer, and any change that requires it.
- Edits to the Operator's existing personal notes or existing Vault content.
- macOS and Windows support for the new Runtime (decision D8: Phase 0 is Linux-only; existing macOS/Windows scripts stay untouched or are marked legacy).
- The optional personalization interview wizard (decision D19).
- A full rename of the repository and directories (decision D9); only user-facing names change.
- Forking Backtalk, ai-visualizer, and Barehands (Phase 1, from the reviewed revisions).
- Concurrent task execution beyond one Worker slot, and multi-user operation.
