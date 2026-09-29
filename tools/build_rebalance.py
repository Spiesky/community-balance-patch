#!/usr/bin/env python3
"""Build the rebalance pack from the solver's proposals.

    python3 rebalance_survey.py && python3 rebalance_solve.py && python3 build_rebalance.py
                                                            -> ../build/community_balance_patch.pack

What goes in, per changed unit (from _rebalance.json, written by rebalance_solve.py):

  land_units      melee_attack, melee_defence and bonus_hit_points moved by the proposal's delta against the vanilla
                  row (never the model's absolute figure: the model folds permanent passives in), num_mounts where the
                  unit size changes, morale / charge_bonus / armour for the decided four, primary_melee_weapon and
                  primary_missile_weapon pointed at the land unit's own copies where damage moves. A land unit shared
                  by several main units is written once, and only if every sharer agrees.
  melee_weapons   a copy of the unit's weapon under the land unit's key with damage, AP, bonus vs large and vs infantry
                  multiplied by the proposal's factor k. Weapons are shared between units (six units swing wh_main_emp_sword), so a shared row is
                  never edited: every unit whose damage moves gets its own.
  projectiles     the same for the projectile, and a missile_weapons row pointing at it, where the unit shoots; a
                  unit's alternate ammunition (unit_missile_weapon_junctions) is copied and scaled the same way, with
                  the vanilla junction row overridden by its id
  main_units      multiplayer_cost, recruitment_cost (0 stays 0: Tomb Kings pay in other ways), upkeep_cost, num_men

The decided units (decided.STATS) are written from STATS as they are.
The pack stands on its own. Check it with refcheck.py and rebalance_check.py, and read docs/METHOD.md before
trusting any number in it.
"""
import json
import os
import sys

import vanilla as V
import gamever
import packwrite
from decided import STATS, coerce

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("CBP_OUT", os.path.join(os.path.dirname(HERE), "build", "community_balance_patch.pack"))
PROPOSALS = os.path.join(HERE, "_rebalance.json")
PREFIX = "gr_"                     # the great rebalance's own keys


def main():
    LU = V.index("land_units")
    MU = V.index("main_units", "unit")
    MW = V.index("melee_weapons")
    MIS = V.index("missile_weapons")
    PJ = V.index("projectiles")
    BE = V.index("battle_entities")
    MO = V.index("mounts")
    ENG = V.index("battlefield_engines")
    ARMOUR = {r["key"] for r in V.table("unit_armour_types")}
    ALT = {}
    for r in V.table("unit_missile_weapon_junctions"):
        ALT.setdefault(r["unit"], []).append(r)
    props = json.load(open(PROPOSALS))["units"]
    only = {a for a in sys.argv[1:] if not a.startswith("--")}

    land, main_rows, weapons, missiles, projectiles, junctions = [], [], [], [], [], []
    counts = dict(units=0, weapons=0, projectiles=0, alternates=0, resized=0, priced=0, held=0)
    include_review = "--include-review" in sys.argv

    # Everything is written as a change against the vanilla row, never as the model's absolute figure: the model's card
    # folds permanent passives into attack, defence and damage (Swords of Ulric read 44 attack, the database says 34),
    # so an absolute write would count the passive twice. Attack, defence and HP move by the proposal's delta; every
    # damage figure by the proposal's factor k.
    def deltas(o):
        a, b = o["after"], o["before"]
        return dict(k=o.get("k") or 1.0, dma=round(a["ma"] - b["ma"]), dmd=round(a["md"] - b["md"]), dhp=round(a["hp"] - b["hp"]),
                    men=(a["men"] if a["men"] != b["men"] else None), missile=bool(a.get("missile") and b.get("missile")))

    # Some main units share one land_units row (the Ghorgon and Khorne's, Throgg's trolls and Chaos's). The row is
    # written once, and only if every sharer the pack touches agrees on the change.
    by_land = {}
    for o in props:
        if o["action"] == "none" or (only and o["key"] not in only) or (o.get("held") and not include_review):
            continue
        by_land.setdefault(MU[o["key"]]["land_unit"], []).append(o)
    for lukey, os_ in by_land.items():
        if len(os_) > 1 and any(o["key"] in STATS for o in os_):
            raise SystemExit("%s: a decided unit shares its land unit with %s" % (lukey, [o["key"] for o in os_]))
        ds = {json.dumps(deltas(o), sort_keys=True) for o in os_ if o["key"] not in STATS}
        if len(ds) > 1:
            raise SystemExit("%s: main units sharing this land unit disagree: %s" % (lukey, [(o["key"], deltas(o)) for o in os_]))
    for o in props:
        if o["action"] == "none" or (only and o["key"] not in only):
            continue
        if o.get("held") and not include_review:
            counts["held"] += 1
            continue
        key = o["key"]
        if key not in MU or MU[key]["land_unit"] not in LU:
            raise SystemExit("not a vanilla unit: %s" % key)
        lukey = MU[key]["land_unit"]
        others = [x["key"] for x in props if x["key"] != key and MU[x["key"]]["land_unit"] == lukey and x["action"] == "none"]
        if others and key not in STATS and (deltas(o)["dma"] or deltas(o)["dmd"] or deltas(o)["dhp"] or abs(deltas(o)["k"] - 1) > 1e-9):
            print("   note: %s shares its land unit with unchanged %s, which will change with it" % (key, others))
        lu, mu = dict(LU[lukey]), dict(MU[key])
        a, b = o["after"], o["before"]
        touched = False
        first_for_land = by_land[lukey][0]["key"] == key

        if key in STATS:
            s = STATS[key]
            for k_ in ("melee_attack", "melee_defence", "charge_bonus", "bonus_hit_points", "morale"):
                lu[k_] = str(s[k_])
            if s["armour"] not in ARMOUR:
                raise SystemExit("%s: no such armour tier %s" % (key, s["armour"]))
            lu["armour"] = s["armour"]
            mu["recruitment_cost"] = mu["multiplayer_cost"] = str(s["cost"])
            mu["upkeep_cost"] = str(int(s["cost"] * 0.25))
            touched = True
        else:
            d = deltas(o)
            k = d["k"]
            if d["dma"] or d["dmd"]:
                lu["melee_attack"] = str(int(float(lu["melee_attack"])) + d["dma"])
                lu["melee_defence"] = str(int(float(lu["melee_defence"])) + d["dmd"])
                touched = True
            if d["dhp"]:
                lu["bonus_hit_points"] = str(max(0, int(float(lu["bonus_hit_points"])) + d["dhp"]))
                touched = True
            if d["men"]:
                mu["num_men"] = str(int(d["men"]))
                if int(float(lu["num_mounts"])) == b["men"]:
                    lu["num_mounts"] = str(int(d["men"]))
                counts["resized"] += 1
                touched = True
            if abs(k - 1.0) > 1e-9:
                vw = MW[lu["primary_melee_weapon"]]
                w = dict(vw)
                w["key"] = PREFIX + lukey
                for col in ("damage", "ap_damage", "bonus_v_large", "bonus_v_infantry"):
                    w[col] = str(int(round(float(vw[col] or 0) * k)))
                if first_for_land:
                    weapons.append(coerce("melee_weapons", w))
                    counts["weapons"] += 1
                lu["primary_melee_weapon"] = w["key"]
                touched = True
            gun_d, gun_r = o.get("gun") or (1.0, 1.0)     # gunpowder.py: heavier volley, slower reload
            if (abs(k - 1.0) > 1e-9 or o.get("gun")) and d["missile"] and lu.get("primary_missile_weapon"):
                vmw = MIS[lu["primary_missile_weapon"]]
                p = dict(PJ[vmw["default_projectile"]])
                p["key"] = PREFIX + lukey
                for col in ("damage", "ap_damage", "bonus_v_large", "bonus_v_infantry"):
                    p[col] = str(int(round(float(p[col] or 0) * k * gun_d)))
                p["base_reload_time"] = str(round(float(p["base_reload_time"]) * gun_r, 2))
                mw = dict(vmw)
                mw["key"], mw["default_projectile"] = PREFIX + lukey, p["key"]
                if first_for_land:
                    projectiles.append(coerce("projectiles", p))
                    missiles.append(coerce("missile_weapons", mw))
                    counts["projectiles"] += 1
                lu["primary_missile_weapon"] = mw["key"]
                touched = True
                # alternate ammunition (unit_missile_weapon_junctions): the same factor on each alternate weapon, and the
                # vanilla junction row overridden by its id so the unit switches to the scaled copy, not the vanilla one
                for i, j in enumerate(ALT.get(key, [])):
                    if j["missile_weapon"] not in MIS:
                        continue
                    amw = dict(MIS[j["missile_weapon"]])
                    ap_ = dict(PJ[amw["default_projectile"]])
                    ap_["key"] = "%s%s_alt%d" % (PREFIX, key, i)
                    for col in ("damage", "ap_damage", "bonus_v_large", "bonus_v_infantry"):
                        ap_[col] = str(int(round(float(ap_[col] or 0) * k * gun_d)))
                    ap_["base_reload_time"] = str(round(float(ap_["base_reload_time"]) * gun_r, 2))
                    projectiles.append(coerce("projectiles", ap_))
                    amw["key"], amw["default_projectile"] = ap_["key"], ap_["key"]
                    missiles.append(coerce("missile_weapons", amw))
                    jj = dict(j)
                    jj["missile_weapon"] = amw["key"]
                    junctions.append(coerce("unit_missile_weapon_junctions", jj))
                    counts["alternates"] += 1
            if o["new_cost"] != o["cost"] or o["new_campaign_cost"] != o["campaign_cost"]:
                mu["multiplayer_cost"] = str(int(o["new_cost"]))
                mu["recruitment_cost"] = str(int(o["new_campaign_cost"]))
                mu["upkeep_cost"] = str(int(o["new_upkeep"]))
                counts["priced"] += 1
                touched = True
        if not touched:
            continue
        if first_for_land:
            land.append(coerce("land_units", lu))
        main_rows.append(coerce("main_units", mu))
        counts["units"] += 1

    entries = [("db/land_units_tables/!community_balance_patch", packwrite.build_db("land_units_tables", gamever.ver("land_units"), land)),
               ("db/main_units_tables/!community_balance_patch", packwrite.build_db("main_units_tables", gamever.ver("main_units"), main_rows))]
    if weapons:
        entries.append(("db/melee_weapons_tables/!community_balance_patch", packwrite.build_db("melee_weapons_tables", gamever.ver("melee_weapons"), weapons)))
    if projectiles:
        entries.append(("db/projectiles_tables/!community_balance_patch", packwrite.build_db("projectiles_tables", gamever.ver("projectiles"), projectiles)))
        entries.append(("db/missile_weapons_tables/!community_balance_patch", packwrite.build_db("missile_weapons_tables", gamever.ver("missile_weapons"), missiles)))
    if junctions:
        entries.append(("db/unit_missile_weapon_junctions_tables/!community_balance_patch", packwrite.build_db("unit_missile_weapon_junctions_tables", gamever.ver("unit_missile_weapon_junctions"), junctions)))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(packwrite.build_pack(entries))
    print("written: %s  %d bytes" % (OUT, os.path.getsize(OUT)))
    print("   %(units)d units; %(weapons)d weapon copies, %(projectiles)d projectile copies (+%(alternates)d alternate ammunition), %(resized)d resized, %(priced)d repriced; %(held)d held for review (--include-review writes them)" % counts)


if __name__ == "__main__":
    main()
