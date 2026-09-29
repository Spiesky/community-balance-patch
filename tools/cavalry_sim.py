"""A regiment-against-regiment battle simulator for the cavalry study, on the game's own rules and constants.

Beyond cavalry_model.py's damage rules it runs, second by second:

  abilities   every ability on the unit, from unit_special_abilities and its phases:
                permanent passives            always on
                timed passives (By Our Blood, Murderous Prowess)   from the start, for their duration
                active abilities (Apocalyptic Charge)   used at the start, recharged and used again
                formations (the lance formation)        on the charge only
              each phase applies to the unit itself only when it targets self (auras for friends do not),
              and phases that target enemies (Blinding Radiance) apply to the opponent;
              stat effects, attributes granted (unbreakable, immune to psychology), healing
  fatigue     _kv_fatigue: combat and charging add fatigue; unit_fatigue_effects: winded, tired, very tired,
              exhausted each cut attack, charge, AP damage, defence, armour. fatigue_immune ignores it.
              Rates are read as per tick at 10 ticks a second (an assumption: exhausted after ~2.5 min of melee)
  morale      _kv_morale: leadership plus total-casualty and recent-casualty penalties (by share of HP lost),
              winning and losing combat, fear (-8, "unit frightened"), exhaustion. Morale below 0 breaks the
              unit; terror breaks it outright below 13. Immune to psychology ignores fear and terror;
              units that cause fear or terror are not frightened by it; unbreakable units never break.
              Undead and daemons do not rout: while broken they crumble (their instability damage).
  outcome     a unit loses when it routs, crumbles away or dies. Time limit 300 s.

Both regiments are fully engaged (every living model fights); the square-law result sits at the numbers-heavy end.
"""
import math

import cavalry_model as M
import vanilla as V

USA = V.index("unit_special_abilities")
JUNC = {}
for r in V.table("special_ability_to_special_ability_phase_junctions"):
    JUNC.setdefault(r["special_ability"], []).append(r)
PHASE = V.index("special_ability_phases", "id")
PHASE_ATTR = {}
for r in V.table("special_ability_phase_attribute_effects"):
    PHASE_ATTR.setdefault(r["phase"], []).append(r["attribute"])

FATIGUE = {r["key"]: float(r["value"]) for r in V.table("_kv_fatigue")}
FATIGUE_FX = {}
for r in V.table("unit_fatigue_effects"):
    FATIGUE_FX.setdefault(r["fatigue_level"], {})[r["stat"]] = float(r["value"])
MORALE = {r["key"]: float(r["value"]) for r in V.table("_kv_morale")}

TICKS = 10.0
LEVELS = [("threshold_exhausted", "exhausted"), ("threshold_very_tired", "very_tired"), ("threshold_tired", "tired"),
          ("threshold_winded", "winded"), ("threshold_active", "active")]
STAT_FIELD = dict(M.STAT_MAP, stat_armour="armour", scalar_speed=None)


def f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def _stat_effects(phase):
    return [(s, v, h) for s, v, h in M.PHASE_STATS.get(phase, [])]


def ability_plan(c):
    """[(kind, start, duration, recharge, uses, phase, on_self, on_enemy)] for the unit's abilities"""
    plan = []
    for ab in c["abilities"]:
        row = USA.get(ab, {})
        passive = row.get("passive") == "true"
        active_time = f(row.get("active_time"), -1)
        recharge = f(row.get("recharge_time"), -1)
        uses = int(f(row.get("num_uses"), -1))
        formation = "formation" in ab
        for j in JUNC.get(ab, []):
            ph = j["phase"]
            info = PHASE.get(ph, {})
            dur = f(info.get("duration"), -1)
            on_self = j.get("target_self") == "true" or (row.get("affect_self") == "true" and j.get("target_friends") != "true" and j.get("target_enemies") != "true")
            on_enemy = j.get("target_enemies") == "true"
            if not (on_self or on_enemy):
                continue                                   # auras for friends only
            if formation:
                kind = "charge"
            elif passive and dur == -1 and active_time == -1:
                kind = "permanent"
            elif passive:
                kind = "timed"
            else:
                kind = "active"
            plan.append(dict(kind=kind, phase=ph, duration=dur if dur > 0 else active_time, recharge=recharge,
                             uses=uses, on_self=on_self, on_enemy=on_enemy, behaviour=row.get("behaviour", "")))
    return plan


class Side:
    def __init__(self, card):
        self.base = dict(card)
        self.base.update(self._undo_folded(card))
        self.men = card["men"]
        self.pool = card["men"] * card["hp"]
        self.max_pool = self.pool
        self.plan = ability_plan(card)
        self.fatigue = FATIGUE["threshold_active"] * 0.7       # arrives having ridden in
        self.history = []                                      # (t, dealt, taken)
        self.routed = False
        self.broken_since = None
        self.attrs = set(card["attrs"])
        self.uses = {}

    @staticmethod
    def _undo_folded(card):
        """cavalry_model folds permanent self passives into the card; the simulator applies abilities itself"""
        c = M.card(card["key"]) if card.get("key") in M.MU else None
        if c is None:
            return {}
        raw = dict(c)
        for field, (add, mult) in M.passives(c["abilities"]).items():
            if field == "res_flame_weak":                  # folded into res_flame by card(); undo it there
                raw["res_flame"] = raw["res_flame"] - add * mult
                continue
            if mult and field in raw:
                raw[field] = raw[field] / mult - add
        overrides = {k: v for k, v in card.items() if k in raw and card[k] != c[k]}
        raw.update(overrides)
        return {k: raw[k] for k in ("ma", "md", "cb", "morale", "ward", "res_physical", "res_missile", "res_magic",
                                   "res_flame", "base", "ap", "armour") if k in raw}

    def alive(self):
        return max(0, math.ceil(self.pool / self.base["hp"] - 1e-9))

    def fatigue_level(self):
        if "fatigue_immune" in self.attrs:
            return None
        for key, name in LEVELS:
            if self.fatigue >= FATIGUE[key]:
                return key
        return None


def active_phases(side, t, charging):
    out = []
    for i, a in enumerate(side.plan):
        if a["kind"] == "permanent":
            out.append(a)
        elif a["kind"] == "charge":
            if charging:
                out.append(a)
        elif a["kind"] == "timed":
            if a["duration"] <= 0 or t < a["duration"]:
                out.append(a)
        elif a["kind"] == "active":
            dur = max(1.0, a["duration"])
            cycle = dur + max(0.0, a["recharge"]) if a["recharge"] > 0 else None
            if cycle:
                k = int(t // cycle)
                if (a["uses"] < 0 or k < a["uses"]) and (t - k * cycle) < dur:
                    out.append(a)
            elif t < dur:
                out.append(a)
    return out


def effective(side, other, t, charging):
    """the card this side fights with right now"""
    c = dict(side.base)
    attrs = set(side.attrs)
    mods = {}

    def push(stat, value, how):
        field = STAT_FIELD.get(stat)
        if not field:
            return
        add, mult = mods.get(field, (0.0, 1.0))
        mods[field] = (add + value, mult) if how == "add" else (add, mult * value)

    for a in active_phases(side, t, charging):
        if a["on_self"]:
            for s, v, h in _stat_effects(a["phase"]):
                push(s, v, h)
            attrs.update(PHASE_ATTR.get(a["phase"], []))
    for a in active_phases(other, t, charging):
        if a["on_enemy"]:
            for s, v, h in _stat_effects(a["phase"]):
                push(s, v, h)
    lvl = side.fatigue_level()
    if lvl and lvl in FATIGUE_FX:
        for s, v in FATIGUE_FX[lvl].items():
            push(s, v, "mult")
    for field, (add, mult) in mods.items():
        if field in c:
            c[field] = (c[field] + add) * mult
    c["res_flame"] = c.get("res_flame", 0.0)
    c["attrs"] = sorted(attrs)
    return c


def morale(side, other_card, own_card, t):
    lvl = MORALE
    m = own_card["morale"]
    lost = 1.0 - side.pool / side.max_pool
    for pct in (90, 80, 70, 60, 50, 40, 30, 20, 10):
        if lost * 100 >= pct:
            m += lvl["total_casualties_penalty_%d" % pct]
            break
    recent_taken = sum(tk for tt, dl, tk in side.history if t - tt <= 10.0)
    recent = recent_taken / side.max_pool * 100
    for pct in (50, 33, 15, 10, 6):
        if recent >= pct:
            m += lvl["recent_casualties_penalty_%d" % pct]
            break
    dealt = sum(dl for tt, dl, tk in side.history if t - tt <= 10.0)
    if recent_taken > 0 or dealt > 0:
        ratio = (dealt + 1e-6) / (recent_taken + 1e-6)
        if ratio > 2.0:
            m += lvl["winning_combat_significantly"]
        elif ratio > 1.5:
            m += lvl["winning_combat"]
        elif ratio > 1.1:
            m += lvl["winning_combat_slightly"]
        elif ratio < 0.5:
            m += lvl["losing_combat_significantly"]
        elif ratio < 0.9:
            m += lvl["losing_combat"]
    psych = "immune_to_psychology" in own_card["attrs"]
    if not psych and ("causes_fear" in other_card["attrs"] or "causes_terror" in other_card["attrs"]) \
            and "causes_fear" not in own_card["attrs"] and "causes_terror" not in own_card["attrs"]:
        m += lvl["ume_concerned_unit_frightened"]
    lvlname = side.fatigue_level()
    if lvlname == "threshold_exhausted":
        m += lvl["ume_concerned_exhausted"]
    elif lvlname == "threshold_very_tired":
        m += lvl["ume_concerned_very_tired"]
    return m


def undead(card):
    return "undead" in card["attrs"] or "daemonic" in card["attrs"]


def crumble_rate(side):
    for a in side.plan:
        if a["behaviour"] in ("undead_crumbling", "daemonic_instability"):
            dmg = PHASE.get(a["phase"], {}).get("damage_amount")
            return f(dmg, 20.0)
    return 20.0


def heal_rate(side, t):
    rate = 0.0
    for a in active_phases(side, t, False):
        if a["on_self"]:
            info = PHASE.get(a["phase"], {})
            if f(info.get("heal_amount")) > 0 and f(info.get("hp_change_frequency")) > 0:
                rate += f(info.get("heal_amount")) * side.max_pool / f(info.get("hp_change_frequency"))
    return rate


def fight(card_a, card_b, dt=0.5, limit=300.0):
    a, b = Side(card_a), Side(card_b)
    t = 0.0
    result = None
    while t < limit:
        charging = t < 1e-9
        ea, eb = effective(a, b, t, charging), effective(b, a, t, charging)
        na, nb = a.alive(), b.alive()
        if na <= 0 or nb <= 0:
            break
        if charging:
            da = na * M.blow(ea, eb, True)                  # the charge: every model's first blow
            db = nb * M.blow(eb, ea, True)
            step = min(ea["interval"], eb["interval"])
        else:
            da = na * M.blow(ea, eb) / ea["interval"] * dt
            db = nb * M.blow(eb, ea) / eb["interval"] * dt
            step = dt
        b.pool -= da
        a.pool -= db
        for s, dealt, taken in ((a, da, db), (b, db, da)):
            s.history.append((t, dealt, taken))
            s.history = [h for h in s.history if t - h[0] <= 10.0]
            s.fatigue += (FATIGUE["charging"] if charging else FATIGUE["combat"]) * TICKS * step
            s.pool = min(s.max_pool, s.pool + heal_rate(s, t) * step)
        t += step
        for s, other, es, eo in ((a, b, ea, eb), (b, a, eb, ea)):
            if s.pool <= 0:
                continue
            m = morale(s, eo, es, t)
            unbreakable = "unbreakable" in es["attrs"]
            terror = ("causes_terror" in eo["attrs"] and "immune_to_psychology" not in es["attrs"]
                      and "causes_terror" not in es["attrs"] and m < MORALE["morale_shock_terror_morale_threshold_short"])
            if unbreakable:
                continue
            if undead(es):
                if m < 0:
                    s.pool -= crumble_rate(s) * step
                continue
            if m < 0 or terror:
                s.routed = True
        if a.routed or b.routed or a.pool <= 0 or b.pool <= 0:
            break
    left_a, left_b = max(0.0, a.pool) / a.max_pool, max(0.0, b.pool) / b.max_pool
    if (a.routed or a.pool <= 0) and not (b.routed or b.pool <= 0):
        winner = "B"
    elif (b.routed or b.pool <= 0) and not (a.routed or a.pool <= 0):
        winner = "A"
    else:
        winner = "A" if left_a > left_b else "B"
    how = "rout" if (a.routed or b.routed) else ("destroyed" if min(a.pool, b.pool) <= 0 else "time")
    return dict(winner=winner, how=how, time=t, left_a=left_a, left_b=left_b)


def equal_gold(card_a, card_b):
    """B scaled to A's gold (men rounded); the cards' own costs"""
    if not card_a["cost"] or not card_b["cost"]:
        return None
    b = dict(card_b)
    b["men"] = max(1, round(card_b["men"] * card_a["cost"] / card_b["cost"]))
    return fight(card_a, b)
