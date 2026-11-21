#!/bin/sh
# usage: run_approval_nb_unit.sh mode   (task 3.1; transient user unit, dedicated CODEX_HOME)
M=$1; shift
P=/home/agustin/dev/pixie/pixie-fullstack/spikes/p0-01
NODE=$(dirname $(ls -d /home/agustin/.nvm/versions/node/*/bin/node | tail -1))
systemd-run --user --unit=pixie-spike-nb-$M --wait --collect -p RuntimeMaxSec=290 -p StandardInput=null \
 -p StandardOutput=file:$P/raw/nb-$M.redacted.json -p StandardError=file:$P/raw/nb-$M.stderr.txt \
 -p WorkingDirectory=$P "$@" -E CODEX_HOME=$P/.codex-home -E PATH=$NODE:/usr/local/bin:/usr/bin:/bin -E HOME=/home/agustin \
 $P/.venv/bin/python $P/run_approval_nb_probe.py $M
