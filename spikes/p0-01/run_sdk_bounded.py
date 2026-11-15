# Throwaway spike code (task 1.1). Never imported by application code.
"""One bounded task through the Python SDK. Prints a redacted JSON record."""
import json, os, re, signal, sys, time
from datetime import datetime, timezone

PROMPT = "Reply with exactly the word PONG. Do not run any commands or use any tools."
TIMEOUT_S = 240
rec = {"interface": "python-sdk (openai-codex)", "input": PROMPT,
       "start": datetime.now(timezone.utc).isoformat(), "outcome": None, "result": None}


def redact(s: str) -> str:
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", s)
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    return s[:600]


def on_alarm(*_):
    raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)


signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(TIMEOUT_S)
t0 = time.monotonic()
try:
    from openai_codex import Codex
    with Codex() as codex:
        thread = codex.thread_start()
        result = thread.run(PROMPT)
        rec["outcome"] = "completed"
        rec["result"] = redact(str(result.final_response))
except TimeoutError as e:
    rec["outcome"] = "timeout"; rec["result"] = str(e)
except BaseException as e:  # record, do not retry
    rec["outcome"] = "error:" + type(e).__name__
    rec["result"] = redact(str(e))
finally:
    signal.alarm(0)
    rec["end"] = datetime.now(timezone.utc).isoformat()
    rec["elapsed_s"] = round(time.monotonic() - t0, 2)
    print(json.dumps(rec, indent=2))
