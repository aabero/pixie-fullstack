# Spike P0-01 report: Codex integration

Date written: 2026-11-15. Spec: `pixie-phase0-runtime`. Task: 1.8.

This report only summarizes what the task 1.1 to 1.7 notes recorded. No new experiment was run for it. Where the notes hold no evidence, the item says "not verified" and gives the reason. Nothing is filled from assumptions or documentation claims, and documentation-only facts are labelled as such.

Evidence files (all under `spikes/p0-01/`):
[NOTES-1.1](../spikes/p0-01/NOTES-1.1.md), [NOTES-1.2](../spikes/p0-01/NOTES-1.2.md), [NOTES-1.3](../spikes/p0-01/NOTES-1.3.md), [NOTES-1.4](../spikes/p0-01/NOTES-1.4.md), [NOTES-1.5](../spikes/p0-01/NOTES-1.5.md), [NOTES-1.6](../spikes/p0-01/NOTES-1.6.md), [NOTES-1.7](../spikes/p0-01/NOTES-1.7.md). Raw outputs (redacted) are in [`spikes/p0-01/raw/`](../spikes/p0-01/raw/). Nothing in this report contains credentials, account identifiers or e-mail addresses. Thread and turn identifiers were not saved.

Common run setup (from the notes): every bounded run was a transient user unit named `pixie-spike-*` started with `systemd-run --user --wait --collect`, with `StandardInput=null`, `RuntimeMaxSec` at most 290, a minimal `PATH` (node directory plus `/usr/local/bin:/usr/bin:/bin`), the absolute venv Python, and the dedicated `CODEX_HOME` at `spikes/p0-01/.codex-home` (never `~/.codex`). All units were cleaned up (`--collect`); `systemctl --user list-units 'pixie-spike-*' --all` was empty after each task.

---

## 1. Bounded task run (Requirement 1.1)

- Mechanism: Python SDK `openai-codex` 0.169.0, run from transient unit `pixie-spike-sdk-3` (service-like environment: no terminal, minimal PATH, dedicated Codex_Home).
- Input: `Reply with exactly the word PONG. Do not run any commands or use any tools.`
- Outcome: `completed`. Final result: `PONG`. Unit exit 0 (success).
- Run: `systemd-run --user --unit=pixie-spike-sdk-3 --wait --collect --pipe -p RuntimeMaxSec=290 ...` (full form in NOTES-1.1). Start 2026-11-15T21:29:42.970731Z, end 2026-11-15T21:29:47.537404Z (4.57 s, limit 300 s).
- Earlier attempt, unit `pixie-spike-sdk-2`, 2026-11-15T21:23:22Z to 21:23:38Z (16.06 s): outcome `error`, HTTP 401 because the dedicated Codex_Home had no login yet. The Operator then logged in with `codex login --device-auth`, and sdk-3 is the successful run. A first run (`sdk-run-0`) failed only because the Codex_Home directory did not exist (setup error).
- The `--pipe` flag forwarded the terminal's stdin in sdk-3. The "no terminal" condition is shown by the later runs in section 9 (stdin, stdout and stderr not a tty).
- Evidence: [NOTES-1.1](../spikes/p0-01/NOTES-1.1.md), [raw/sdk-run-3.redacted.json](../spikes/p0-01/raw/sdk-run-3.redacted.json), [raw/sdk-run-1.redacted.json](../spikes/p0-01/raw/sdk-run-1.redacted.json), [raw/sdk-run-0-missing-codex-home.redacted.json](../spikes/p0-01/raw/sdk-run-0-missing-codex-home.redacted.json).

Status: **verified**. One executed run completed within 300 s from a user-unit environment with no terminal.

## 2. Versions and pinning (Requirements 1.2, 1.10)

- Tools found: uv 0.13.8; codex-cli 0.167.2 (nvm node v26.13.0; not used by the SDK path).
- SDK: `openai-codex==0.169.0`, which pulls `openai-codex-cli-bin==0.169.0` (bundled Codex binary) and pydantic 2.14.3. The bundled app-server and binary version is 0.169.0.
- Pinning method: `spikes/p0-01/uv.lock` (added with `uv add openai-codex`). The login made with CLI 0.167.2 was accepted by the bundled 0.169.0 binary. This is inferred from the successful run; the credential format was not inspected.
- Python: both packages declare `Requires-Python >=3.10`. Import-only check passed on CPython 3.12.16, 3.13.18 and 3.14.4.
- **Python 3.14.4 works**: the whole spike (every run in 1.1 to 1.7) ran on CPython 3.14.4 (`/usr/bin/python3.14`, the system interpreter that uv selected, pinned in `spikes/p0-01/.python-version`).
- Python 3.12 and 3.13: only imports were checked. A full SDK run on them was not done, so it is "not verified" (not run).
- Evidence: [NOTES-1.1](../spikes/p0-01/NOTES-1.1.md), `spikes/p0-01/uv.lock`.

Status: **verified** for the versions, the pinning method and 3.14.4. **Not verified** for full runs on 3.12 and 3.13 (not run).

## 3. Mechanisms and observed results (Requirement 1.3)

All from [NOTES-1.2](../spikes/p0-01/NOTES-1.2.md). Run: transient unit `pixie-spike-sdk-4`, script `run_sdk_stream_interrupt.py`, 2026-11-15T21:40:21.539Z to 21:40:38.023Z (16.48 s), unit exit 0. Raw: [raw/sdk-run-4.redacted.json](../spikes/p0-01/raw/sdk-run-4.redacted.json). Threads used a temp cwd, `Sandbox.read_only`, `ApprovalMode.deny_all`, and prompts that forbid tools.

| Item | Mechanism | Input | Observed result |
| --- | --- | --- | --- |
| Start execution | `Codex()` starts the bundled app-server; `codex.thread_start(...)`; `thread.turn(prompt)` returns a non-blocking `TurnHandle`; `thread.run(prompt)` blocks and returns `TurnResult` | `Reply with exactly the word PONG. Do not run any commands or use any tools.` | Turn started at once and completed |
| Stream events | `TurnHandle.stream()` yields typed `Notification` objects and ends after `turn/completed` | same | 10 events in 2.7 s: `turn/started`, `item/started` x2, `item/completed` x2, `item/agentMessage/delta` x2, `turn/moderationMetadata`, `thread/tokenUsage/updated`, `turn/completed`. First delta at 2.63 s |
| Retain thread references | `thread.id` (36-character string) available right after `thread_start`; `turn.id` and `turn.thread_id` after `thread.turn` | n/a | `thread.read(include_turns=True)` returned 1 turn, status `completed` |
| Retrieve results | `TurnResult` (id, status, error, started_at, completed_at, duration_ms, final_response, items, usage) | second turn on the same thread: `What single word did I ask you to reply with earlier?...` | Answered `PONG`, status `completed`, usage present, 2 items. Thread context is retained |
| Interrupt | `TurnHandle.interrupt()` | `Write a very long numbered list from 1 to 400 ...` (no tools), interrupted after the 5th delta (2.55 s into the turn) | See section 4 |
| Delegate from natural language | MCP host tool configured on `thread_start` | see section 13 | Works |

Not verified (from the notes): events for tools, approvals and errors were not observed in this run (they appear in sections 5 and 6). Thread and turn identifiers were not saved, only their presence and length.

Status: **verified** for start, stream, thread references, results. Interrupt is in section 4 and delegation in section 13.

## 4. Interruption (Requirement 1.4)

- Mechanism: `TurnHandle.interrupt()` on a text-generation turn (run `pixie-spike-sdk-4`, timestamps in section 3).
- Time to stop: the call returned in 0.006 s with `TurnInterruptResponse`. `turn/completed` with status `interrupted` arrived 0.006 s after the request (3 more delta events were already in flight). The limit is 10 s.
- Final state: `interrupted`.
- Thread reference after interrupt: usable.
  - Same client: next turn `Reply with exactly the word OK...` returned `OK`, status `completed`. `thread.read` lists statuses [interrupted, completed].
  - New client (fresh app-server process): `thread_resume(<id>)` on the interrupted thread and on the earlier completed thread, then one turn each, gave `OK` and `PONG` (the second recalled earlier context). Both completed.
- Interrupt while an approval is pending (from [NOTES-1.4](../spikes/p0-01/NOTES-1.4.md), run B, unit `pixie-spike-appr-2`, 2026-11-15T22:06:14Z to 22:07:07Z): with an approval handler that blocked, `turn.interrupt()` did not return within 20 s. After the handler was released, the interrupt returned 0.002 s later and the turn ended `interrupted` at 50.0 s. The thread was usable afterwards (follow-up `OK`, `completed`). The cause is that a blocking handler holds the SDK reader thread, so no other message is processed.
- Not verified: interrupt during a tool or command execution, interrupt during long reasoning, and app-server crash or kill mid-turn with later recovery (none was run; tools were forbidden by prompt to keep runs bounded). Resume was tested only after a clean client close.

Status: **partly verified**. The 10 s bound is verified for model streaming only. With a blocked approval handler the interrupt is not met until the handler returns.

## 5. Approval surfacing and unattended behavior (Requirement 1.5)

Evidence: [NOTES-1.4](../spikes/p0-01/NOTES-1.4.md), raw [approval-decline](../spikes/p0-01/raw/approval-decline.redacted.json), [approval-wait](../spikes/p0-01/raw/approval-wait.redacted.json), [approval-wait-long](../spikes/p0-01/raw/approval-wait-long.redacted.json).

- Public SDK surface: the high-level API offers only `ApprovalMode.deny_all` (policy `never`, no approval is ever requested) and `ApprovalMode.auto_review` (policy `on-request` with an automatic reviewer, not the application). The public `Codex()` constructor has no approval handler parameter. `CodexClient(config, approval_handler=...)` does.
- **The SDK's default handler auto-accepts** command and file-change approvals (source `client.py::_default_approval_handler`, read, not run). With `approvalsReviewer=user` and no custom handler, anything the model asks for would be approved. The Runtime must install its own handler or use `deny_all`.
- Path used to reach the application: low-level. `codex._client.thread_start({"approvalPolicy": "on-request", "approvalsReviewer": "user", "sandbox": "read-only", "cwd": <temp dir>})`, wrapped with `Thread(client, id)`, and the private attribute `CodexClient._approval_handler` replaced.
- Input: `Use a shell command to create a file named approval-probe.txt in the current directory containing the word hello. If the sandbox blocks the write, request approval to run it outside the sandbox. Do not do anything else.`
- How it surfaces: as a server-to-client JSON-RPC request `item/commandExecution/requestApproval` (file changes: `item/fileChange/requestApproval` per source, not triggered). It is not in `TurnHandle.stream()`; the stream shows only `item/started` and later `item/completed` with status `declined`. The request reaches the handler on the SDK reader thread. Param keys: availableDecisions, command, commandActions, cwd, environmentId, itemId, kind, proposedExecpolicyAmendment, reason, startedAtMs, threadId, turnId. Decisions offered: `accept`, `acceptWithExecpolicyAmendment`, `cancel`. A `decline` reply was accepted by the backend.
- Unattended behavior (worker waits):

| Run | Unit | Start to end (UTC, 2026-11-15) | Handler | Result |
| --- | --- | --- | --- | --- |
| A | `pixie-spike-appr-1` | 22:05:20 to 22:05:32 | answers `decline` at once | Request at about 7.9 s, item `declined`, turn `completed` at 8.85 s, file not created, thread answered `OK` afterwards |
| B | `pixie-spike-appr-2` | 22:06:14 to 22:07:07 | blocks (no user) | Handler blocked 43.5 s; interrupt hung (section 4); turn `interrupted` at 50.0 s |
| C | `pixie-spike-appr-3` | 22:07:58 to 22:12:12 | blocks 240 s, then declines | Worker waited the full 240.0 s with no timeout, deny or failure from the backend; after the decline the turn `completed` at 250.9 s |

- Conclusion: with no user connected the worker **waits** (it does not deny or fail). Verified for 240 s. A wait longer than 240 s was not run.
- A blocking handler stalls the reader thread: no other response or notification is processed on that client, including the reply to `interrupt`. The handler must answer without blocking (immediate deny, or a return after its own timeout well below 10 s).
- Not verified: the `accept` path, file-change approvals, approvals for tools other than a shell command, waits over 240 s, `serverRequest/resolved` (not observed).

Status: **verified** for surfacing and for unattended wait behavior (240 s). **Not verified** for the accept path, file-change approvals and longer waits.

## 6. Failure signals: expired auth, network, usage limit (Requirement 1.6)

Evidence: [NOTES-1.4](../spikes/p0-01/NOTES-1.4.md) section 2 and [NOTES-1.3](../spikes/p0-01/NOTES-1.3.md) section 3. Raw: [failure-netfail-base](../spikes/p0-01/raw/failure-netfail-base.redacted.json), [failure-netfail-proxy](../spikes/p0-01/raw/failure-netfail-proxy.redacted.json), [failure-usage](../spikes/p0-01/raw/failure-usage.redacted.json) (discarded as a usage result), [failure-usage-provider](../spikes/p0-01/raw/failure-usage-provider.redacted.json), [login-probe-1](../spikes/p0-01/raw/login-probe-1.redacted.json), [login-probe-2](../spikes/p0-01/raw/login-probe-2.redacted.json).

| Condition | How it was produced | Signal seen by the Runtime | Thread state |
| --- | --- | --- | --- |
| Missing auth (simulated; real expiry **not verified**) | Empty temp `CODEX_HOME` (login 2 run, 2026-11-15T21:44:54Z to 21:45:09Z). The real login was not touched | `codex login status` exits 1, prints "Not logged in". SDK run raises `RuntimeError` "unexpected status 401 Unauthorized: Missing bearer or basic authentication in header" after about 15.7 s. This is an exception, not a typed turn error | **Not verified** (the empty home has no threads) |
| Network failure (simulated) | Unit `pixie-spike-fail-netfail-base`, 22:14:29Z to 22:14:49Z: `chatgpt_base_url` pointed at a closed loopback port. Unit `pixie-spike-fail-netfail-proxy`, 22:17:04Z to 22:17:24Z: proxy env pointing at a closed loopback port | Client start and `thread_resume` succeed. `turn/started`, then `error` notifications with `will_retry=true`, `Reconnecting... N/5` (`ResponseStreamDisconnected`), two cycles; then `error` with `will_retry=false`, message "workspace routing discovery failed", `codex_error_info=other`, and `turn/completed` status `failed`. About 12.5 s from turn start | **Preserved**. A new client resumed the thread; statuses [completed, failed]; the follow-up turn recalled the earlier word |
| Usage limit (simulated) | Unit `pixie-spike-fail-usage-provider`, 22:18:37Z to 22:18:46Z: custom `model_provider` whose `base_url` is a loopback fake answering HTTP 429 with a `usage_limit_reached` body. A dummy key was used; the real login was not sent | `error` with `will_retry=false`, `codex_error_info=usageLimitExceeded` (typed), message "You've hit your usage limit ... try again later", then `turn/completed` status `failed`, 0.6 s after turn start, no retries | **Partly**: readable in the same live client (one turn, `failed`). Cross-client resume **not verified** (it failed with JSON-RPC -32600 because the fake provider was no longer configured; an artifact of the simulation) |

Other facts and limits:
- First usage attempt (22:14:08Z to 22:14:29Z, `chatgpt_base_url` fake returning 429) is not a valid simulation: the failure came from the discovery step, so the 429 body was never evaluated. It is kept only as a raw file.
- The network failure message names the pre-request discovery step. The exact message for a failure on the model request itself was not observed.
- Real token expiry or refresh failure: not verified, because it cannot be reproduced without damaging the working login. The signal for an expired token may differ from the missing-login 401.
- Real usage limit: not verified (real quota not exhausted, by rule). The reset time was not shown as a typed field in what was printed.
- Mapping hint for the event mapper: retryable trouble is an `error` with `will_retry=true`; terminal is `will_retry=false` plus `turn/completed` `failed`; classify with `codex_error_info` (`usageLimitExceeded`, `responseStreamDisconnected`, `other`).

Status: **partly verified**. Network failure and usage limit were simulated (said so above). Real auth expiry and real usage limit are not verified. Thread survival is verified for network failure and only same-client for usage limit; for auth it is not verified.

## 7. Limitations and interface chosen, with reasons earlier ones were rejected (Requirement 1.7)

Order tried (runbook): Python SDK, then app-server JSON-RPC, then `codex exec`.

- **Chosen: Python SDK `openai-codex` 0.169.0** (bundles the app-server, which it launches over JSON-RPC). It met the needs of 1.1 to 1.7 on Python 3.14.4, so the stop rule applied.
- **Earlier interfaces rejected:** none. The SDK is the first in the order.
- **Later interfaces (app-server JSON-RPC directly, `codex exec`):** not tried, and not rejected. Reason: the SDK did not fail any required behavior. They remain documented fallbacks.
- Limitations of the SDK as found (each is a limitation of the public API, not of the backend; a documented alternative inside the same interface was found and used, so no workaround outside a documented interface was needed):
  1. No public approval handler. The public API has only `deny_all` and `auto_review`, and the default handler auto-accepts. Reaching application code needed `CodexClient(config, approval_handler=...)` (public constructor of the client class) or, as done in the spike, `codex._client` with the private attribute `_approval_handler` replaced. A real adapter should use `CodexClient` and not private attributes. Whether `CodexClient` can be used without them was **not verified** (the spike used the private path).
  2. The public `Sandbox` enum takes no writable roots. Writable roots and permission profiles go through `config` on `thread_start`, or the low-level `thread_start` with raw params.
  3. A blocking approval handler stalls the reader thread, including the reply to `interrupt` (section 4).
  4. Invalid model or effort values are not rejected at `thread_start` (section 12).
- Since the low-level paths were required, the Operator may want to confirm whether a direct app-server JSON-RPC client (interface 2) would give a cleaner approval path. That was not evaluated, and this report does not recommend it.

Status: **verified** for the interface choice and the recorded limitations. App-server and `codex exec` are **not verified** (not tried, because not needed).

## 8. Authentication route, eligibility, usage limits, terms, billing (Requirement 1.8)

Source: [NOTES-1.3](../spikes/p0-01/NOTES-1.3.md) sections 1 and 4. The official pages were fetched 2026-11-15: [Authentication](https://learn.chatgpt.com/docs/auth), [Pricing](https://learn.chatgpt.com/docs/pricing), [Using Codex with your ChatGPT plan](https://help.openai.com/en/articles/11369540-using-codex-with-your-chatgpt-plan). None had a published date. The content below is paraphrased from those pages and is documentation, not observation, unless it says "observed".

- Route: ChatGPT subscription login, subscription-based. Observed: `codex login status` printed "Logged in using ChatGPT". No API key was involved (the unit environment held no variable matching OPENAI, CODEX_API or API_KEY). The Operator logged in with `codex login --device-auth`.
- Credential store: observed that `auth.json` is a file in the dedicated Codex_Home and the login worked from a service with no keyring session. The default value of `cli_auth_credentials_store` was not established ("not verified"). The Runtime should set it to `file` explicitly. The docs say `auth.json` is plaintext and should be treated like a password (mode 0600 was observed).
- Eligibility (docs): Codex is included across ChatGPT plans, including Free and Go, with usage limits varying by plan. Local CLI and SDK access is listed for Plus, Pro, Business, Enterprise/Edu and API key. **The Operator's plan was not checked** (not verified). Whether an admin setting restricts Codex local use on this account: not verified.
- Usage limits (docs): given as estimated local messages per 5-hour period per model for Plus and Standard Business, with weekly limits possible; they are estimates and not fixed limits. Local messages and cloud chats share one allowance, as do Codex and ChatGPT Work. Interactive use and the Runtime therefore share one pool (docs, not observed). When the limit is reached mid-turn that turn may continue within fair use; after that the user waits for reset or buys credits (Plus and Pro). Numbers for this account: not verified (dashboard not checked).
- Terms for automated use: the help article says the ChatGPT Terms of Use and Privacy Policy apply to data shared between Codex and ChatGPT. The auth page recommends API-key auth for programmatic CLI workflows such as CI/CD and describes Enterprise access tokens for trusted non-interactive automation. No page found explicitly permits or forbids an always-on personal service on a personal subscription login, and the Terms of Use text was not read. **Whether unattended personal-subscription use is permitted: not verified.**
- Billing (docs): subscription use draws on the plan allowance with no per-token charge unless credits are bought. API-key sign-in is billed per token on the OpenAI Platform account. The Runtime must not buy credits or switch to an API key (Requirement 2.14 and D3 say subscription only). Model retirements are announced, so a pinned model can disappear (example in the docs: a model retired for ChatGPT sign-in on 2026-10-14).

Status: **partly verified**. The route and the credential file are observed. Eligibility, limits and billing come from documentation only. The account plan, the account's limits and the terms for automated use are not verified.

## 9. Unattended login from a user service and expiry detection (Requirement 1.9)

Evidence: [NOTES-1.3](../spikes/p0-01/NOTES-1.3.md), raw [login-probe-2](../spikes/p0-01/raw/login-probe-2.redacted.json) and [login-probe-1](../spikes/p0-01/raw/login-probe-1.redacted.json).

- Run B, unit `pixie-spike-login-2` (`systemd-run --user --wait --collect -p RuntimeMaxSec=290 -p StandardInput=null`, stdout and stderr to files, no `--pipe`), 2026-11-15T21:45:20Z to 21:45:39Z (19.0 s), success. stdin, stdout and stderr were not a tty and `TERM` was unset. No nvm shell init. `~/.codex` was not used.
  - `codex login status` in the dedicated home: exit 0, "Logged in using ChatGPT".
  - Bounded SDK task `Reply with exactly the word PONG. Do not run any commands or use any tools.`: `completed`, `PONG`, 3.5 s.
- Run A (`pixie-spike-login-1`, with `--pipe`, 21:44:50Z to 21:45:10Z) is raw-only, because `--pipe` made stdin a tty.
- Result: the stored login is reused unattended from a user unit with no terminal and no browser. The login was created at about 21:29Z and was still reused by the last run on 2026-11-15 (delegation runs ending 23:32Z), about 2 hours.
- Not possible unattended: creating the first login. It needed the Operator's device-code step (NOTES-1.1).
- Detecting a missing login: `codex login status` exits 1 and prints "Not logged in" (no model call); a turn without login fails with a 401 `RuntimeError`. Suggested detection (not tested): run `codex login status` at start and after a 401, and treat exit 1 as `auth_required`.
- Detecting an **expired** login: **not verified**. Only the empty-home simulation was done. The docs say ChatGPT sessions refresh tokens during use; no refresh was observed. A real expired token may give a different signal.
- Not verified: behavior over days (token lifetime and refresh), and lingering or boot (see section 16).

Status: **partly verified**. Unattended reuse works for the observed window of a few hours. Expiry detection and long-term behavior are not verified.

## 10. Permission profiles and read confinement (Requirement 1.11)

Evidence: [NOTES-1.5](../spikes/p0-01/NOTES-1.5.md). Raw: [sandbox-ro](../spikes/p0-01/raw/sandbox-ro.redacted.json), [sandbox-ww](../spikes/p0-01/raw/sandbox-ww.redacted.json), [sandbox-prof](../spikes/p0-01/raw/sandbox-prof.redacted.json), [sandbox-profdeny](../spikes/p0-01/raw/sandbox-profdeny.redacted.json), [sandbox-profdeny2](../spikes/p0-01/raw/sandbox-profdeny2.redacted.json), [sandbox-nosb](../spikes/p0-01/raw/sandbox-nosb.redacted.json). All runs: transient `pixie-spike-sbx-<mode>` units, 2026-11-15 22:27Z to 22:48Z, `approvalPolicy=never`, low-level `thread_start` with `config`. Host: `/usr/bin/bwrap` present; unprivileged user namespaces enabled.

**Enforcement mechanism.** The backend launches each command through its Linux sandbox helper (bubblewrap). A blocked write is an ordinary command failure (exit 2 or 1) and the turn status stays `completed`. The Runtime must read the command item's exit code. Evidence counts only OS-level results (command output, exit code, file existence), not model refusals.

| Profile | How set | Observed |
| --- | --- | --- |
| `read-only` | `thread_start` `sandbox=read-only` | Unit `pixie-spike-sbx-ro`, 22:27:21 to 22:27:34. Prompt demanded `sh -c 'echo RO > ws/w.txt'` even if it fails: exit 2, "Read-only file system", file absent |
| `workspace-write` with writable roots | `sandbox=workspace-write` plus `config` `sandbox_workspace_write.{writable_roots, exclude_slash_tmp=true, exclude_tmpdir_env_var=true, network_access=false}` | Unit `pixie-spike-sbx-ww`, 22:27:39 to 22:28:00. Write in cwd exit 0, file exists. Write in the extra root exit 0, file exists. Write outside every root (22:27:52): exit 2, "Read-only file system", file absent |

- Canary requirement met: the out-of-bounds write was demanded and blocked, and the same write form succeeded inside the cwd and the extra root in the same thread, so the sandbox is not a no-op.
- Profiles that cannot be enforced: none found on this host.
- Without `exclude_slash_tmp` and `exclude_tmpdir_env_var`, `/tmp` stays writable (and `:workspace` keeps `/tmp` writable: a sibling `/tmp` write succeeded in `profdeny`, 22:45:23 to 22:45:59). Set both exclusions to true.
- **Read confinement.**
  - Legacy `read-only` and `workspace-write` do **not** confine reads. `cat outside/canary.txt` printed the marker under both (22:27:29 and 22:27:57).
  - A named permission profile (`default_permissions` plus `permissions.<id>.filesystem`, not combined with `sandbox`) does confine. Unit `pixie-spike-sbx-prof`, final run 22:44:40 to 22:45:23, profile `{":minimal": read, <codex bin dir>: read, allowed: read, ws: write, fakehome: deny}`: allowed file readable (exit 0); an unlisted directory gave "No such file or directory" (exit 1); a symlink in the workspace to the outside file and a script reading it also failed (exit 1); write in ws worked; write outside gave "Directory nonexistent" (exit 2).
  - The directory holding the Codex binary must be listed as readable. Without it every command failed with `bwrap: execvp ...: No such file or directory`. This first run's raw file was overwritten, so that detail comes from the task transcript, not a saved file. Other host paths a real task needs (shared libraries, `/etc`, interpreters): not verified; only `sh`, `cat` and `echo` were exercised.
- **Excluding a path from reads.** Profile `pixie_denyhome` = `extends ":workspace"` plus `{fakehome: deny}`, unit `pixie-spike-sbx-profdeny2`, 22:47:13 to 22:47:24, neutral script that does not mention the denied path: `Permission denied`, exit 1. A control read of an unrelated outside file succeeded. So an explicit `deny` is enforced by the OS. It was tested on a stand-in directory, **not on the real Codex_Home** (not touched, by rule).
- Models refuse to touch a path when the policy is visible to them. Those refusals are not enforcement evidence.
- **Sandbox cannot be applied.** Simulated with the unit property `RestrictNamespaces=user` (no system change). Unit `pixie-spike-sbx-nosb`, 22:48:38 to 22:48:51: both writes failed with `bwrap: No permissions to create a new namespace ...`, item status `failed`, exit 1, files absent. The backend fails closed per command, but the thread starts without error and the turn is `completed`. There is no start-up signal, so the Runtime needs a probe (Doctor `--probe` or a worker-start canary) to detect it (supports Requirement 8.13).
- Not verified: the real Codex_Home as a deny target, deny globs, deny versus allow ordering, file-change (`apply_patch`) enforcement (only shell commands were run), network enforcement beyond the echoed `networkAccess=false`, single-file writable paths, behavior when the model asks to escalate under `approvalPolicy=never`, real-host causes of sandbox failure (AppArmor, sysctl, missing bwrap; only the seccomp simulation was run), other kernels, and which profile is active (the `thread_start` response echoes only a legacy-shaped `sandbox` projection and no `activePermissionProfile` key was seen).

Status: **partly verified**. Write bounds (read-only, writable roots), read confinement by listing directories, and path exclusion on a stand-in are verified on this host. The items in the last bullet are not verified.

## 11. Instruction discovery and injection strategy (Requirement 1.12)

Evidence: [NOTES-1.6](../spikes/p0-01/NOTES-1.6.md) sections 1 and 2. Raw: [instr-disc](../spikes/p0-01/raw/instr-disc.redacted.json), [instr-mitig](../spikes/p0-01/raw/instr-mitig.redacted.json), [instr-strat](../spikes/p0-01/raw/instr-strat.redacted.json), [instr-strat-run2](../spikes/p0-01/raw/instr-strat-run2.redacted.json), [instr-home](../spikes/p0-01/raw/instr-home.redacted.json). Method: `thread_start` response field `instructionSources` plus canary markers `PXMARK-<NAME>-<4 hex>` in temp directories, confirmed by the agent's reply; prompts forbade tools.

**Discovery** (run `disc`, unit `pixie-spike-ins-disc`, 2026-11-15T23:19:25Z to 23:19:50Z):
- With a `.git` root, every `AGENTS.md` from the repo root down to the cwd is loaded, root first. A sibling directory is not loaded.
- With **no** `.git` root above, the walk still goes up through ancestor directories. A cwd outside any Git repository with a parent holding `AGENTS.md` loaded the parent file. A clean tree with no file above gave `instructionSources: []`. The walk was observed only up to the temp parent holding the canary.
- Only `AGENTS.md` is read. `CLAUDE.md` was not loaded (no fallback filenames configured).
- This repository has no root `AGENTS.md`, nor any in `~`, `~/dev`, `~/dev/pixie`, `/` or `/tmp`, so the "inherits the repository's own AGENTS.md" case was not run; the canary parent stood in for it.

**Mitigations** (run `mitig`, unit `pixie-spike-ins-mitig`, 23:20:13Z to 23:20:36Z, `thread_start.config`):
- `project_root_markers = []`: only the cwd's own file is loaded (no-git parent file skipped; repo root file skipped).
- `project_doc_max_bytes = 0`: no project documents at all, in all three cwds.

**Injection strategies** (runs `strat`, 23:21:15Z to 23:21:32Z and 23:22:16Z to 23:22:37Z, clean cwd):
- `explicit`: `developerInstructions` and `baseInstructions` on `thread_start`. Developer instructions: marker reported, and a behavioral check (`end every reply with token X`, prompt `Reply with the word PONG`) returned `PONG PXMARK-EXPLBEH-4cf1`. Base instructions: marker reported in run 2; in the final run the model declined to disclose hidden tokens (model behavior, not a delivery failure). No behavioral check for base instructions. `instructionSources` stays `[]` for explicit instructions.
- `inline` (prepended to the prompt): marker reported by the agent. Verified. (The first inline attempt was a flawed prompt of mine and was discarded.)
- `codex_home` (global `AGENTS.md` in Codex_Home): run `home`, unit `pixie-spike-ins-home`, 23:21:32Z to 23:21:47Z, with a credential-less throwaway home. Discovery shown (`instructionSources` listed `<CODEX_HOME>/AGENTS.md`); the turn failed with 401, so **the model seeing it is not verified**.
- Not verified: whether `project_doc_max_bytes=0` also blocks the global file, whether global and project files combine in order, and the walk-up beyond the temp parent.

Status: **partly verified**. Discovery rules, both mitigations, `explicit` and `inline` are verified. `codex_home` delivery and its interaction with the mitigations are not verified.

## 12. Model and reasoning effort (Requirement 1.13)

Evidence: [NOTES-1.6](../spikes/p0-01/NOTES-1.6.md) section 3, raw [instr-model](../spikes/p0-01/raw/instr-model.redacted.json). Run `model`, unit `pixie-spike-ins-model`, 2026-11-15T23:22:45Z to 23:22:59Z.

- Listing: `codex._client.model_list(include_hidden=True)` (SDK `Codex.models()`), one page. 10 models (8 visible, 2 hidden), a default model with default effort `low`. Entries carry `id/model`, `hidden`, `isDefault`, `defaultReasoningEffort`, `supportedReasoningEfforts`. Efforts offered: `low` to `ultra` (some models without `ultra`); `none` and `minimal` are offered by none. Names and per-model lists are account-specific, kept in the raw file only, and must not be hard-coded.
- How set: model through `thread_start` param `model`, turn param `model` (SDK `Thread.turn(model=)`) or config key `model`. Effort through turn param `effort` (SDK `Thread.turn(effort=)`) or config key `model_reasoning_effort` at `thread_start`. The SDK's `ReasoningEffort` accepts any string.
- Executed results: nothing set: `completed`, default model. Thread `model` = another listed model plus turn `effort=low`: `completed`. Config `model` plus `model_reasoning_effort=ultra`: accepted, response echoes `reasoningEffort: ultra`. Turn `effort=none` (valid enum member, not offered): turn `failed`, backend 400 `unsupported_value` listing accepted values. Turn `model=<nonexistent>`: `failed`, typed `modelNotFound`. Turn `effort=bogus-effort`: `failed`, 400 "Invalid value". `thread_start model=<nonexistent>`: the thread is created and the first turn fails with `modelNotFound`.
- Consequence: bad values are not rejected at start. They surface as a failed turn. Validating against `model_list` first is the only early check seen.
- Accepted values on this account are what `model_list` returns. Confirmed by execution for the default model, one other listed model, and efforts `low` and `ultra`. Other model and effort pairs were not each run (not verified per pair).
- Not verified: effective effort echo for turn-level overrides (only "no error"), stability of the list across logins and plans, whether an unlisted but real (hidden) model name works for a turn.

Status: **partly verified**. The setting mechanisms and the list are verified. Per-pair acceptance and stability are not.

## 13. Natural-language delegation proof (Requirement 1.14)

Evidence: [NOTES-1.7](../spikes/p0-01/NOTES-1.7.md). Raw: [deleg-task-run1-approval-never](../spikes/p0-01/raw/deleg-task-run1-approval-never.redacted.json), [deleg-task](../spikes/p0-01/raw/deleg-task.redacted.json), [deleg-sched](../spikes/p0-01/raw/deleg-sched.redacted.json), [deleg-neg](../spikes/p0-01/raw/deleg-neg.redacted.json).

- Mechanism: **host tools through an MCP server** (the first in the order tried, and it worked). A throwaway stdio MCP server (`spikes/p0-01/stub/mcp_server.py`, hand-written JSON-RPC, no extra dependency) exposes `create_task(title, instructions)` and `propose_schedule(title, cadence, instructions)`, backed by a SQLite stub store. It is configured per thread through `config.mcp_servers.pixie_stub` in `thread_start`. Thread params: `sandbox=read-only`, `approvalPolicy=never`, temp cwd, `project_doc_max_bytes=0`. Each run was a transient unit `pixie-spike-del-<case>` (`run_delegation_unit.sh`).
- Store ruling: per the Operator ruling recorded in tasks.md, the throwaway stub store is accepted as the reading of "present in the Store" for Requirement 1.14. Persistence in the real Store is covered by the thin end-to-end slice (tasks 6.9 and 6.11).

| Run | Time (UTC, 2026-11-15) | Input | Result |
| --- | --- | --- | --- |
| 1 (task, default approval) | 23:29:13 to 23:29:25 | `Please remind me to renew my library card: set up a one-off task called 'Renew library card' for me to do this week.` | Model called `create_task` with sensible arguments. The call **failed at once**: "MCP tool call requires approval, but approval policy is never". No row stored |
| 2 (task, after fix) | 23:31:58 to 23:32:08 | same | `create_task` item `completed`, tool result `{"id": "task-aeae2a74"}`. SQLite read afterwards: `tasks` has exactly one row, `task-aeae2a74`, title "Renew library card"; `schedules` empty. Id returned by the tool and found in the store |
| 3 (sched) | 23:32:39 to 23:32:50 | `Every weekday at 08:00, I want a short summary of my open tasks. Please propose that as a recurring schedule, don't activate anything.` | Two `propose_schedule` calls observed as 4 events. One row `sched-9bd59551`, status `proposed`, title "Weekday open tasks summary". The model added a timezone to the cadence itself |
| 4 (negative) | 23:32:50 to 23:32:55 | `What is the capital of Portugal? Just answer, no need to set anything up.` | Reply "Lisbon.", zero tool calls, store never created |

- Fix used for run 2: server config `default_tools_approval_mode = "approve"`. The key name was found in the binary's config keys and in no document read. A per-tool `approval_mode` was not tested. With other policies (`on-request`, `auto_review`) not tested.
- Result for the "host tools, structured output or slash commands" record: **host tools work**. Dynamic tools (the other host-tool route), structured output (`output_schema`) and slash commands were not tried, because an earlier route in the order worked. Nothing was rejected, and this is not the "reduced conversational functionality" outcome.
- Caveats: the negative case is weak (the prompt itself said not to set anything up). A neutral chat message without that hint was not tested. One run per case, so determinism is not verified. The model chose its own arguments, and made 2 calls where 1 was asked in run 3, so the Runtime must validate arguments itself. The MCP server's write was not confined by the thread's read-only sandbox (inferred from the observed write; the process-level confinement of MCP servers was not examined directly), so MCP servers are trusted extensions and the thread's write bounds do not constrain them. Concurrent calls and tool error handling beyond the run 1 denial were not tested.

Status: **verified** for host tools with a stub store (two executed runs with ids read back from SQLite). Dynamic tools, structured output and slash commands are **not verified** (not tried, not needed). The negative case is only partly verified.

## 14. Selected backend (only this one is built)

**A. Python SDK `openai-codex` 0.169.0** (bundled Codex 0.169.0 app-server), pinned in `uv.lock`, run on CPython 3.14.4. Phase 0 builds only this adapter. Where it needs more than the public API offers (approval handler, writable roots, permission profiles, raw `thread_start` params), the adapter should use `CodexClient` and `config` parameters first; the spike used private attributes (`codex._client`, `_approval_handler`) and whether `CodexClient` removes that need was not verified.

Status: **verified** as to what the spike ran. The cleaner access to the low-level parameters is not verified.

## 15. Filled capability record (design `AdapterCapabilities`)

Values are for backend A as observed. "Doctor re-verify" means `pixie doctor --probe` must confirm it, as the design requires.

| Flag | Value | Evidence and limits |
| --- | --- | --- |
| `streaming_events` | true | Section 3: 10 events streamed incrementally, first delta at 2.63 s |
| `thread_resume` | true | Section 4: `thread_resume` from a new client on a completed and an interrupted thread (NOTES-1.2); after network failure (NOTES-1.4). After an app-server crash: not verified |
| `interrupt` | true, with condition | 0.006 s on a model-streaming turn. Not met while an approval handler blocks (section 4). During tool execution: not verified |
| `approval_requests` | true, low-level only | Server request `item/commandExecution/requestApproval` reaches a custom handler. Not available through the public `Codex()` API. Non-blocking handler required. Accept path not verified |
| `sandbox_read_only` | true | Section 10, `pixie-spike-sbx-ro`. Failure to apply shows only as command failures (no start-up signal), so a probe is needed |
| `sandbox_writable_roots` | true | Section 10, `pixie-spike-sbx-ww`, via `config` (not the public `Sandbox` enum). Set `exclude_slash_tmp` and `exclude_tmpdir_env_var` |
| `read_confinement` | true, partly | Only through a named permission profile, not the legacy modes. Directory confinement and path deny verified on stand-ins. Real Codex_Home deny, globs and `apply_patch` not verified |
| `host_tools` | true | Section 13, via MCP per thread. Dynamic tools not tried. Needs `default_tools_approval_mode="approve"` or an approval handler |
| `output_schema` | not verified | Not tried in any run (task 1.7 stopped at host tools). Treat as absent until tested |
| `instruction_injection` | `explicit` | Section 11. `inline` also verified. `codex_home` partly (discovery only) |
| `model_selection` | true | Section 12 |
| `effort_selection` | true | Section 12. Values must come from `list_models`; invalid values fail the turn |
| `list_models` | true | Section 12, `model_list(include_hidden=True)` |
| `auth_probe` | true, for missing login | `codex login status` (exit 0 or 1), no model call (NOTES-1.3). Expired-token signal not verified |
| `unattended_login` | true, for the observed window | Section 9. The first login needs the Operator (device code). Multi-day behavior not verified |
| `backend_pid_report` | not verified | Not examined in any task 1.1 to 1.7 note. The SDK starts the app-server as a child process, but whether its pid and start time are reportable through the SDK was not checked |

Status: **partly verified**. Two flags (`output_schema`, `backend_pid_report`) have no evidence. Several others carry conditions listed above.

## 16. D2, D3 and D5 conclusions

**D2 (Codex integration interface).** Conclusion: the Python SDK `openai-codex` 0.169.0 is usable on Python 3.14.4 and meets the needs of Requirement 1 for streaming, thread references, results, interrupt (model streaming), approvals (low-level path), write bounds, read confinement through permission profiles, instruction discovery, model and effort selection and host-tool delegation. The limits are in sections 4 to 7, 10 and 15.

**D3 (authentication route and billing).** Conclusion: the ChatGPT-subscription login works unattended from a user service with no terminal, for the observed window (a few hours on 2026-11-15). The gate does not fail, so no stop is needed. Not verified: real token expiry and refresh over days, the Operator's plan and limits, and whether the Terms of Use permit an always-on personal service. The Operator should read the Terms before relying on it (section 8).

**D5 (logout and boot lifecycle).** What was observable: the spike ran every task from transient user units (`systemd-run --user`), which shows that the Codex login works under the user manager with no terminal and no nvm shell init. The notes do not record the lingering state of the user (`loginctl show-user` output), any logout or any reboot, because the runbook forbids enabling lingering, logging out or rebooting.
- Survives logout: **not verified**. Reason: no logout was performed, and lingering state was not recorded.
- Starts at boot: **not verified**. Reason: no reboot was performed, and no persistent unit was installed (no unit was enabled; none exists yet).
- Operator follow-ups (the Operator runs them, once the real `pixie-runtime.service` exists or with a throwaway user unit):
  1. Record `loginctl show-user $USER` (field `Linger`) before and after any change.
  2. With lingering off: log out, log in again, and check whether the user service is still running and whether the Codex login still works.
  3. With lingering on (`loginctl enable-linger`, only with the Operator's consent): log out and check that the service survives.
  4. Reboot with lingering on and no login: check that the service starts at boot and that `codex login status` in the dedicated Codex_Home still reports a login.
  5. Record each as met, not met, or unverified (D5 says so).

Status: D2 **verified** (with the conditions above). D3 **partly verified**. D5 **not verified** (Operator checks pending).

## 17. Design degradations that apply, and requirements issues found

### 17a. Degradations from design "Degradation by backend"

The selected backend is A, so the "A fails" and "B fails" rules do not apply. Rows and rules checked against the evidence:

| Design expectation (marked unverified there) | Result |
| --- | --- |
| A: Python 3.14.4 support "unverified, may force B" | Verified. 3.14.4 works; no fall to B |
| A: streaming, thread resume, interrupt, approval requests "expected" | Verified, with the conditions in sections 4, 5 and 15 (approvals only on the low-level path, interrupt blocked by a blocking approval handler) |
| A: host tools "via MCP config or dynamic tools" | MCP verified, dynamic tools not tried |
| Rule: `host_tools` absent -> structured output or slash commands | Does not apply (host tools work) |
| Rule: `sandbox_read_only` or `sandbox_writable_roots` absent -> profile fails closed (8.13) | Does not apply on this host. The "sandbox cannot be applied" case (section 10) must still be detected by a probe so that 8.13 can fail closed |
| Rule: slash-only outcome -> "reduced conversational functionality" | Does not apply |
| Rule: `output_schema` fallback for `host_tools` | Not evaluated; `output_schema` not verified |

### 17b. Requirements and design issues found

None of these edit `requirements.md` or `design.md`. They are for the Operator to decide.

1. **Requirement 3.16 assumption (instruction inheritance).** A working directory outside a Git repository does not avoid inheriting an ancestor `AGENTS.md`; it only avoids it when no ancestor holds one (section 11). Workarounds verified: `project_root_markers = []` (cwd file only) and `project_doc_max_bytes = 0` (no project docs). The Task cwd and config must set one of them; a cwd choice alone is not enough. This repository has no root `AGENTS.md` today, so the effect on it was not directly tested.
2. **Approvals (Requirements 8.3, 8.4 and the `answer_approval` operation).** The public SDK offers only `deny_all` and `auto_review`, and its default handler auto-accepts (section 5). Separately, the approval request arrives as a synchronous handler call on the SDK reader thread, and a handler that waits stalls the reader, including `interrupt`. The design's asynchronous `answer_approval(h, approval_ref, decision)` model, where a human answers later, does not fit a handler that must return quickly. The adapter must answer the backend immediately (for example deny or a stored decision) and resume the Task afterwards, or use another approach. This is not decided here.
3. **Read confinement (Requirements 8.2, 8.16, design flag `read_confinement`).** The legacy `read-only` and `workspace-write` modes do not confine reads. Read confinement requires a named permission profile in `config`, with the Codex binary directory listed, and was shown only for shell commands. The design's `SandboxSpec` (mode, writable roots, network flag, approval policy) has no field for read roots. The public SDK `Sandbox` enum also carries no writable roots.
4. **Permission_Profile `workspace-write` and `/tmp`.** The `:workspace` profile keeps `/tmp` writable. An explicit `workspace_write` config with `exclude_slash_tmp` and `exclude_tmpdir_env_var` set to true is needed for bounds that exclude `/tmp`.
5. **Sandbox failure has no start-up signal (Requirement 8.13).** When bubblewrap cannot run, the thread starts and the turn is `completed`; only the command items fail. A fail-closed rule needs a probe, because "thread started" does not prove the sandbox works.
6. **Delegation tools need pre-approval (Requirements 12.1, 3.7).** MCP calls fail under `approvalPolicy=never` unless the server has `default_tools_approval_mode="approve"` (an undocumented key found in the binary) or an approval handler answers. The MCP server also ran outside the thread's read-only sandbox (inferred from the observed write; not checked directly), so write bounds do not constrain it. The Runtime must treat MCP tools as trusted code, validate every argument (the model chose its own, including a timezone and a duplicate call), and keep the tool set per thread.
7. **Failure signals for the mapper (Requirement 2).** Auth failure surfaces as an exception (`RuntimeError` 401), not a typed turn error. Network failure and usage limit surface as `error` events plus a `failed` turn, with `codex_error_info` as the classifier. The design's `check_auth` returns `ok | missing | expired | unknown`: `missing` has a signal (`codex login status`), `expired` has none verified.
8. **Authentication and terms (D3, Requirement 2.14).** Whether automated, unattended use of a personal ChatGPT subscription is allowed by the Terms of Use is not verified. The Operator's plan and limits were not read. The docs recommend API-key auth for programmatic use, which the requirements exclude.
9. **Model validation (Requirement 2.11).** Invalid model and effort values fail only at turn time. The adapter must validate against `list_models` before submitting. `none` and `minimal` effort were not offered on this account.
10. **Design says "SDK interrupt is expected" (Requirement 1.4, 5.5, 10.6).** The 10 s bound held only for a model-streaming turn. During an approval wait it depends on the handler (see issue 2).
11. **`backend_pid_report` and `output_schema` have no evidence** (section 15). If the design depends on them (Requirements 7.4 and 7.11 for the pid; the structured-output fallback for 12.1), they need a test before use.
12. **Credential store default.** The Runtime should set `cli_auth_credentials_store = "file"` explicitly. The default was not established.

Contradictions with requirements or design, in short: issues 1, 2, 3 and 10 contradict assumptions in Requirement 3.16, the `answer_approval` model, the `SandboxSpec` shape and the interrupt expectation. Issues 4 to 9, 11 and 12 are gaps or constraints that the documents do not yet state.

Status: **verified** for the degradation table and the issues as recorded in the notes. Issue 2's design consequence and issue 3's `SandboxSpec` remark are my reading of design.md; no experiment tested them.

## 18. Python version decision from task 2.1

Pending task 2.1. This report does not decide it. Evidence available for that task: the whole spike ran on CPython 3.14.4 and passed (section 2); 3.12 and 3.13 have import-only checks and no full run (section 2).

Status: **not verified**. The decision belongs to task 2.1 and has not been made.
