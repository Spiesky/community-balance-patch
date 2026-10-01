#!/usr/bin/env python3
"""Check the built pack against the proposals, row by row, and against the rules that must never break.

    python3 rebalance_check.py [pack]        exit 0 when everything holds, 1 with a list of failures

What is checked, for every unit in the pack:
  identity      armour, charge bonus, morale, weapon type, attack interval, splash and shield are the vanilla values
                (the decided four may change charge, morale and armour, as STATS says, nothing else; a lore elite's
                charge bonus moves by its proposal's delta; a gun's ammunition is the gunpowder rule's)
  stats         attack, defence and bonus HP are the vanilla row plus the proposal's delta (the model folds passives
                in, so absolutes would be wrong); the melee weapon the row points at is the land unit's copy carrying
                vanilla damage, AP and bonuses times the proposal's factor, or the vanilla weapon when the factor is 1;
                the same for the projectile and every alternate ammunition
  size          num_men is the proposal's, and num_mounts follows it where the vanilla unit had one mount per model
  prices        multiplayer and campaign prices are the proposal's, multiples of 25, and a campaign price of 0 stays 0;
                upkeep keeps the vanilla ratio within rounding
  references    every gr_ key the pack points at is in the pack; no gr_ row is unreferenced; no key is written twice
  alternates    every alternate ammunition junction of a scaled unit points at a scaled copy in the pack
  held          units held for review are absent unless the pack was built with --include-review
  drift         identity_drift of every changed unit is under DRIFT_MAX
  version       the pack carries the cbp_version localisation entry and it is the VERSION file's
  auto-resolve  no autoresolver table is in the pack unless it was built with CBP_AUTORESOLVE=1
"""
import json
import math
import os
import sys

import vanilla as V
from packread import Pack
from dbread import decode
import decided as DECIDED
import gunpowder as GP
import unit_model as UM

HERE = os.path.dirname(os.path.abspath(__file__))
PACK = (sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--")
        else os.environ.get("CBP_OUT") or os.path.join(os.path.dirname(HERE), "build", "draft", "community_balance_patch_DRAFT.pack"))
PROPOSALS = os.environ.get("CBP_PROPOSALS") or os.path.join(HERE, "_rebalance.json")
DRIFT_MAX = 0.02
PREFIX = "gr_"


def norm(x):
    """decoded pack values (float32, bool, int) and dump strings on one footing"""
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, (int, float)):
        return round(float(x), 3)
    s = str(x).strip()
    if s in ("true", "false"):
        return s
    try:
        return round(float(s), 3)
    except ValueError:
        return s


def same(a, b):
    return norm(a) == norm(b)


def rows_of(pack):
    out = {}
    for n, _, _ in pack.entries:
        if n.startswith("db/"):
            t = n.split("/")[1][:-7]
            _, cols, rows = decode(pack.get(n), n.split("/")[1])
            out.setdefault(t, []).extend(rows)
    return out


def version_problems(pack):
    """the pack's version entry must be exactly one row, cbp_version = the VERSION file, which the Battle Logger reads"""
    import re
    from refresh_vanilla import read_loc
    version = open(os.path.join(os.path.dirname(HERE), "VERSION")).read().strip()
    if not re.match(r"^\d+\.\d+(\.\d+)?$", version):
        return ["the VERSION file does not hold a version number: %r" % version]
    loc = pack.get("text/db/community_balance_patch.loc")
    if not loc:
        return ["no version entry (text/db/community_balance_patch.loc)"]
    rows = read_loc(loc)
    if rows != [["cbp_version", version, "false"]]:
        return ["the version entry is %r, expected cbp_version = %s" % (rows, version)]
    return []


def main():
    fails = []

    def fail(msg):
        fails.append(msg)

    P = {o["key"]: o for o in json.load(open(PROPOSALS))["units"]}
    S = json.load(open(os.path.join(HERE, "_survey.json")))
    UM.WEIGHTS.update(S["weights"]); UM.reset()
    pack = Pack(PACK)
    T = rows_of(pack)
    LU, MU = V.index("land_units"), V.index("main_units", "unit")
    MW, MIS, PJ = V.index("melee_weapons"), V.index("missile_weapons"), V.index("projectiles")
    BE, MO, ENG = V.index("battle_entities"), V.index("mounts"), V.index("battlefield_engines")
    AR = {r["key"]: float(r["armour_value"]) for r in V.table("unit_armour_types")}
    ALT = {}
    for r in V.table("unit_missile_weapon_junctions"):
        ALT.setdefault(r["unit"], []).append(r)

    land = {r["key"]: r for r in T.get("land_units", [])}
    main = {r["unit"]: r for r in T.get("main_units", [])}
    weapons = {r["key"]: r for r in T.get("melee_weapons", [])}
    missiles = {r["key"]: r for r in T.get("missile_weapons", [])}
    projectiles = {r["key"]: r for r in T.get("projectiles", [])}
    junctions = {str(r["id"]): r for r in T.get("unit_missile_weapon_junctions", [])}
    for name, rows, keyf in (("land_units", T.get("land_units", []), "key"), ("main_units", T.get("main_units", []), "unit"),
                             ("melee_weapons", T.get("melee_weapons", []), "key"), ("projectiles", T.get("projectiles", []), "key"),
                             ("missile_weapons", T.get("missile_weapons", []), "key")):
        keys = [r[keyf] for r in rows]
        if len(keys) != len(set(keys)):
            fail("%s: duplicate keys" % name)
    wanted_land = {MU[k]["land_unit"] for k in main if k in MU}
    if wanted_land != set(land):
        fail("land_units and main_units do not match: %s" % sorted(wanted_land ^ set(land))[:5])

    referenced = set()
    include_review = "--include-review" in sys.argv
    for key, o in P.items():
        held = o.get("held") and not include_review
        mu = MU.get(key)
        if not mu:
            fail("%s: not a vanilla main unit" % key); continue
        lukey = mu["land_unit"]
        if o["action"] == "none" or held:
            if key in main:
                fail("%s: in the pack but should not be (%s)" % (key, "held" if held else "no change"))
            continue
        if key not in main or lukey not in land:
            fail("%s: missing from the pack" % key); continue
        lu, mrow, v, a, b = land[lukey], main[key], LU[lukey], o["after"], o["before"]
        decided = key in DECIDED.STATS

        # identity
        for col in ("shield", "spacing", "man_entity", "mount", "engine", "attribute_group", "category", "class", "damage_mod_all", "damage_mod_physical", "damage_mod_missile", "damage_mod_magic", "damage_mod_flame"):
            if not same(lu[col], v[col]):
                fail("%s: %s changed %r -> %r" % (key, col, v[col], lu[col]))
        want_ammo = GP.ammo(v["primary_ammo"]) if o.get("gun") and a.get("missile") else v["primary_ammo"]
        if not same(lu["primary_ammo"], want_ammo):
            fail("%s: ammunition %r, expected %r (vanilla %r)" % (key, lu["primary_ammo"], want_ammo, v["primary_ammo"]))
        if not decided:
            for col in ("armour", "morale"):
                if not same(lu[col], v[col]):
                    fail("%s: %s changed %r -> %r" % (key, col, v[col], lu[col]))
            moves = abs(a["cb"] - b["cb"]) > 1e-9
            if moves and not o.get("elite"):
                fail("%s: charge bonus moves in the proposal but the unit is not a lore elite" % key)
            # as a factor on the database value: the card's figure has passives folded in (Frenzy multiplies it)
            want_cb = int(round(float(v["charge_bonus"]) * a["cb"] / b["cb"])) if moves else int(float(v["charge_bonus"]))
            if int(float(lu["charge_bonus"])) != want_cb:
                fail("%s: charge bonus %s, expected %s" % (key, lu["charge_bonus"], want_cb))
            if o.get("elite") and (o.get("k") or 1.0) > 1.0 and abs(float(lu["charge_bonus"]) / float(v["charge_bonus"]) - o["k"]) > 0.02:
                fail("%s: charge bonus x%.3f, the damage factor is x%.3f" % (key, float(lu["charge_bonus"]) / float(v["charge_bonus"]), o["k"]))
        else:
            s = DECIDED.STATS[key]
            for col, want in (("charge_bonus", s["charge_bonus"]), ("morale", s["morale"]), ("armour", s["armour"]), ("melee_attack", s["melee_attack"]), ("melee_defence", s["melee_defence"]), ("bonus_hit_points", s["bonus_hit_points"])):
                if not same(lu[col], want):
                    fail("%s (decided): %s is %r, STATS says %r" % (key, col, lu[col], want))
            if int(mrow["multiplayer_cost"]) != s["cost"] or int(mrow["recruitment_cost"]) != s["cost"]:
                fail("%s (decided): price %s/%s, STATS says %s" % (key, mrow["multiplayer_cost"], mrow["recruitment_cost"], s["cost"]))
            continue

        # stats: deltas and factors against the vanilla row, as the builder writes them
        k = o.get("k") or 1.0
        dma, dmd, dhp = round(a["ma"] - b["ma"]), round(a["md"] - b["md"]), round(a["hp"] - b["hp"])
        if int(lu["melee_attack"]) != int(float(v["melee_attack"])) + dma or int(lu["melee_defence"]) != int(float(v["melee_defence"])) + dmd:
            fail("%s: attack/defence %s/%s, expected %s/%s" % (key, lu["melee_attack"], lu["melee_defence"], int(float(v["melee_attack"])) + dma, int(float(v["melee_defence"])) + dmd))
        if int(float(lu["bonus_hit_points"])) != max(0, int(float(v["bonus_hit_points"])) + dhp):
            fail("%s: bonus HP %s, expected %s" % (key, lu["bonus_hit_points"], max(0, int(float(v["bonus_hit_points"])) + dhp)))
        # melee weapon
        wkey = lu["primary_melee_weapon"]
        w = weapons.get(wkey) or MW.get(wkey)
        if not w:
            fail("%s: melee weapon %s not in the pack or vanilla" % (key, wkey)); continue
        vw = MW[v["primary_melee_weapon"]]
        if abs(k - 1.0) > 1e-9:
            if wkey != PREFIX + lukey:
                fail("%s: melee weapon should be the copy %s, is %s" % (key, PREFIX + lukey, wkey))
            referenced.add(("melee_weapons", wkey))
        elif wkey != v["primary_melee_weapon"]:
            fail("%s: melee weapon changed without a factor" % key)
        for col in ("melee_weapon_type", "melee_attack_interval", "splash_attack_target_size", "splash_attack_max_attacks", "splash_attack_power_multiplier", "is_magical", "ignition_amount", "contact_phase", "weapon_length", "collision_attack_max_targets"):
            if not same(w[col], vw[col]):
                fail("%s: weapon %s changed %r -> %r" % (key, col, vw[col], w[col]))
        for col in ("damage", "ap_damage", "bonus_v_large", "bonus_v_infantry"):
            if abs(int(float(w[col])) - round(float(vw[col] or 0) * k)) > 1:
                fail("%s: weapon %s %s, expected %s" % (key, col, w[col], round(float(vw[col] or 0) * k)))
        # missile
        if a.get("missile") and b.get("missile"):
            mkey = lu["primary_missile_weapon"]
            if mkey:
                mw = missiles.get(mkey) or MIS.get(mkey)
                if not mw:
                    fail("%s: missile weapon %s missing" % (key, mkey)); continue
                p = projectiles.get(mw["default_projectile"]) or PJ.get(mw["default_projectile"])
                if not p:
                    fail("%s: projectile %s missing" % (key, mw["default_projectile"])); continue
                gd, gr = o.get("gun") or (1.0, 1.0)
                scaled = abs(k - 1.0) > 1e-9 or bool(o.get("gun"))
                if scaled:
                    if mkey != PREFIX + lukey:
                        fail("%s: missile weapon should be the copy %s, is %s" % (key, PREFIX + lukey, mkey))
                    referenced.add(("missile_weapons", mkey)); referenced.add(("projectiles", mw["default_projectile"]))
                elif mkey != v["primary_missile_weapon"]:
                    fail("%s: missile weapon changed without a factor" % key)
                vp = PJ[MIS[v["primary_missile_weapon"]]["default_projectile"]]
                for col in ("damage", "ap_damage", "bonus_v_large", "bonus_v_infantry"):
                    if abs(int(float(p[col])) - round(float(vp[col] or 0) * k * gd)) > 1:
                        fail("%s: projectile %s %s, expected %s" % (key, col, p[col], round(float(vp[col] or 0) * k * gd)))
                if abs(float(p["base_reload_time"]) - float(vp["base_reload_time"]) * gr) > 0.02:
                    fail("%s: reload %s, expected %s" % (key, p["base_reload_time"], float(vp["base_reload_time"]) * gr))
                for col in ("category", "shot_type", "explosion_type", "effective_range", "calibration_area", "projectile_number", "shots_per_volley", "burst_size", "projectile_penetration", "is_magical", "ignition_amount", "contact_stat_effect"):
                    if not same(p[col], vp[col]):
                        fail("%s: projectile %s changed %r -> %r" % (key, col, vp[col], p[col]))
                # alternates
                for j in ALT.get(key, []):
                    jj = junctions.get(str(j["id"]))
                    if scaled and not jj:
                        fail("%s: alternate ammunition %s not overridden" % (key, j["missile_weapon"]))
                    elif jj:
                        amw = missiles.get(jj["missile_weapon"])
                        ap_ = amw and projectiles.get(amw["default_projectile"])
                        if not amw or not ap_:
                            fail("%s: alternate %s points at a missing copy" % (key, jj["missile_weapon"])); continue
                        referenced.add(("missile_weapons", amw["key"])); referenced.add(("projectiles", ap_["key"]))
                        vap = PJ[MIS[j["missile_weapon"]]["default_projectile"]]
                        for col in ("damage", "ap_damage", "bonus_v_large", "bonus_v_infantry"):
                            if abs(int(float(ap_[col])) - round(float(vap[col] or 0) * k * gd)) > 1:
                                fail("%s: alternate %s %s %s, expected %s" % (key, j["missile_weapon"], col, ap_[col], round(float(vap[col] or 0) * k * gd)))
                        if abs(float(ap_["base_reload_time"]) - float(vap["base_reload_time"]) * gr) > 0.02:
                            fail("%s: alternate %s reload %s, expected %s" % (key, j["missile_weapon"], ap_["base_reload_time"], float(vap["base_reload_time"]) * gr))
        # size: entities are the vehicles or the monster, num_men counts the crew too; only a resize changes it
        want_men = a["men"] if a["men"] != b["men"] else int(mu["num_men"])
        if int(mrow["num_men"]) != want_men:
            fail("%s: num_men %s, expected %s" % (key, mrow["num_men"], want_men))
        if int(float(v["num_mounts"])) == b["men"] and int(float(lu["num_mounts"])) != a["men"]:
            fail("%s: num_mounts %s should follow num_men %s" % (key, lu["num_mounts"], a["men"]))
        # prices
        if int(mrow["multiplayer_cost"]) != o["new_cost"] or int(mrow["recruitment_cost"]) != o["new_campaign_cost"]:
            fail("%s: prices %s/%s, proposal %s/%s" % (key, mrow["multiplayer_cost"], mrow["recruitment_cost"], o["new_cost"], o["new_campaign_cost"]))
        if o["new_cost"] % 25 or o["new_campaign_cost"] % 25:
            fail("%s: price not a multiple of 25: %s / %s" % (key, o["new_cost"], o["new_campaign_cost"]))
        if int(mu["recruitment_cost"]) == 0 and o["new_campaign_cost"] != 0:
            fail("%s: campaign price was 0 and is now %s" % (key, o["new_campaign_cost"]))
        if o["cost"] and abs(int(mrow["upkeep_cost"]) - o["upkeep"] * o["new_cost"] / o["cost"]) > 1.5:
            fail("%s: upkeep %s, expected %.0f" % (key, mrow["upkeep_cost"], o["upkeep"] * o["new_cost"] / o["cost"]))
        # drift
        if o.get("drift", 0) > DRIFT_MAX:
            fail("%s: identity drift %.4f" % (key, o["drift"]))

    # every gr_ row referenced, every reference present
    for t, rows in (("melee_weapons", weapons), ("missile_weapons", missiles), ("projectiles", projectiles)):
        for k in rows:
            if k.startswith(PREFIX) and (t, k) not in referenced:
                fail("%s: %s written but nothing points at it" % (t, k))
    for mw in missiles.values():
        if mw["default_projectile"] not in projectiles and mw["default_projectile"] not in PJ:
            fail("missile weapon %s: projectile %s missing" % (mw["key"], mw["default_projectile"]))

    # the version entry, and no auto-resolve tables unless asked for
    if not any(a for a in sys.argv[1:] if not a.startswith("--") and a != PACK):
        for msg in version_problems(pack):
            fail(msg)
    if any("autoresolver" in n for n, _, _ in pack.entries) and (
            os.environ.get("CBP_AUTORESOLVE") != "1" or os.path.basename(PACK) == "community_balance_patch.pack"):
        fail("autoresolver tables are in the pack; they belong in the test pack (autoresolve_rules.py)")

    n = len(main)
    if fails:
        print("FAIL: %d problems in %s (%d units)" % (len(fails), os.path.basename(PACK), n))
        for m in fails[:60]:
            print("   " + m)
        if len(fails) > 60:
            print("   ... and %d more" % (len(fails) - 60))
        return 1
    print("PASS: %s, %d units, %d weapon copies, %d projectile copies, %d alternate junctions; every row matches its proposal" % (
        os.path.basename(PACK), n, len(weapons), len(projectiles), len(junctions)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
