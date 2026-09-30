#!/usr/bin/env python3
"""Fairer auto-resolve: units you would keep at the back of a real battle are not killed as fast as your front line.

The auto-resolver works out each unit's kills per second from its stats; autoresolver_modifier_group_to_modifiers adds
to that rate (value -0.7 = 30% of the normal rate), aimed at a class matchup through autoresolver_modifier_targets.
These rules aim at "anyone against <back-line class>", applied in every auto-resolve battle type.

    python3 autoresolve_rules.py            -> ../build/cbp_autoresolve_test.pack (a test pack on its own)

The values are a first guess; the Battle Logger's auto-resolve entries are what they get tuned against.
"""
import json
import os
import packwrite
import gamever
import vanilla as V
from decided import coerce

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get("CBP_AR_OUT", os.path.join(os.path.dirname(HERE), "build", "cbp_autoresolve_test.pack"))
GROUP = "cbp_protect_back_line"
BUG_ROW = "432943812"             # the second missile row of wh_moderate_kps_multiplier_bonus
# class kept at the back: added to the enemy's kill rate against it. autoresolve_rules.json (written by
# autoresolve_calibrate.py from players' battle logs) replaces these starting guesses once there is enough data.
RULES = {"art_fld": -0.70, "inf_mis": -0.35, "cav_mis": -0.25}
_json = os.path.join(os.path.dirname(os.path.abspath(__file__)), "autoresolve_rules.json")
if os.path.exists(_json):
    RULES = json.load(open(_json))["rules"]


def entries():
    """the auto-resolve rows as pack entries; build_rebalance.py puts them in the patch itself"""
    targets, mods, lookups = [], [], []
    for n, (cls, value) in enumerate(sorted(RULES.items())):
        key = "cbp_all_v_" + cls
        targets.append(coerce("autoresolver_modifier_targets", dict(key=key, target_unit_class="", vs_unit_class=cls)))
        for m, bonus in enumerate(("unit_melee_kps_multiplier", "unit_missile_kps_multiplier")):
            mods.append(coerce("autoresolver_modifier_group_to_modifiers", dict(
                id=str(1904110000 + n * 10 + m), group=GROUP, modifier_bonus=bonus, modifier_target=key, value=str(value))))
    for n, bt in enumerate(sorted(r["key"] for r in V.table("autoresolver_battle_types"))):
        lookups.append(coerce("autoresolver_modifier_group_lookups", dict(
            id=str(1904120000 + n), battle_type=bt, modifier_group_applied=GROUP, modifier_value_multiplier_mechanic="none",
            player_type="any")))
    # CA's bug, still in 9.0: wh_moderate_kps_multiplier_bonus has two identical missile rows and no melee row (its
    # sibling wh_spell_moderate_kps_multiplier_bonus has one of each). One of the two becomes the melee row.
    fix = V.index("autoresolver_modifier_group_to_modifiers", "id").get(BUG_ROW)
    if fix and fix["group"] == "wh_moderate_kps_multiplier_bonus" and fix["modifier_bonus"] == "unit_missile_kps_multiplier":
        mods.append(coerce("autoresolver_modifier_group_to_modifiers", dict(fix, modifier_bonus="unit_melee_kps_multiplier")))
    keys = [coerce("autoresolver_modifier_group_keys", dict(group_key=GROUP))]
    entries = []
    for table, rows in (("autoresolver_modifier_group_keys", keys), ("autoresolver_modifier_targets", targets),
                        ("autoresolver_modifier_group_to_modifiers", mods), ("autoresolver_modifier_group_lookups", lookups)):
        entries.append(("db/%s_tables/!cbp_autoresolve" % table, packwrite.build_db(table + "_tables", gamever.ver(table), rows)))
    return entries, (len(targets), len(mods), len(lookups))


def main():
    e, (t, m, l) = entries()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(packwrite.build_pack(e))
    print("written: %s  %d bytes; %d targets, %d modifiers, %d battle types" % (OUT, os.path.getsize(OUT), t, m, l))


if __name__ == "__main__":
    main()
