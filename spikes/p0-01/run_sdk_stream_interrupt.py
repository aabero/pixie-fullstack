# Throwaway spike code (task 1.2). Never imported by application code.
"""Streaming, thread refs, result retrieval and interrupt through the Python SDK.
Prints a redacted JSON record. Prompt text/response text is truncated."""
import json, re, signal, sys, tempfile, time, threading
from datetime import datetime, timezone
from collections import Counter

TIMEOUT_S = 240
P_STREAM = "Reply with exactly the word PONG. Do not run any commands or use any tools."
P_FOLLOW = "What single word did I ask you to reply with earlier? Answer with just that word. Do not use tools."
P_LONG = ("Write a very long numbered list from 1 to 400, one short sentence per item about "
          "different animals. Do not run any commands or use any tools.")
P_AFTER_INT = "Reply with exactly the word OK. Do not run any commands or use any tools."

rec = {"interface": "python-sdk (openai-codex)", "start": datetime.now(timezone.utc).isoformat(),
       "scenarios": {}}


def redact(s, n=120):
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", str(s))
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    return s[:n]


def on_alarm(*_):
    raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)


def delta_text(ev):
    p = ev.payload
    return getattr(p, "delta", None)


signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(TIMEOUT_S)
t0 = time.monotonic()
try:
    from openai_codex import Codex, ApprovalMode, Sandbox
    cwd = tempfile.mkdtemp(prefix="pixie-spike-cwd-")
    kw = dict(cwd=cwd, sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all)
    with Codex() as codex:
        # A: streaming + thread ref + result retrieval
        th = codex.thread_start(cwd=cwd, sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all)
        thread_id = th.id
        a = {"input": P_STREAM, "thread_id_present": bool(thread_id), "thread_id_len": len(thread_id)}
        turn = th.turn(P_STREAM, **kw)
        a["turn_id_present"] = bool(turn.id)
        s0 = time.monotonic(); events = []; text = ""
        for ev in turn.stream():
            d = delta_text(ev)
            if isinstance(d, str):
                text += d
            events.append({"t": round(time.monotonic() - s0, 3), "method": ev.method,
                           "payload_type": type(ev.payload).__name__})
        a["event_count"] = len(events)
        a["event_methods"] = dict(Counter(e["method"] for e in events))
        a["first_events"] = events[:12]
        a["last_event"] = events[-1] if events else None
        a["streamed_text"] = redact(text)
        rd = th.read(include_turns=True)
        a["thread_read_type"] = type(rd).__name__
        turns = getattr(getattr(rd, "thread", rd), "turns", None)
        a["thread_read_turns"] = len(turns) if turns is not None else None
        if turns:
            a["thread_read_last_turn_status"] = str(getattr(turns[-1], "status", None))
        # result via TurnHandle.run / Thread.run on a second turn in same thread (context retention)
        r2 = th.run(P_FOLLOW, **kw)
        a["followup_input"] = P_FOLLOW
        a["followup_status"] = str(r2.status)
        a["followup_final_response"] = redact(r2.final_response)
        a["followup_usage_present"] = r2.usage is not None
        a["followup_items"] = len(r2.items or [])
        rec["scenarios"]["A_stream_result_thread"] = a

        # B: interrupt an active turn
        th2 = codex.thread_start(cwd=cwd, sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all)
        b = {"input": P_LONG, "thread_id_len": len(th2.id)}
        turn2 = th2.turn(P_LONG, **kw)
        s0 = time.monotonic(); n_delta = 0; t_int = None; t_done = None; final = None; evs = []
        for ev in turn2.stream():
            now = time.monotonic()
            evs.append({"t": round(now - s0, 3), "method": ev.method})
            if isinstance(delta_text(ev), str):
                n_delta += 1
            if t_int is None and n_delta >= 5:
                t_int = now
                resp = turn2.interrupt()
                b["interrupt_response_type"] = type(resp).__name__
                b["interrupt_call_returned_after_s"] = round(time.monotonic() - t_int, 3)
            if ev.method == "turn/completed":
                t_done = now
                final = getattr(getattr(ev.payload, "turn", None), "status", None)
        b["deltas_before_interrupt"] = n_delta
        b["interrupt_requested_at_s"] = round(t_int - s0, 3) if t_int else None
        b["time_to_stop_s"] = round(t_done - t_int, 3) if (t_int and t_done) else None
        b["turn_completed_status"] = str(final)
        b["events_after_interrupt"] = len([e for e in evs if t_int and e["t"] > round(t_int - s0, 3)])
        b["last_events"] = evs[-4:]
        # thread ref usability after interrupt: same client
        rb = th2.run(P_AFTER_INT, **kw)
        b["same_client_followup_status"] = str(rb.status)
        b["same_client_followup_response"] = redact(rb.final_response)
        rd2 = th2.read(include_turns=True)
        turns2 = getattr(getattr(rd2, "thread", rd2), "turns", None)
        b["thread_read_turn_statuses"] = [str(getattr(t, "status", None)) for t in (turns2 or [])]
        rec["scenarios"]["B_interrupt"] = b
        th2_id = th2.id; th_id = thread_id

    # C: new client (fresh app-server process) resumes thread refs
    with Codex() as codex2:
        c = {}
        res = codex2.thread_resume(th2_id, cwd=cwd, sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all)
        rc = res.run(P_AFTER_INT, **kw)
        c["resume_interrupted_thread_status"] = str(rc.status)
        c["resume_interrupted_thread_response"] = redact(rc.final_response)
        res1 = codex2.thread_resume(th_id, cwd=cwd, sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all)
        rc1 = res1.run(P_FOLLOW, **kw)
        c["resume_completed_thread_status"] = str(rc1.status)
        c["resume_completed_thread_response"] = redact(rc1.final_response)
        rec["scenarios"]["C_resume_new_client"] = c
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
