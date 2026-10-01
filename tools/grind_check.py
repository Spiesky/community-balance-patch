#!/usr/bin/env python3
"""Elites against chaff: how many chaff models an elite unit kills for every model it loses, vanilla and patched.

The question: how long can an elite unit keep grinding chaff, and how fast does it clear it? Worst case:
the chaff never routs and keeps coming. Each elite model is fought by REACH chaff models at once (the ones that fit
around it); every model's damage is the game's melee formula (cavalry_model.blow) on the simulator's effective cards,
passives included, no charges (a grind is sustained melee). A blow kills at most the models it can reach (one, or a
splash attack's few): damage beyond a chaff model's hit points is overkill and counts for nothing.

Two figures per unit: chaff killed for every elite model lost (how long the unit can keep it up), and chaff killed per
minute by the whole unit (how fast). Fewer, stronger models do better on the first and worse on the second.

    python3 grind_check.py
"""
import json, os
import unit_model as UM
import cavalry_model as M
import cavalry_sim as SIM
import rebalance_verify as RV

REACH = {"cavalry": 4.0, "infantry": 2.5}
ELITES = ["wh_main_brt_cav_grail_knights", "wh_dlc07_brt_cav_grail_guardians_0", "wh3_main_vmp_blood_knights_sword_shield",
          "wh_dlc02_vmp_cav_blood_knights_0", "wh_pro04_chs_cav_chaos_knights_ror_0", "wh_main_chs_cav_chaos_knights_0",
          "wh_main_emp_cav_reiksguard", "wh_main_emp_cav_demigryph_knights_0", "wh_main_chs_inf_chosen_0",
          "wh_main_chs_inf_chaos_warriors_0", "wh_main_emp_inf_greatswords", "wh2_main_lzd_inf_temple_guards",
          "wh2_main_hef_inf_phoenix_guard", "wh_main_dwf_inf_ironbreakers"]
CHAFF = ["wh2_main_skv_inf_skavenslaves_0", "wh_main_vmp_inf_zombie"]


def eff(card, other):
    return SIM.effective(SIM.Side(card), SIM.Side(other), 1.0, False)


def ratio(elite, chaff):
    e, c = eff(elite, chaff), eff(chaff, elite)
    kill = M.blow(e, c, usable=True) / e["interval"] / chaff["hp"]        # chaff models one elite model kills per second
    reach = REACH["cavalry" if "cav" in elite["key"] or elite.get("mount") else "infantry"]
    lose = reach * M.blow(c, e) / c["interval"] / elite["hp"]             # elite models lost per elite model per second
    return (kill / lose if lose > 0 else float("inf")), kill * 60.0 * elite["men"]


def main():
    for ck in CHAFF:
        if ck not in UM.LU:
            continue
        chaff = UM.card(ck)
        print("\nagainst %s (%d models, %.0f HP each): chaff killed per elite model lost, and per minute by the whole unit" % (chaff["label"], chaff["men"], chaff["hp"]))
        for k in ELITES:
            if k not in UM.LU:
                continue
            v, _ = UM.card(k), None
            p, _ = RV.after(k)
            (rv, mv), (rp, mp) = ratio(v, chaff), ratio(p, chaff)
            print("   %-34s vanilla %6.1f per model lost, %4.0f a minute   patched %6.1f per model lost, %4.0f a minute" % (
                v["label"][:34], rv, mv, rp, mp))


if __name__ == "__main__":
    main()
