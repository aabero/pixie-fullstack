#!/bin/sh
# usage: run_delegation_unit.sh case "prompt"
C=$1; PR=$2
P=/home/agustin/dev/pixie/pixie-fullstack/spikes/p0-01
NODE=$(dirname $(ls -d /home/agustin/.nvm/versions/node/*/bin/node | tail -1))
systemd-run --user --unit=pixie-spike-del-$C --wait --collect -p RuntimeMaxSec=290 -p StandardInput=null \
 -p StandardOutput=file:$P/raw/deleg-$C.redacted.json -p StandardError=file:$P/raw/deleg-$C.stderr.txt \
 -p WorkingDirectory=$P -E CODEX_HOME=$P/.codex-home -E PATH=$NODE:/usr/local/bin:/usr/bin:/bin -E HOME=/home/agustin \
 $P/.venv/bin/python $P/run_delegation_probe.py "$C" "$PR"
echo "unit-exit=$?"
