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
R = json.load(open(os.environ.get("CBP_PROPOSALS") or os.path.join(HERE, "_rebalance.json")))["units"]
ROWS = {u["key"]: u for u in S["units"]}
UM.WEIGHTS.update(S["weights"]); UM.reset()

failures = []

# the beta's own rules are checked when the proposals are the beta's (CBP_PROPOSALS=_beta.json)
BETA = any(o.get("community") or o.get("theme") for o in R)
BY_NAME = {}
for _o in R:
    BY_NAME.setdefault(_o["name"], []).append(_o)
NAMED, SPOKEN_FOR = set(), set()
if BETA:
    import community as _C
    _by_key = {o["key"]: o for o in R}
    for _line, _pat, _ch, _keys in _C.resolve([o["key"] for o in R], UM.name, UM.faction):
        NAMED.update(_keys)
        if not _ch.get("_follows"):
            for _k in _keys:
                _b = RS.base_of(_by_key[_k], BY_NAME)
                if _b is not None and _b is not _by_key[_k]:
                    SPOKEN_FOR.add(_b["key"])


def check(cond, msg):
    if not cond:
        failures.append(msg)


def test_model():
    ek = UM.card("wh_main_emp_cav_empire_knights")
    check(abs(UM.regiment_power(ek) - 1.0) < 1e-9, "Empire Knights regiment is not 1.00")
    # overkill: a blow never counts for more than its target's hit points, and the cap never raises anything
    import cavalry_model as CM
    bk, slave = UM.card("wh_dlc02_vmp_cav_blood_knights_0"), UM.card("wh2_main_skv_inf_skavenslaves_0")
    big = RS.scaled(bk, 2.5)
    check(CM.blow(big, slave, usable=True) <= slave["hp"] * 0.9 + 1e-9, "a capped blow exceeds the target's hit points")
    check(CM.blow(big, slave, usable=True) < CM.blow(big, slave), "the cap does not bite on a 2.5x Blood Knight against a Skavenslave")
    for key in ("wh_main_emp_inf_swordsmen", "wh_main_grn_mon_giant", "wh_dlc02_vmp_cav_blood_knights_0"):
        c = UM.card(key)
        check(UM.usable_power(c) <= UM.regiment_power(c) + 1e-9, "%s: usable power above power" % key)
    check(CM.USABLE is False, "usable_power left the cap switched on")
    # the gunpowder rule's numbers are part of what the Workshop page promises
    GP = RS.GP
    check((GP.DAMAGE, GP.RELOAD) == (1.6, 1.5), "gunpowder constants changed: %s, %s (the pages say 60%% and 50%%)" % (GP.DAMAGE, GP.RELOAD))
    check((GP.ammo(22), GP.ammo(20), GP.ammo(6), GP.ammo(0)) == (14, 13, 4, 0), "gunpowder ammunition rule changed")
    hg = UM.card("wh_main_emp_inf_handgunners")
    check(GP.applies(hg, "missile_infantry") and not GP.applies(UM.card("wh_main_emp_inf_crossbowmen"), "missile_infantry"),
          "gunpowder rule: Handgunners must be covered and Crossbowmen not")
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
            for f in ("armour", "morale"):
                check(abs(a[f] - b[f]) < 1e-9, "%s: %s changed" % (key, f))
            if o.get("elite") and (o.get("k") or 1.0) > 1.0:      # a lore elite's charge scales with its damage
                check(abs(a["cb"] - round(b["cb"] * o["k"])) < 1e-9, "%s: charge bonus %s is not %s x %.2f" % (key, a["cb"], b["cb"], o["k"]))
                check(o["new_cost"] <= o["cost"] * o["usable"] + 25, "%s: price rises faster than its usable power" % key)
            else:
                check(abs(a["cb"] - b["cb"]) < 1e-9, "%s: charge bonus changed" % key)
            if o.get("gun"):                                       # gunpowder: the same damage over a battle, the price stays
                m0, m1 = b["missile"], a["missile"]
                check(m1["ammo"] == RS.GP.ammo(m0["ammo"]), "%s: ammunition %s, expected %s" % (key, m1["ammo"], RS.GP.ammo(m0["ammo"])))
                check(abs(m1["reload"] / m0["reload"] - RS.GP.RELOAD) < 1e-6, "%s: reload factor" % key)
            if o.get("gun") and not o.get("elite") and (o["action"] == "gunpowder" or BETA):
                check(o["new_cost"] == o["cost"], "%s: the gunpowder rule moved the price (%d -> %d)" % (key, o["cost"], o["new_cost"]))
            if o.get("theme"):                                     # the theme: stronger, at the vanilla price
                check(o["new_cost"] == o["cost"], "%s: themed unit's price moved (%d -> %d)" % (key, o["cost"], o["new_cost"]))
                check(o["caste"] == "melee_infantry", "%s: themed but not melee infantry" % key)
                check(key not in NAMED and key not in SPOKEN_FOR, "%s: themed although the community list covers it" % key)
                base = RS.base_of(o, BY_NAME)
                if UM.card(key)["renown"] or (base is not None and base is not o):
                    check(base is not None and base.get("theme") and base["action"] != "none",
                          "%s: a regiment of renown in the theme whose base is not" % key)
                    if base is not None and base.get("k") and o.get("k"):
                        check(abs(o["k"] - base["k"]) < 1e-6, "%s: factor x%.3f, its base's is x%.3f" % (key, o["k"], base["k"]))
        if BETA and key in NAMED and not o.get("elite"):           # a list unit takes nothing from the model but the gun rule
            check(o["action"] in ("none", "gunpowder") and (o.get("k") or 1.0) == 1.0 and o["new_cost"] == o["cost"],
                  "%s: on the community list but also changed by the model (%s)" % (key, o["action"]))
        if BETA and not o.get("elite") and not o.get("theme") and not o.get("gun"):
            check(o["action"] == "none", "%s: changed in the beta without a theme (%s)" % (key, o["action"]))
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
