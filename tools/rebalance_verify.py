#!/usr/bin/env python3
"""Check the proposals with the regiment simulator: equal-gold duels before and after, on landmark matchups.

    python3 rebalance_verify.py            the landmark matchups
    python3 rebalance_verify.py --sweep    every changed unit against its caste's reference, largest swings first

cavalry_sim.fight runs two regiments against each other second by second with the game's rules and constants
(abilities, fatigue, morale, crumbling). Here each pair fights twice: vanilla against vanilla, and rebalanced against
rebalanced, with B scaled to A's gold in both. A balanced pair ends near 50/50 or with the winner leaving little behind;
a matchup that was lopsided and stays lopsided is a unit that counters the other by design, which the identity rule
protects. Nothing here changes the proposals; it is a second opinion from a different model.
"""
import json
import os
import sys

import unit_model as UM
import cavalry_sim as SIM

HERE = os.path.dirname(os.path.abspath(__file__))
R = {o["key"]: o for o in json.load(open(os.path.join(HERE, "_rebalance.json")))["units"]}
S = json.load(open(os.path.join(HERE, "_survey.json")))
UM.WEIGHTS.update(S["weights"])
UM.reset()

PAIRS = [
    ("wh_main_brt_cav_grail_knights", "wh_main_chs_cav_chaos_knights_0"),
    ("wh_dlc02_vmp_cav_blood_knights_0", "wh_main_emp_cav_demigryph_knights_0"),
    ("wh_main_emp_cav_reiksguard", "wh_main_brt_cav_knights_of_the_realm"),
    ("wh_main_emp_inf_greatswords", "wh_main_chs_inf_chaos_warriors_0"),
    ("wh_main_emp_inf_swordsmen", "wh2_main_skv_inf_clanrats_0"),
    ("wh_main_emp_inf_halberdiers", "wh_main_emp_cav_empire_knights"),
    ("wh_main_chs_inf_chosen_0", "wh_main_dwf_inf_ironbreakers"),
    ("wh_main_emp_cav_empire_knights", "wh2_main_hef_cav_silver_helms_0"),
    ("wh2_main_lzd_inf_temple_guards", "wh_main_chs_inf_chaos_warriors_0"),
    ("wh2_main_hef_inf_phoenix_guard", "wh2_main_def_inf_black_guard_0"),
    ("wh_main_chs_inf_chaos_warriors_0", "wh_main_dwf_inf_longbeards"),
    ("wh3_main_kho_mon_bloodthirster_0", "wh_main_grn_mon_giant"),
    ("wh2_dlc13_lzd_mon_dread_saurian_1", "wh2_main_hef_mon_star_dragon"),
]


def after(key):
    """the card as the proposal leaves it"""
    c = UM.card(key)
    o = R.get(key)
    if not o or o["action"] == "none":
        return c, o["cost"] if o else c["cost"]
    a = o["after"]
    c = dict(c, men=a["men"], ma=a["ma"], md=a["md"], cb=a["cb"], hp=a["hp"], armour=a["armour"], morale=a["morale"],
             base=a["base"], ap=a["ap"], bvl=a["bvl"], bvi=a["bvi"])
    return c, o["new_cost"]


def duel(ca, cost_a, cb, cost_b):
    a, b = dict(ca, cost=cost_a), dict(cb, cost=cost_b)
    r = SIM.equal_gold(a, b)
    if r is None:
        return "n/a"
    who = a["label"] if r["winner"] == "A" else b["label"]
    left = r["left_a"] if r["winner"] == "A" else r["left_b"]
    return "%s wins by %s, %.0f%% left, %.0fs" % (who[:24], r["how"], left * 100, r["time"])


REFERENCE = {                        # the caste's yardstick for the sweep
    "melee_infantry": "wh_main_chs_inf_chaos_warriors_0", "missile_infantry": "wh_main_chs_inf_chaos_warriors_0",
    "monstrous_infantry": "wh3_main_ogr_inf_ogres_0", "melee_cavalry": "wh_main_emp_cav_empire_knights",
    "missile_cavalry": "wh_main_emp_cav_empire_knights", "monstrous_cavalry": "wh_main_emp_cav_demigryph_knights_0",
    "monster": "wh_main_grn_mon_giant", "war_beast": "wh_main_vmp_mon_dire_wolves", "chariot": "wh_main_chs_cav_chaos_chariot",
}


def margin(ca, cost_a, cb, cost_b):
    """A's share of its own strength left minus B's, from -1 to 1, at equal gold; None where the sim cannot price it"""
    a, b = dict(ca, cost=cost_a), dict(cb, cost=cost_b)
    r = SIM.equal_gold(a, b)
    if r is None:
        return None
    return r["left_a"] - r["left_b"]


def sweep():
    """every changed unit against its caste's reference, vanilla and rebalanced; the largest swings first"""
    out = []
    for key, o in R.items():
        if o["action"] == "none" or o.get("held") or o["caste"] not in REFERENCE:
            continue
        ref = REFERENCE[o["caste"]]
        if ref == key:
            continue
        va, vb = UM.card(key), UM.card(ref)
        ra, ca = after(key)
        rb, cb = after(ref)
        m0 = margin(va, int(UM.MU[key]["multiplayer_cost"]), vb, int(UM.MU[ref]["multiplayer_cost"]))
        m1 = margin(ra, ca, rb, cb)
        if m0 is None or m1 is None:
            continue
        out.append((m1 - m0, m0, m1, o))
    out.sort(key=lambda t: -abs(t[0]))
    print("%-44s %-8s %-18s %8s %8s %7s" % ("unit (vs caste reference, equal gold)", "action", "power", "vanilla", "rebal.", "swing"))
    for swing, m0, m1, o in out[:40]:
        print("%-44s %-8s x%-17.2f %+8.2f %+8.2f %+7.2f" % (o["name"][:44], o["action"][:8], o["after"]["power_reg"] / o["power_reg"] if o["power_reg"] else 1, m0, m1, swing))
    flips = [(o, m0, m1) for _, m0, m1, o in out if m0 < -0.3 and m1 > 0.3]
    print("\n%d units checked; %d flip from losing clearly to winning clearly:" % (len(out), len(flips)))
    for o, m0, m1 in flips:
        print("   %-44s %+.2f -> %+.2f" % (o["name"][:44], m0, m1))


def main():
    if "--sweep" in sys.argv:
        return sweep()
    print("%-26s vs %-26s | %-58s | %s" % ("A", "B (scaled to A's gold)", "vanilla", "rebalanced"))
    for ka, kb in PAIRS:
        va, vb = UM.card(ka), UM.card(kb)
        ra, ca = after(ka)
        rb, cb = after(kb)
        print("%-26s vs %-26s | %-58s | %s" % (va["label"][:26], vb["label"][:26],
              duel(va, int(UM.MU[ka]["multiplayer_cost"]), vb, int(UM.MU[kb]["multiplayer_cost"])), duel(ra, ca, rb, cb)))


if __name__ == "__main__":
    main()
