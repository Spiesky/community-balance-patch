#!/usr/bin/env python3
"""Test bench for one unit's design: fight a variant against a set of opponents at equal gold.

    python3 unit_lab.py UNIT_KEY [--set FIELD=V ...] [--vs KEY,KEY,...] [--opp KEY:FIELD=V ...] [--db DIR]

FIELD is a unit_model.card() field (men, hp, ma, md, cb, base, ap, bvl, bvi, armour, ward, res_physical, res_magic,
res_missile, magical, mass, speed, cost, ...). V is a number, true/false, or *X to multiply the current value
(hp=*2.0). --set changes the unit under test, --opp changes one opponent (repeatable). --db points at a database
folder (default: vanilla_db; CBP_DB works too). Opponents are scaled to the tested unit's gold: an opponent costing
half as much fields twice the models. One head-on fight each (cavalry_sim.fight: charge, melee, morale, The Hunger
style healing, abilities the sim reads); terrain, flanking and on-hit contact effects are not modelled.
"""
import os
import sys

args = sys.argv[1:]
if "--db" in args:
    i = args.index("--db")
    os.environ["CBP_DB"] = os.path.abspath(args[i + 1])
    del args[i:i + 2]

import unit_model as M          # noqa: E402  (reads CBP_DB at import)
import cavalry_sim as S         # noqa: E402

DEFAULT_VS = [
    "wh_main_brt_cav_grail_knights", "wh_dlc07_brt_cav_grail_guardians_0", "wh_main_emp_cav_reiksguard",
    "wh_main_emp_cav_demigryph_knights_0", "wh_main_chs_cav_chaos_knights_0", "wh_pro04_chs_cav_chaos_knights_ror_0",
    "wh_dlc02_vmp_cav_blood_knights_0", "wh3_main_vmp_blood_knights_sword_shield", "wh_main_vmp_cav_hexwraiths",
    "wh_main_grn_inf_black_orcs", "wh2_main_hef_inf_phoenix_guard", "wh_main_chs_inf_chosen_0",
    "wh2_main_skv_inf_skavenslaves_0", "wh_main_grn_mon_giant",
]


def value(cur, v):
    if v.lower() in ("true", "false"):
        return v.lower() == "true"
    if v.startswith("*"):
        return cur * float(v[1:])
    return float(v)


def apply(card, sets):
    c = dict(card)
    for s in sets:
        k, v = s.split("=", 1)
        if k not in c:
            sys.exit("unknown card field %r (fields: %s)" % (k, ", ".join(sorted(c))))
        c[k] = value(c[k], v)
    c["men"] = int(round(c["men"]))
    return c


def main():
    if not args or args[0].startswith("-"):
        sys.exit(__doc__)
    unit, sets, vs, opp = args[0], [], DEFAULT_VS, {}
    i = 1
    while i < len(args):
        a = args[i]
        if a == "--set":
            sets.append(args[i + 1]); i += 2
        elif a == "--vs":
            vs = args[i + 1].split(","); i += 2
        elif a == "--opp":
            k, s = args[i + 1].split(":", 1)
            opp.setdefault(k, []).append(s); i += 2
        else:
            sys.exit("unknown argument %r" % a)
    me = apply(M.card(unit), sets)
    print("%s: %d x %.0f hp, MA %.0f MD %.0f CB %.0f, dmg %.0f+%.0f, armour %.0f, ward %.0f phys %.0f, magical %s, %d gold"
          % (me["label"], me["men"], me["hp"], me["ma"], me["md"], me["cb"], me["base"], me["ap"], me["armour"],
             me["ward"], me["res_physical"], me["magical"], me["cost"]))
    for k in vs:
        if k == unit:
            continue
        try:
            o = apply(M.card(k), opp.get(k, []))
        except KeyError:
            print("  %-45s not in this database" % k)
            continue
        scale = me["cost"] / o["cost"] if o["cost"] else 1.0
        o = dict(o, men=max(1, int(round(o["men"] * scale))))
        r = S.fight(me, o)
        if r["winner"] == "A":
            res = "WIN  %3.0f%% left" % (100 * r["left_a"])
        elif r["winner"] == "B":
            res = "LOSS (they keep %3.0f%%)" % (100 * r["left_b"])
        else:
            res = "draw (%3.0f%% / %3.0f%%)" % (100 * r["left_a"], 100 * r["left_b"])
        print("  vs %-45s x%-4d %-26s %5.1fs %s" % (o["label"][:45], o["men"], res, r["time"], r.get("how", "")))


if __name__ == "__main__":
    main()
