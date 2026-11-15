# Throwaway spike code (task 1.3). Never imported by application code.
"""Unattended-login probe. Runs inside a transient systemd user unit.
Never reads auth.json. Prints a redacted JSON record."""
import json, os, re, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

CODEX = str(Path(__file__).parent / ".venv/lib/python3.14/site-packages/codex_cli_bin/bin/codex")
REAL = os.environ["CODEX_HOME"]
PROMPT = "Reply with exactly the word PONG. Do not run any commands or use any tools."

def redact(s):
    s = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", s)
    s = re.sub(r"(sk|tok|eyJ)[A-Za-z0-9_\-\.]{12,}", "<secret>", s)
    return s[:800]

def status(home):
    env = dict(os.environ, CODEX_HOME=home)
    t = datetime.now(timezone.utc).isoformat()
    p = subprocess.run([CODEX, "login", "status"], env=env, capture_output=True, text=True, timeout=60)
    return {"start": t, "end": datetime.now(timezone.utc).isoformat(), "exit": p.returncode,
            "stdout": redact(p.stdout), "stderr": redact(p.stderr)}

def sdk_run(home):
    os.environ["CODEX_HOME"] = home
    rec = {"start": datetime.now(timezone.utc).isoformat()}
    import signal
    signal.signal(signal.SIGALRM, lambda *_: (_ for _ in ()).throw(TimeoutError("timeout 120s")))
    signal.alarm(120)
    try:
        from openai_codex import Codex
        with Codex() as c:
            r = c.thread_start().run(PROMPT)
            rec["outcome"] = "completed"; rec["result"] = redact(str(r.final_response))
    except BaseException as e:
        rec["outcome"] = "error:" + type(e).__name__; rec["result"] = redact(str(e))
    finally:
        signal.alarm(0)
        rec["end"] = datetime.now(timezone.utc).isoformat()
    return rec

out = {"env": {
    "stdin_isatty": sys.stdin.isatty(), "stdout_isatty": sys.stdout.isatty(),
    "stderr_isatty": sys.stderr.isatty(),
    "PATH": os.environ.get("PATH"), "TERM_set": "TERM" in os.environ,
    "SSH_AUTH_SOCK_set": "SSH_AUTH_SOCK" in os.environ,
    "DISPLAY_set": "DISPLAY" in os.environ, "BROWSER_set": "BROWSER" in os.environ,
    "api_key_env_vars_present": sorted(k for k in os.environ if re.search(r"OPENAI|CODEX_API|API_KEY", k)),
    "CODEX_HOME_is_dedicated": REAL.endswith("spikes/p0-01/.codex-home"),
    "nvm_in_PATH": ".nvm" in os.environ.get("PATH", "").replace(os.environ.get("NODE_DIR", "@@"), ""),
    "config_toml_exists": Path(REAL, "config.toml").exists(),
    "auth_json_exists": Path(REAL, "auth.json").exists(),
    "auth_json_size": Path(REAL, "auth.json").stat().st_size,
}}
out["status_dedicated"] = status(REAL)
empty = tempfile.mkdtemp(prefix="pixie-spike-empty-home-")
out["status_empty_home"] = status(empty)
out["sdk_dedicated"] = sdk_run(REAL)
out["sdk_empty_home"] = sdk_run(empty)
out["empty_home_files_after"] = sorted(p.name for p in Path(empty).iterdir())
out["auth_json_exists_in_empty_after"] = Path(empty, "auth.json").exists()
print(json.dumps(out, indent=2))
