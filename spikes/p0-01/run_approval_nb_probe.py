# Throwaway spike code (task 3.1). Never imported by application code.
"""Non-blocking approval probe. argv[1] =
  sdk-ctor      (d) CodexClient(config, approval_handler=h), public ctor only, immediate decline
  sdk-handoff   (a) handler hands the decision to another thread and waits for it (reader thread still waits)
  sdk-async     (a) AsyncCodex (async wrapper); handler installed through a private attribute
  sdk-subclass  (a) CodexClient subclass whose reader loop answers server requests from a worker pool
  direct-interrupt (b,e) own JSON-RPC client over the app-server stdio; approval left pending, interrupt sent
  direct-accept    (b,c) own client; other requests served while pending; later answer `accept`
Thread: approvalPolicy=on-request, approvalsReviewer=user, sandbox=read-only, temp cwd. Prints redacted JSON."""
import asyncio, json, os, re, signal, subprocess, sys, tempfile, threading, time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

MODE = sys.argv[1]
TIMEOUT_S = int(os.environ.get("SPIKE_TIMEOUT_S", 200))
HOLD_S = float(os.environ.get("SPIKE_HOLD_S", 25))      # how long a handler/answer is held
INT_DELAY_S = float(os.environ.get("SPIKE_INT_DELAY_S", 3))  # interrupt this long after the request arrives
INT_LIMIT_S = 10.0
cwd = tempfile.mkdtemp(prefix="pixie-spike-cwd-")
outside = tempfile.mkdtemp(prefix="pixie-spike-out-")
if MODE == "direct-accept":
    PROMPT = ("Run exactly one shell command: sh -c 'echo hello > approval-probe.txt; echo hello > %s/approval-outside.txt; "
              "echo done'. The sandbox is read-only, so request approval to run it outside the sandbox. "
              "Do nothing else, then reply with the command output." % outside)
else:
    PROMPT = ("Use a shell command to create a file named approval-probe.txt in the current directory containing "
              "the word hello. If the sandbox blocks the write, request approval to run it outside the sandbox. "
              "Do not do anything else.")
THREAD_PARAMS = {"approvalPolicy": "on-request", "approvalsReviewer": "user", "sandbox": "read-only", "cwd": cwd}
rec = {"mode": MODE, "input": PROMPT, "start": datetime.now(timezone.utc).isoformat(),
       "approval_requests": [], "events": [], "notes": []}


def redact(s, n=400):
    s = str(s)
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", s)
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", s)
    s = s.replace(os.path.expanduser("~"), "<home>")
    return s[:n]


def on_alarm(*_):
    raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)


signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(TIMEOUT_S)
t0 = time.monotonic()
now = lambda: round(time.monotonic() - t0, 3)


def summarize_event(method, pl, t):
    e = {"t": t, "method": method}
    item = pl.get("item") if isinstance(pl, dict) else getattr(pl, "item", None)
    if item is not None:
        g = (lambda k: item.get(k)) if isinstance(item, dict) else (lambda k: getattr(getattr(item, "root", item), k, None))
        e["item_type"] = redact(g("type"), 40)
        for k in ("status", "exitCode", "aggregatedOutput"):
            v = g(k)
            if v is not None:
                e["item_" + k] = redact(v, 200)
    if method == "turn/completed":
        turn = pl.get("turn") if isinstance(pl, dict) else getattr(pl, "turn", None)
        e["turn_status"] = redact(turn.get("status") if isinstance(turn, dict) else getattr(turn, "status", None), 40)
    return e


# ------------------------------------------------------------------ SDK modes
def run_sdk():
    from openai_codex import CodexConfig
    from openai_codex.api import Thread
    from openai_codex.client import CodexClient
    release = threading.Event()
    requested = threading.Event()
    pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="decider")

    def decide():  # runs where the decision is taken
        released = release.wait(HOLD_S)
        return {"decision": "decline"}, released

    def handler(method, params):
        p = params or {}
        ent = {"t_request_s": now(), "method": method, "param_keys": sorted(p.keys()),
               "command": redact(p.get("command"), 200), "available_decisions": p.get("availableDecisions"),
               "handler_thread": threading.current_thread().name}
        requested.set()
        if MODE == "sdk-ctor":
            ent["answered"] = "decline immediately"; rec["approval_requests"].append(ent)
            return {"decision": "decline"}
        if MODE == "sdk-handoff":
            result, released = pool.submit(decide).result()  # hand off to another thread, wait for it
        else:  # sdk-subclass: this runs in a pool worker, not the reader thread
            result, released = decide()
        ent["answered_at_s"] = now(); ent["released_by_main"] = released
        rec["approval_requests"].append(ent)
        return result

    class NBClient(CodexClient):
        """Workaround probe: reader loop never waits for the approval handler."""
        def _reader_loop(self):
            wp = ThreadPoolExecutor(max_workers=4, thread_name_prefix="approval-answer")
            try:
                while True:
                    msg = self._read_message()
                    if "method" in msg and "id" in msg:
                        def work(m=msg):
                            r = self._handle_server_request(m)
                            self._write_message({"id": m["id"], "result": r})
                        wp.submit(work)
                    elif "method" in msg:
                        if isinstance(msg["method"], str):
                            self._router.route_notification(self._coerce_notification(msg["method"], msg.get("params")))
                    else:
                        self._router.route_response(msg)
            except BaseException as exc:
                self._router.fail_all(exc)

    cls = NBClient if MODE == "sdk-subclass" else CodexClient
    client = cls(CodexConfig(), approval_handler=handler)  # public constructor argument only
    client.start(); client.initialize()
    rec["handler_installed_via"] = "CodexClient(config, approval_handler=...) constructor argument"
    started = client.thread_start(THREAD_PARAMS)
    th = Thread(client, started.thread.id)
    turn = th.turn(PROMPT)
    s0 = time.monotonic()
    state = {}

    def interrupter():
        if not requested.wait(60):
            return
        time.sleep(INT_DELAY_S)
        a = time.monotonic(); done = threading.Event(); res = {"sent_at_s": now()}
        def call():
            try:
                turn.interrupt(); res["returned_after_s"] = round(time.monotonic() - a, 3)
            except BaseException as e:
                res["error"] = redact(repr(e))
            done.set()
        threading.Thread(target=call, daemon=True).start()
        res["returned_within_10s"] = done.wait(INT_LIMIT_S)
        state["int"] = res; rec["interrupt"] = res
        if not res["returned_within_10s"]:
            release.set(); res["handler_released_at_s"] = now()
            done.wait(20); res["returned_after_release_s"] = round(time.monotonic() - a, 3)
    if MODE != "sdk-ctor":
        threading.Thread(target=interrupter, daemon=True).start()
    for ev in turn.stream():
        rec["events"].append(summarize_event(ev.method, ev.payload, now()))
    rec["turn_wall_s"] = round(time.monotonic() - s0, 3)
    release.set()
    r = th.run("Reply with exactly the word OK. Do not use tools.")
    rec["followup_status"] = str(r.status); rec["followup_response"] = redact(r.final_response, 60)
    rec["file_created_in_cwd"] = os.path.exists(os.path.join(cwd, "approval-probe.txt"))
    time.sleep(1)
    client.close()


async def run_sdk_async():
    from openai_codex import AsyncCodex
    from openai_codex.api import AsyncThread
    release = threading.Event(); requested = threading.Event()

    def handler(method, params):
        p = params or {}
        ent = {"t_request_s": now(), "method": method, "handler_thread": threading.current_thread().name,
               "command": redact(p.get("command"), 200)}
        requested.set()
        ent["released_by_main"] = release.wait(HOLD_S); ent["answered_at_s"] = now()
        rec["approval_requests"].append(ent)
        return {"decision": "decline"}

    async with AsyncCodex() as codex:
        rec["constructor_has_handler_param"] = False
        codex._client._sync._approval_handler = handler  # private: AsyncCodex(config) has no handler parameter
        rec["handler_installed_via"] = "private attribute AsyncCodex._client._sync._approval_handler"
        started = await codex._client.thread_start(THREAD_PARAMS)
        th = AsyncThread(codex, started.thread.id)
        turn = await th.turn(PROMPT)

        async def interrupter():
            await asyncio.to_thread(requested.wait, 60)
            await asyncio.sleep(INT_DELAY_S)
            a = time.monotonic(); res = {"sent_at_s": now()}
            try:
                await asyncio.wait_for(turn.interrupt(), INT_LIMIT_S)
                res["returned_after_s"] = round(time.monotonic() - a, 3); res["returned_within_10s"] = True
            except asyncio.TimeoutError:
                res["returned_within_10s"] = False
                release.set(); res["handler_released_at_s"] = now()
            except BaseException as e:
                res["error"] = redact(repr(e))
            rec["interrupt"] = res
        it = asyncio.create_task(interrupter())
        async for ev in turn.stream():
            rec["events"].append(summarize_event(ev.method, ev.payload, now()))
        release.set()
        await it
        # event loop liveness is not the issue here: the reader thread is
        r = await th.run("Reply with exactly the word OK. Do not use tools.")
        rec["followup_status"] = str(r.status); rec["followup_response"] = redact(r.final_response, 60)
    rec["file_created_in_cwd"] = os.path.exists(os.path.join(cwd, "approval-probe.txt"))


# ------------------------------------------------------------------ direct JSON-RPC mode
class Direct:
    """Minimal app-server stdio JSON-RPC client; the caller's event loop owns the read loop."""
    def __init__(self, codex_bin):
        self.bin = codex_bin; self.next_id = 1; self.futs = {}; self.notes = asyncio.Queue(); self.srv_reqs = asyncio.Queue()
        self.all_notes = []
    async def start(self):
        self.proc = await asyncio.create_subprocess_exec(self.bin, "app-server", "--listen", "stdio://",
            stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            limit=16 * 1024 * 1024)
        self.rt = asyncio.create_task(self.read_loop())
        self.et = asyncio.create_task(self.drain_err())
        await self.request("initialize", {"clientInfo": {"name": "pixie_spike", "title": "Pixie spike", "version": "0"},
                                           "capabilities": {"experimentalApi": True}})
        await self.send({"method": "initialized"})
    async def drain_err(self):
        async for _ in self.proc.stderr:
            pass
    async def send(self, obj):
        self.proc.stdin.write((json.dumps(obj) + "\n").encode()); await self.proc.stdin.drain()
    async def request(self, method, params, timeout=30):
        i = self.next_id; self.next_id += 1
        f = asyncio.get_running_loop().create_future(); self.futs[i] = f
        await self.send({"id": i, "method": method, "params": params})
        return await asyncio.wait_for(f, timeout)
    async def read_loop(self):
        while True:
            line = await self.proc.stdout.readline()
            if not line:
                for f in self.futs.values():
                    if not f.done(): f.set_exception(ConnectionError("app-server closed stdout"))
                return
            m = json.loads(line)
            if "method" in m and "id" in m:
                await self.srv_reqs.put((m, now()))     # never blocks: the Runtime decides later
            elif "method" in m:
                self.all_notes.append((m, now())); await self.notes.put((m, now()))
            else:
                f = self.futs.pop(m.get("id"), None)
                if f and not f.done():
                    if "error" in m: f.set_exception(RuntimeError(redact(m["error"], 300)))
                    else: f.set_result(m.get("result"))
    async def close(self):
        try:
            self.proc.stdin.close(); self.proc.terminate(); await asyncio.wait_for(self.proc.wait(), 5)
        except Exception:
            self.proc.kill()


async def run_direct():
    import codex_cli_bin
    codex_bin = os.path.join(os.path.dirname(codex_cli_bin.__file__), "bin", "codex")
    d = Direct(codex_bin)
    await d.start()
    rec["handler_installed_via"] = "own JSON-RPC client; server requests are queued, answered by Runtime code later"
    th = (await d.request("thread/start", THREAD_PARAMS))["thread"]["id"]
    ts = await d.request("turn/start", {"threadId": th, "input": [{"type": "text", "text": PROMPT}]})
    turn_id = ts["turn"]["id"]
    s0 = time.monotonic()
    req, t_req = await asyncio.wait_for(d.srv_reqs.get(), 90)
    p = req.get("params") or {}
    rec["approval_requests"].append({"t_request_s": t_req, "method": req["method"], "param_keys": sorted(p.keys()),
        "command": redact(p.get("command"), 300), "reason": redact(p.get("reason"), 200),
        "available_decisions": p.get("availableDecisions"), "rpc_id_type": type(req["id"]).__name__})

    async def collect_until(pred, limit):
        end = time.monotonic() + limit
        while time.monotonic() < end:
            try:
                m, t = await asyncio.wait_for(d.notes.get(), max(0.01, end - time.monotonic()))
            except asyncio.TimeoutError:
                return None
            rec["events"].append(summarize_event(m["method"], m.get("params") or {}, t))
            if pred(m): return m, t
        return None

    def is_done(m): return m["method"] == "turn/completed"
    if MODE == "direct-interrupt":
        pings = []
        await asyncio.sleep(INT_DELAY_S)
        a = time.monotonic()
        try:
            await d.request("thread/read", {"threadId": th, "includeTurns": False}, 10)
            pings.append(round(time.monotonic() - a, 3))
        except Exception as e:
            pings.append("error:" + redact(repr(e), 100))
        rec["other_request_latency_while_pending_s"] = pings
        a = time.monotonic(); res = {"sent_at_s": now(), "pending_approval_unanswered": True}
        try:
            await d.request("turn/interrupt", {"threadId": th, "turnId": turn_id}, INT_LIMIT_S)
            res["response_after_s"] = round(time.monotonic() - a, 3)
        except Exception as e:
            res["error"] = redact(repr(e), 200)
        fin = await collect_until(is_done, INT_LIMIT_S)
        res["turn_completed_after_s"] = round(time.monotonic() - a, 3) if fin else None
        res["turn_status"] = (fin[0]["params"]["turn"]["status"] if fin else None)
        res["interrupt_effective_within_10s"] = bool(fin and res["turn_status"] == "interrupted" and time.monotonic() - a <= INT_LIMIT_S)
        rec["interrupt"] = res
        await asyncio.sleep(1)
        names = [n[0]["method"] for n in d.all_notes]
        rec["serverRequest_resolved_seen"] = "serverRequest/resolved" in names
        # reply to the (now stale) request afterwards to see whether the backend objects
        try:
            await d.send({"id": req["id"], "result": {"decision": "decline"}}); rec["late_reply_sent"] = True
        except Exception as e:
            rec["late_reply_sent"] = "error:" + redact(repr(e), 100)
        await asyncio.sleep(1)
    else:  # direct-accept
        pings = []
        end = time.monotonic() + HOLD_S
        while time.monotonic() < end:
            await asyncio.sleep(5)
            a = time.monotonic()
            try:
                await d.request("thread/read", {"threadId": th, "includeTurns": False}, 10)
                pings.append(round(time.monotonic() - a, 3))
            except Exception as e:
                pings.append("error:" + redact(repr(e), 100))
        rec["other_request_latency_while_pending_s"] = pings
        rec["held_s"] = round(time.monotonic() - s0, 2)
        rec["answer_sent_at_s"] = now()
        await d.send({"id": req["id"], "result": {"decision": "accept"}})
        fin = await collect_until(is_done, 90)
        rec["turn_completed"] = bool(fin)
        rec["file_in_cwd"] = os.path.exists(os.path.join(cwd, "approval-probe.txt"))
        rec["file_outside_cwd"] = os.path.exists(os.path.join(outside, "approval-outside.txt"))
        if rec["file_in_cwd"]:
            rec["file_in_cwd_content"] = open(os.path.join(cwd, "approval-probe.txt")).read().strip()
    # is the thread still usable?
    if MODE == "direct-interrupt":
        ts2 = await d.request("turn/start", {"threadId": th, "input": [{"type": "text", "text": "Reply with exactly the word OK. Do not use tools."}]})
        fin2 = await collect_until(is_done, 90)
        rec["followup_turn_status"] = fin2[0]["params"]["turn"]["status"] if fin2 else None
    rec["file_created_in_cwd"] = os.path.exists(os.path.join(cwd, "approval-probe.txt"))
    await d.close()


try:
    if MODE == "sdk-async":
        asyncio.run(run_sdk_async())
    elif MODE.startswith("sdk-"):
        run_sdk()
    else:
        asyncio.run(run_direct())
    rec["outcome"] = "completed"
except TimeoutError as e:
    rec["outcome"] = "timeout"; rec["error"] = str(e)
except BaseException as e:
    import traceback
    rec["outcome"] = "error:" + type(e).__name__; rec["error"] = redact(str(e), 600)
    rec["trace_tail"] = redact(traceback.format_exc()[-1200:], 1200)
finally:
    signal.alarm(0)
    rec["end"] = datetime.now(timezone.utc).isoformat(); rec["elapsed_s"] = round(time.monotonic() - t0, 2)
    import shutil
    shutil.rmtree(cwd, ignore_errors=True); shutil.rmtree(outside, ignore_errors=True)
    print(redact(json.dumps(rec, indent=2, default=str), 200000))
