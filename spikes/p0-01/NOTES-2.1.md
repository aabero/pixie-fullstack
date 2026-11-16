# Task 2.1: uv can provide Python 3.14.4 (2026-11-15)

Tool: uv 0.13.8 (`/home/agustin/.local/bin/uv`), Linux x86_64.

| # | Command | Observed result | Python version |
| --- | --- | --- | --- |
| 1 | `uv --version` | `uv 0.13.8 (x86_64-unknown-linux-gnu)` | n/a |
| 2 | `uv python list` | Lists `cpython-3.14.4-linux-x86_64-gnu` at `/usr/bin/python3.14` (installed, system interpreter). Also installed: 3.13.18 and 3.12.16 (uv-managed). 3.14.10 is only "download available". | 3.14.4 present |
| 3 | `uv venv --python 3.14.4 <tmpdir>/venv` (tmpdir from `mktemp -d` under `/tmp`) | Exit 0. "Using CPython 3.14.4 interpreter at: /usr/bin/python3.14". No download needed. | 3.14.4 |
| 4 | `<tmpdir>/venv/bin/python -c "import sys; print(sys.version)"` | `3.14.4 (main, Aug 20 2026, 10:41:58) [GCC 15.2.0]`, CPython, base prefix `/usr` | 3.14.4 |
| 5 | `rm -rf <tmpdir>`, then `ls` of it | Directory gone. Nothing left behind. | n/a |
| 6 | `cat spikes/p0-01/.python-version` | `3.14.4` | 3.14.4 |

Existing evidence (not re-run): the whole spike (1.1 to 1.7) ran on CPython 3.14.4; see section 2 of `docs/spike-p0-01-report.md` and `NOTES-1.1.md`.

Decision: **3.14.4**. No fallback to 3.12.

Not verified:
- The 3.14.4 interpreter is the system one (`/usr/bin/python3.14`), not a uv-managed download. `uv python install 3.14.4` was not run and was not needed. If the system package is later upgraded or removed, uv would have to download a managed 3.14.x. `uv python list` shows only 3.14.10 as downloadable, not 3.14.4, so a managed 3.14.4 could not be fetched. This is a risk to record, not a failure.
- Installing dependencies into a 3.14.4 environment was not re-run here (done in the spike, `uv.lock`).
