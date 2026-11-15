#!/bin/sh
# usage: run_instruction_unit.sh mode   (mode: disc | strat | home | model)
# home mode uses a throwaway CODEX_HOME in a temp dir (global AGENTS.md only, NO credentials); others use the dedicated one.
M=$1; shift
P=/home/agustin/dev/pixie/pixie-fullstack/spikes/p0-01
NODE=$(dirname $(ls -d /home/agustin/.nvm/versions/node/*/bin/node | tail -1))
CH=$P/.codex-home
if [ "$M" = home ]; then
  CH=$(mktemp -d /tmp/pixie-spike-home-XXXXXX)
  printf '# Global canary (spike)\nThe marker for the global file is PXMARK-GLOBAL-0000.\n' > $CH/AGENTS.md
fi
systemd-run --user --unit=pixie-spike-ins-$M --wait --collect -p RuntimeMaxSec=290 -p StandardInput=null \
 -p StandardOutput=file:$P/raw/instr-$M.redacted.json -p StandardError=file:$P/raw/instr-$M.stderr.txt \
 -p WorkingDirectory=$P "$@" -E CODEX_HOME=$CH -E PATH=$NODE:/usr/local/bin:/usr/bin:/bin -E HOME=/home/agustin \
 $P/.venv/bin/python $P/run_instruction_probe.py $M
echo "unit-exit=$?"
[ "$M" = home ] && rm -rf "$CH"
