#!/usr/bin/env python3
"""Units whose numbers were set by hand rather than by the solver ("decided"), and coerce(), which casts dump strings
to the types the schema wants. The solver writes decided units exactly as they are here."""
import gamever
from dbread import load_defs

GRYPHITES = "wh_dlc04_emp_cav_royal_altdorf_gryphites_0"

# Armour stays on vanilla's scale: 120 is the knightly ceiling (Grail Knights, Chaos Knights, vanilla Reiksguard),
# 125 only for demigryph riders, as vanilla. Grombrindal's gromril is 125 and Karl Franz wears 100; no regiment of
# mortal knights may out-armour them.
STATS = {
    "wh_main_emp_cav_reiksguard": dict(
        melee_attack=38, melee_defence=40, charge_bonus=66,
        bonus_hit_points=110, armour="wh2_main_plate_120", morale=75, cost=1300,
        why="The all-rounder, and the yardstick. Nothing they do is the best in "
            "the roster and nothing they do is weak."),

    "wh_dlc04_emp_cav_knights_blazing_sun_0": dict(
        melee_attack=40, melee_defence=27, charge_bonus=74,
        bonus_hit_points=100, armour="wh2_main_plate_120", morale=70, cost=1200,
        why="Myrmidia's knights fight the battle they chose. Hardest charge in "
            "the Empire, and the least to show for it once the charge is spent."),

    "wh3_dlc25_emp_cav_knights_of_the_black_rose": dict(
        melee_attack=36, melee_defence=52, charge_bonus=30,
        bonus_hit_points=120, armour="wh2_main_plate_120", morale=85, cost=1250,
        why="Morr's knights have already made their peace with dying. They do "
            "not charge, they hold, and they do not rout."),

    GRYPHITES: dict(
        melee_attack=52, melee_defence=52, charge_bonus=78,
        bonus_hit_points=240, armour="wh2_main_plate_125", morale=90, cost=2000,
        why="The Emperor's own household cavalry. Best in the Empire at "
            "everything, and priced so that fielding two of them hurts."),
}


def coerce(table, row):
    """Dump values are strings; cast them to what the schema wants."""
    out = {}
    for name, ftype in load_defs("%s_tables" % table)[gamever.ver(table)]:
        v = row.get(name, "")
        if ftype == "Boolean":
            out[name] = str(v).strip().lower() == "true"
        elif ftype in ("I16", "I32", "I64", "ColourRGB"):
            try:
                out[name] = int(float(v)) if v not in ("", None) else 0
            except (TypeError, ValueError):
                out[name] = 0
        elif ftype in ("F32", "F64"):
            try:
                out[name] = float(v) if v not in ("", None) else 0.0
            except (TypeError, ValueError):
                out[name] = 0.0
        else:
            out[name] = "" if v is None else str(v)
    return out
