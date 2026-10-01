#!/usr/bin/env python3
"""The last check, on the very file that gets uploaded.

    python3 final_check.py [pack]          default ../build/beta/community_balance_patch.pack

Every other check reads a pack it built itself (build/check/without.pack, with.pack). This one reads the Workshop pack
and requires: the same rows, table by table, as build/check/with.pack, the build community_check.py has just verified
(only the tables' random ids may differ); the version entry, exactly; every table at the game's version; no autoresolver
table. When all of that holds it writes build/beta/CHECKED (the pack's sha256 and the version), which tools/upload.sh
requires. Run by tools/patch_day.sh after every other check has passed.
"""
import hashlib
import os
import sys

import gamever
from packread import Pack
from dbread import decode
from rebalance_check import version_problems

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PACK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "beta", "community_balance_patch.pack")
CHECKED = os.path.join(ROOT, "build", "check", "with.pack")


def tables(pack):
    out = {}
    for n, _, _ in pack.entries:
        if n.startswith("db/"):
            ver, cols, rows = decode(pack.get(n), n.split("/")[1])
            out[n] = (ver, rows)
    return out


def main():
    stamp = os.path.join(os.path.dirname(PACK), "CHECKED")
    if os.path.exists(stamp):
        os.remove(stamp)                       # a failed run must not leave an old stamp behind
    fails = []
    pack, ref = Pack(PACK), Pack(CHECKED)
    a, b = tables(pack), tables(ref)
    for n in sorted(set(a) | set(b)):
        if n not in a or n not in b:
            fails.append("%s is only in %s" % (n, "the Workshop pack" if n in a else "the checked build"))
        elif a[n] != b[n]:
            diff = sum(1 for x, y in zip(a[n][1], b[n][1]) if x != y) + abs(len(a[n][1]) - len(b[n][1]))
            fails.append("%s differs from the checked build in %d rows" % (n, diff))
    for n, (ver, rows) in a.items():
        want = gamever.ver(n.split("/")[1])
        if want is not None and ver != want:
            fails.append("%s is at version %s, the game is on %s" % (n, ver, want))
    others = sorted(n for n, _, _ in pack.entries if not n.startswith("db/") and n != "text/db/community_balance_patch.loc")
    if others:
        fails.append("files that should not be in the pack: %s" % others)
    if any("autoresolver" in n for n, _, _ in pack.entries):
        fails.append("autoresolver tables are in the Workshop pack; they belong in the test pack")
    fails += version_problems(pack)
    if fails:
        print("FAIL: %s is not the build the checks verified" % os.path.basename(PACK))
        for f in fails:
            print("   " + f)
        return 1
    digest = hashlib.sha256(open(PACK, "rb").read()).hexdigest()
    version = open(os.path.join(ROOT, "VERSION")).read().strip()
    open(stamp, "w").write("%s  %s\n" % (digest, version))
    print("PASS: %s is the checked build, %d tables, version %s; stamped for upload" % (os.path.basename(PACK), len(a), version))
    return 0


if __name__ == "__main__":
    sys.exit(main())
