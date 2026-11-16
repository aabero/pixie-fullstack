# V-2: prompt_toolkit for the Chat_Client (task 2.3)

Throwaway uv project, not part of the project manifest. Python 3.14.4 (`/usr/bin/python3.14`, system interpreter), prompt_toolkit 3.0.53, pyte 0.8.2 (test-only terminal emulator), wcwidth 0.9.4. Versions pinned in `uv.lock`.

## Method and its limit

No human-operated terminal was available. The driver `driver.py` starts each client under a real kernel pty (stdlib `pty.fork`, 24x80, `TERM=xterm`), so prompt_toolkit really runs its raw-mode and escape-sequence code path. It reads the output through the `pyte` terminal emulator and reads the screen buffer to see where lines land. Latency is measured from the driver writing the input (or from the client's own timestamp of an update emission) to the text appearing on the emulated screen.

This is a faithful test of ordering, cursor/line placement and timing. It is NOT a real terminal emulator or a human typing, so the items under "Not verified" remain open.

Client behaviour (identical in both candidates): a stream task prints `stream token N` every 0.25 s for 10 s; an update task prints `UPDATE task-1 running` 3 s after start; typed `/status` prints `STATUS ok`, `/approve` prints `APPROVED ok`. Driver sequence: wait 1.5 s, type `hel` without Enter, wait for the update, snapshot the screen, Ctrl-U, send `/status` + Enter, then `/approve` + Enter (both mid-stream).

## Results (8 repetitions each, raw lines in `raw-pt.txt` and `raw-fallback.txt`)

Command: `cd spikes/v2-prompt-toolkit && uv run python driver.py pt_client.py 8`

| Check | Result for prompt_toolkit (`PromptSession.prompt_async` inside `patch_stdout`) |
|---|---|
| (a) update printed from a background task appears above the input line | 8/8: update on screen row 13, prompt on row 21 (last line), prompt still read `you> hel` (partial input kept) |
| (b) task update during a streaming reply | 0.0007 to 0.0045 s from emission to screen, 8/8 |
| (b) `/status` typed mid-stream answered | 0.106 to 0.129 s, 8/8 |
| (b) `/approve` typed mid-stream answered | 0.071 to 0.085 s, 8/8 |

Verdict: prompt_toolkit meets (a) and (b) with a large margin (worst case 0.13 s against the 2 s limit), with no flakiness in 8 runs. The fallback was therefore not needed. It was run anyway for contrast.

Command: `cd spikes/v2-prompt-toolkit && uv run python driver.py fb_client.py 8`

| Check | Result for the fallback (`input()` in a worker thread, prints from the event loop) |
|---|---|
| (a) | Fails 8/8. The stream and update lines are written over/into the prompt line (prompt row 0 read `you> stream token 0`), and the partially typed `hel` was not kept on the prompt line. The prompt is not kept below the output. |
| (b) | Update 0.0003 to 0.0009 s, `/status` 0.0018 to 0.0031 s, `/approve` 0.0007 to 0.0044 s. Within 2 s, 8/8. |

No requirements issue for 11.9 or 11.11 (prompt_toolkit meets 2 s). Choose prompt_toolkit; the fallback is only usable if (a) is relaxed.

## Not verified

- Behaviour in a real terminal emulator (the pty test used pyte): cursor handling, resize while streaming, bracketed paste, wide characters and very long wrapped update lines.
- Stream rates above 4 lines per second and very long streams (only 40 lines over 10 s were tried).
- Windows and macOS terminals (not in scope; only Linux checked).
- Behaviour under systemd or without a tty (the client is interactive only).

## Operator commands for a hands-on check (real terminal)

Run each in a real terminal, type `hel` without Enter around second 3, and watch that `UPDATE task-1 running` appears above the `you>` line while `hel` stays. Then type `/status` and `/approve` while tokens still stream (they stream for about 10 s) and confirm `STATUS ok` and `APPROVED ok` appear immediately. `/quit` exits.

```
cd spikes/v2-prompt-toolkit
V2_LOG=/tmp/v2-pt.log uv run python pt_client.py
V2_LOG=/tmp/v2-fb.log uv run python fb_client.py    # fallback, for contrast
```
