# Throwaway spike code (task 1.4). Never imported by application code.
"""Approval surfacing probe. argv[1] = decline | wait.
decline: custom handler records the request and answers 'decline' at once.
wait: handler blocks (no user connected) up to WAIT_S, then declines; main thread tries
turn.interrupt() after INT_AT_S to see whether the client can still act while an approval is pending.
Thread is started with approvalPolicy=on-request, approvalsReviewer=user, read-only sandbox, temp cwd.
Prints a redacted JSON record."""
import json, os, re, signal, sys, tempfile, threading, time
from datetime import datetime, timezone

MODE = sys.argv[1]
TIMEOUT_S = int(os.environ.get("SPIKE_TIMEOUT_S", 200))
WAIT_S = int(os.environ.get("SPIKE_WAIT_S", 90))
INT_AT_S = int(os.environ.get("SPIKE_INT_AT_S", 30))
PROMPT = ("Use a shell command to create a file named approval-probe.txt in the current directory "
          "containing the word hello. If the sandbox blocks the write, request approval to run it "
          "outside the sandbox. Do not do anything else.")
rec = {"interface": "python-sdk (openai-codex) low-level client + approvalHandler", "mode": MODE,
       "input": PROMPT, "start": datetime.now(timezone.utc).isoformat(), "approval_requests": [],
       "events": []}


def redact(s, n=200):
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", str(s))
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    return s[:n]


def on_alarm(*_):
    raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)


signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(TIMEOUT_S)
t0 = time.monotonic()
release = threading.Event()


def handler(method, params):
    t = time.monotonic() - t0
    p = params or {}
    entry = {"t_request_s": round(t, 3), "method": method, "param_keys": sorted(p.keys()),
             "command": redact(p.get("command")), "reason": redact(p.get("reason")),
             "available_decisions": p.get("availableDecisions"),
             "handler_thread": threading.current_thread().name}
    if MODE == "wait":
        released = release.wait(WAIT_S)
        entry["blocked_for_s"] = round(time.monotonic() - t0 - t, 3)
        entry["released_by_main"] = released
    entry["answered"] = "decline"
    rec["approval_requests"].append(entry)
    return {"decision": "decline"}


try:
    from openai_codex import Codex
    from openai_codex.api import Thread
    from openai_codex.client import CodexClient
    cwd = tempfile.mkdtemp(prefix="pixie-spike-cwd-")
    with Codex() as codex:
        codex._client._approval_handler = handler
        started = codex._client.thread_start({
            "approvalPolicy": "on-request", "approvalsReviewer": "user",
            "sandbox": "read-only", "cwd": cwd})
        th = Thread(codex._client, started.thread.id)
        turn = th.turn(PROMPT)
        s0 = time.monotonic()
        state = {"int": None}

        def interrupter():
            time.sleep(INT_AT_S)
            if MODE != "wait" or release.is_set():
                return
            a = time.monotonic()
            res = {"requested_at_s": round(a - s0, 3)}
            done = threading.Event()

            def call():
                try:
                    turn.interrupt(); res["returned_after_s"] = round(time.monotonic() - a, 3)
                except BaseException as e:
                    res["error"] = redact(repr(e))
                done.set()
            threading.Thread(target=call, daemon=True).start()
            res["returned_within_20s"] = done.wait(20)
            state["int"] = res
            if not done.is_set():
                release.set()  # let the handler answer so the run can finish
                res["released_handler_after_s"] = round(time.monotonic() - a, 3)
        if MODE == "wait":
            threading.Thread(target=interrupter, daemon=True).start()
        for ev in turn.stream():
            e = {"t": round(time.monotonic() - s0, 3), "method": ev.method}
            pl = ev.payload
            item = getattr(pl, "item", None)
            if item is not None:
                root = getattr(item, "root", item)
                e["item_type"] = str(getattr(root, "type", type(root).__name__))
                st = getattr(root, "status", None)
                if st is not None:
                    e["item_status"] = str(st)
            if ev.method == "turn/completed":
                t = getattr(pl, "turn", None)
                e["turn_status"] = str(getattr(t, "status", None))
                err = getattr(t, "error", None)
                if err:
                    e["turn_error"] = redact(err)
            rec["events"].append(e)
        rec["turn_wall_s"] = round(time.monotonic() - s0, 3)
        rec["interrupt_attempt"] = state["int"]
        rd = th.read(include_turns=True)
        turns = getattr(getattr(rd, "thread", rd), "turns", None) or []
        rec["thread_read_turn_statuses"] = [str(getattr(t, "status", None)) for t in turns]
        # is the thread still usable?
        r = th.run("Reply with exactly the word OK. Do not use tools.", approval_mode=None)
        rec["followup_status"] = str(r.status)
        rec["followup_response"] = redact(r.final_response, 60)
    import os
    rec["file_created_in_cwd"] = os.path.exists(os.path.join(cwd, "approval-probe.txt"))
    rec["outcome"] = "completed"
except TimeoutError as e:
    rec["outcome"] = "timeout"; rec["error"] = str(e)
except BaseException as e:
    import traceback
    rec["outcome"] = "error:" + type(e).__name__
    rec["error"] = redact(str(e), 600)
    rec["trace_tail"] = redact(traceback.format_exc()[-800:], 800)
finally:
    signal.alarm(0)
    rec["end"] = datetime.now(timezone.utc).isoformat()
    rec["elapsed_s"] = round(time.monotonic() - t0, 2)
    print(json.dumps(rec, indent=2, default=str))
