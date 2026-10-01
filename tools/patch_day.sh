#!/bin/bash
# Patch day: CA updated the game (or the patch's rules changed). Re-read the game's data, rebuild the beta on the new
# numbers, run every check, and regenerate the pages that describe the pack. One command; it stops at the first check
# that fails and shows why.
#
#   tools/patch_day.sh                 everything
#   tools/patch_day.sh --no-refresh    skip re-reading the game's packs (vanilla_db/ is already current)
#
# Needs python3 with numpy, zstandard and lz4 (tools/requirements.txt), RPFM's WH3 schema (CBP_SCHEMA) and, unless
# --no-refresh, the installed game (CBP_GAME, the folder that holds data/db.pack). CBP_PYTHON picks the interpreter.
#
# What comes out:
#   build/beta/community_balance_patch.pack    the Workshop pack (VERSION is stamped into it)
#   build/cbp_autoresolve_test.pack            the optional auto-resolve test pack (not part of the patch)
#   reports/beta_changelog.md                  what the Workshop pack changes, unit by unit
#   reports/changelog.md, proposals.md, survey.md, ladder.md   the whole draft
# Read the "changed:" lines (tables CA touched) and the check results before anything ships, then follow
# docs/RELEASING.md.
set -euo pipefail
cd "$(dirname "$0")"
# the build decides its own inputs: a CBP_ variable left over in the shell must not change what ships
unset CBP_AUTORESOLVE CBP_BETA CBP_CHANGELOG CBP_COMMUNITY CBP_COMMUNITY_LOG CBP_OUT CBP_PROPOSALS CBP_AR_OUT CBP_LOGGER_OUT
case "${1:-}" in
    ""|--no-refresh) ;;
    *) echo "usage: tools/patch_day.sh [--no-refresh]"; exit 2 ;;
esac
if [ -n "${CBP_PYTHON:-}" ]; then PY="$CBP_PYTHON"
elif [ -x "$HOME/Tools/venvs/wh3/bin/python" ]; then PY="$HOME/Tools/venvs/wh3/bin/python"
else PY=python3; fi
LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

# run a step, keep its last lines, and stop with the whole output if it fails (a pipe to tail would hide the failure)
step() {
    local lines="$1"; shift
    echo "== $*"
    if ! "$@" > "$LOG" 2>&1; then
        cat "$LOG"
        echo "FAILED: $*"
        exit 1
    fi
    tail -n "$lines" "$LOG" | sed 's/^/   /'
}

VERSION="$(cat ../VERSION)"
grep -q "^## $VERSION\( \|\$\)" ../CHANGELOG.md || { echo "CHANGELOG.md has no '## $VERSION' entry: write it first (docs/RELEASING.md)"; exit 1; }
rm -f ../build/beta/CHECKED                  # only a run that passes every check stamps the pack for upload
OUT="$PWD/../build/beta/community_balance_patch.pack"
mkdir -p ../build/beta ../build/check

if [ "${1:-}" != "--no-refresh" ]; then
    step 40 "$PY" refresh_vanilla.py
fi
step 2  "$PY" rebalance_survey.py           # the measurements the solver reads: stale after a CA patch otherwise
step 9  "$PY" rebalance_solve.py
step 2  "$PY" community.py                  # every list entry still names the units on record (community_resolved.json)

export CBP_PROPOSALS="$PWD/_beta.json"
step 3  env CBP_COMMUNITY=1 CBP_OUT="$OUT" "$PY" build_rebalance.py
step 1  "$PY" refcheck.py "$OUT"
step 8  "$PY" sense_check.py
step 2  "$PY" community_check.py            # builds build/check/without.pack and with.pack
step 1  env CBP_OUT="$PWD/../build/check/without.pack" "$PY" rebalance_check.py
step 5  env CBP_OUT="$PWD/../build/check/without.pack" "$PY" test_rebalance.py
step 2  "$PY" test_logs.py
step 1  "$PY" ../logger/tests/run_mock.py   # the Battle Logger against mock game objects, in Lua 5.1 (needs lupa)
step 1  "$PY" build_logger.py
step 2  "$PY" autoresolve_rules.py          # the test pack, on its own

step 1  env CBP_BETA=1 CBP_CHANGELOG="$PWD/../reports/beta_changelog.md" "$PY" rebalance_changelog.py
step 1  "$PY" unit_pages.py                 # the numbers on units/*.md and the auto-resolve page
unset CBP_PROPOSALS
step 1  "$PY" rebalance_changelog.py
step 1  "$PY" rebalance_ladder_view.py
step 4  "$PY" workshop_text.py              # the Workshop descriptions and change notes, from this build's numbers
step 1  "$PY" final_check.py "$OUT"         # the file that gets uploaded is the build the checks verified; stamps it

echo
echo "built $OUT (version $VERSION)"
echo "pages that changed (commit them with the release):"
git -C .. status --short reports units docs | sed 's/^/   /' || true
