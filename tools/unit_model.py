#!/usr/bin/env python3
"""The combat model behind the great rebalance: a fighting card and a power measure for every recruitable unit in the
game, whatever its caste. It keeps cavalry_model.py's melee rules (hit chance, armour, bonuses, splash, charge, passives)
and adds what the other castes need:

  entities      the thing that fights and dies. Infantry, cavalry, beasts and monsters: one model. Chariots and war
                machines: the vehicle (land_units.num_engines), whose HP is what the health bar shows, with the crew
                as its attackers. A monster with a crew (a stegadon, a lantern) is one entity.
  radius        the entity's collision radius; for capsules and ellipses the geometric mean of the two axes, so a long
                monster is not counted as a round one twelve metres across.
  shields       unit_shield_types.missile_block_chance: a share of missiles from the front are blocked outright.
  missiles      the primary missile weapon, or the engine's for artillery. Per shot: hit chance from the projectile's
                calibration against the target's size (single entities are hard to hit, blocks are not), damage with
                armour and resistances, explosions spread over the models in their radius, penetration through ranks.
                Volley = projectiles x shots per volley x burst; rate from the reload time; capped by ammunition over a
                shooting window; longer range earns more volleys before contact.
  abilities     breath attacks, dropped rocks and bound bolts (unit_special_abilities with an activated projectile or a
                bombardment): the projectile's damage per use, the uses a battle window affords (one plus the window
                over the recharge, capped by num_uses), per entity where every entity fires it, once per unit otherwise.
                Permanent passives with a bombardment (the Rogue Idol's rubble) are auras and are left out.
  collision     mass and charge speed, as a proxy for what a chariot or monster does by running into things: the
                game's collision damage rules (_kv_rules: collision_damage_maximum 70, modifier 0.6) give an expected
                damage per model hit; the number hit per charge is the weapon's collision_attack_max_targets.
  reference opponents   the same five melee targets as the cavalry study (Empire Knights, Halberdiers, Chaos Warriors,
                Spearmen, a Giant), three melee attackers, and two missile attackers (Crossbowmen, base damage;
                Handgunners, armour-piercing) so that armour and shields are both priced.

Per regiment, against each reference regiment, frontage-limited: the attackers that fight at once are all of them or
as many as fit around the targets (FRONT_C x (R + r) / r of radius r around an entity of radius R). A giant is fought
by the dozen halberdiers that fit around it, a knight by the two that reach him, a swordsman by one. This sits Lanchester's
square law (everyone fights) and linear law (frontage decides) side by side without choosing.
  off_melee    total melee damage per second, sustained with a charge every 30 s (geometric mean over the five targets)
  off_ranged   total missile damage per second, ammunition and range folded in (mean over the five targets)
  off_impact   total collision damage per second of a charge cycle (mean; chariots, monsters, heavy cavalry)
  off_ability  total breath-attack and bombardment damage per second over the battle window (mean)
  tough_melee  seconds the regiment lasts against a reference regiment (geometric mean over the three attackers)
  tough_missile  the same against the two missile regiments, shields and missile resistance counted
  power_reg    sqrt(offence x toughness) with the composition weights in WEIGHTS; the Empire Knights regiment = 1.00
  power        per model: power_reg / entities x 60, so a 60-model unit of Empire Knight quality reads 1.00 per model
The survey (rebalance_survey.py) fits the weights and the price curve from the game's own prices.

Everything is read from the vanilla dump (vanilla.py). Nothing here is a proposal; rebalance_solve.py makes those.
"""
import math
import os
import re
import glob

import vanilla as V
import cavalry_model as CM

f = CM.f
SIZE_RANK = CM.SIZE_RANK
BE, MO, LU, MU, MW, MIS, PJ, AR = CM.BE, CM.MO, CM.LU, CM.MU, CM.MW, CM.MIS, CM.PJ, CM.AR
SH = {r["key"]: f(r["missile_block_chance"]) for r in V.table("unit_shield_types")}
ENG = V.index("battlefield_engines")
EXPL = V.index("projectiles_explosions")
PEN = {r["key"]: (r["entity_size_cap"], f(r["max_penetration"], 0)) for r in V.table("projectile_penetration_junctions")}
RULES = {r["key"]: f(r["value"]) for r in V.table("_kv_rules")}
FACTIONS = V.index("factions")

# ---- composition weights. The survey (rebalance_survey.py) fits these from vanilla prices; the numbers here are its
# result, so that every script agrees on what "power" means.
WEIGHTS = dict(               # the survey's fit of 2026-09-16 (_survey.json carries the live values)
    ranged=1.0,        # a point of missile dps per model counted against a point of melee dps
    impact=0.5,        # a point of collision dps
    ability=0.0,       # a point of breath-attack or bombardment dps: measured, but the prices show no premium for it
    missile_tough=0.3, # share of toughness that is toughness against missiles (geometric blend)
    range_exp=0.5,     # off_ranged x (range / 150) ^ range_exp
    window=240.0,      # seconds of shooting a battle affords; ammunition beyond it is worth nothing
    reach=2.0,         # ranks of attackers that reach the exposed edge of a regiment (engagement geometry)
)
CHARGE_EVERY = CM.CHARGE_EVERY

CASTES = ("melee_infantry", "missile_infantry", "monstrous_infantry", "melee_cavalry", "missile_cavalry",
          "monstrous_cavalry", "war_beast", "monster", "chariot", "warmachine")
VEHICLE = ("chariot", "warmachine")

SUBCULTURE = {
    "wh_main_sc_emp_empire": "emp", "wh_main_sc_brt_bretonnia": "brt", "wh_main_sc_vmp_vampire_counts": "vmp",
    "wh_main_sc_grn_greenskins": "grn", "wh_main_sc_dwf_dwarfs": "dwf", "wh_main_sc_chs_chaos": "chs",
    "wh_dlc03_sc_bst_beastmen": "bst", "wh_dlc05_sc_wef_wood_elves": "wef", "wh_dlc08_sc_nor_norsca": "nor",
    "wh2_main_sc_hef_high_elves": "hef", "wh2_main_sc_def_dark_elves": "def", "wh2_main_sc_lzd_lizardmen": "lzd",
    "wh2_main_sc_skv_skaven": "skv", "wh2_dlc09_sc_tmb_tomb_kings": "tmb", "wh2_dlc11_sc_cst_vampire_coast": "cst",
    "wh3_main_sc_kho_khorne": "kho", "wh3_main_sc_nur_nurgle": "nur", "wh3_main_sc_sla_slaanesh": "sla",
    "wh3_main_sc_tze_tzeentch": "tze", "wh3_main_sc_ksl_kislev": "ksl", "wh3_main_sc_cth_cathay": "cth",
    "wh3_main_sc_ogr_ogre_kingdoms": "ogr", "wh3_dlc23_sc_chd_chaos_dwarfs": "chd", "wh3_main_sc_dae_daemons": "dae",
}
FACTION_NAMES = {
    "emp": "The Empire", "brt": "Bretonnia", "vmp": "Vampire Counts", "grn": "Greenskins", "dwf": "Dwarfs",
    "chs": "Warriors of Chaos", "bst": "Beastmen", "wef": "Wood Elves", "nor": "Norsca", "hef": "High Elves",
    "def": "Dark Elves", "lzd": "Lizardmen", "skv": "Skaven", "tmb": "Tomb Kings", "cst": "Vampire Coast",
    "kho": "Khorne", "nur": "Nurgle", "sla": "Slaanesh", "tze": "Tzeentch", "ksl": "Kislev", "cth": "Grand Cathay",
    "ogr": "Ogre Kingdoms", "chd": "Chaos Dwarfs", "dae": "Daemons of Chaos",
}

_unit_factions = {}
for r in V.table("units_custom_battle_permissions"):
    sc = FACTIONS.get(r["faction"], {}).get("subculture", "")
    if sc in SUBCULTURE:
        _unit_factions.setdefault(r["unit"], set()).add(SUBCULTURE[sc])
_military = {r["unit"] for r in V.table("units_to_groupings_military_permissions")}

_names = {}
for path in glob.glob(os.path.join(V.DUMP, "text", "**", "*land_units*.tsv"), recursive=True):
    try:
        for line in open(path, encoding="utf-8", errors="replace"):
            if line.startswith("land_units_onscreen_name_"):
                a = line.rstrip("\n").split("\t")
                _names[a[0][len("land_units_onscreen_name_"):]] = a[1]
    except OSError:
        pass


def name(key):
    mu = MU.get(key)
    return _names.get(mu["land_unit"], key) if mu else key


def factions(key):
    return sorted(_unit_factions.get(key, ()))


def faction(key):
    fs = factions(key)
    m = re.search(r"_(emp|brt|cst|vmp|tmb|chs|nor|kho|nur|sla|tze|hef|def|wef|lzd|grn|ogr|ksl|cth|chd|bst|dwf|skv|dae)_", key)
    own = m.group(1) if m else None
    if own in fs or (own and not fs):
        return own
    if "chs" in fs and len(fs) > 1:
        fs = [x for x in fs if x != "chs"] + ["chs"]     # the god factions share Warriors of Chaos units
    return fs[0] if fs else (own or "?")


EXCLUDE = re.compile(r"_(qb|dm|mp|summoned|tutorial|boss)\b|_blessed$|_nakai$|_dechala$|_waaagh_|_pro_|^wh3_main_pro|chieftain|imperial_supply|_cp1_|_ror_summ|_summon")


def recruitable():
    """every unit the rebalance is about: non-character, in a custom battle or military permission table"""
    out = []
    for k, m in sorted(MU.items()):
        if m["caste"] not in CASTES or m["land_unit"] not in LU:
            continue
        if EXCLUDE.search(k):
            continue
        if k not in _unit_factions and k not in _military:
            continue
        out.append(k)
    return out


# ------------------------------------------------------------------------------------------------------ the card

def projectile_card(pkey):
    """what a projectile does per shot, as ranged_shot() needs it; None if the key is not a projectile"""
    p = PJ.get(pkey)
    if not p:
        return None
    ex = EXPL.get(p.get("explosion_type", ""), {})
    cap, maxpen = PEN.get(p.get("projectile_penetration", ""), ("", 0))
    volley = max(1.0, f(p["projectile_number"], 1)) * max(1.0, f(p["shots_per_volley"], 1)) * max(1.0, f(p["burst_size"], 1))
    return dict(
        projectile=p["key"], category=p["category"],
        base=f(p["damage"]), ap=f(p["ap_damage"]), bvl=f(p["bonus_v_large"]), bvi=f(p["bonus_v_infantry"]),
        reload=max(0.5, f(p["base_reload_time"], 10)), volley=volley, range=f(p["effective_range"]),
        magical=p.get("is_magical") == "true" or ex.get("is_magical") == "true",
        flaming=f(p.get("ignition_amount")) > 0 or f(ex.get("ignition_amount")) > 0,
        calibration=max(0.1, f(p.get("calibration_area"), 5.0)),
        ex_radius=f(ex.get("detonation_radius")), ex_base=f(ex.get("detonation_damage")), ex_ap=f(ex.get("detonation_damage_ap")),
        pen_cap=cap, pen_max=maxpen if maxpen >= 0 else 10,
        contact=p.get("contact_stat_effect", "") or ex.get("contact_phase_effect", ""),
    )


def missile_card(key, lu):
    """the ranged weapon: the unit's own, or its engine's"""
    mkey = lu.get("primary_missile_weapon") or ENG.get(lu.get("engine", ""), {}).get("missile_weapon", "")
    if not mkey or mkey not in MIS:
        return None
    m = projectile_card(MIS[mkey]["default_projectile"])
    if not m:
        return None
    m.update(key=mkey, ammo=f(lu.get("primary_ammo")))
    return m


USA = V.index("unit_special_abilities")
BOMB = {r["bombardment_key"]: r for r in V.table("projectile_bombardments")}


def ability_cards(abilities):
    """the unit's damaging abilities (breath attacks, dropped rocks, bound bolts): each a projectile card with the
    shots it fires per use, the uses a battle affords and whether every entity fires it or the unit once"""
    out = []
    for ab in abilities:
        row = USA.get(ab)
        if not row:
            continue
        recharge, uses, passive = f(row.get("recharge_time"), -1), int(f(row.get("num_uses"), -1)), row.get("passive") == "true"
        if passive and recharge <= 0:
            continue                                     # a permanent passive with a bombardment is an aura, not a weapon
        if row.get("activated_projectile"):
            m = projectile_card(row["activated_projectile"])
            per_entity, n_proj = False, 1.0
        elif row.get("bombardment") and row["bombardment"] in BOMB:
            b = BOMB[row["bombardment"]]
            m = projectile_card(b["projectile_type"])
            per_entity, n_proj = b.get("launch_source") == "activaters_entities", max(1.0, f(b.get("num_projectiles"), 1))
        else:
            continue
        if not m or (m["base"] + m["ap"] + m["ex_base"] + m["ex_ap"]) <= 0:
            continue
        m.update(ability=ab, uses=uses, recharge=recharge, n_proj=n_proj, per_entity=per_entity)
        out.append(m)
    return out


def card(key, label=None, **over):
    """the fighting card of a main unit, passives folded in; keyword arguments override fields"""
    mu = MU[key]
    lu = LU[mu["land_unit"]]
    w = MW.get(lu["primary_melee_weapon"], {})
    man = BE[lu["man_entity"]]
    mount = BE.get(MO.get(lu["mount"], {}).get("entity", ""), {})
    engine = ENG.get(lu.get("engine", ""), {})
    eng_ent = BE.get(engine.get("battle_entity", ""), {})
    caste = mu["caste"]
    men = int(f(mu["num_men"]))
    n_eng = int(f(lu.get("num_engines")))
    n_mnt = int(f(lu.get("num_mounts")))
    if n_eng > 0:
        entities, crew = n_eng, max(1, men // n_eng)             # chariots and war machines: the vehicles
    elif 0 < n_mnt < men:
        entities, crew = n_mnt, max(1, men // n_mnt)             # a stegadon and its skinks, a lantern and its crew
    else:
        entities, crew = men, 1
    body = mount or man
    if caste == "warmachine" and eng_ent:
        hp = f(eng_ent.get("hit_points")) + f(lu["bonus_hit_points"])
        body = eng_ent
    else:
        hp = f(man["hit_points"]) + f(mount.get("hit_points")) + f(lu["bonus_hit_points"])
    c = dict(
        key=key, label=label or name(key), caste=caste, category=lu["category"], klass=lu["class"],
        faction=faction(key), factions=factions(key), tier=int(f(mu.get("tier"), 0)),
        renown=mu.get("is_renown") == "true" or "_ror" in key, cap=int(f(mu.get("campaign_cap"), -1)),
        men=entities, crew=crew, cost=int(f(mu["recruitment_cost"])), upkeep=int(f(mu["upkeep_cost"])),
        ma=f(lu["melee_attack"]), md=f(lu["melee_defence"]), cb=f(lu["charge_bonus"]), morale=f(lu["morale"]),
        hp=hp, armour=AR.get(lu["armour"], 0.0), armour_key=lu["armour"], shield=SH.get(lu["shield"], 0.0),
        base=f(w.get("damage")), ap=f(w.get("ap_damage")), bvl=f(w.get("bonus_v_large")), bvi=f(w.get("bonus_v_infantry")),
        interval=f(w.get("melee_attack_interval"), 4.0) or 4.0, weapon=lu["primary_melee_weapon"],
        splash_size=w.get("splash_attack_target_size") or "", splash_n=f(w.get("splash_attack_max_attacks"), 1),
        splash_mult=f(w.get("splash_attack_power_multiplier"), 1) or 1.0,
        collision_n=f(w.get("collision_attack_max_targets")),
        magical=w.get("is_magical") == "true", flaming=f(w.get("ignition_amount")) > 0,
        ward=f(lu["damage_mod_all"]), res_physical=f(lu["damage_mod_physical"]), res_missile=f(lu["damage_mod_missile"]),
        res_magic=f(lu["damage_mod_magic"]), res_flame=f(lu["damage_mod_flame"]), res_flame_weak=0.0,
        speed=f(body.get("run_speed")), charge_speed=f(body.get("charge_speed")) or f(body.get("run_speed")),
        mass=f(man.get("mass")) + f(mount.get("mass")) + f(eng_ent.get("mass")),
        radius=f(body.get("radius"), 0.6) * (math.sqrt(min(1.0, f(body.get("radii_ratio"), 1.0) or 1.0)) if body.get("shape", "circle") != "circle" else 1.0),
        size=body.get("size", "small"),
        attrs=CM.ATTR.get(lu["attribute_group"], []), abilities=CM.ABIL.get(mu["land_unit"], []),
        missile=missile_card(key, lu), ability_shots=ability_cards(CM.ABIL.get(mu["land_unit"], [])),
    )
    for field, (add, mult) in CM.passives(c["abilities"]).items():
        c[field] = (c[field] + add) * mult
    c["res_flame"] += c.pop("res_flame_weak")
    c["flying"] = "flying" in c["attrs"] or "flight" in c["attrs"]
    c.update(over)
    return c


# --------------------------------------------------------------------------------------------------- the rules

is_large = CM.is_large
armour_block = CM.armour_block
resist = CM.resist


def attackers(att):
    """melee attacks per entity per swing: a chariot's two crew both strike; a war machine's crew do not fight for it"""
    if att["caste"] == "chariot":
        return min(2, att.get("crew", 1))
    return 1


def blow(att, dfn, charging=False):
    """expected damage of one melee attack by one entity"""
    return CM.blow(att, dfn, charging) * attackers(att)


def melee_dps(att, dfn):
    sustained = blow(att, dfn) / att["interval"]
    burst = max(0.0, blow(att, dfn, True) - blow(att, dfn))
    return sustained + burst / CHARGE_EVERY


# expected models inside an explosion or along a penetrating shot, by what the target is
DENSITY = {"very_small": 0.6, "small": 0.45, "medium": 0.12, "large": 0.06, "very_large": 0.0}   # models per m2 in close order
BLOCK_WIDTH = 30.0          # metres of infantry block a shot can land in and still hit something
SINGLE_HIT = 2.0            # a single entity of radius R is hit with chance min(1, SINGLE_HIT x R / calibration)
EX_FALLOFF = 0.35           # share of the models in an explosion's radius that take its full damage (falloff, thin blobs)
EX_CAP = 15.0               # and never more than this many per detonation
PEN_RANKS = 3.0             # a penetrating shot goes through at most this many ranks of small models
MAX_SHOTS_PER_S = 3.0       # no weapon fires faster than this, whatever its burst figures say


def ranged_shot(m, dfn):
    """expected damage of one projectile against one target unit (not per model): hit chance, damage, spread"""
    single = dfn["men"] <= 1
    if single:
        acc = min(1.0, SINGLE_HIT * dfn["radius"] / m["calibration"])
    else:
        acc = min(1.0, (BLOCK_WIDTH + 2 * m["ex_radius"]) / m["calibration"])
    base = m["base"] + (m["bvl"] if is_large(dfn) else m["bvi"])
    r = dfn["ward"] + dfn["res_missile"] + (dfn["res_magic"] if m["magical"] else dfn["res_physical"]) + (dfn["res_flame"] if m["flaming"] else 0.0)
    r = max(-100.0, min(90.0, r))
    dmg = (base * (1.0 - armour_block(dfn["armour"])) + m["ap"]) * (1.0 - r / 100.0)
    dmg *= 1.0 - dfn["shield"] / 100.0 * 0.5             # half the shots come from the front arc
    hits = 1.0
    if m["pen_max"] > 0 and not single and not (m["pen_cap"] and SIZE_RANK.get(dfn["size"], 1) >= SIZE_RANK.get(m["pen_cap"], 9)):
        hits += min(m["pen_max"], PEN_RANKS) * DENSITY.get(dfn["size"], 0.4) / 0.45
    total = acc * dmg * hits
    if m["ex_radius"] > 0 and (m["ex_base"] + m["ex_ap"]) > 0:
        ex = (m["ex_base"] * (1.0 - armour_block(dfn["armour"])) + m["ex_ap"]) * (1.0 - r / 100.0)
        n = 1.0 if single else min(EX_CAP, 1.0 + EX_FALLOFF * DENSITY.get(dfn["size"], 0.4) * math.pi * m["ex_radius"] ** 2)
        total += acc * ex * n
    return total


def ranged_dps(att, dfn):
    """missile damage per second of one entity, ammunition and range folded in"""
    m = att.get("missile")
    if not m or m["ammo"] <= 0:
        return 0.0
    per_shot = ranged_shot(m, dfn)
    rate = per_shot * min(m["volley"] / m["reload"], MAX_SHOTS_PER_S)
    ammo_factor = min(1.0, m["ammo"] * m["reload"] / WEIGHTS["window"])
    range_factor = (max(30.0, m["range"]) / 150.0) ** WEIGHTS["range_exp"]
    return rate * ammo_factor * range_factor


def ability_dps(att, dfn, window):
    """damage per second from breath attacks and bombardments over a battle window, as (per-entity, per-unit) parts"""
    per_entity = per_unit = 0.0
    for m in att.get("ability_shots", []):
        per_use = ranged_shot(m, dfn) * m["volley"] * m["n_proj"]
        n = 1 + (window / m["recharge"] if m["recharge"] > 0 else 0)
        if m["uses"] > 0:
            n = min(n, m["uses"])
        dps = per_use * n / window
        if m["per_entity"]:
            per_entity += dps
        else:
            per_unit += dps
    return per_entity, per_unit


def impact_dps(att, dfn):
    """collision damage per second of a charge cycle: mass and speed against the target, capped by the game's rules"""
    if att["mass"] <= 0 or att["collision_n"] <= 0 and att["caste"] not in ("chariot", "monster", "monstrous_cavalry"):
        return 0.0
    if dfn["men"] <= 1:
        return 0.0                                          # nothing knocks a giant over
    ratio = att["mass"] / max(1.0, dfn["mass"])
    if ratio < 1.5:
        return 0.0
    momentum = att["charge_speed"] * min(ratio, 10.0) * RULES.get("collision_damage_modifier", 0.6)
    dmg = min(RULES.get("collision_damage_maximum", 70.0), momentum)
    dmg = dmg * (1.0 - armour_block(dfn["armour"]) * (1 - RULES.get("collision_damage_armour_penetration_ratio", 0.7)))
    n = max(att["collision_n"], 3.0 if att["caste"] == "chariot" else 1.0)
    return dmg * n / CHARGE_EVERY


# ------------------------------------------------------------------------------------------ reference opponents

REF_TARGETS = dict(CM.REF_TARGETS)
REF_ATTACKERS = dict(CM.REF_ATTACKERS)
REF_SHOOTERS = {"crossbows": "wh_main_emp_inf_crossbowmen", "handguns": "wh_main_emp_inf_handgunners"}
_refs = {}


def ref(key):
    if key not in _refs:
        _refs[key] = card(key)
    return _refs[key]


def geo(d):
    return math.exp(sum(math.log(max(1e-6, v)) for v in d.values()) / len(d))


def mean(d):
    return sum(d.values()) / len(d)


PACKING = 1.1               # a close-order formation covers PACKING x N x (2R)^2 of ground


def footprint(n, R):
    """radius of the ground a regiment of n entities of radius R stands on"""
    return math.sqrt(PACKING * n * (2 * R) ** 2 / math.pi)


def engaged(n_att, r_att, n_tgt, R_tgt, reach):
    """attackers that fight at once: all of them, or as many as line the exposed half of the targets' footprint,
    reach ranks deep. One swordsman in a block of 120 is fought by a third of a halberdier; a giant by a dozen."""
    return min(n_att, math.pi * footprint(n_tgt, R_tgt) * reach / (2 * max(0.3, r_att)))


def pieces(c):
    """everything the composition needs, per model, with the geometry to derive engagement under any weights"""
    out = dict(n=c["men"], R=c["radius"], hp=c["hp"], melee={}, ranged={}, impact={}, ability={}, taken={}, shot={}, targets={},
               ranged_meta=(c["missile"]["ammo"], c["missile"]["reload"], c["missile"]["range"]) if c["missile"] else None)
    for n, k in REF_TARGETS.items():
        t = ref(k)
        out["targets"][n] = (t["men"], t["radius"])
        out["melee"][n] = melee_dps(c, t)
        m = c["missile"]
        out["ranged"][n] = ranged_shot(m, t) * min(m["volley"] / m["reload"], MAX_SHOTS_PER_S) if m and m["ammo"] > 0 else 0.0
        out["impact"][n] = impact_dps(c, t)
        out["ability"][n] = ability_dps(c, t, WEIGHTS["window"])          # (per entity, per unit), for the default window
    for n, k in REF_ATTACKERS.items():
        a = ref(k)
        out["taken"][n] = (a["men"], a["radius"], melee_dps(a, c))
    for n, k in REF_SHOOTERS.items():
        s = ref(k)
        m = s["missile"]
        out["shot"][n] = (s["men"], ranged_shot(m, c) * min(m["volley"] / m["reload"], MAX_SHOTS_PER_S))
    return out


def compose(p, W):
    """the regiment against each reference regiment, frontage-limited (Lanchester between the square and linear laws):
    a giant is fought by the dozen halberdiers that fit around it, a swordsman in a block by a third of one.
    Totals are for the whole regiment; per-model figures divide by the entities."""
    N, R, reach = p["n"], p["R"], W["reach"]
    off_m, off_r, off_i, off_a = {}, {}, {}, {}
    rf = 1.0
    if p["ranged_meta"]:
        ammo, reload, rng = p["ranged_meta"]
        rf = min(1.0, ammo * reload / W["window"]) * (max(30.0, rng) / 150.0) ** W["range_exp"]
    for n, (M, r) in p["targets"].items():
        off_m[n] = engaged(N, R, M, r, reach) * p["melee"][n]
        off_r[n] = N * p["ranged"][n] * rf
        off_i[n] = N * p["impact"][n]
        pe, pu = p.get("ability", {}).get(n, (0.0, 0.0))
        off_a[n] = N * pe + pu
    life_m = {n: N * p["hp"] / max(1e-6, engaged(M, r, N, R, reach) * dps) for n, (M, r, dps) in p["taken"].items()}
    life_r = {n: N * p["hp"] / max(1e-6, M * dps) for n, (M, dps) in p["shot"].items()}
    off_melee, off_ranged, off_impact, off_ability = geo(off_m), mean(off_r), mean(off_i), mean(off_a)
    tm, tr = geo(life_m), geo(life_r)
    w = W["missile_tough"]
    tough = tm ** (1 - w) * tr ** w
    off = off_melee + W["ranged"] * off_ranged + W["impact"] * off_impact + W.get("ability", 0.0) * off_ability
    power_reg = math.sqrt(max(1e-9, off) * tough)
    return dict(offence=off_m, ranged=off_r, impact=off_i, ability=off_a, toughness=life_m, tough_missile=life_r,
                off_melee=off_melee, off_ranged=off_ranged, off_impact=off_impact, off_ability=off_ability,
                tough_melee=tm, tough_ranged=tr, off=off, tough=tough, power_reg=power_reg, power=power_reg / N)


def profile(c, W=None):
    return compose(pieces(c), W or WEIGHTS)


_ek = None


def ek():
    """the Empire Knights regiment's power, the unit of the scale"""
    global _ek
    if _ek is None:
        _ek = profile(ref("wh_main_emp_cav_empire_knights"))["power_reg"]
    return _ek


def reset():
    """after WEIGHTS change"""
    global _ek
    _ek = None


def regiment_power(c):
    """the regiment, Empire Knights = 1.00"""
    return profile(c)["power_reg"] / ek()


def power(c):
    """per model, on the same scale: a unit of 60 models each as good as an Empire Knight has 60 x 1/60 = 1.00 per model"""
    return regiment_power(c) / c["men"] * 60.0


def identity(c):
    """the shape of a unit, independent of its magnitude: the shares of its power that come from each source, and
    its matchup profile. Two cards with the same identity vector fight the same way at different sizes."""
    pr = profile(c)
    om = pr["offence"]
    tot = sum(om.values()) or 1.0
    v = {"match_" + n: om[n] / tot for n in om}
    off = pr["off"] or 1e-9
    v["share_melee"] = pr["off_melee"] / off
    v["share_ranged"] = WEIGHTS["ranged"] * pr["off_ranged"] / off
    v["share_impact"] = WEIGHTS["impact"] * pr["off_impact"] / off
    v["share_ability"] = WEIGHTS.get("ability", 0.0) * pr["off_ability"] / off
    dmg = c["base"] + c["ap"] or 1e-9
    v["ap_share"] = c["ap"] / dmg
    v["charge_share"] = c["cb"] / max(1.0, c["ma"] + c["cb"])
    v["off_over_tough"] = math.log(max(1e-6, pr["off"]) / max(1e-6, pr["tough"]))
    return v


def identity_drift(a, b):
    """1 - cosine similarity of the matchup and share components; 0 means the unit fights exactly the same way"""
    ia, ib = identity(a), identity(b)
    keys = [k for k in ia if k.startswith("match_") or k.startswith("share_")]
    dot = sum(ia[k] * ib[k] for k in keys)
    na = math.sqrt(sum(ia[k] ** 2 for k in keys)) or 1e-9
    nb = math.sqrt(sum(ib[k] ** 2 for k in keys)) or 1e-9
    return 1.0 - dot / (na * nb)


if __name__ == "__main__":
    import sys
    keys = sys.argv[1:] or ["wh_main_emp_cav_empire_knights", "wh_main_emp_inf_swordsmen", "wh_main_emp_inf_handgunners",
                            "wh_main_emp_art_great_cannon", "wh_main_chs_cav_chaos_chariot", "wh_main_grn_mon_giant",
                            "wh3_main_ogr_inf_ogres_0", "wh_main_vmp_mon_dire_wolves", "wh_main_emp_veh_steam_tank",
                            "wh2_main_lzd_mon_stegadon_1", "wh_main_emp_veh_luminark_of_hysh_0", "wh_main_vmp_inf_zombie"]
    for k in keys:
        c = card(k)
        pr = profile(c)
        print("%-32s %-18s n=%3d hp=%6.0f | melee %6.1f ranged %6.1f impact %5.1f | life m %6.0f r %6.0f | reg %6.2f per model %5.2f  cost %d" % (
            c["label"][:32], c["caste"], c["men"], c["hp"], pr["off_melee"], pr["off_ranged"], pr["off_impact"],
            pr["tough_melee"], pr["tough_ranged"], regiment_power(c), power(c), c["cost"]))
