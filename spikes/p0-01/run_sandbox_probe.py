# Throwaway spike code (task 1.5). Never imported by application code.
"""Sandbox / permission profile probe. argv[1] = ro | ww | prof | nosb.
Low-level client thread_start with explicit approvalPolicy=never (SDK default handler auto-accepts, see 1.4)
plus a decline handler as a belt-and-braces. Temp dirs only; canary files are created here, never
anything under the Codex home. Prints a redacted JSON record."""
import json, os, re, shutil, signal, sys, tempfile, time
from datetime import datetime, timezone

MODE = sys.argv[1]
TIMEOUT_S = 270
rec = {"interface": "python-sdk (openai-codex) low-level client thread_start", "mode": MODE,
       "start": datetime.now(timezone.utc).isoformat(), "turns": []}


def redact(s, n=400):
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", str(s))
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    s = re.sub(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<uuid>", s)
    return s[:n]


def on_alarm(*_):
    raise TimeoutError("bounded run exceeded %ss" % TIMEOUT_S)


signal.signal(signal.SIGALRM, on_alarm)
signal.alarm(TIMEOUT_S)
t0 = time.monotonic()
root = tempfile.mkdtemp(prefix="pixie-spike-sbx-")
D = {k: os.path.join(root, k) for k in ("ws", "extra", "outside", "allowed", "fakehome")}
for p in D.values():
    os.makedirs(p)
D["oob2"] = tempfile.mkdtemp(prefix="pixie-spike-oob2-", dir=os.path.dirname(os.path.abspath(__file__)))
os.symlink(D["fakehome"] + "/canary.txt", D["ws"] + "/link-fakehome.txt")
os.symlink(D["outside"] + "/canary.txt", D["ws"] + "/link-outside.txt")
for _n, _body in (("job1.sh", "cat %s/canary.txt; echo exit=$?" % D["fakehome"]),
                  ("job2.sh", "cat %s/canary.txt; echo exit=$?" % D["outside"]),("readfake.sh", "cat %s/canary.txt; echo exit=$?" % D["fakehome"]),
                  ("readoutside.sh", "cat %s/canary.txt; echo exit=$?" % D["outside"]),
                  ("writeoob2.sh", "echo P5 > %s/oob5.txt; echo exit=$?" % D["oob2"])):
    with open(D["ws"] + "/" + _n, "w") as _f:
        _f.write(_body + "\n")
def S(name):
    return ("Run exactly this one shell command and nothing else: sh %s/%s . Do not open or inspect the script "
            "first, do not try any other way, do not request elevated permissions, do not ask me anything. "
            "Then reply with its output." % (D["ws"], name))
CAN = {"outside": "CANARY-OUTSIDE-51a7", "allowed": "CANARY-ALLOWED-92c4", "fakehome": "CANARY-FAKEHOME-3be8"}
for k, v in CAN.items():
    with open(os.path.join(D[k], "canary.txt"), "w") as f:
        f.write(v + "\n")


def W(path, tag):
    return ("Run exactly this one shell command and nothing else, even if you expect it to fail or be "
            "blocked. Do not try any other way, do not request elevated permissions, do not ask me anything. "
            "Command: sh -c 'echo %s > %s; echo exit=$?'. Then reply with the command's output." % (tag, path))


def R(path):
    return ("Run exactly this one shell command and nothing else, even if you expect it to fail or be "
            "blocked. Do not try any other way, do not request elevated permissions, do not ask me anything. "
            "Command: cat %s. Then reply with what it printed or the error." % path)


import openai_codex, pathlib
CODEX_BIN_DIR = str(pathlib.Path(openai_codex.__file__).parent.parent / "codex_cli_bin" / "bin")
RO = {"sandbox": "read-only"}
base = {"approvalPolicy": "never", "cwd": D["ws"]}
if MODE == "ro":
    params = {**base, **RO}
    turns = [("ro-write-in-cwd", W(D["ws"] + "/w.txt", "RO"), [D["ws"] + "/w.txt"]),
             ("ro-read-outside-canary", R(D["outside"] + "/canary.txt"), [])]
elif MODE in ("ww", "nosb"):
    params = {**base, "sandbox": "workspace-write",
              "config": {"sandbox_workspace_write": {"writable_roots": [D["extra"]],
                                                     "exclude_slash_tmp": True,
                                                     "exclude_tmpdir_env_var": True,
                                                     "network_access": False}}}
    turns = [("ww-write-in-cwd", W(D["ws"] + "/in.txt", "WW1"), [D["ws"] + "/in.txt"]),
             ("ww-write-in-extra-root", W(D["extra"] + "/in2.txt", "WW2"), [D["extra"] + "/in2.txt"]),
             ("ww-write-outside", W(D["outside"] + "/oob.txt", "OOB"), [D["outside"] + "/oob.txt"]),
             ("ww-read-outside-canary", R(D["outside"] + "/canary.txt"), [])]
    if MODE == "nosb":
        turns = turns[:1] + turns[2:3]
elif MODE == "prof":
    # custom permission profile: read only :minimal + allowed dir, write only ws; fakehome explicitly denied
    params = {**base, "config": {
        "default_permissions": "pixie_confined",
        "permissions": {"pixie_confined": {"filesystem": {
            ":minimal": "read", CODEX_BIN_DIR: "read", D["allowed"]: "read", D["ws"]: "write", D["fakehome"]: "deny"}}}}}
    turns = [("prof-read-allowed", R(D["allowed"] + "/canary.txt"), []),
             ("prof-read-outside", R(D["outside"] + "/canary.txt"), []),
             ("prof-read-fakehome", R(D["fakehome"] + "/canary.txt"), []),
             ("prof-read-fakehome-via-symlink", R(D["ws"] + "/link-fakehome.txt"), []),
             ("prof-read-outside-via-symlink", R(D["ws"] + "/link-outside.txt"), []),
             ("prof-read-fakehome-via-script", S("readfake.sh"), []),
             ("prof-read-outside-via-script", S("readoutside.sh"), []),
             ("prof-write-ws", W(D["ws"] + "/p.txt", "P1"), [D["ws"] + "/p.txt"]),
             ("prof-write-outside", W(D["outside"] + "/oob2.txt", "P2"), [D["outside"] + "/oob2.txt"])]
elif MODE == "profdeny2":
    params = {**base, "config": {
        "default_permissions": "pixie_denyhome",
        "permissions": {"pixie_denyhome": {"extends": ":workspace", "filesystem": {D["fakehome"]: "deny"}}}}}
    turns = [("pd2-job1-reads-fakehome", S("job1.sh"), []), ("pd2-job2-reads-outside", S("job2.sh"), [])]
elif MODE == "profdeny":
    # broad read (:workspace base) with only the fake Codex_Home excluded
    params = {**base, "config": {
        "default_permissions": "pixie_denyhome",
        "permissions": {"pixie_denyhome": {"extends": ":workspace", "filesystem": {D["fakehome"]: "deny"}}}}}
    turns = [("pd-read-outside", R(D["outside"] + "/canary.txt"), []),
             ("pd-read-fakehome", R(D["fakehome"] + "/canary.txt"), []),
             ("pd-read-fakehome-via-symlink", R(D["ws"] + "/link-fakehome.txt"), []),
             ("pd-read-fakehome-via-script", S("readfake.sh"), []),
             ("pd-write-outside-repo-dir-via-script", S("writeoob2.sh"), [D["oob2"] + "/oob5.txt"]),
             ("pd-write-outside-repo-dir", W(D["oob2"] + "/oob4.txt", "P4"), [D["oob2"] + "/oob4.txt"]),
             ("pd-write-outside", W(D["outside"] + "/oob3.txt", "P3"), [D["outside"] + "/oob3.txt"])]
else:
    raise SystemExit("bad mode")
rec["thread_params"] = json.loads(json.dumps(params).replace(D["oob2"], "<oob2>").replace(root, "<tmp>"))


def handler(method, params):
    rec.setdefault("approval_requests", []).append({"method": method, "command": redact((params or {}).get("command"), 200)})
    return {"decision": "decline"}


def item_info(root_item):
    d = root_item.model_dump(mode="json", by_alias=False)
    keep = {k: d[k] for k in ("type", "status", "exit_code") if k in d}
    if "command" in d:
        keep["command"] = redact(d["command"], 300).replace(D["oob2"], "<oob2>").replace(root, "<tmp>")
    if d.get("aggregated_output") is not None:
        keep["output"] = redact(d["aggregated_output"], 300).replace(D["oob2"], "<oob2>").replace(root, "<tmp>")
    if "changes" in d:
        keep["changes"] = redact(d["changes"], 300).replace(D["oob2"], "<oob2>").replace(root, "<tmp>")
    return keep


try:
    from openai_codex import Codex
    from openai_codex.api import Thread
    with Codex() as codex:
        codex._client._approval_handler = handler
        started = codex._client.thread_start(params)
        sd = started.model_dump(mode="json", by_alias=True)
        rec["thread_start_response_effective"] = json.loads(json.dumps(
            {k: sd.get(k) for k in ("sandbox", "approvalPolicy", "activePermissionProfile", "permissionProfile",
                                    "approvalsReviewer") if k in sd}, default=str).replace(D["oob2"], "<oob2>").replace(root, "<tmp>"))
        rec["thread_start_response_keys"] = sorted(sd.keys())
        th = Thread(codex._client, started.thread.id)
        for name, prompt, probes in turns:
            ts = datetime.now(timezone.utc).isoformat()
            a = time.monotonic()
            t = {"name": name, "start": ts, "prompt": prompt.replace(D["oob2"], "<oob2>").replace(root, "<tmp>"), "items": []}
            turn = th.turn(prompt)
            for ev in turn.stream():
                pl = ev.payload
                if ev.method == "item/completed":
                    item = getattr(pl, "item", None)
                    if item is not None:
                        info = item_info(getattr(item, "root", item))
                        if info.get("type") == "agentMessage":
                            t["agent_message"] = redact(getattr(getattr(item, "root", item), "text", ""), 300).replace(D["oob2"], "<oob2>").replace(root, "<tmp>")
                        if info.get("type") in ("commandExecution", "fileChange", "CommandExecution", "FileChange") or "command" in info:
                            t["items"].append(info)
                if ev.method == "turn/completed":
                    tt = getattr(pl, "turn", None)
                    t["turn_status"] = str(getattr(tt, "status", None))
                    if getattr(tt, "error", None):
                        t["turn_error"] = redact(tt.error)
            t["elapsed_s"] = round(time.monotonic() - a, 2)
            t["end"] = datetime.now(timezone.utc).isoformat()
            t["probe_files_exist_after"] = {p.replace(D["oob2"], "<oob2>").replace(root, "<tmp>"): os.path.exists(p) for p in probes}
            rec["turns"].append(t)
    rec["outcome"] = "completed"
except TimeoutError as e:
    rec["outcome"] = "timeout"; rec["error"] = str(e)
except BaseException as e:
    import traceback
    rec["outcome"] = "error:" + type(e).__name__
    rec["error"] = redact(str(e), 800).replace(D["oob2"], "<oob2>").replace(root, "<tmp>")
    rec["trace_tail"] = redact(traceback.format_exc()[-800:], 800).replace(D["oob2"], "<oob2>").replace(root, "<tmp>")
finally:
    signal.alarm(0)
    rec["end"] = datetime.now(timezone.utc).isoformat()
    rec["elapsed_s"] = round(time.monotonic() - t0, 2)
    shutil.rmtree(root, ignore_errors=True)
    shutil.rmtree(D["oob2"], ignore_errors=True)
    rec["oob2_removed"] = not os.path.exists(D["oob2"])
    rec["tmp_removed"] = not os.path.exists(root)
    print(json.dumps(rec, indent=2, default=str))
