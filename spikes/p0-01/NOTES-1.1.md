# Task 1.1 notes (spike P0-01) - status: DONE (SDK works after Operator login)

Date: 2026-11-15. Branch kiro-phase0. Throwaway; not application code.

## Environment
- uv 0.13.8; uv provides CPython 3.14.4 (/usr/bin/python3.14, system interpreter). Spike pinned to 3.14.4 (`.python-version`); `requires-python >=3.14` is throwaway.
- Found: codex-cli 0.167.2 (nvm node v26.13.0). Not used by the SDK path.
- Dedicated CODEX_HOME: `spikes/p0-01/.codex-home` (git-ignored via spikes/p0-01/.gitignore). `codex login status` there: "Not logged in".

## Candidate 1: Python SDK `openai-codex` (tried first)
- Added with `uv add openai-codex`; resolved openai-codex==0.169.0, which pulls openai-codex-cli-bin==0.169.0 (bundled Codex binary, 167 MB), pydantic 2.14.3. Pinning method: `uv.lock` (spikes/p0-01/uv.lock).
- Both packages declare Requires-Python >=3.10. Imported OK on 3.12.16, 3.13.18 and 3.14.4 (import only, no run on 3.12/3.13). 3.14.4 is the interpreter of the spike project and ran the harness.
- API: `Codex(config=CodexConfig(...))`, `thread_start()`, `Thread.run()`, `login_chatgpt()` / `login_chatgpt_device_code()`, `TurnHandle`, `Sandbox`, `ApprovalMode`, `CodexConfig.env/cwd/config_overrides`.
- Needs satisfied so far: starts the bundled app-server and speaks to it (error came from the backend, so transport works). Streaming, interrupt, thread refs are task 1.2, not tested.
- Bounded run, transient unit `pixie-spike-sdk-2` (CODEX_HOME dedicated, PATH = node dir + system dirs, RuntimeMaxSec=290):
  - input: "Reply with exactly the word PONG. Do not run any commands or use any tools."
  - start 2026-11-15T21:23:22Z, end 21:23:38Z (16.06 s)
  - outcome: error:RuntimeError, HTTP 401 Unauthorized "Missing bearer or basic authentication" (no credentials in dedicated CODEX_HOME). No final result.
  - raw: raw/sdk-run-1.redacted.json. Earlier run raw/sdk-run-0-missing-codex-home.redacted.json failed only because the CODEX_HOME dir did not exist (my setup error).
- Not rejected: no evidence against the SDK. Interfaces 2 (app-server JSON-RPC) and 3 (`codex exec`) were NOT tried, since the stop rule is "first that satisfies the needs" and the SDK has not yet been shown to fail; nothing was recorded as rejected.

## Blocker
Unattended/any login is required in the dedicated CODEX_HOME. The Operator must do the ChatGPT login (browser or device code) there. Suggested:
  `CODEX_HOME=/home/agustin/dev/pixie/pixie-fullstack/spikes/p0-01/.codex-home codex login --device-auth`
(codex-cli 0.167.2 vs bundled 0.169.0: credential format compatibility not verified.) Then re-run:
  `systemd-run --user --unit=pixie-spike-sdk-3 --wait --collect --pipe -p RuntimeMaxSec=290 -p WorkingDirectory=$PWD -E CODEX_HOME=$PWD/.codex-home -E PATH=<node dir>:/usr/local/bin:/usr/bin:/bin -E HOME=$HOME $PWD/.venv/bin/python run_sdk_bounded.py` from spikes/p0-01.

## Cleanup
No `pixie-spike-*` units remain (--collect).

## Update: run after Operator login (2026-11-15)
- Operator ran `codex login --device-auth` (CLI 0.167.2, ChatGPT subscription) in the dedicated CODEX_HOME. `auth.json` exists (4084 bytes); contents not read.
- Bounded run, transient unit `pixie-spike-sdk-3` (--wait --collect --pipe, RuntimeMaxSec=290, PATH = node dir + /usr/local/bin:/usr/bin:/bin, absolute python from spikes/p0-01/.venv, in-script alarm 240 s):
  - input: "Reply with exactly the word PONG. Do not run any commands or use any tools."
  - start 2026-11-15T21:29:42.970731Z, end 2026-11-15T21:29:47.537404Z (4.57 s)
  - outcome: completed. final result: "PONG". unit exit status 0/SUCCESS.
  - raw: raw/sdk-run-3.redacted.json (stderr: raw/sdk-run-3.stderr.txt, systemd messages only).
- Credential compatibility: the 0.167.2 CLI login was accepted by the bundled 0.169.0 binary (inferred from the successful run; format not inspected).
- Interface decision: the SDK satisfies the needs for this bounded run, so app-server JSON-RPC (2) and `codex exec` (3) were not tried. Nothing was rejected. Streaming, interrupt and thread references remain for 1.2.
- Versions: uv 0.13.8; CPython 3.14.4 (system /usr/bin/python3.14); openai-codex==0.169.0, openai-codex-cli-bin==0.169.0; pinned via spikes/p0-01/uv.lock. Python support: both packages declare >=3.10; import-only OK on 3.12.16, 3.13.18; full bounded run only on 3.14.4, which works. 3.12/3.13 runs: not verified (not run).
- Cleanup: `systemctl --user list-units 'pixie-spike-*' --all` is empty.
