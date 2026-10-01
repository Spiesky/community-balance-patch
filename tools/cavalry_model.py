"""The thorough combat model behind the cavalry rebalance study.

A unit card holds everything the database says about how the unit fights. Damage between two cards follows
the game's melee rules as the community has measured them:

  hit chance        clamp(35 + attacker MA (+ charge bonus on the charge) - defender MD, 8, 90) %
  bonus damage      + bonus vs large against large targets (cavalry, monsters, monstrous infantry),
                    + bonus vs infantry against everything else; bonus damage adds to base damage
  charge            the charge bonus is added to melee attack and to damage, split between base and AP
  armour            blocks a random 50-100% of its value (as a percentage) of base damage, capped at 100%
  armour-piercing   ignores armour
  resistances       ward save (all) always; physical resistance against non-magical attacks; magic resistance
                    against magical attacks; flame resistance against flaming attacks. Capped at 90%.
  splash            a weapon whose splash size covers the target spreads each blow across up to N models;
                    the total damage is multiplied by its splash power multiplier (enough targets assumed)
  attack interval   the weapon's own melee_attack_interval

Per model, against reference opponents that are real vanilla units:
  offence   damage per second, sustained, plus a charge every 30 seconds (cycle charging)
  toughness seconds a model lasts against one opposing model
  ranged    missile damage per second against the same targets (reload, shots per volley, burst, projectiles)
"""
import math

import vanilla as V

BE = V.index("battle_entities")
MO = V.index("mounts")
LU = V.index("land_units")
MU = V.index("main_units", "unit")
MW = V.index("melee_weapons")
MIS = V.index("missile_weapons")
PJ = V.index("projectiles")
AR = {r["key"]: float(r["armour_value"]) for r in V.table("unit_armour_types")}
ATTR = {}
for r in V.table("unit_attributes_to_groups_junctions"):
    ATTR.setdefault(r["attribute_group"], []).append(r["attribute"])
ABIL = {}
for r in V.table("land_units_to_unit_abilites_junctions"):
    ABIL.setdefault(r["land_unit"], []).append(r["ability"])
PHASES = {}
for r in V.table("special_ability_to_special_ability_phase_junctions"):
    PHASES.setdefault(r["special_ability"], []).append(r["phase"])
PHASE_INFO = V.index("special_ability_phases", "id")
PHASE_STATS = {}
for r in V.table("special_ability_phase_stat_effects"):
    PHASE_STATS.setdefault(r["phase"], []).append((r["stat"], float(r["value"]), r["how"]))

SIZE_RANK = {"very_small": 0, "small": 1, "medium": 2, "large": 3, "very_large": 4}
CHARGE_EVERY = 30.0

STAT_MAP = {
    "stat_melee_attack": "ma", "stat_melee_defence": "md", "stat_charge_bonus": "cb",
    "stat_resistance_all": "ward", "stat_resistance_physical": "res_physical", "stat_resistance_missile": "res_missile",
    "stat_resistance_magic": "res_magic", "stat_resistance_flame": "res_flame", "stat_weakness_flame": "res_flame_weak",
    "stat_melee_damage_base": "base", "stat_melee_damage_ap": "ap", "stat_morale": "morale",
    "stat_armour": "armour",
}


def f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


USA = V.index("unit_special_abilities")
JUNCTIONS = {}
for r in V.table("special_ability_to_special_ability_phase_junctions"):
    JUNCTIONS.setdefault(r["special_ability"], []).append(r)


def passives(abilities):
    """permanent passive abilities that act on the unit itself: {card field: (add, mult)}.
    Auras that only buff friends (the Swords of Chaos' Guardian) and debuffs on enemies are left out;
    timed and active abilities are the simulator's business (cavalry_sim.py)."""
    out = {}
    for ab in abilities:
        if "formation" in ab:
            continue
        row = USA.get(ab, {})
        if row.get("passive") != "true" or f(row.get("active_time"), -1) != -1:
            continue
        for j in JUNCTIONS.get(ab, []):
            ph = j["phase"]
            on_self = j.get("target_self") == "true" or (row.get("affect_self") == "true" and j.get("target_friends") != "true" and j.get("target_enemies") != "true")
            if not on_self:
                continue
            info = PHASE_INFO.get(ph, {})
            if f(info.get("duration"), 0) != -1:
                continue
            for stat, value, how in PHASE_STATS.get(ph, []):
                field = STAT_MAP.get(stat)
                if not field:
                    continue
                add, mult = out.get(field, (0.0, 1.0))
                out[field] = (add + value, mult) if how == "add" else (add, mult * value)
    return out


def ranged(lu):
    key = lu.get("primary_missile_weapon")
    if not key or key not in MIS:
        return None
    p = PJ.get(MIS[key]["default_projectile"])
    if not p:
        return None
    volley = max(1.0, f(p["projectile_number"], 1)) * max(1.0, f(p["shots_per_volley"], 1)) * max(1.0, f(p["burst_size"], 1))
    return dict(base=f(p["damage"]), ap=f(p["ap_damage"]), bvl=f(p["bonus_v_large"]), bvi=f(p["bonus_v_infantry"]),
                reload=max(0.5, f(p["base_reload_time"], 10)), volley=volley, range=f(p["effective_range"]),
                ammo=f(lu.get("primary_ammo")), magical=p.get("is_magical") == "true", flaming=f(p.get("ignition_amount")) > 0)


def card(key, label=None, **over):
    """the fighting card of a main unit, passives folded in; keyword arguments override fields"""
    mu = MU[key]
    lu = LU[mu["land_unit"]]
    w = MW.get(lu["primary_melee_weapon"], {})
    man = BE[lu["man_entity"]]
    mount = BE.get(MO.get(lu["mount"], {}).get("entity", ""), {})
    body = mount or man
    c = dict(
        key=key, label=label or key, men=int(f(mu["num_men"])), cost=int(f(mu["recruitment_cost"])),
        upkeep=int(f(mu["upkeep_cost"])), caste=mu["caste"],
        ma=f(lu["melee_attack"]), md=f(lu["melee_defence"]), cb=f(lu["charge_bonus"]), morale=f(lu["morale"]),
        hp=f(man["hit_points"]) + f(mount.get("hit_points")) + f(lu["bonus_hit_points"]),
        armour=AR.get(lu["armour"], 0.0),
        base=f(w.get("damage")), ap=f(w.get("ap_damage")), bvl=f(w.get("bonus_v_large")), bvi=f(w.get("bonus_v_infantry")),
        interval=f(w.get("melee_attack_interval"), 4.0) or 4.0,
        splash_size=w.get("splash_attack_target_size") or "", splash_n=f(w.get("splash_attack_max_attacks"), 1),
        splash_mult=f(w.get("splash_attack_power_multiplier"), 1) or 1.0,
        magical=w.get("is_magical") == "true", flaming=f(w.get("ignition_amount")) > 0,
        ward=f(lu["damage_mod_all"]), res_physical=f(lu["damage_mod_physical"]), res_missile=f(lu["damage_mod_missile"]),
        res_magic=f(lu["damage_mod_magic"]), res_flame=f(lu["damage_mod_flame"]), res_flame_weak=0.0,
        speed=f(body.get("run_speed")), charge_speed=f(body.get("charge_speed")),
        mass=f(man.get("mass")) + f(mount.get("mass")),
        size=body.get("size", "small"),
        attrs=ATTR.get(lu["attribute_group"], []), abilities=ABIL.get(mu["land_unit"], []),
        missile=ranged(lu),
    )
    for field, (add, mult) in passives(c["abilities"]).items():
        c[field] = (c[field] + add) * mult
    c["res_flame"] += c.pop("res_flame_weak")
    c.update(over)
    return c


def is_large(c):
    return SIZE_RANK.get(c["size"], 1) >= 2


def resist(att, dfn, magical=None, flaming=None):
    magical = att["magical"] if magical is None else magical
    flaming = att["flaming"] if flaming is None else flaming
    r = dfn["ward"] + (dfn["res_magic"] if magical else dfn["res_physical"]) + (dfn["res_flame"] if flaming else 0.0)
    return max(-100.0, min(90.0, r))


def armour_block(armour):
    lo, hi = armour / 200.0, armour / 100.0
    if hi <= 1.0:
        return (lo + hi) / 2
    if lo >= 1.0:
        return 1.0
    below = (1.0 - lo) / (hi - lo)
    return below * (lo + 1.0) / 2 + (1 - below)


USABLE = False              # True: a blow never does more than its targets have hit points (see blow)


def blow(att, dfn, charging=False, usable=None):
    """expected damage of one melee attack.

    usable (default: the module's USABLE switch): cap the blow at the hit points of what it can reach, one model, or
    the splash attack's models. A 188-damage swing into a 50-HP Skavenslave kills one Skavenslave, not 3.8 of them:
    the rest is overkill. The survey's scale is fitted without the cap (it is pinned, docs/METHOD.md); the cap is used
    where a change multiplies a unit's damage, the lore elites and grind_check.py, so their worth is not counted in
    damage they cannot spend."""
    ma = att["ma"] + (att["cb"] if charging else 0.0)
    chance = min(90.0, max(8.0, 35.0 + ma - dfn["md"])) / 100.0
    base = att["base"] + (att["bvl"] if is_large(dfn) else att["bvi"])
    ap = att["ap"]
    if charging and base + ap > 0:
        base, ap = base + att["cb"] * base / (base + ap), ap + att["cb"] * ap / (base + ap)
    dmg = base * (1.0 - armour_block(dfn["armour"])) + ap
    dmg *= 1.0 - resist(att, dfn) / 100.0
    reach = 1.0
    if att["splash_size"] and SIZE_RANK.get(dfn["size"], 1) <= SIZE_RANK.get(att["splash_size"], 0):
        dmg *= att["splash_mult"]
        reach = max(1.0, att["splash_n"])
    if USABLE if usable is None else usable:
        dmg = min(dmg, reach * dfn["hp"])
    return chance * dmg


def melee_dps(att, dfn):
    """sustained damage per second of one model, with a charge every CHARGE_EVERY seconds"""
    sustained = blow(att, dfn) / att["interval"]
    burst = max(0.0, blow(att, dfn, True) - blow(att, dfn))
    return sustained + burst / CHARGE_EVERY


def ranged_dps(att, dfn):
    m = att.get("missile")
    if not m:
        return 0.0
    base = m["base"] + (m["bvl"] if is_large(dfn) else m["bvi"])
    dmg = base * (1.0 - armour_block(dfn["armour"])) + m["ap"]
    r = dfn["ward"] + dfn["res_missile"] + (dfn["res_magic"] if m["magical"] else 0.0) + (dfn["res_flame"] if m["flaming"] else 0.0)
    dmg *= 1.0 - max(-100.0, min(90.0, r)) / 100.0
    return dmg * m["volley"] / m["reload"]


# ---- reference opponents: real vanilla units
REF_TARGETS = {
    "cavalry": "wh_main_emp_cav_empire_knights",
    "anti-large infantry": "wh_main_emp_inf_halberdiers",
    "heavy infantry": "wh_main_chs_inf_chaos_warriors_0",
    "light infantry": "wh_main_emp_inf_spearmen_0",
    "monster": "wh_main_grn_mon_giant",
}
REF_ATTACKERS = {
    "cavalry": "wh_main_emp_cav_empire_knights",
    "anti-large infantry": "wh_main_emp_inf_halberdiers",
    "heavy infantry": "wh_main_chs_inf_chaos_warriors_0",
}
_refs = {}


def ref(key):
    if key not in _refs:
        _refs[key] = card(key)
    return _refs[key]


def profile(c):
    off = {name: melee_dps(c, ref(k)) for name, k in REF_TARGETS.items()}
    tough = {name: c["hp"] / max(1e-6, melee_dps(ref(k), c)) for name, k in REF_ATTACKERS.items()}
    rng = {name: ranged_dps(c, ref(k)) for name, k in REF_TARGETS.items()} if c.get("missile") else None
    geo = lambda d: math.exp(sum(math.log(max(1e-6, v)) for v in d.values()) / len(d))
    power = math.sqrt(geo(off) * geo(tough))
    return dict(offence=off, toughness=tough, ranged=rng, power=power, off=geo(off), tough=geo(tough))
