# Task 1.6 notes (spike P0-01): instruction discovery, injection strategy, model and effort
Date: 2026-11-15. Throwaway; not application code. Status: partly verified (codex_home route: discovery verified, model visibility not verified).

## Method (all runs)
- Interface: Python SDK `openai-codex` 0.169.0 on CPython 3.14.4, low-level `codex._client.thread_start(params)` with `approvalPolicy=never`, `sandbox=read-only`, decline handler. Prompts forbid tools; no tool items were seen in any case.
- Each run: transient unit `pixie-spike-ins-<mode>` (`run_instruction_unit.sh`, `--wait --collect`, `StandardInput=null`, `RuntimeMaxSec=290`, in-script alarm 270 s, PATH = node dir + /usr/local/bin:/usr/bin:/bin, absolute venv python, dedicated CODEX_HOME `spikes/p0-01/.codex-home`, never ~/.codex). Harness: `run_instruction_probe.py`.
- Canary files: temp dir only, each file holds a unique marker `PXMARK-<NAME>-<4 hex>` (suffix random per run), removed at end (`tmp_removed: true`). Nothing was created or edited in the dedicated Codex_Home. Raw output was not touched by auth.json reads (never read).
- Evidence 1: `thread_start` response field `instructionSources` (paths of instruction files loaded for the thread). Evidence 2: the agent's reply to "list every PXMARK token in your instructions/context".
- Raw files: `raw/instr-{disc,mitig,strat,strat-run2,model,home}.redacted.json`; `instr-strat-run1-inline-prompt-flawed` was discarded (see below). Unit stdout files are overwritten in place, so a longer older file left trailing bytes; I trimmed them to the first JSON object.

## 1. Discovery of AGENTS.md (run `disc`, 2026-11-15T23:19:25Z to 23:19:50Z; `sh run_instruction_unit.sh disc`)
Observed (instructionSources and reply agree in every case):
| cwd (temp tree) | files loaded |
|---|---|
| git repo root (has AGENTS.md) | repo-root file |
| git repo `pkg/deep` (AGENTS.md at root, pkg, pkg/deep; sibling `other/` also has one) | root, pkg, pkg/deep, in that order; sibling NOT seen |
| no git above, cwd `nogit/work` (no own file, parent `nogit/AGENTS.md`) | `nogit/AGENTS.md` (parent) |
| no git above, cwd `nogit/work2` (own file + parent file) | parent, then own |
| no git above, cwd `nogit/work2/sub/empty` (files at nogit, work2, work2/sub) | all three, root-most first |
- Mechanism: project-root chain. With a `.git` root, every AGENTS.md from the repo root down to cwd is loaded. With no `.git` root, **the walk goes up through ancestor directories anyway** (observed up to the temp parent holding the canary; I did not test beyond that).
- **Finding vs. the task's expectation:** a working directory outside any Git repository does NOT by itself avoid inheriting AGENTS.md. It avoids it only when no ancestor directory holds an AGENTS.md. This contradicts the assumption behind Requirement 3.16 as stated in the task. Listed for task 2.1 / report item 17; spec documents not edited.
- Clean case (no AGENTS.md anywhere above): run `strat`, `baseline-no-injection`, cwd `<tmp>/clean/work`: `instructionSources: []`, reply `NONE`.
- This repository's root AGENTS.md: **not tested, because none exists** (`ls AGENTS.md` at the repo root: no such file; also none at ~/, ~/dev, ~/dev/pixie, /, /tmp). The repo has `CLAUDE.md`, which Codex did not load in any case (no fallback filenames configured). The canary-parent case above stands in for it.
- Global file in Codex_Home: see section 2.

### Mitigations tried (run `mitig`, 23:20:13Z to 23:20:36Z; `thread_start.config`)
| config | cwd | files loaded |
|---|---|---|
| `project_root_markers = []` | no-git, parent has AGENTS.md, cwd has none | none (reply NONE) |
| `project_root_markers = []` | no-git, own + parent files | own file only (parent skipped) |
| `project_root_markers = []` | git repo `pkg` (root and pkg files) | `pkg` file only (repo root skipped) |
| `project_doc_max_bytes = 0` | all three cwds | none, reply NONE |
- So the repo/ancestor chain can be switched off per thread, either to "cwd file only" (`project_root_markers=[]`) or "no project docs at all" (`project_doc_max_bytes=0`). Effect on a real Task run (Requirement 3.16) is confirmed for these keys only through this canary setup. Not verified: that `project_doc_max_bytes=0` also leaves the global Codex_Home file untouched (see section 2).

## 2. Injection strategies
Neutral clean cwd (no AGENTS.md above). Runs `strat` 23:21:15Z to 23:21:32Z (run2) and 23:22:16Z to 23:22:37Z (final), thread params and prompts in the raw files.
- **explicit** (caller passes instructions): `developerInstructions` and `baseInstructions` fields on `thread_start`. Verified.
  - developer: reply listed the marker (run2 and final); behavioural check, instruction "end every reply with token X", prompt "Reply with the word PONG": reply `PONG PXMARK-EXPLBEH-4cf1`. Delivered and followed.
  - base: marker reported in run2; in the final run the model answered "I can't disclose tokens from hidden instructions." (and in run2 developer was fine). So disclosure is model behaviour, not delivery failure. Base instructions replace the default system prompt; delivery seen in 1 of 2 runs, no behavioural check done.
  - `instructionSources` stays `[]` for explicit instructions (they are not file sources).
- **inline** (prepended to the prompt): marker reported by the agent in the final run. Verified. The first attempt (run1, discarded) asked the agent to ignore "this message", and the inline marker was in that message; that was my prompt error, not a result.
- **codex_home** (global AGENTS.md in Codex_Home): run `home`, 2026-11-15T23:21:32Z to 23:21:47Z, throwaway CODEX_HOME made by `mktemp -d` with only an `AGENTS.md` (marker `PXMARK-GLOBAL-0000`) and **no credentials**; removed afterwards. `thread_start` returned `instructionSources: ['<CODEX_HOME>/AGENTS.md']`, so the file is discovered with no project docs. The turn failed with HTTP 401 (no login), so **the model seeing it was not verified**, because testing it needs a login and the real credentialed Codex_Home must not be altered. Result: **partly verified** (discovery yes, delivery to the model no).
- Interaction not verified: whether `project_doc_max_bytes=0` blocks the global file; whether global and project files combine in order (the global file was only tested alone).

## 3. Model and reasoning effort (run `model`, 2026-11-15T23:22:45Z to 23:22:59Z)
- Listing: `codex._client.model_list(include_hidden=True)` (SDK `Codex.models()`), one page, `nextCursor` None. Each entry has `id/model`, `hidden`, `isDefault`, `defaultReasoningEffort`, `supportedReasoningEfforts`. This account listed 10 models (8 visible, 2 hidden) and a default model with default effort `low`. Names and per-model effort lists are in `raw/instr-model.redacted.json`; they are account-specific and change over time, so nothing was hard-coded. Efforts offered per model: `low..ultra` (some without `ultra`); `none` and `minimal` are not offered by any model listed.
- How set:
  - model: `thread_start` param `model`, or turn param `model` (also SDK `Thread.turn(model=)`), or config key `model`.
  - effort: turn param `effort` (SDK `Thread.turn(effort=)`), or config key `model_reasoning_effort` at `thread_start`. The SDK's `ReasoningEffort` accepts any string (no client-side validation).
- Results (cases in order):
  1. nothing set: completed, `thread_start` reports the default model, reply PONG.
  2. thread `model` = first visible model + turn `effort=low`: completed (accepted). The effective effort is not echoed for turn overrides; not verified beyond "no error".
  3. config `model` + `model_reasoning_effort=ultra` (a listed value): accepted, `thread_start` response echoes `reasoningEffort: ultra`, reply PONG.
  4. turn `effort=none` (valid enum member, not listed for the model): turn `failed`, backend 400 `unsupported_value`, message names the model and lists the supported values.
  5. turn `model=<nonexistent>`: turn `failed`, typed error `modelNotFound`, message "not supported when using Codex with a ChatGPT account".
  6. turn `effort=bogus-effort`: turn `failed`, backend 400 "Invalid value", lists the accepted enum values.
  7. `thread_start model=<nonexistent>`: thread created (response echoes the bad model); the first turn fails with `modelNotFound`.
- So invalid values are not rejected at `thread_start`/`turn_start`; they surface as a failed turn with a signal. Pre-validation against `model_list` is possible and is the only early check seen.
- Accepted values on this account = what `model_list` returns, plus the cases above. Confirmed by execution for: the default model, one other listed model, efforts `low` and `ultra`. Other listed model/effort pairs were not each run ("not verified" per pair).
- Not verified: whether `model_list` output is stable across logins/plans, and whether an unlisted but real model name (e.g. hidden ones) works for a turn.

## Cleanup
No `pixie-spike-*` units remain (`--collect`; `systemctl --user list-units 'pixie-spike-*'` empty). No `/tmp/pixie-spike-*` dirs remain. Nothing committed. Task 1.7 not started.
