#!/bin/sh
# Patch day: CA updated the game. Re-read its data, rebuild the patch on the new numbers, run every check.
#   ./patch_day.sh
# Then read the "changed:" lines (tables CA touched) and the check results before anything ships.
set -e
cd "$(dirname "$0")"
PY="${CBP_PYTHON:-$HOME/Tools/venvs/wh3/bin/python}"
"$PY" refresh_vanilla.py
"$PY" rebalance_solve.py | tail -4
export CBP_PROPOSALS="$PWD/_beta.json"
OUT="$PWD/../build/beta/community_balance_patch.pack"
CBP_COMMUNITY=1 CBP_OUT="$OUT" "$PY" build_rebalance.py | tail -2
"$PY" refcheck.py "$OUT" | tail -1
"$PY" sense_check.py | tail -1
"$PY" community_check.py | tail -2
echo "built $OUT"
