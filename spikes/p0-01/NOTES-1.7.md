# Task 1.7 notes (spike P0-01): natural-language delegation proof. Status: verified (host tools via MCP)
Date: 2026-11-15. Throwaway; not application code. SDK openai-codex 0.169.0 (bundled binary 0.169.0), Python 3.14.4, dedicated CODEX_HOME (`spikes/p0-01/.codex-home`).

## Stub
- `stub/stub_ops.py`: SQLite store; `create_task(title, instructions)` inserts into `tasks` and returns `task-<8 hex>`; `propose_schedule(title, cadence, instructions)` inserts into `schedules` with status `proposed` and returns `sched-<8 hex>`.
- `stub/mcp_server.py`: minimal stdio MCP server (hand-written newline-delimited JSON-RPC, no extra dependency) exposing those two tools. Started by Codex as a short-lived child of the transient unit; ends with the app-server.
- Per-case DB files `stub/stub-<case>.db` (git-ignored; fake data only), recreated at the start of each run. Verification read them with Python `sqlite3` after the unit ended, independent of the agent reply.

## Mechanism order
1. **Host tools (MCP server, configured with `config.mcp_servers.pixie_stub` in `thread_start`)**: tried first, **works**. Stopped here.
2. Dynamic tools (the other host-tool route): not tried; the MCP route already works.
3. Structured output: not tried (a mechanism earlier in the order worked). Not verified.
4. Slash commands only: not tried. Not verified. Nothing was rejected; no reduced-conversational-functionality finding applies.

## Runs (each: transient unit `pixie-spike-del-<case>`, `--wait --collect`, RuntimeMaxSec=290, in-script alarm 200 s, StandardInput=null, PATH = node dir + /usr/local/bin:/usr/bin:/bin, absolute venv python, dedicated CODEX_HOME). Runner: `run_delegation_unit.sh <case> "<prompt>"` -> `run_delegation_probe.py`. Thread params: `sandbox=read-only`, `approvalPolicy=never`, temp cwd (removed after), `project_doc_max_bytes=0`.
Run 1 (task, approval default). 2026-11-15T23:29:13Z to 23:29:25Z (11.5 s). Input: "Please remind me to renew my library card: set up a one-off task called 'Renew library card' for me to do this week."
- The model called `create_task` (item `mcpToolCall`, server `pixie_stub`) with sensible arguments. The call **failed at once**: "MCP tool call requires approval, but approval policy is never". No row stored. The agent said so. Result: tool selection from natural language works, but MCP tool calls need approval by default.
- raw: `raw/deleg-task-run1-approval-never.redacted.json`.
Fix: server config key `default_tools_approval_mode = "approve"` (name found in the binary's config keys; not documented anywhere I read). This pre-approves the server's tools, so no handler is needed. Whether `approval_mode` per tool works: not verified.
Run 2 (task). 2026-11-15T23:31:58Z to 23:32:08Z (10.5 s). Same input.
- `create_task` called, item status `completed`, tool result text `{"id": "task-aeae2a74"}`. Reply: "Created the one-off task "Renew library card" for this week." (reply does not quote the id).
- Independent check of `stub/stub-task.db`: `tasks` has exactly one row, `task-aeae2a74`, title "Renew library card", `schedules` empty. **Identifier returned by the tool and found in the store.**
- raw: `raw/deleg-task.redacted.json`.
Run 3 (sched, propose_schedule). 2026-11-15T23:32:39Z to 23:32:50Z (10.7 s). Input: "Every weekday at 08:00, I want a short summary of my open tasks. Please propose that as a recurring schedule, don't activate anything."
- Four `mcpToolCall` events (2 calls, started+completed). Store `stub-sched.db`: `tasks` empty, `schedules` has one row `sched-9bd59551`, status `proposed`, title "Weekday open tasks summary", cadence "Every weekday (Monday-Friday) at 08:00 America/Montevideo" (the model added the timezone itself; the stub did not ask for one). Reply says it was proposed and is not active.
- raw: `raw/deleg-sched.redacted.json`.
Run 4 (neg, no operation). 2026-11-15T23:32:50Z to 23:32:55Z (4.1 s). Input: "What is the capital of Portugal? Just answer, no need to set anything up."
- Reply "Lisbon.". Zero `mcpToolCall` events. `stub-neg.db` was never created (the server stored nothing; the file is only created on a call). **Correct no-call.** Caveat: the prompt itself says "no need to set anything up", so this is a weak negative. A neutral chat message without that hint was not tested: not verified.
- raw: `raw/deleg-neg.redacted.json`.

## Findings
- Delegation through host tools works on 0.169.0: a natural-language message made the model pick `create_task` or `propose_schedule`, fill the arguments, and receive a persisted id. Verified by SQLite reads.
- With `approvalPolicy=never`, MCP calls are denied unless the server is configured `default_tools_approval_mode="approve"`. A Runtime that wants unattended delegation must set this per trusted server (or answer the approval request). Not tested with other policies (`on-request`, `auto_review`).
- The MCP server runs outside the sandbox (it wrote the DB although the thread sandbox was read-only). It is a trusted extension: write bounds on the thread do not constrain it. Inference from the observed write; the process-level confinement of MCP servers was not examined.
- The MCP config rides in `thread_start config`, so the Runtime can scope tools per thread. Config-level `mcp_servers` in the shared home was not used.
- Natural-language ambiguity (2 calls vs 1 for sched, model-added timezone) means the Runtime must validate arguments server-side. Repeat runs / determinism: one run per case, not verified.
- Not covered: dynamic tools, structured output, slash commands (not needed), concurrent calls, tool error handling beyond the denial in run 1.
- The ancestor-AGENTS.md carry-over did not affect these runs (temp cwd, `project_doc_max_bytes=0`).

## Cleanup
`systemctl --user list-units 'pixie-spike-*' --all` empty (units used `--collect`). No `/tmp/pixie-spike-*` dirs remain. Stub DB files under `stub/` are git-ignored and contain only fake data. Nothing committed. Task 1.8 not started.
