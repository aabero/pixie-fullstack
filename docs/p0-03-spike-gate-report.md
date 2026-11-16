You're right, task 3 is in the file. I also need to correct something. I said I tried `"3."`, but I didn't. I only tried `"3"`. I'll try the title form now.The tools do recognize task 3, but only under the ID `3. Checkpoint - spike gate`. My earlier mistake was using the bare number. I'll mark it in progress and wait for the result before dispatching.Task 3 is a pass: the spike gate holds and D3 did not fail. I changed nothing except an appended task 3 entry in `docs/dev-log.md`, and I did not start task 4.

## Checks

1. **Report:** `docs/spike-p0-01-report.md` exists. Section 14 names the selected backend: Python SDK `openai-codex` 0.169.0 (bundled Codex 0.169.0), on CPython 3.14.4. No section is marked pending. The only "pending" matches are about approvals and the Operator's D5 checks (lines 62–65 and 282).
2. **D3:** Section 16 says the gate does not fail. The ChatGPT login was reused unattended from a user unit with no terminal (section 9). Nothing in the report says scope needs review. D3 is only partly verified: a few hours of observation, no real token expiry, no plan or limit check, and the Terms of Use were not read.
3. **Housekeeping:**
   - **Units:** `systemctl --user list-units 'pixie-spike-*' --all` lists nothing.
   - **Git:** `git status` shows only `tasks.md` and `tasks.meta.json` modified. `spikes/p0-01/.gitignore:1` ignores `.codex-home/` and `auth.json`. The only tracked path matching `codex-home|token|secret|.env` is `spikes/p0-01/raw/sdk-run-0-missing-codex-home.redacted.json`, and it matches on its name only.
   - **Scan of `spikes/` and `docs/`** (excluding `.codex-home`, `uv.lock` and the venv):
     - No matches for emails, JWT-like strings (`eyJ…`) or `sk-`/`ghp_`/`xox`-style prefixes.
     - 40+ hex: `docs/always-on-agent-prototype-plan.md` lines 342 and 344. Line 342 is a link to a GitHub repository, and I did not inspect line 344.
     - Runs of 48+ characters:
       - `docs/always-on-agent-prototype-plan.md`: 342, 344.
       - `docs/spike-p0-01-report.md`: 128, 217.
       - `spikes/p0-01/NOTES-1.1.md`: 24.
       - `spikes/p0-01/NOTES-1.3.md`: 27.
       - `spikes/p0-01/run_delegation_unit.sh`: 4.
       - `spikes/p0-01/run_instruction_unit.sh`: 5.
       - `spikes/p0-01/run_sandbox_unit.sh`: 4.
       - `spikes/p0-01/raw/sandbox-prof.redacted.json`: 167.
       - `spikes/p0-01/raw/sdk-run-0-missing-codex-home.redacted.json`: 7.
       - `spikes/p0-01/raw/failure-netfail-base.redacted.json`, `failure-netfail-proxy.redacted.json` and `failure-usage.redacted.json`: lines 30, 35, 40, 45, 50, 55, 60, 65, 70 in each.
     - I masked and looked at four of these lines (the raw files at line 30, 167 and 7, and plan line 342). They are a URL, an error string, a path and stderr text, not tokens. The rest I did not inspect. I did not read `auth.json`.
4. **Tests:** there is no `tests/` directory yet (`ls tests` fails). Task 4.1 creates it. I created no suite, so there is nothing to run.

## Decisions for the Operator
I decided and applied none of these.

**Report section 17b**
- **17b-1 (3.16, tasks 6.4, 8.1):** a cwd outside Git still inherits an ancestor `AGENTS.md`. Options: set `project_root_markers=[]`, set `project_doc_max_bytes=0`, or rely on the cwd alone. Recommend `project_doc_max_bytes=0` plus `explicit` injection. Never rely on the cwd.
- **17b-2 (8.3, 8.4, `answer_approval`; tasks 5.2, 8.1, 10.2):** the SDK's default approval handler auto-accepts, and a blocking handler stalls `interrupt`. Options: a non-blocking handler that denies at once and resumes later, a direct app-server JSON-RPC client, or `deny_all` only in Phase 0. Recommend an immediate-answer handler on `CodexClient`, with resume after the human answers.
- **17b-3 (8.2, 8.16, `SandboxSpec`; tasks 5.2, 8.1, 10.1):** only a named permission profile confines reads, and `SandboxSpec` has no read roots. Options: add `read_roots` to the spec and use profiles, or accept legacy modes with no read confinement. Recommend adding read roots, and listing the Codex binary directory.
- **17b-4 (tasks 8.1, 10.1):** `:workspace` keeps `/tmp` writable. Options: explicit `workspace_write` with both `/tmp` exclusions on, or accept `/tmp` writable. Recommend the explicit exclusions.
- **17b-5 (8.13; tasks 8.2, 10.6, 17.3):** a failed sandbox gives no start-up signal. Options: a canary at worker start, only `doctor --probe`, or both. Recommend both.
- **17b-6 (12.1, 3.7; task 8.3):** MCP tools need `default_tools_approval_mode="approve"`, an undocumented key. MCP servers also run outside the thread's write bounds. Options: use that key, use a handler, or use dynamic tools (not tried). Recommend the key plus strict argument validation.
- **17b-7 (task 8.2):** auth failure arrives as a 401 exception, and expired-token behavior is unknown. Options: map `codex login status` exit 1 to `missing` and 401 to `unknown`, or test real expiry first. Recommend the first, and decide on a real-expiry test later.
- **17b-8 (D3, 2.14; no task):** the Terms of Use position for unattended personal use is unverified. Options: the Operator reads the Terms and continues, or stops. Recommend the Operator reads them before relying on the service.
- **17b-9 (2.11; task 8.2):** invalid model or effort values fail only when the turn runs. Options: validate against `list_models` before submit, or accept a failed turn. Recommend validating first.
- **17b-10 (1.4, 5.5, 10.6; task 10.3):** the 10 s interrupt bound holds only for a model-streaming turn. Options: relax the requirement text for approval waits, or enforce a non-blocking handler. Recommend the non-blocking handler, and treat 17b-2 as the fix.
- **17b-11 (7.4, 7.11, 12.1; tasks 8.1, 8.3):** `backend_pid_report` and `output_schema` have no evidence. Options: test both in task 8.1, or treat both as absent. Recommend treating them as absent and testing the pid first.
- **17b-12 (task 8.1):** the credential store default is unknown. Options: set `cli_auth_credentials_store="file"` explicitly, or leave the default. Recommend setting it explicitly.

**Other decisions**
- **Task 2.1 (tasks 4.1, 17.1, 17.2):** only the system `/usr/bin/python3.14` provides 3.14.4. uv can only download 3.14.10, so a system upgrade would break the pin. Options:
  - (a) Set `requires-python = ">=3.14,<3.15"`, pin 3.14.4 in `.python-version`, and have setup record the interpreter path it finds.
  - (b) Pin 3.14.10, which means re-running the spike.
  - (c) Use 3.12.
  - Recommend (a). The unit file uses the environment's interpreter by absolute path. Setup checks that the interpreter reports 3.14.4 and stops with instructions if it does not. Re-verify if the system Python changes.
- **Task 2.2 (task 14.1, Property 6):** `0 * * * *` fires in both overlap hours. Property 6 says a repeated local time fires exactly once. Options:
  - (a) The wrapper skips any fire whose `fold=1` repeats an instant already fired.
  - (b) Document the double fire as accepted.
  - (c) Change Property 6, which needs Operator sign-off.
  - Recommend (a). It matches Property 6 as written. Add a test for wildcard-hour expressions across the New_York 2026-11-01 overlap.
- **Task 2.3 (task 6.8):** the V-2 result is pty-based only (prompt_toolkit 3.0.53, 8/8 runs, worst latency 0.13 s). Run the commands in `spikes/v2-prompt-toolkit/NOTES.md` in a real terminal:
  - `V2_LOG=/tmp/v2-pt.log uv run python pt_client.py`, with the `cd spikes/v2-prompt-toolkit` before it.
  - Type `hel` without Enter around second 3 and check that the update line appears above the prompt while `hel` stays.
  - Type `/status` and `/approve` mid-stream and check they answer at once.
  - Also try a window resize, a paste and a long wrapped line, which the pty test did not cover.

  Recommend it should not block anything. Continue with prompt_toolkit and revisit only if the manual check fails.

**D5 (not in your list):** logout survival and boot start are unverified, and the Operator checks are in report section 16. Recommend deferring them until the real unit exists (task 17.1), and do not enable lingering without agreement.Task 3 passed and is marked completed. The spike gate holds and D3 did not fail. The only file the sub-agent changed was `docs/dev-log.md`, where it appended the task 3 entry. I did not start task 4.1, which is now ready.

My earlier "not found" errors were my mistake. The tools only accept the full title `3. Checkpoint - spike gate` as the task ID, not the bare number.

## Checks

1. **Report:** `docs/spike-p0-01-report.md` exists and has no pending sections. It names the Python SDK `openai-codex` 0.169.0 as the selected backend, on CPython 3.14.4.
2. **D3:** Section 16 of the report says unattended login worked from a user unit with no terminal. Nothing in it says scope needs review. D3 is only partly verified, because the report records:
   - a few hours of observation;
   - no real token expiry;
   - no plan or usage-limit check;
   - the Terms of Use not read (17b-8).
3. **Housekeeping:**
   - No `pixie-spike-*` units are left.
   - `git status` shows only `tasks.md` and `tasks.meta.json` modified. No credential files or `.codex-home` are tracked, and `spikes/p0-01/.gitignore` ignores `.codex-home/` and `auth.json`.
   - The scan found no emails, JWT-like strings or `sk-`/`ghp_`/`xox`-style prefixes.
   - It did flag long strings (48+ characters) in the files below, and 40+ hex in the plan file. The sub-agent masked and looked at four lines (a URL, an error string, a path and stderr text) and found no tokens.
   - These flagged lines were not inspected:
     - `docs/spike-p0-01-report.md`: lines 128 and 217.
     - `docs/always-on-agent-prototype-plan.md`: line 344.
     - `spikes/p0-01/NOTES-1.1.md`: line 24.
     - `spikes/p0-01/NOTES-1.3.md`: line 27.
     - `spikes/p0-01/run_delegation_unit.sh`: line 4.
     - `spikes/p0-01/run_instruction_unit.sh`: line 5.
     - `spikes/p0-01/run_sandbox_unit.sh`: line 4.
     - Raw JSON files: the other flagged lines, mostly in the `failure-*` files.

   I can have those checked if you want.
4. **Tests:** No `tests/` directory exists yet, because task 4.1 creates it. Nothing was created or run.

## Decisions for you

I decided and applied none of these.

**Report section 17b**

| Item | Affects | Options | Recommendation |
|---|---|---|---|
| 17b-1 | 3.16; tasks 6.4, 8.1 | A cwd outside Git still inherits an ancestor `AGENTS.md`. Set `project_root_markers=[]`, set `project_doc_max_bytes=0`, or rely on the cwd alone. | `project_doc_max_bytes=0` plus `explicit` injection. |
| 17b-2 | 8.3, 8.4; tasks 5.2, 8.1, 10.2 | The SDK's default approval handler auto-accepts, and a blocking handler stalls `interrupt`. Use a non-blocking handler that denies at once and resumes later, a direct JSON-RPC client, or `deny_all` only in Phase 0. | An immediate-answer handler, with resume after the human answers. |
| 17b-3 | 8.2, 8.16; tasks 5.2, 8.1, 10.1 | Only a named permission profile confines reads, and `SandboxSpec` has no read roots. Add `read_roots` and use profiles, or accept no read confinement. | Add read roots, and list the Codex binary directory. |
| 17b-4 | tasks 8.1, 10.1 | `:workspace` keeps `/tmp` writable. Use explicit `workspace_write` with both `/tmp` exclusions on, or accept it. | The explicit exclusions. |
| 17b-5 | 8.13; tasks 8.2, 10.6, 17.3 | A failed sandbox gives no start-up signal. Use a canary at worker start, only `doctor --probe`, or both. | Both. |
| 17b-6 | 12.1, 3.7; task 8.3 | MCP tools need `default_tools_approval_mode="approve"`, an undocumented key, and MCP servers run outside the thread's write bounds. Use the key, use a handler, or use dynamic tools (not tried). | The key plus strict argument validation. |
| 17b-7 | task 8.2 | Auth failure arrives as a 401 exception, and expired-token behavior is unknown. Map `codex login status` exit 1 to `missing` and 401 to `unknown`, or test real expiry first. | Map them now. Decide on a real-expiry test later. |
| 17b-8 | D3, 2.14; no task | The Terms of Use position for unattended personal use is unverified. You read them and continue, or stop. | Read them before relying on the service. |
| 17b-9 | 2.11; task 8.2 | Invalid model or effort values fail only when the turn runs. Validate against `list_models` before submit, or accept a failed turn. | Validate first. |
| 17b-10 | 1.4, 5.5, 10.6; task 10.3 | The 10 s interrupt bound holds only for a model-streaming turn. Relax the requirement text for approval waits, or enforce a non-blocking handler. | The non-blocking handler, which is the 17b-2 fix. |
| 17b-11 | 7.4, 7.11, 12.1; tasks 8.1, 8.3 | `backend_pid_report` and `output_schema` have no evidence. Test both in task 8.1, or treat both as absent. | Treat both as absent, and test the pid first. |
| 17b-12 | task 8.1 | The credential store default is unknown. Set `cli_auth_credentials_store="file"` explicitly, or leave the default. | Set it explicitly. |

**Other decisions**

- **Task 2.1 (tasks 4.1, 17.1, 17.2):** Only the system `/usr/bin/python3.14` provides 3.14.4, and uv can only download 3.14.10. The options are:
  - (a) Set `requires-python = ">=3.14,<3.15"` and pin 3.14.4 in `.python-version`. Setup records the interpreter path it finds.
  - (b) Pin 3.14.10, which means re-running the spike.
  - (c) Use 3.12.

  I recommend (a). The unit file uses the environment's interpreter by absolute path. Setup checks that it reports 3.14.4 and stops with instructions if not. Re-verify if the system Python changes.
- **Task 2.2 (task 14.1, Property 6):** `0 * * * *` fires in both overlap hours, but Property 6 says a repeated local time fires once. The options are:
  - (a) The wrapper skips any fire whose `fold=1` repeats an instant already fired.
  - (b) Document the double fire as accepted.
  - (c) Change Property 6, which needs your sign-off.

  I recommend (a), plus a test for wildcard-hour expressions across the New_York 2026-11-01 overlap.
- **Task 2.3 (task 6.8):** The V-2 result is pty-based only (prompt_toolkit 3.0.53, 8/8 runs, worst latency 0.13 s). Check this yourself in a real terminal, using `spikes/v2-prompt-toolkit/NOTES.md`:
  - From `spikes/v2-prompt-toolkit`, run `V2_LOG=/tmp/v2-pt.log uv run python pt_client.py`.
  - Type `hel` without Enter around second 3. The update line should appear above the prompt while `hel` stays.
  - Type `/status` and `/approve` mid-stream. Both should answer at once.
  - Also try a window resize, a paste and a long wrapped line, which the pty test did not cover.

  I recommend it blocks nothing. Continue with prompt_toolkit and revisit only if the manual check fails.

**D5 (not in your list):** Logout survival and boot start are unverified, and your checks are in report section 16. I recommend deferring them until the real unit exists (task 17.1). Don't enable lingering without your agreement.