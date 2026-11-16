"""Drives a client under a real pty (stdlib pty) and reads the screen through a pyte
terminal emulator. Measures latency from sending input / emitting an update to the text
appearing on the emulated screen. Usage: driver.py <client.py> <reps>"""
import fcntl, os, pty, select, struct, sys, tempfile, termios, time
import pyte

client, reps = sys.argv[1], int(sys.argv[2])
ROWS, COLS = 24, 80

def run_once():
    log = tempfile.mktemp(prefix="v2log")
    pid, fd = pty.fork()
    if pid == 0:
        os.environ.update(V2_LOG=log, TERM="xterm")
        os.execvp("uv", ["uv", "run", "--no-project" if False else "python", client])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", ROWS, COLS, 0, 0))
    screen = pyte.Screen(COLS, ROWS); stream = pyte.ByteStream(screen)
    t0 = time.time()
    first_seen = {}
    def pump(dur):
        end = time.time() + dur
        while time.time() < end:
            r, _, _ = select.select([fd], [], [], 0.01)
            if r:
                try: data = os.read(fd, 65536)
                except OSError: return
                if not data: return
                stream.feed(data)
            now = time.time()
            text = "\n".join(screen.display)
            for key in ("UPDATE task-1", "STATUS ok", "APPROVED ok"):
                if key in text and key not in first_seen:
                    first_seen[key] = now
    def wait_for(key, timeout):
        end = time.time() + timeout
        while time.time() < end and key not in first_seen:
            pump(0.02)
    def rows():
        return [l.rstrip() for l in screen.display]
    pump(1.5)
    sent = {}
    for ch in "hel":                     # partial, unsent input
        os.write(fd, ch.encode()); pump(0.05)
    pump(2.5)                            # update emitted ~3 s after start
    wait_for("UPDATE task-1", 4)
    pump(0.5)
    snap = rows()
    upd_row = next((i for i, l in enumerate(snap) if "UPDATE task-1" in l), None)
    prompt_row = max((i for i, l in enumerate(snap) if "you>" in l), default=None)
    prompt_text = snap[prompt_row] if prompt_row is not None else None
    os.write(fd, b"\x15"); pump(0.3)     # ctrl-u: clear partial line
    os.write(fd, b"/status\r"); sent["STATUS ok"] = time.time()
    wait_for("STATUS ok", 4); pump(0.5)
    os.write(fd, b"/approve\r"); sent["APPROVED ok"] = time.time()
    wait_for("APPROVED ok", 4); pump(0.5)
    streaming_still = any("stream token" in l for l in rows())
    os.write(fd, b"/quit\r"); pump(0.5)
    try: os.kill(pid, 9)
    except ProcessLookupError: pass
    os.waitpid(pid, 0); os.close(fd)
    emitted = None
    if os.path.exists(log):
        for l in open(log):
            n, v = l.split()
            if n == "UPDATE": emitted = float(v)
        os.unlink(log)
    res = {
        "update_latency_s": (first_seen["UPDATE task-1"] - emitted) if emitted and "UPDATE task-1" in first_seen else None,
        "status_latency_s": first_seen["STATUS ok"] - sent["STATUS ok"] if "STATUS ok" in first_seen else None,
        "approve_latency_s": first_seen["APPROVED ok"] - sent["APPROVED ok"] if "APPROVED ok" in first_seen else None,
        "update_row": upd_row, "prompt_row": prompt_row, "prompt_line": prompt_text,
        "update_above_prompt": upd_row is not None and prompt_row is not None and upd_row < prompt_row,
        "partial_input_kept": bool(prompt_text and prompt_text.endswith("hel")),
    }
    return res

for i in range(reps):
    print(i, run_once(), flush=True)
