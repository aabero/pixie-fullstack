# Throwaway spike code (task 1.7). Never imported by application code.
"""argv[1]=case name (task|sched|neg), argv[2]=prompt. Mechanism: stdio MCP server configured via thread_start config.
Stub DB: stub/stub-<case>.db (fresh). Prints a redacted JSON record."""
import json, os, re, signal, sys, tempfile, time, shutil
from datetime import datetime, timezone
CASE, PROMPT = sys.argv[1], sys.argv[2]
HERE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(HERE, "stub", "stub-%s.db" % CASE)
if os.path.exists(DB): os.remove(DB)
TIMEOUT_S = 200
rec = {"mechanism": "host tool: stdio MCP server via thread_start config.mcp_servers (default_tools_approval_mode=approve, approvalPolicy=never, read-only sandbox)", "case": CASE, "input": PROMPT,
       "start": datetime.now(timezone.utc).isoformat(), "events": [], "tool_items": []}
def redact(s, n=400):
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", str(s))
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    return s[:n]
def on_alarm(*_): raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)
signal.signal(signal.SIGALRM, on_alarm); signal.alarm(TIMEOUT_S)
t0 = time.monotonic(); cwd = tempfile.mkdtemp(prefix="pixie-spike-cwd-")
try:
    from openai_codex import Codex
    from openai_codex.api import Thread
    with Codex() as codex:
        started = codex._client.thread_start({
            "approvalPolicy": "never", "sandbox": "read-only", "cwd": cwd,
            "config": {"project_doc_max_bytes": 0, "mcp_servers": {"pixie_stub": {
                "command": sys.executable, "args": [os.path.join(HERE, "stub", "mcp_server.py")],
                "env": {"STUB_DB": DB}, "default_tools_approval_mode": "approve"}}}})
        th = Thread(codex._client, started.thread.id)
        turn = th.turn(PROMPT)
        final = None
        for ev in turn.stream():
            pl = ev.payload; item = getattr(pl, "item", None)
            e = {"t": round(time.monotonic() - t0, 2), "method": ev.method}
            if item is not None:
                root = getattr(item, "root", item)
                e["item_type"] = str(getattr(root, "type", type(root).__name__))
                if "mcp" in e["item_type"].lower() or "dynamic" in e["item_type"].lower():
                    d = root.model_dump(mode="json") if hasattr(root, "model_dump") else str(root)
                    rec["tool_items"].append(json.loads(redact(json.dumps(d, default=str), 1500)) if False else redact(json.dumps(d, default=str), 1500))
                if e["item_type"].endswith("agentMessage") or e["item_type"] == "agentMessage":
                    final = getattr(root, "text", None)
            if ev.method == "turn/completed":
                t = getattr(pl, "turn", None); e["turn_status"] = str(getattr(t, "status", None))
                if getattr(t, "error", None): e["turn_error"] = redact(t.error)
            rec["events"].append(e)
        rec["final_message"] = redact(final)
    rec["outcome"] = "completed"
except TimeoutError as e:
    rec["outcome"] = "timeout"; rec["error"] = str(e)
except BaseException as e:
    import traceback
    rec["outcome"] = "error:" + type(e).__name__; rec["error"] = redact(e, 600); rec["trace_tail"] = redact(traceback.format_exc()[-800:], 800)
finally:
    signal.alarm(0); shutil.rmtree(cwd, ignore_errors=True)
    rec["end"] = datetime.now(timezone.utc).isoformat(); rec["elapsed_s"] = round(time.monotonic() - t0, 2)
    print(json.dumps(rec, indent=2, default=str))
