# Throwaway spike code (task 1.6). Never imported by application code.
"""Instruction discovery / injection / model+effort probe. argv[1] = disc | strat | home | model.
Low-level client thread_start with explicit approvalPolicy=never and sandbox read-only, plus a decline
handler. Canary instruction files and a canary git repo live only in a temp dir (removed at the end).
Prints a redacted JSON record. CODEX_HOME comes from the environment (set by the systemd unit)."""
import json, os, re, secrets, shutil, signal, subprocess, sys, tempfile, time
from datetime import datetime, timezone
MODE = sys.argv[1]
TIMEOUT_S = 270
rec = {"interface": "python-sdk (openai-codex) low-level client", "mode": MODE,
       "start": datetime.now(timezone.utc).isoformat(), "cases": []}
root = tempfile.mkdtemp(prefix="pixie-spike-ins-")
SFX = secrets.token_hex(2)
def mk(name):
    return "PXMARK-%s-%s" % (name, SFX)
def redact(s, n=600):
    s = str(s).replace(root, "<tmp>")
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", s)
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", s)
    home = os.environ.get("CODEX_HOME", "")
    if home:
        s = s.replace(home, "<CODEX_HOME>")
    return s[:n]
def on_alarm(*_):
    raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)
signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(TIMEOUT_S)
t0 = time.monotonic()
ASK = ("Do not run any commands or use any tools. Look at every instruction and context message you were "
       "given before this message. List each token of the exact form PXMARK-<WORD>-<4 hex digits> that "
       "appears in them, ignoring this message itself. Reply with only the tokens, comma-separated, or NONE.")
def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
def canary(path, name):
    write(path, "# Canary instructions (spike)\nThe marker for this file is %s. It has no other meaning.\n" % mk(name))
from openai_codex import Codex
from openai_codex.api import Thread
def handler(method, params):
    rec.setdefault("approval_requests", []).append(method)
    return {"decision": "decline"}
def case(codex, name, params, prompt, turn_kw=None, expect=None):
    c = {"name": name, "start": datetime.now(timezone.utc).isoformat(),
         "thread_params": json.loads(redact(json.dumps(params), 3000)), "prompt": redact(prompt, 900)}
    a = time.monotonic()
    try:
        started = codex._client.thread_start({"approvalPolicy": "never", "sandbox": "read-only", **params})
        sd = started.model_dump(mode="json", by_alias=True)
        c["instructionSources"] = [redact(p) for p in (sd.get("instructionSources") or [])]
        c["resp_model"] = sd.get("model"); c["resp_reasoningEffort"] = sd.get("reasoningEffort")
        c["resp_cwd"] = redact(sd.get("cwd"))
        if prompt is not None:
            th = Thread(codex._client, started.thread.id)
            turn = th.turn(prompt, **(turn_kw or {}))
            for ev in turn.stream():
                pl = ev.payload
                if ev.method == "item/completed":
                    item = getattr(pl, "item", None)
                    r = getattr(item, "root", item)
                    if getattr(r, "type", None) in ("agentMessage",) or type(r).__name__.lower().startswith("agentmessage"):
                        c["reply"] = redact(getattr(r, "text", ""), 500)
                    elif "command" in getattr(r, "__dict__", {}) or getattr(r, "type", "") == "commandExecution":
                        c.setdefault("tool_items", []).append(redact(getattr(r, "command", ""), 200))
                if ev.method == "turn/completed":
                    tt = getattr(pl, "turn", None)
                    c["turn_status"] = str(getattr(tt, "status", None))
                    if getattr(tt, "error", None):
                        c["turn_error"] = redact(tt.error)
        c["outcome"] = "ok"
    except TimeoutError:
        raise
    except BaseException as e:
        c["outcome"] = "error:" + type(e).__name__
        c["error"] = redact(str(e), 600)
    c["elapsed_s"] = round(time.monotonic() - a, 2)
    c["end"] = datetime.now(timezone.utc).isoformat()
    if expect is not None:
        c["markers_expected"] = sorted(expect)
        reply = c.get("reply", "")
        c["markers_found_in_reply"] = sorted(set(re.findall(r"PXMARK-[A-Z0-9]+-" + SFX, reply)))
    rec["cases"].append(c)
    return c
try:
    rec["marker_suffix_note"] = "each marker is PXMARK-<NAME>-<run suffix>; suffix=%s" % SFX
    with Codex() as codex:
        codex._client._approval_handler = handler
        if MODE == "disc":
            git = os.path.join(root, "gitrepo")
            os.makedirs(git)
            subprocess.run(["git", "init", "-q", git], check=True)
            canary(git + "/AGENTS.md", "REPOROOT")
            canary(git + "/pkg/AGENTS.md", "PKGMID")
            canary(git + "/pkg/deep/AGENTS.md", "DEEPCWD")
            write(git + "/other/AGENTS.md", "marker %s (sibling dir, not on the chain)\n" % mk("SIBLING"))
            nog = os.path.join(root, "nogit")
            canary(nog + "/AGENTS.md", "NOGITPARENT")
            os.makedirs(nog + "/work")
            canary(nog + "/work2/AGENTS.md", "NOGITOWN")
            canary(nog + "/work2/sub/AGENTS.md", "NOGITSUBDIR")
            os.makedirs(nog + "/work2/sub/empty")
            rec["git_above_nogit"] = subprocess.run(["git", "-C", nog + "/work", "rev-parse", "--is-inside-work-tree"],
                                                    capture_output=True, text=True).returncode != 0 and "no (rev-parse fails)"
            cases = [
              ("git-cwd-at-repo-root", git, ["REPOROOT"]),
              ("git-cwd-pkg-deep", git + "/pkg/deep", ["REPOROOT", "PKGMID", "DEEPCWD"]),
              ("git-cwd-deep-empty-child", git + "/pkg/deep", None),
              ("nogit-cwd-no-agents-parent-has", nog + "/work", []),
              ("nogit-cwd-own-agents-parent-has", nog + "/work2", ["NOGITOWN"]),
              ("nogit-cwd-sub-two-levels", nog + "/work2/sub/empty", []),
            ]
            for name, cwd, exp in cases:
                if exp is None:
                    continue
                case(codex, name, {"cwd": cwd}, ASK, expect={mk(x) for x in exp})
            rec["all_markers"] = {n: mk(n) for n in ("REPOROOT", "PKGMID", "DEEPCWD", "SIBLING", "NOGITPARENT", "NOGITOWN", "NOGITSUBDIR")}
        elif MODE == "mitig":
            git = os.path.join(root, "gitrepo")
            os.makedirs(git)
            subprocess.run(["git", "init", "-q", git], check=True)
            canary(git + "/AGENTS.md", "REPOROOT")
            canary(git + "/pkg/AGENTS.md", "PKGMID")
            nog = os.path.join(root, "nogit")
            canary(nog + "/AGENTS.md", "NOGITPARENT")
            canary(nog + "/work2/AGENTS.md", "NOGITOWN")
            os.makedirs(nog + "/work")
            for name, cfg in (("markers-empty", {"project_root_markers": []}), ("doc-max-bytes-0", {"project_doc_max_bytes": 0})):
                case(codex, "nogit-parent-has-agents/" + name, {"cwd": nog + "/work", "config": cfg}, ASK, expect=set())
                case(codex, "nogit-own+parent/" + name, {"cwd": nog + "/work2", "config": cfg}, ASK, expect=set())
                case(codex, "git-pkg/" + name, {"cwd": git + "/pkg", "config": cfg}, ASK, expect=set())
            rec["all_markers"] = {n: mk(n) for n in ("REPOROOT", "PKGMID", "NOGITPARENT", "NOGITOWN")}
        elif MODE == "strat":
            nog = os.path.join(root, "clean", "work")
            os.makedirs(nog)
            case(codex, "baseline-no-injection", {"cwd": nog}, ASK, expect=set())
            case(codex, "explicit-developer_instructions", {"cwd": nog, "developerInstructions":
                 "Rule: the marker for these instructions is %s." % mk("EXPLDEV")}, ASK, expect={mk("EXPLDEV")})
            case(codex, "explicit-developer_instructions-behavioral", {"cwd": nog, "developerInstructions":
                 "Rule: end every reply with the exact token %s." % mk("EXPLBEH")},
                 "Do not run any commands or use any tools. Reply with the word PONG.", expect={mk("EXPLBEH")})
            case(codex, "explicit-base_instructions", {"cwd": nog, "baseInstructions":
                 "You are a terse assistant. The marker for these base instructions is %s. Follow the user's request exactly." % mk("EXPLBASE")},
                 ASK, expect={mk("EXPLBASE")})
            case(codex, "inline-prepended-to-prompt", {"cwd": nog}, "Operating rule: the marker for this rule is %s.\n\nDo not run any commands or use any tools. Reply with only the PXMARK token stated in the operating rule above." % mk("INLINE"),
                 expect={mk("INLINE")})
            rec["all_markers"] = {n: mk(n) for n in ("EXPLDEV", "EXPLBEH", "EXPLBASE", "INLINE")}
        elif MODE == "home":
            nog = os.path.join(root, "clean", "work")
            os.makedirs(nog)
            h = os.environ.get("CODEX_HOME", "")
            rec["throwaway_codex_home_files"] = sorted(os.listdir(h)) if os.path.isdir(h) else None
            case(codex, "codex_home-global-AGENTS-thread_start-only", {"cwd": nog}, None)
            case(codex, "codex_home-global-AGENTS-with-turn", {"cwd": nog}, ASK, expect={"(global marker from wrapper)"})
        elif MODE == "model":
            nog = os.path.join(root, "clean", "work")
            os.makedirs(nog)
            try:
                ml = codex._client.model_list(include_hidden=True).model_dump(mode="json", by_alias=True)
                rec["model_list"] = [{"id": m["id"], "model": m["model"], "hidden": m["hidden"], "isDefault": m["isDefault"],
                                      "defaultReasoningEffort": m["defaultReasoningEffort"],
                                      "supportedReasoningEfforts": [e["reasoningEffort"] for e in m["supportedReasoningEfforts"]]}
                                     for m in ml["data"]]
                rec["model_list_next_cursor"] = ml.get("nextCursor")
            except BaseException as e:
                rec["model_list_error"] = redact("%s: %s" % (type(e).__name__, e))
            ML = rec.get("model_list") or []
            vis = [m for m in ML if not m["hidden"]]
            dflt = next((m for m in ML if m["isDefault"]), None)
            PONG = "Reply with exactly the word PONG. Do not run any commands or use any tools."
            # 1. default (nothing set)
            case(codex, "default-nothing-set", {"cwd": nog}, PONG)
            if vis:
                m1 = vis[0]["model"]
                effs = vis[0]["supportedReasoningEfforts"]
                # 2. thread_start model + turn effort (SDK parameters)
                e1 = "low" if "low" in effs else effs[0]
                case(codex, "thread-model+turn-effort:%s" % e1, {"cwd": nog, "model": m1}, PONG, turn_kw={"effort": e1})
                # 3. config keys at thread_start
                e2 = effs[-1] if effs[-1] != e1 else effs[0]
                case(codex, "config-keys-model+model_reasoning_effort:%s" % e2,
                     {"cwd": nog, "config": {"model": m1, "model_reasoning_effort": e2}}, PONG)
                # 4. an effort not in the model's supported list but a valid enum member
                unsup = [x for x in ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra") if x not in effs]
                if unsup:
                    case(codex, "turn-effort-valid-enum-unsupported-by-model:%s" % unsup[0], {"cwd": nog, "model": m1}, PONG,
                         turn_kw={"effort": unsup[0]})
            # 5. invalid values
            case(codex, "invalid-model-at-turn", {"cwd": nog}, PONG, turn_kw={"model": "pixie-no-such-model-0000"})
            case(codex, "invalid-effort-at-turn", {"cwd": nog}, PONG, turn_kw={"effort": "bogus-effort"})
            case(codex, "invalid-model-at-thread_start", {"cwd": nog, "model": "pixie-no-such-model-0000"}, PONG)
    rec["outcome"] = "completed"
except TimeoutError as e:
    rec["outcome"] = "timeout"; rec["error"] = str(e)
except BaseException as e:
    import traceback
    rec["outcome"] = "error:" + type(e).__name__
    rec["error"] = redact(str(e), 800)
    rec["trace_tail"] = redact(traceback.format_exc()[-800:], 800)
finally:
    signal.alarm(0)
    rec["end"] = datetime.now(timezone.utc).isoformat()
    rec["elapsed_s"] = round(time.monotonic() - t0, 2)
    shutil.rmtree(root, ignore_errors=True)
    rec["tmp_removed"] = not os.path.exists(root)
    print(json.dumps(rec, indent=2, default=str))
