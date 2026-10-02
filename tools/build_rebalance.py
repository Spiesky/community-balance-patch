#!/usr/bin/env python3
"""Build the rebalance pack from the solver's proposals.

    python3 rebalance_survey.py && python3 rebalance_solve.py && python3 build_rebalance.py
                                                            -> ../build/draft/community_balance_patch_DRAFT.pack

That is the whole draft, for study. The Workshop pack is the beta: tools/patch_day.sh builds it (CBP_PROPOSALS=_beta.json,
CBP_COMMUNITY=1, CBP_OUT=../build/beta/community_balance_patch.pack). The draft carries a different file name so it
cannot be uploaded by mistake.

What goes in, per changed unit (from _rebalance.json, written by rebalance_solve.py):

  land_units      melee_attack, melee_defence and bonus_hit_points moved by the proposal's delta against the vanilla
                  row (never the model's absolute figure: the model folds permanent passives in), num_mounts where the
                  unit size changes, charge_bonus for the lore elites (it scales with their damage), morale / charge_bonus
                  / armour for the decided four, primary_ammo for the gunpowder rule, primary_melee_weapon and
                  primary_missile_weapon pointed at the land unit's own copies where damage moves. A land unit shared
                  by several main units is written once, and only if every sharer agrees.
  melee_weapons   a copy of the unit's weapon under the land unit's key with damage, AP, bonus vs large and vs infantry
                  multiplied by the proposal's factor k. Weapons are shared between units (six units swing wh_main_emp_sword), so a shared row is
                  never edited: every unit whose damage moves gets its own.
  projectiles     the same for the projectile, and a missile_weapons row pointing at it, where the unit shoots; a
                  unit's alternate ammunition (unit_missile_weapon_junctions) is copied and scaled the same way, with
                  the vanilla junction row overridden by its id
  main_units      multiplayer_cost, recruitment_cost (0 stays 0: Tomb Kings pay in other ways), upkeep_cost, num_men
  text            one localisation entry, cbp_version = the VERSION file, so the Battle Logger (a separate pack) can
                  write down which build a battle was fought with. The pack's name never changes: renaming it would
                  switch the mod off for every subscriber.

The decided units (decided.STATS) are written from STATS as they are. The auto-resolve rules (autoresolve_rules.py) are
NOT part of the patch: they build as their own test pack, and only CBP_AUTORESOLVE=1 puts them in here.
The pack stands on its own. Check it with refcheck.py and rebalance_check.py, and read docs/METHOD.md before
trusting any number in it.
"""
import json
import os
import sys

import vanilla as V
import gamever
import gunpowder as GP
import packwrite
from decided import STATS, ELITE_BODIES, coerce

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("CBP_OUT", os.path.join(os.path.dirname(HERE), "build", "draft", "community_balance_patch_DRAFT.pack"))
PROPOSALS = os.environ.get("CBP_PROPOSALS") or os.path.join(HERE, "_rebalance.json")
COMMUNITY = os.environ.get("CBP_COMMUNITY") == "1"   # apply the community's own list (community.py) on top
AUTORESOLVE = os.environ.get("CBP_AUTORESOLVE") == "1"   # also carry the auto-resolve test rules (off: they are a test pack)
VERSION = open(os.path.join(os.path.dirname(HERE), "VERSION")).read().strip()
VERSION_KEY = "cbp_version"                          # the Battle Logger reads this localisation key
YIELD_TO_BUGFIX = {"wh3_dlc25_dwf_inf_slayer_pirates", "wh3_dlc25_dwf_inf_slayer_pirates_ror"}   # its animation fix
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
        # the charge bonus moves only for the lore elites, and as a factor: the card's figure has passives folded in
        # (Frenzy multiplies it), so a difference written onto the database value would count the passive twice
        return dict(k=o.get("k") or 1.0, dma=round(a["ma"] - b["ma"]), dmd=round(a["md"] - b["md"]), dhp=round(a["hp"] - b["hp"]),
                    cbx=round(a["cb"] / b["cb"], 4) if b["cb"] and abs(a["cb"] - b["cb"]) > 1e-9 else 1.0, gun=bool(o.get("gun")),
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
            if d["cbx"] != 1.0:                           # the lore elites only: charge scales with their damage
                lu["charge_bonus"] = str(int(round(float(lu["charge_bonus"]) * d["cbx"])))
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
                if o.get("gun"):                          # less ammunition: the same damage over a battle as vanilla
                    lu["primary_ammo"] = str(GP.ammo(lu["primary_ammo"]))
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

    if COMMUNITY:                              # the community's own list on top (community.py)
        import community
        import unit_model as UM
        out = dict(land_units={r["key"]: r for r in land}, main_units={r["unit"]: r for r in main_rows},
                   melee_weapons={r["key"]: r for r in weapons}, projectiles={r["key"]: r for r in projectiles},
                   missile_weapons={r["key"]: r for r in missiles},
                   unit_missile_weapon_junctions={str(r["id"]): r for r in junctions})
        skip = {o["key"]: "lore elite, set by the patch's own design" for o in props if o.get("elite")}
        guns = {MU[o["key"]]["land_unit"]: tuple(o["gun"]) for o in props if o.get("gun")}
        clog = community.apply(out, V, coerce, UM.name, UM.faction, UM.recruitable(), skip, guns)
        land, main_rows = list(out["land_units"].values()), list(out["main_units"].values())
        weapons, projectiles, missiles = list(out["melee_weapons"].values()), list(out["projectiles"].values()), list(out["missile_weapons"].values())
        junctions = list(out["unit_missile_weapon_junctions"].values())
        entities = list(out.get("battle_entities", {}).values())
        print("   community list: %d changes, %d land units, %d entities" % (len(clog), len(land), len(entities)))
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        json.dump([[l, k, c] for l, k, c in clog], open(os.path.join(os.path.dirname(OUT), "community_log.json"), "w"), indent=0)
    # lore elites' bodies (decided.ELITE_BODIES): heavier, so a few tough models are not thrown about all battle
    elite_lands = {MU[o["key"]]["land_unit"] for o in props if o.get("elite")}
    ents = {r["key"]: r for r in (entities if COMMUNITY else [])}
    for ek, sets in ELITE_BODIES.items():
        if any(LU[l]["man_entity"] == ek for l in elite_lands):
            r = ents.get(ek) or coerce("battle_entities", BE[ek])
            r.update(sets)
            ents[ek] = r
    entities = list(ents.values())
    # Campaign copies. Some main units share another's land unit under a campaign-only key (an Imperial Supply
    # Handgunner, Dechala's Daemonettes): they get the stats through the shared row, so when the price of the unit they
    # copy moves, theirs moves by the same ratio (a campaign cost or upkeep of 0 stays 0).
    written = {r["unit"]: r for r in main_rows}
    for r in list(main_rows):
        v = MU[r["unit"]]
        old, new = int(float(v["multiplayer_cost"])), int(r["multiplayer_cost"])
        if not old or new == old:
            continue
        for s in (m for m in MU.values() if m["land_unit"] == v["land_unit"] and m["unit"] not in written
                  and int(float(m["multiplayer_cost"])) == old):
            t = dict(s)
            t["multiplayer_cost"] = str(new)
            t["recruitment_cost"] = str(int(round(float(s["recruitment_cost"]) * new / old / 25.0)) * 25)
            t["upkeep_cost"] = str(int(round(float(s["upkeep_cost"]) * new / old)))
            row = coerce("main_units", t)
            main_rows.append(row)
            written[s["unit"]] = row
            counts["copies"] = counts.get("copies", 0) + 1
    # rows the Community Bug Fix Mod also fixes go in a file that sorts after its "zzz_cbfm_*" files: with it installed its
    # fix wins, without it ours applies (checked against its pack of 2026-09-27, Game v9 Batch 1)
    yielded = [r for r in land if r["key"] in YIELD_TO_BUGFIX]
    land = [r for r in land if r["key"] not in YIELD_TO_BUGFIX]
    entries = [("db/land_units_tables/!community_balance_patch", packwrite.build_db("land_units_tables", gamever.ver("land_units"), land)),
               ("db/main_units_tables/!community_balance_patch", packwrite.build_db("main_units_tables", gamever.ver("main_units"), main_rows))]
    if weapons:
        entries.append(("db/melee_weapons_tables/!community_balance_patch", packwrite.build_db("melee_weapons_tables", gamever.ver("melee_weapons"), weapons)))
    if projectiles:
        entries.append(("db/projectiles_tables/!community_balance_patch", packwrite.build_db("projectiles_tables", gamever.ver("projectiles"), projectiles)))
        entries.append(("db/missile_weapons_tables/!community_balance_patch", packwrite.build_db("missile_weapons_tables", gamever.ver("missile_weapons"), missiles)))
    if junctions:
        entries.append(("db/unit_missile_weapon_junctions_tables/!community_balance_patch", packwrite.build_db("unit_missile_weapon_junctions_tables", gamever.ver("unit_missile_weapon_junctions"), junctions)))
    if yielded:
        entries.append(("db/land_units_tables/zzzz_community_balance_patch_after_bugfix", packwrite.build_db("land_units_tables", gamever.ver("land_units"), yielded)))
    if entities:
        entries.append(("db/battle_entities_tables/!community_balance_patch", packwrite.build_db("battle_entities_tables", gamever.ver("battle_entities"), entities)))
    if not only:                               # the build's version, for the Battle Logger (a data row, not a script)
        entries.append(("text/db/community_balance_patch.loc", packwrite.build_loc([(VERSION_KEY, VERSION)])))
    if AUTORESOLVE:                            # the auto-resolve test rules: their own pack unless asked for here
        import autoresolve_rules
        ar, (nt, nm, nl) = autoresolve_rules.entries()
        entries += ar
        print("   auto-resolve rules INCLUDED (CBP_AUTORESOLVE=1): %s" % autoresolve_rules.describe())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(packwrite.build_pack(entries))
    print("written: %s  %d bytes, version %s" % (OUT, os.path.getsize(OUT), VERSION))
    print("   %(units)d units; %(weapons)d weapon copies, %(projectiles)d projectile copies (+%(alternates)d alternate ammunition), %(resized)d resized, %(priced)d repriced; %(held)d held for review (--include-review writes them)" % counts)
    if counts.get("copies"):
        print("   %d campaign copies repriced with the unit they copy" % counts["copies"])


if __name__ == "__main__":
    main()
