# Task 1.2 notes (spike P0-01) - status: DONE

Date: 2026-11-15. Throwaway; not application code. Interface: Python SDK `openai-codex==0.169.0` (bundled `openai-codex-cli-bin==0.169.0`), CPython 3.14.4, pinned via `uv.lock`. Dedicated CODEX_HOME from NOTES-1.1 (no new login; auth files not read).

## Run
- Script: `run_sdk_stream_interrupt.py`. Unit `pixie-spike-sdk-4` (`systemd-run --user --wait --collect --pipe`, RuntimeMaxSec=290, in-script alarm 240 s, PATH = node dir + /usr/local/bin:/usr/bin:/bin, absolute venv python, no terminal).
- Start 2026-11-15T21:40:21.539Z, end 21:40:38.023Z (16.48 s). Unit exit 0/SUCCESS.
- Raw: `raw/sdk-run-4.redacted.json`, `raw/sdk-run-4.stderr.txt` (systemd messages only). Response text truncated to 120 chars, e-mail/secret patterns scrubbed. Thread and turn ids were not saved (only presence and length).
- Sessions ran with cwd = a temp dir, `Sandbox.read_only`, `ApprovalMode.deny_all`, and prompts forbidding tools.

## Observations (mechanism, input, result)
1. Start execution: `Codex()` context manager starts the bundled app-server; `codex.thread_start(...)` then `thread.turn(prompt, ...)` returns a `TurnHandle` (non-blocking); `thread.run(prompt)` blocks and returns `TurnResult`. Input: "Reply with exactly the word PONG. Do not run any commands or use any tools." Result: turn started immediately, completed.
2. Streaming: `TurnHandle.stream()` yields typed `Notification` objects (method + payload) and ends after `turn/completed`. Observed 10 events in 2.7 s: `turn/started`, `item/started` x2, `item/completed` x2, `item/agentMessage/delta` x2 (concatenated "PONG"), `turn/moderationMetadata`, `thread/tokenUsage/updated`, `turn/completed`. Events arrive as they happen (first delta at 2.63 s).
3. Thread references: `thread.id` is a 36-character string available immediately after `thread_start`; `turn.id` and `turn.thread_id` available after `thread.turn`. `thread.read(include_turns=True)` returned 1 turn with status `completed`.
4. Result retrieval: `thread.run(...)` returns `TurnResult` (fields: id, status, error, started_at, completed_at, duration_ms, final_response, items, usage). Second turn on the same thread: "What single word did I ask you to reply with earlier?..." -> "PONG" (status completed, usage present, 2 items), so thread context is retained. `thread.read(include_turns=True)` also gives per-turn status.
5. Interrupt: input "Write a very long numbered list from 1 to 400 ..." (no tools). After the 5th delta (7 deltas seen, 2.55 s into the turn) called `TurnHandle.interrupt()`: call returned in 0.006 s with `TurnInterruptResponse`; `turn/completed` with status `interrupted` arrived 0.006 s after the request (3 more delta events were already in flight). Time to stop 0.006 s, well under 10 s. Final state: `interrupted`.
6. Thread reference after interrupt: usable. Same client: next turn "Reply with exactly the word OK..." -> "OK", completed; `thread.read` lists turn statuses [interrupted, completed]. New client (fresh `Codex()` app-server process) `thread_resume(<id>)` on both the interrupted thread and the earlier completed thread, then a turn on each: "OK" and "PONG" (the latter recalls the earlier context), both completed.

## Limitations and untested cases
- Interrupt was tested only on a text-generation turn. Interrupt during a tool/command execution, during an approval wait, or on a long-reasoning phase: not verified (not run; tools were forbidden by prompt to keep the run bounded and safe). 10 s bound is therefore verified for model streaming only.
- Process-level kill/crash recovery of the thread (app-server killed mid-turn) not verified; resume was tested only after a clean client close.
- `thread/tokenUsage` and `turn/moderationMetadata` events exist and will need handling in the event mapper (design task 5.2); other event kinds (tool, approval, error) not observed here.
- No SDK limitation found for the items in 1.2, so app-server JSON-RPC and `codex exec` were not tried and nothing is rejected.
- Python 3.12/3.13 runs: not verified (unchanged from 1.1).

## Cleanup
`systemctl --user list-units 'pixie-spike-*' --all` is empty after the run (--collect). No other unit touched.
