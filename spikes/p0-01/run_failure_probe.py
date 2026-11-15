# Throwaway spike code (task 1.4). Never imported by application code.
"""Simulated failure signals. argv[1] = netfail-base | netfail-proxy | usage | usage-provider.
A: normal client creates a thread and a turn (state persisted in the dedicated CODEX_HOME).
B: a second client whose backend endpoint is broken resumes the thread and runs a turn; record signal.
C: a normal client resumes the same thread; check that state survived (earlier word recalled).
The real login is never modified. Requests with credentials only go to a loopback fake or a closed port;
headers/bodies are never logged. Prints a redacted JSON record."""
import json, re, signal, sys, tempfile, threading, time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer

MODE = sys.argv[1]
TIMEOUT_S = 270
rec = {"interface": "python-sdk (openai-codex)", "mode": MODE, "start": datetime.now(timezone.utc).isoformat()}


def redact(s, n=400):
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", str(s))
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", s)
    return s[:n]


def on_alarm(*_):
    raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)


hits = []


class H(BaseHTTPRequestHandler):
    def _go(self):
        n = int(self.headers.get("content-length") or 0)
        if n:
            self.rfile.read(n)
        hits.append({"method": self.command, "path": re.sub(r"[0-9a-f-]{20,}", "<id>", self.path)[:80]})
        body = json.dumps({"error": {"type": "usage_limit_reached",
                                     "message": "The usage limit has been reached",
                                     "plan_type": "plus", "resets_in_seconds": 3600}}).encode()
        self.send_response(429)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    do_POST = do_GET = _go

    def log_message(self, *a):
        pass


signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(TIMEOUT_S)
t0 = time.monotonic()
try:
    from openai_codex import Codex, ApprovalMode, Sandbox
    from openai_codex.client import CodexConfig
    cwd = tempfile.mkdtemp(prefix="pixie-spike-cwd-")
    kw = dict(cwd=cwd, sandbox=Sandbox.read_only, approval_mode=ApprovalMode.deny_all)
    # A
    with Codex() as a:
        th = a.thread_start(**kw)
        ra = th.run("Remember the secret word LANTERN. Reply with just OK. Do not use tools.")
        tid = th.id
        rec["A"] = {"status": str(ra.status), "response": redact(ra.final_response, 40)}
    # B
    srv = None
    if MODE == "usage-provider":
        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        cfg = CodexConfig(config_overrides=(
            'model_provider="pixiefake"',
            'model_providers.pixiefake={name="pixiefake", base_url="http://127.0.0.1:%d/v1", env_key="PIXIE_FAKE_KEY", wire_api="responses"}' % srv.server_port,),
            env={"PIXIE_FAKE_KEY": "placeholder-not-a-secret"})
        rec["B_simulation"] = "custom model_provider on loopback fake (dummy key) answering HTTP 429 usage_limit_reached on /v1/responses; real login not sent"
    elif MODE == "usage":
        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        cfg = CodexConfig(config_overrides=('chatgpt_base_url="http://127.0.0.1:%d/backend-api"' % srv.server_port,))
        rec["B_simulation"] = "loopback fake server answering HTTP 429 usage_limit_reached on chatgpt_base_url override"
    elif MODE == "netfail-base":
        cfg = CodexConfig(config_overrides=('chatgpt_base_url="http://127.0.0.1:1/backend-api"',))
        rec["B_simulation"] = "chatgpt_base_url override to closed loopback port 1 (connection refused)"
    else:
        px = "http://127.0.0.1:1"
        cfg = CodexConfig(env={"HTTPS_PROXY": px, "HTTP_PROXY": px, "ALL_PROXY": px,
                               "https_proxy": px, "http_proxy": px, "all_proxy": px, "NO_PROXY": ""})
        rec["B_simulation"] = "HTTPS_PROXY/HTTP_PROXY/ALL_PROXY env pointing at closed loopback port 1 for the app-server process"
    b = {}; b2id = None
    tb = time.monotonic()
    try:
        with Codex(cfg) as cb:
            b["client_start_ok"] = True
            try:
                if MODE == "usage-provider":
                    tr = cb.thread_start(model_provider="pixiefake", **kw)
                    b["thread_start_ok"] = True; b2id = tr.id
                else:
                    tr = cb.thread_resume(tid, **kw)
                    b["thread_resume_ok"] = True
                turn = tr.turn("What was the secret word? Reply with just the word. Do not use tools.", **kw)
                evs = []
                try:
                    for ev in turn.stream():
                        e = {"t": round(time.monotonic() - tb, 2), "method": ev.method}
                        t = getattr(ev.payload, "turn", None)
                        if t is not None:
                            e["turn_status"] = str(getattr(t, "status", None))
                            err = getattr(t, "error", None)
                            if err is not None:
                                e["turn_error"] = redact(err, 600)
                        if ev.method == "error" or "rror" in ev.method:
                            e["payload"] = redact(ev.payload, 600)
                        evs.append(e)
                except BaseException as ex:
                    b["stream_exception"] = type(ex).__name__ + ": " + redact(ex, 600)
                try:
                    rdb = tr.read(include_turns=True)
                    tb_ = getattr(getattr(rdb, "thread", rdb), "turns", None) or []
                    b["same_client_thread_read_statuses"] = [str(getattr(t, "status", None)) for t in tb_]
                    b["same_client_thread_still_readable"] = True
                except BaseException as ex:
                    b["same_client_thread_read_error"] = redact(ex, 300)
                b["events"] = [e for e in evs if e["method"] != "item/agentMessage/delta"][:20]
            except BaseException as ex:
                b["resume_or_turn_exception"] = type(ex).__name__ + ": " + redact(ex, 600)
    except BaseException as ex:
        b["client_exception"] = type(ex).__name__ + ": " + redact(ex, 600)
    b["elapsed_s"] = round(time.monotonic() - tb, 2)
    if srv:
        b["fake_server_hits"] = hits[:10]
        srv.shutdown()
    rec["B"] = b
    # C
    with Codex() as c:
        if b2id:
            try:
                t2 = c.thread_resume(b2id, **kw)
                rec["C_failed_thread_resume_ok"] = True
            except BaseException as ex:
                rec["C_failed_thread_resume_error"] = redact(ex, 300)
        trc = c.thread_resume(tid, **kw)
        rd = trc.read(include_turns=True)
        turns = getattr(getattr(rd, "thread", rd), "turns", None) or []
        rc = trc.run("What was the secret word? Reply with just the word. Do not use tools.", **kw)
        rec["C"] = {"turn_statuses_before_followup": [str(getattr(t, "status", None)) for t in turns],
                    "followup_status": str(rc.status), "followup_response": redact(rc.final_response, 60)}
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
