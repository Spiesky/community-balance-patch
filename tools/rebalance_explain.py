#!/usr/bin/env python3
"""One unit, end to end: its card, its measurement, its place on the price line, the ladder's word, the proposal,
and an equal-gold duel against its caste's reference before and after.

    python3 rebalance_explain.py wh2_main_lzd_inf_temple_guards
    python3 rebalance_explain.py "Temple Guard"          # by name (first match)
"""
import json
import os
import sys

import unit_model as UM
import lore_ladder as LL
import cavalry_sim as SIM

HERE = os.path.dirname(os.path.abspath(__file__))
S = json.load(open(os.path.join(HERE, "_survey.json")))
ROWS = {u["key"]: u for u in S["units"]}
R = {o["key"]: o for o in json.load(open(os.path.join(HERE, "_rebalance.json")))["units"]}
UM.WEIGHTS.update(S["weights"]); UM.reset()
CO = S["coefficients"]
REFERENCE = {"melee_infantry": "wh_main_chs_inf_chaos_warriors_0", "missile_infantry": "wh_main_chs_inf_chaos_warriors_0",
             "monstrous_infantry": "wh3_main_ogr_inf_ogres_0", "melee_cavalry": "wh_main_emp_cav_empire_knights",
             "missile_cavalry": "wh_main_emp_cav_empire_knights", "monstrous_cavalry": "wh_main_emp_cav_demigryph_knights_0",
             "monster": "wh_main_grn_mon_giant", "war_beast": "wh_main_vmp_mon_dire_wolves", "chariot": "wh_main_chs_cav_chaos_chariot",
             "warmachine": "wh_main_emp_art_great_cannon"}


def find(arg):
    if arg in ROWS:
        return arg
    for k, u in ROWS.items():
        if u["name"].lower() == arg.lower():
            return k
    for k, u in ROWS.items():
        if arg.lower() in u["name"].lower():
            return k
    return None


def after_card(key):
    c = UM.card(key)
    o = R.get(key)
    if not o or o["action"] == "none":
        return c, ROWS[key]["cost"]
    a = o["after"]
    return dict(c, men=a["men"], ma=a["ma"], md=a["md"], cb=a["cb"], hp=a["hp"], armour=a["armour"], morale=a["morale"],
                base=a["base"], ap=a["ap"], bvl=a["bvl"], bvi=a["bvi"]), o["new_cost"]


def main():
    key = find(" ".join(sys.argv[1:])) if len(sys.argv) > 1 else None
    if not key:
        print(__doc__); return 1
    u, c, o = ROWS[key], UM.card(key), R.get(key)
    pr = UM.profile(c)
    print("%s  (%s)  %s, %s, tier %s" % (u["name"], key, UM.FACTION_NAMES.get(u["faction"], u["faction"]), u["caste"].replace("_", " "), u["tier"]))
    print("  card      %d entities x %d crew, MA %.0f MD %.0f CB %.0f Ld %.0f, HP %.0f, armour %.0f, shield %.0f%%, speed %.1f, mass %.0f, radius %.2f" % (
        c["men"], c["crew"], c["ma"], c["md"], c["cb"], c["morale"], c["hp"], c["armour"], c["shield"], c["speed"], c["mass"], c["radius"]))
    print("  weapon    %.0f+%.0f vL+%.0f vI+%.0f, every %.1fs%s%s%s" % (c["base"], c["ap"], c["bvl"], c["bvi"], c["interval"],
          " splash %s x%.1f" % (c["splash_size"], c["splash_mult"]) if c["splash_size"] and c["splash_n"] > 1 else "", " magical" if c["magical"] else "", " flaming" if c["flaming"] else ""))
    if c["missile"]:
        m = c["missile"]
        print("  missile   %s: %.0f+%.0f x%.0f per volley, reload %.1fs, range %.0f, ammo %.0f, calibration %.1f%s" % (
            m["key"], m["base"], m["ap"], m["volley"], m["reload"], m["range"], m["ammo"], m["calibration"], (", explodes %.0f+%.0f r%.0f" % (m["ex_base"], m["ex_ap"], m["ex_radius"])) if m["ex_radius"] else ""))
    for m in c.get("ability_shots", []):
        print("  ability   %s: %.0f+%.0f x%.0f, %s uses, recharge %.0fs%s" % (m["ability"], m["base"], m["ap"], m["volley"] * m["n_proj"], m["uses"] if m["uses"] > 0 else "unlimited", m["recharge"], ", per entity" if m["per_entity"] else ""))
    attrs = [a for a in c["attrs"] if a != "hide_forest"]
    if attrs:
        print("  attributes " + ", ".join(attrs))
    print("  measure   melee dps %.1f (vs %s), ranged %.1f, impact %.1f, ability %.1f; lasts %.0fs in melee, %.0fs under fire" % (
        pr["off_melee"], " / ".join("%s %.0f" % (n[:5], v) for n, v in pr["offence"].items()), pr["off_ranged"], pr["off_impact"], pr["off_ability"], pr["tough_melee"], pr["tough_ranged"]))
    print("  power     regiment %.2f (Empire Knights = 1.00), per model %.2f" % (u["power_reg"], u["power"]))
    a, s = CO["intercept"] + CO.get("caste:" + u["caste"], 0.0), CO["log_power"] + CO.get("slope:" + u["caste"], 0.0)
    print("  price     %d multiplayer, %d campaign; the caste's line (slope %.2f) says %.0f is fair; residual %s%s" % (
        u["cost"], u["campaign_cost"], s, u["fair_cost"], ("%+.2f" % u["residual"]) if u["residual"] is not None else "n/a",
        (" (over-priced)" if (u["residual"] or 0) > 0.15 else " (a bargain)" if (u["residual"] or 0) < -0.15 else " (balanced)")))
    e = LL.entry(key)
    if e:
        L = LL.lore(key, ROWS)
        kind = "keep" if e["keep"] else ("price only" if e["target"] is None and e["price_add"] is None else ("price %+d" % e["price_add"] if e["price_add"] is not None else "target %.2f%s%s" % (e["target"], " (regiment)" if e["reg"] else " per model", ", size %d" % e["size"] if e["size"] else "")))
        print("  ladder    %s [%s]: %s%s" % (e["tier"] or "-", kind, e["note"], (" base %s, factor x%.2f" % (L.get("base", key), L["factor"])) if L and L["factor"] != 1.0 else ""))
    else:
        print("  ladder    no entry (the cavalry study or the price layer decides)")
    if o:
        b, aa = o["before"], o["after"]
        print("  proposal  %s: %s" % (o["action"], o["note"]))
        if o["action"] != "none":
            print("            men %d -> %d, MA/MD %.0f/%.0f -> %.0f/%.0f, HP %.0f -> %.0f, dmg %.0f+%.0f -> %.0f+%.0f, regiment %.2f -> %.2f, price %d -> %d (campaign %d -> %d), drift %.4f" % (
                b["men"], aa["men"], b["ma"], b["md"], aa["ma"], aa["md"], b["hp"], aa["hp"], b["base"], b["ap"], aa["base"], aa["ap"], o["power_reg"], aa["power_reg"], o["cost"], o["new_cost"], o["campaign_cost"], o["new_campaign_cost"], o.get("drift", 0)))
    ref = REFERENCE.get(u["caste"])
    if ref and ref != key and u["cost"]:
        rv = UM.card(ref)
        rb, cb = after_card(ref)
        ra, ca = after_card(key)
        for label, A, costA, B, costB in (("vanilla", c, u["cost"], rv, ROWS[ref]["cost"]), ("rebalanced", ra, ca, rb, cb)):
            r = SIM.equal_gold(dict(A, cost=costA), dict(B, cost=costB))
            if r:
                who = A["label"] if r["winner"] == "A" else B["label"]
                left = r["left_a"] if r["winner"] == "A" else r["left_b"]
                print("  duel      %-10s vs %s at equal gold: %s wins by %s with %.0f%% left after %.0fs" % (label, rv["label"], who, r["how"], left * 100, r["time"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
