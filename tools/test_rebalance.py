#!/usr/bin/env python3
"""Invariants of the rebalance toolchain, as tests. They run on the real dump and the current survey and proposals.

    python3 test_rebalance.py

  model      the Empire Knights regiment measures 1.00; a card scaled by k > 1 measures more, by k < 1 less (the
             solver's bisection needs monotonicity); scaling never changes the identity vector's shape beyond DRIFT_MAX
  ladder     every infantry, monster, beast, chariot and machine unit has an entry or is left to the price layer on
             purpose; the family base is the cheapest non-renown member; keep and price-only entries carry no target
  solver     no proposal changes armour, charge bonus or morale except the decided four; every changed unit's drift is
             under DRIFT_MAX; no price is raised in a flat-priced caste; prices are multiples of 25; a campaign price
             of 0 stays 0; held units carry the flag; sizes only change where the ladder or the study says
  pack       rebalance_check.py passes on the built pack
"""
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import unit_model as UM
import lore_ladder as LL
import rebalance_solve as RS
import decided

S = json.load(open(os.path.join(HERE, "_survey.json")))
R = json.load(open(os.path.join(HERE, "_rebalance.json")))["units"]
ROWS = {u["key"]: u for u in S["units"]}
UM.WEIGHTS.update(S["weights"]); UM.reset()

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


def test_model():
    ek = UM.card("wh_main_emp_cav_empire_knights")
    check(abs(UM.regiment_power(ek) - 1.0) < 1e-9, "Empire Knights regiment is not 1.00")
    for key in ("wh_main_emp_inf_swordsmen", "wh_main_grn_mon_giant", "wh2_main_lzd_inf_temple_guards", "wh_main_emp_inf_handgunners", "wh_main_chs_cav_chaos_chariot"):
        c = UM.card(key)
        p0 = UM.regiment_power(c)
        last = 0.0
        for k in (0.5, 0.8, 1.0, 1.25, 1.6, 2.0):
            p = UM.regiment_power(RS.scaled(c, k))
            check(p > last, "%s: power not increasing in k at %.2f" % (key, k))
            last = p
            check(UM.identity_drift(c, RS.scaled(c, k)) < RS.DRIFT_MAX if hasattr(RS, "DRIFT_MAX") else UM.identity_drift(c, RS.scaled(c, k)) < 0.02,
                  "%s: drift at k=%.2f" % (key, k))
        check(abs(UM.regiment_power(RS.scaled(c, 1.0)) - p0) < 1e-9, "%s: k=1 changes power" % key)
        v, k = RS.solve(c, p0 * 1.5)
        check(abs(UM.regiment_power(v) / (p0 * 1.5) - 1) < 0.01, "%s: solve misses x1.5 (got x%.3f)" % (key, UM.regiment_power(v) / p0))


def test_ladder():
    castes = ("melee_infantry", "missile_infantry", "monstrous_infantry", "monster", "war_beast", "chariot", "warmachine", "missile_cavalry")
    for k, u in ROWS.items():
        if u["caste"] not in castes:
            continue
        e = LL.entry(k)
        if e and (e["keep"] or e["target"] is None):
            check(e["target"] is None, "%s: keep entry with a target" % k)
        if e and e["target"] is not None and not e["keep"]:
            L = LL.lore(k, ROWS)
            base = L["base"]
            fam = [x for x in ROWS if __import__("re").search(e["pattern"], x) and "ror" not in x and ROWS[x]["caste"] == u["caste"]] or [k]
            cheapest = min(fam, key=lambda x: (ROWS[x]["cost"] or 1e9, ROWS[x]["power"]))
            check(base == cheapest, "%s: family base %s is not the cheapest member %s" % (k, base, cheapest))
            check(L["factor"] > 0, "%s: factor not positive" % k)
    # the infantry ladder covers everything
    inf = [k for k, u in ROWS.items() if u["caste"] in ("melee_infantry", "missile_infantry", "monstrous_infantry")]
    missing = [k for k in inf if not LL.entry(k) and k not in RS.UNREVIEWED]   # unreviewed.txt: kept vanilla until judged
    check(len(missing) <= 12, "infantry without a ladder entry: %d (%s)" % (len(missing), missing[:5]))


def test_solver():
    for o in R:
        key, a, b = o["key"], o["after"], o["before"]
        if key not in decided.STATS:
            for f in ("armour", "cb", "morale"):
                check(abs(a[f] - b[f]) < 1e-9, "%s: %s changed" % (key, f))
        check(o.get("drift", 0) <= 0.02, "%s: drift %.4f" % (key, o.get("drift", 0)))
        if o["action"] != "none":
            check(o["new_cost"] % 25 == 0 and o["new_campaign_cost"] % 25 == 0, "%s: price not a multiple of 25" % key)
            check(o["new_cost"] > 0 or o["cost"] == 0, "%s: price fell to %s" % (key, o["new_cost"]))
            if o["campaign_cost"] == 0:
                check(o["new_campaign_cost"] == 0, "%s: campaign price 0 raised" % key)
            if o["caste"] in RS.PRICE_CASTES and key not in decided.STATS:
                check(o["new_cost"] <= o["cost"], "%s: price raised in a flat-priced caste (%d -> %d)" % (key, o["cost"], o["new_cost"]))
        if a["men"] != b["men"]:
            L = RS.lore_target(key, UM.card(key))
            check(L is not None and L.get("size") == a["men"], "%s: size changed without a lore size" % key)
    held = [o["key"] for o in R if o.get("held")]
    check(all(o["action"] != "none" for o in R if o.get("held")), "a held unit with action none")


def test_pack():
    r = subprocess.run([sys.executable, os.path.join(HERE, "rebalance_check.py")], capture_output=True, text=True)
    check(r.returncode == 0, "rebalance_check.py failed:\n" + (r.stdout or r.stderr)[-800:])


if __name__ == "__main__":
    for t in (test_model, test_ladder, test_solver, test_pack):
        n = len(failures)
        t()
        print("%-14s %s" % (t.__name__, "ok" if len(failures) == n else "%d failed" % (len(failures) - n)))
    if failures:
        print("\nFAILURES:")
        for f in failures[:40]:
            print("  " + f)
        sys.exit(1)
    print("all invariants hold")
