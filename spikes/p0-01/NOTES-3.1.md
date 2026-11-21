# Task 3.1 notes (spike P0-01): non-blocking approvals - status: DONE (pending approval and working interrupt coexist)

Date: 2026-11-21. Throwaway; not application code. Script `run_approval_nb_probe.py`, unit wrapper `run_approval_nb_unit.sh`. Same stack as 1.4: `openai-codex==0.169.0` with bundled `openai-codex-cli-bin==0.169.0`, CPython 3.14.4, `uv.lock`. Dedicated CODEX_HOME (`spikes/p0-01/.codex-home`, already logged in, auth files not read, no new login). Every run: transient unit `pixie-spike-nb-<mode>` (`systemd-run --user --wait --collect`, StandardInput=null, RuntimeMaxSec=290, in-script alarm 200 s, PATH = nvm node dir + system dirs). Thread: `approvalPolicy=on-request`, `approvalsReviewer=user`, `sandbox=read-only`, temp cwd. Raw output (redacted by the script) in `raw/nb-<mode>.redacted.json`. Each run used one real tiny turn plus (where noted) one follow-up turn.

## Runs (UTC, 2026-11-21)
| Mode | Unit | Start - end | Question |
|---|---|---|---|
| direct-interrupt | pixie-spike-nb-direct-interrupt | 01:49:03 - 01:49:18 | b, e |
| direct-accept | pixie-spike-nb-direct-accept | 01:57:07 - 01:57:40 | b, c |
| sdk-ctor | pixie-spike-nb-sdk-ctor | 01:57:40 - 01:57:51 | d |
| sdk-handoff | pixie-spike-nb-sdk-handoff | 01:57:51 - 01:58:14 | a |
| sdk-async | pixie-spike-nb-sdk-async | 02:09:51 - 02:10:14 | a |
| sdk-subclass | pixie-spike-nb-sdk-subclass | 02:10:14 - 02:10:41 | a, d, e |
All six: outcome `completed`, unit exit 0.

## (a) Answering an approval without blocking the SDK reader thread
Source read (`client.py`, not only run): `_reader_loop` calls `_handle_server_request` -> `approval_handler(method, params)` and writes `{"id", "result": <return value>}` as soon as it returns. The handler's return value IS the reply, so the SDK has no "answer later" API. No public way to defer.
- `sdk-handoff` (handler submits the decision to a worker thread and waits for it): the handler still runs on `Thread-2 (_reader_loop)`. Request at 6.6 s, `turn.interrupt()` sent at 9.6 s did not return within 10 s; released at 19.6 s, then the interrupt returned and the turn ended `interrupted` (19.6 s). A thread hand-off does not help, because the reader waits for the return value.
- `sdk-async` (`AsyncCodex`): `AsyncCodex(config)` has no handler parameter and builds `CodexClient(config)` with no handler, which means the auto-accept default. I installed a blocking handler through the private `_client._sync._approval_handler`. The handler ran on `Thread-2 (_reader_loop)`. `await turn.interrupt()` (sent at 10.6 s) did not return within 10 s (`asyncio.wait_for`); released at 20.6 s, turn `interrupted`. The async client only wraps the sync one with `asyncio.to_thread`; it has the same reader thread. Not an answer.
- `sdk-subclass` (workaround): subclass of `CodexClient` that overrides `_reader_loop` so server requests are answered by a worker pool (`approval-answer_0`). It uses private members (`_read_message`, `_write_message`, `_router`, `_coerce_notification`, `_handle_server_request`). The approval stayed pending; `turn.interrupt()` sent 3.0 s after the request returned in 0.013 s, the turn ended `interrupted` immediately (19.9 s run time; the handler was released only after the turn had ended), thread usable (follow-up `OK`, `completed`). This works but depends on private SDK internals that can change between versions (pinned by `uv.lock`).
Answer: no public SDK mechanism. Only a private-internals subclass works.

## (b) Direct app-server JSON-RPC client, Runtime owns the read loop
Own asyncio client over `codex app-server --listen stdio://` (initialize + `initialized`, `thread/start`, `turn/start`, `turn/interrupt`, `thread/read`). The read loop never calls application code inline: server requests go to a queue and are answered later by Runtime code with `{"id": <rpc id>, "result": {"decision": ...}}`.
- `direct-interrupt`: request `item/commandExecution/requestApproval` at 6.9 s (integer rpc id). The approval was left unanswered. At 9.99 s `thread/read` (another request) answered in 0.051 s. `turn/interrupt` sent at 9.99 s: response in 0.009 s, `turn/completed` status `interrupted` 0.009 s later, and a `serverRequest/resolved` notification arrived at the same instant (the pending approval was cancelled by the interrupt). A late reply to the stale rpc id (`decline`) was sent without any visible error. A new turn on the same thread then completed. File not created.
- `direct-accept`: while the approval was pending for 24 s, five `thread/read` requests answered in 0.002 to 0.003 s each. So the reader is not stalled and the approval wait can be unbounded in the app (not tested beyond 24 s here; 1.4 run C showed 240 s of backend patience with a held handler).
Answer: yes, the stall is avoided; the wait can be held and interrupt works.

## (c) Accept path (`direct-accept`)
Prompt asked for one `sh -c` command that writes `approval-probe.txt` in the (read-only) cwd and a second file in a different temp dir outside the cwd, requesting approval. Request at 6.2 s; held for 25 s; replied `{"decision": "accept"}` at 31.3 s. Result: `serverRequest/resolved` at 31.28 s, `item/completed` `commandExecution` status `completed`, exit code 0, output `done`, turn `completed`. BOTH files exist (cwd content `hello`; the outside file exists). So an accepted request runs the command and it runs outside the read-only sandbox, with write access beyond the cwd. Network egress after accept was not tested (not verified). `acceptWithExecpolicyAmendment` and `acceptForSession`-style decisions were not tested. Params: `availableDecisions` carried `accept`, an object `{"acceptWithExecpolicyAmendment": {"execpolicy_amendment": [argv...]}}` and `cancel`; no `decline` is listed, but 1.4 showed `decline` is accepted.
Implication: `accept` is a full sandbox escape for that command; the Runtime must treat the accept decision as granting unconfined execution of exactly the shown command and must show the command to the human before answering.

## (d) `CodexClient(config, approval_handler=...)` without private attributes (`sdk-ctor`)
`client = CodexClient(CodexConfig(), approval_handler=handler); client.start(); client.initialize(); client.thread_start({...}); Thread(client, id).turn(...)`. No private attribute touched. The handler was called (request at 7.1 s, decline), item `declined`, turn `completed`, follow-up `OK`. `thread_start` here still takes raw params (`approvalPolicy`, `approvalsReviewer`, `sandbox`, `cwd`) because the typed `Thread` helpers choose `ApprovalMode` themselves. Public constructor argument works; the handler still runs on the reader thread (see a).
Note: `CodexClient`, `Thread(client, id)` and `client.thread_start` are public by name (no underscore) but `Thread` is documented as created by `Codex`; `from openai_codex.client import CodexClient` is not in the package's top-level exports (not verified whether it is intended to be public).

## (e) Interrupt while an approval is pending, 10 s bound
- Direct client: met. 0.009 s (`direct-interrupt`), approval still unanswered at the time.
- SDK, handler on reader thread (`sdk-handoff`, `sdk-async`): not met (no return in 10 s).
- SDK + reader-loop subclass (`sdk-subclass`): met, 0.013 s.
- Pending approval and a working interrupt therefore coexist, if the application owns the read loop (or replaces the SDK reader loop). They do not coexist with the SDK's own reader loop and a waiting handler.

## Not verified
Approval waits over 240 s; file-change approvals; MCP/tool approvals; accept with network access; `acceptWithExecpolicyAmendment`; interrupt during a running (not pending) command; behavior across app-server restart with a pending approval; the interrupt effect when the approval was raised for a different item than the running one (single item only).

## Cleanup
`systemctl --user list-units 'pixie-spike-*' --all` empty (all `--collect`). Temp dirs `/tmp/pixie-spike-cwd-*` and `/tmp/pixie-spike-out-*` removed by the script. No other unit touched. Raw files grepped for `eyJ`, `sk-`, e-mail patterns and the home path: no matches.
