# Task 1.4 notes (spike P0-01) - status: DONE (approvals verified; auth/network/usage simulated; real expiry and real usage limit not verified)

Date: 2026-11-15. Throwaway; not application code. Interface: Python SDK `openai-codex==0.169.0` (bundled `openai-codex-cli-bin==0.169.0`), CPython 3.14.4, pinned via `uv.lock`. Dedicated CODEX_HOME from NOTES-1.1; auth files never read; the working login was not modified. Every run: transient unit `pixie-spike-*` (`systemd-run --user --wait --collect`, StandardInput=null, stdout/stderr to files, RuntimeMaxSec <= 290, minimal PATH = nvm node dir + /usr/local/bin:/usr/bin:/bin, absolute venv python, in-script alarm). Raw outputs in `raw/` (redacted by the scripts: e-mails, token patterns, UUIDs).

## 1. Approvals
Scripts: `run_approval_probe.py`. The high-level SDK API only offers `ApprovalMode.deny_all` (policy `never`: no approval is ever requested) and `ApprovalMode.auto_review` (policy `on-request` with an automatic reviewer, not the application). To reach application code I used the low-level path: `codex._client.thread_start({"approvalPolicy": "on-request", "approvalsReviewer": "user", "sandbox": "read-only", "cwd": <temp dir>})`, wrapped with `Thread(client, id)`, and replaced `CodexClient._approval_handler` (private attribute; the public `Codex()` constructor has no handler parameter, `CodexClient(config, approval_handler=...)` does).
Input: "Use a shell command to create a file named approval-probe.txt in the current directory containing the word hello. If the sandbox blocks the write, request approval to run it outside the sandbox. Do not do anything else."

How it surfaces:
- As a server-to-client JSON-RPC request `item/commandExecution/requestApproval` (file edits: `item/fileChange/requestApproval` per source, not triggered). It is NOT in `TurnHandle.stream()`; the stream only shows `item/started` (commandExecution, in_progress) and later `item/completed` with status `declined`. The request is delivered to the approval handler on the SDK reader thread (`Thread-2 (_reader_loop)`).
- Param keys: availableDecisions, command, commandActions, cwd, environmentId, itemId, kind, proposedExecpolicyAmendment, reason, startedAtMs, threadId, turnId. Observed command: `/usr/bin/zsh -lc "printf 'hello\n' > approval-probe.txt"` with a model-written `reason`. availableDecisions seen: `accept`, `acceptWithExecpolicyAmendment`, `cancel` (no plain `decline` listed; the handler returned `{"decision": "decline"}` and the backend accepted it: item status `declined`).
- Default handler (source `client.py::_default_approval_handler`, read, not run): auto-ACCEPTS command and file-change approvals. With `approvalsReviewer=user` and no custom handler, anything the model asks for would be approved. The Runtime must always install its own handler or use `deny_all`.

Runs (all outcome `completed`, unit exit 0):
| Run | Unit | Start - end (UTC) | Handler | Result |
|---|---|---|---|---|
| A decline | pixie-spike-appr-1 | 22:05:20 - 22:05:32 | answers `decline` at once | request at ~7.9 s; item `declined`; agent explained; turn `completed` after 8.85 s; file not created; same thread then answered "OK" |
| B wait + interrupt | pixie-spike-appr-2 | 22:06:14 - 22:07:07 | blocks (no user) | handler blocked 43.5 s. At 30 s I called `turn.interrupt()`: it did NOT return in 20 s (reader thread was held by the blocked handler). I then released the handler (decline); interrupt returned 0.002 s later; turn ended `interrupted` at 50.0 s. Thread usable after: follow-up "OK" `completed`. File not created |
| C wait 240 s | pixie-spike-appr-3 | 22:07:58 - 22:12:12 | blocks 240 s, then decline | worker waited the whole 240.0 s; no backend-side timeout, deny or failure in that window; after my decline the turn completed at 250.9 s (`completed`) |
Conclusions:
- With no user connected the worker WAITS (does not deny or fail). Verified for 240 s (run C); longer than 240 s: not verified. Time to resolution is entirely controlled by the application handler.
- A handler that blocks stalls the SDK reader thread: no other response or notification is processed on that client, including the reply to `interrupt`. The Runtime must answer approvals non-blockingly (immediate deny, or a handler that returns after its own timeout well under the 10 s interrupt bound), or use `deny_all`. This is relevant to design for approvals (D2) and to interrupt-during-approval, which 1.2 left unverified; it is now measured: interrupt is blocked while a handler is pending.
- Approving (`accept`) was not run (no need; not run to avoid writes).

## 2. Failure signals
Script: `run_failure_probe.py`. Pattern: A) normal client creates a thread and a turn ("Remember the secret word LANTERN..." -> "OK"); B) a second client with a broken endpoint runs a turn; C) a normal client resumes the thread and asks for the word.

### 2a. Expired/missing auth
Not re-run. Reuse of 1.3 (empty-home simulation, real login untouched): `codex login status` exit 1 "Not logged in"; SDK run fails with `RuntimeError` "unexpected status 401 Unauthorized: Missing bearer or basic authentication in header" after ~15.7 s (NOTES-1.3, raw/login-probe-1). Real token expiry: not verified (cannot be reproduced without damaging the login). Thread state under auth failure: not tested in 1.3 (new empty home has no threads); expected to behave like 2b, but that is an assumption: not verified.

### 2b. Network failure (simulated)
Two simulations, each against the dedicated home with the real login but pointing the app-server at nothing reachable:
- `netfail-base`, unit pixie-spike-fail-netfail-base, 22:14:29 - 22:14:49Z: config override `chatgpt_base_url="http://127.0.0.1:1/backend-api"` (closed loopback port, connection refused).
- `netfail-proxy`, unit pixie-spike-fail-netfail-proxy, 22:17:04 - 22:17:24Z: HTTP(S)/ALL_PROXY env for the app-server process set to `http://127.0.0.1:1`. This also produced the failure, so proxy env is honored.
Observed (identical in both): client start and `thread_resume` succeed (no network needed). `turn/started`, then a series of `error` notifications with `will_retry=true`, `message="Reconnecting... N/5"`, `codex_error_info = ResponseStreamDisconnected(http_status_code=None)`, `additional_details="workspace routing discovery failed"`; the retry counter runs 2/5 to 5/5, then restarts 1/5 to 5/5 (two cycles), then a final `error` with `will_retry=false`, `message="workspace routing discovery failed"`, `codex_error_info=other`, and `turn/completed` with status `failed` and the same TurnError. Total about 12.5 s from turn start. Note: the failure message names the pre-request discovery step, so the exact message for a failure on the `/responses` call itself was not observed (not verified); the signal class (`will_retry` errors, then turn `failed`) is what was seen.
Thread state: preserved. A new client resumed the thread; turn statuses were [completed, failed]; the follow-up turn completed and recalled "LANTERN" (so prior context survived, and the failed turn left no corrupting state).

### 2c. Usage limit (simulated)
- First attempt `usage` (22:14:08 - 22:14:29Z, `chatgpt_base_url` pointed at a loopback fake returning 429): not a valid simulation. The fake received discovery calls (`wham/accounts/check`, plugin listing), the Codex client reported the same "workspace routing discovery failed" failure as 2b, and the 429 body was never evaluated on the responses path. Discarded as a usage-limit result (kept as raw/failure-usage.redacted.json).
- `usage-provider`, unit pixie-spike-fail-usage-provider, 22:18:37 - 22:18:46Z: new thread on a custom `model_provider` whose `base_url` is a loopback fake that answers HTTP 429 with an error body of type `usage_limit_reached` (plan/reset fields are fake). A dummy placeholder key was used for that provider; the real ChatGPT login was not sent to it (fake server logged only method and path: one `POST /v1/responses`). (An earlier run of the same mode on a resumed thread ignored the provider override and ran one real tiny turn; no other real quota use.)
- Observed: `error` notification with `will_retry=false`, `codex_error_info = usageLimitExceeded` (structured, distinct from `other`), message "You've hit your usage limit ... try again later", then `turn/completed` status `failed` with the same TurnError, 0.6 s after turn start, no retries. The message includes upgrade/purchase URLs; the reset time was not exposed as a typed field in what I printed (not verified whether a field exists).
- Thread state: the failed thread stayed readable in the same client (`thread.read` shows one turn, status `failed`). Resuming it from a normal client is not verified: it failed with JSON-RPC -32600 "This chat uses model provider ... which is no longer configured" (artifact of the fake provider). Survival across a usage-limit failure is therefore only shown for the same live client; for networks, the cross-client resume was verified (2b).
- Real usage-limit behaviour: not verified (real quota not exhausted, by rule). What is simulated is the HTTP 429 mapping in the Codex client, which maps to a typed `usageLimitExceeded`.

## 3. Mapping hints for the event mapper (design 5.2)
- Approval: server request (not a notification); needs an explicit handler contract and non-blocking answer.
- Retryable transport trouble: `error` notification with `will_retry=true`; terminal: `will_retry=false` plus `turn/completed` status `failed`. Classify using `codex_error_info`: `usageLimitExceeded`, `responseStreamDisconnected`, `other` (observed). Auth failure on a fresh turn surfaced as an exception (`RuntimeError`, 401) in 1.1/1.3, not as a typed turn error (as far as observed).
- `serverRequest/resolved` notification: not observed.

## Limitations / not verified
- Real token expiry; real usage limit; thread state after an auth failure; approving a request; file-change approvals; approvals during tool use other than a shell command; handler wait beyond 240 s; Python 3.12/3.13.
- Uses a private attribute (`_client._approval_handler`) and `_client.thread_start` with raw params because the public API has no approval handler; the adapter will need `CodexClient` directly or app-server JSON-RPC (not rejected yet; decision belongs to later spike items).

## Cleanup
`systemctl --user list-units 'pixie-spike-*' --all` is empty (all used --collect). Temp dirs `/tmp/pixie-spike-cwd-*` removed. No other unit touched. Raw files are redacted by the scripts and checked with grep for `eyJ`, `@`, `sk-` (no matches).
