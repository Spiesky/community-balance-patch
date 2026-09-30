#!/usr/bin/env python3
"""The solver: turn the survey's residuals and the lore targets into stat and price proposals that keep every unit's
identity.

    python3 rebalance_solve.py            -> ../reports/proposals.md and _rebalance.json (what build_rebalance.py writes)

Three layers, in order of authority:

  decided     decided.STATS: hand-set units, numbers already decided. Written as they are.
  lore        cavalry_rebalance.LORE for cavalry (the study's per-model targets with its unit-size changes, carried over
              as a ratio: the study measured "how much stronger than vanilla the lore wants this unit" on its own model)
              and lore_ladder.LADDER for everything else (rated on this model's scale; keep = vanilla is the lore, nothing
              moves; target None = the stats are the lore, the price moves). Price goes to what the valuation says the
              new unit is worth, within LORE_PRICE_CAP of vanilla.
  price       everything else: the unit's residual against its caste's price line. Inside the tolerance band nothing
              moves. Outside it, castes whose prices track measured power (infantry and cavalry) have their stats moved
              to what the price pays for, up to a cap; castes CA prices flat (monsters, war beasts, chariots, war
              machines) have their price moved to what the stats are worth. Past the cap the rest goes to price.

Identity. A change moves a unit along its own ray: every damage figure (melee base, armour-piercing, bonus vs large,
bonus vs infantry; the same for the missile) and its hit points scale by one factor k, attack and defence move together
by K ln k, and nothing else changes: charge bonus, armour, speed, mass, size, shield, resistances, abilities, weapon type,
splash and attack interval are the unit's shape and stay. The matchup profile (how its damage divides between cavalry,
halberdiers, heavy and light infantry and monsters) is therefore the same before and after, which identity_drift checks.
The solver bisects k until the regiment reaches its target power.

What it writes per unit: the land_units fields, a per-unit copy of the melee weapon (weapons are shared between units,
so a shared row is never edited), a per-unit copy of the projectile and missile weapon where the unit shoots, and the
main_units prices (multiplayer, campaign and upkeep scaled together; a campaign price of 0 stays 0).
"""
import json
import math
import os
import re
import sys

import unit_model as UM
import cavalry_model as CM
import cavalry_rebalance as CR
import lore_ladder as LL
import decided
import gunpowder as GP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SURVEY = os.path.join(HERE, "_survey.json")
OUT_MD = os.path.join(ROOT, "reports", "proposals.md")
OUT_JSON = os.path.join(HERE, "_rebalance.json")
BETA_JSON = os.path.join(HERE, "_beta.json")   # what the beta ships: the lore elites and the gunpowder rule only

# Close to vanilla: the patch adjusts CA's balance so it makes more sense, it does not replace it.
RESIZE = False              # unit sizes stay vanilla (the ladder's sizes are community questions, e.g. units/blood_knights.md)
POWER_LIMIT = math.log(1.20)   # the most any unit's regiment power moves, up or down
PRICE_LIMIT = math.log(1.20)   # the most any price moves, up or down
FLAT_CASTES_MOVE = False    # monsters, war beasts, chariots, war machines stay vanilla: the campaign says they are too strong,
                            # multiplayer says many are too weak, and the model understands them least

# The exception: the lore's elite cavalry are fewer and far stronger than vanilla makes them. They take the lore's size
# and strength in full, never end up with less total health than vanilla, and their price follows their power (within
# ELITE_PRICE_CAP). Everything else stays close to vanilla.
ELITE = re.compile(r"vmp_blood_knights|vmp_cav_blood_knights|brt_cav_grail_knights|brt_cav_grail_guardians|chs_cav_chaos_knights_ror_0")
ELITE_PRICE_CAP = math.log(1.6)

TOLERANCE = 0.15            # |residual| inside this band (one robust sigma): the unit is fine, nothing moves
CAP = POWER_LIMIT           # the most a unit's regiment power moves through the price layer
PRICE_CAP = PRICE_LIMIT     # the most a price moves
LORE_PRICE_CAP = PRICE_LIMIT   # a lore unit's price goes to what the valuation says it is worth, within this of vanilla
# units added to the game after the ladder was written (update 25507028, 2026-09-24): kept as vanilla until reviewed
UNREVIEWED = {l.split()[0] for l in open(os.path.join(HERE, "unreviewed.txt")) if l.strip() and not l.startswith("#")}
VETO = set()                # units whose stats must not move whatever the residual says (price may): add keys here
STAT_CASTES = {"melee_infantry", "missile_infantry", "monstrous_infantry", "melee_cavalry", "missile_cavalry", "monstrous_cavalry"}
PRICE_CASTES = {"war_beast", "monster", "chariot", "warmachine"}
K_ATTACK = 9.0              # attack and defence move by K_ATTACK x ln k alongside the damage and HP factor k
MA_BOUNDS = (6.0, 80.0)
MD_BOUNDS = (4.0, 80.0)
LORE_ON = os.environ.get("REBALANCE_LORE", "1") == "1"
BLESSED = 1.25              # the cavalry study rates a family once; a Blessed Spawning keeps its edge over the base by this

S = json.load(open(SURVEY))
UM.WEIGHTS.update(S["weights"])
UM.reset()
CO = S["coefficients"]
TRAITS = S["traits"]
ROWS = {u["key"]: u for u in S["units"]}


def caste_line(caste):
    return CO["intercept"] + CO.get("caste:" + caste, 0.0), CO["log_power"] + CO.get("slope:" + caste, 0.0)


def fair_log_cost(x, p_reg):
    a, s = caste_line(x["caste"])
    return a + CO["log_entities"] * math.log(x["men"]) + s * math.log(max(1e-9, p_reg)) + sum(CO[t] * x["traits"][t] for t in TRAITS)


# ------------------------------------------------------------------------------------------------- the scaling

def scaled(c, k):
    """the card moved along its own ray by factor k"""
    v = dict(c)
    v["hp"] = c["hp"] * k
    for d in ("base", "ap", "bvl", "bvi"):
        v[d] = c[d] * k
    if c.get("missile"):
        m = dict(c["missile"])
        for d in ("base", "ap", "bvl", "bvi"):
            m[d] = c["missile"][d] * k
        v["missile"] = m
    d = K_ATTACK * math.log(k)
    # the bounds may stop a change, never reverse it (a vanilla 95 attack is not cut to 80 by a rise)
    v["ma"] = c["ma"] + d if (MA_BOUNDS[0] <= c["ma"] + d <= MA_BOUNDS[1]) else (max(c["ma"], MA_BOUNDS[1]) if d > 0 else min(c["ma"], MA_BOUNDS[0]))
    v["md"] = c["md"] + d if (MD_BOUNDS[0] <= c["md"] + d <= MD_BOUNDS[1]) else (max(c["md"], MD_BOUNDS[1]) if d > 0 else min(c["md"], MD_BOUNDS[0]))
    return v


def solve(c, target_reg, lo=0.35, hi=3.0):
    """bisection on k so that regiment_power(scaled(c, k)) = target_reg"""
    p0 = UM.regiment_power(c)
    if abs(math.log(target_reg / p0)) < 0.005:
        return c, 1.0
    for _ in range(40):
        mid = math.sqrt(lo * hi)
        p = UM.regiment_power(scaled(c, mid))
        if p < target_reg:
            lo = mid
        else:
            hi = mid
        if hi / lo < 1.002:
            break
    k = math.sqrt(lo * hi)
    return scaled(c, k), k


def rounded(v, c):
    """integers the database takes, and HP as bonus_hit_points"""
    r = dict(v)
    r["ma"], r["md"] = round(v["ma"]), round(v["md"])
    r["hp"] = round(v["hp"])
    for d in ("base", "ap", "bvl", "bvi"):
        r[d] = round(v[d])
    if v.get("missile"):
        m = dict(v["missile"])
        for d in ("base", "ap", "bvl", "bvi"):
            m[d] = round(v["missile"][d])
        r["missile"] = m
    return r


# ---------------------------------------------------------------------------------------------- the lore layer

_old_ek = None


def old_power(key, men=None):
    """per-model power on the cavalry study's model, Empire Knights = 1.00"""
    global _old_ek
    if _old_ek is None:
        _old_ek = CM.profile(CM.card("wh_main_emp_cav_empire_knights"))["power"]
    return CM.profile(CM.card(key))["power"] / _old_ek


PER_MODEL = {k: u["power"] for k, u in ROWS.items()}
CASTES = {k: u["caste"] for k, u in ROWS.items()}
COSTS = {k: u["cost"] for k, u in ROWS.items()}
ALL_KEYS = list(ROWS)


def lore_target(key, c):
    """(per-model factor over vanilla, size, tier, note, target, now, keep, price_only) or None.

    Cavalry: the study's table, carried over as a ratio (units that shoot are left to the price layer, as the study
    left them). Everything else: lore_ladder, rated directly on this model's scale."""
    if not LORE_ON:
        return None
    e = LL.lore(key, ROWS)
    if not e and c["caste"] in ("melee_cavalry", "monstrous_cavalry"):
        if c.get("missile"):
            return None
        L = CR.lore(key)
        if not L:
            return None
        target, tier, size, note = L
        if "blessed" in key:
            target *= BLESSED                        # Blessed Spawnings stand above their base, as regiments of renown do
            tier += " (blessed)"
        now = old_power(key)
        return dict(factor=target / now, size=size, tier=tier, note=note, target=target, now=now, keep=False, price_only=False,
                    hold_price=False, price_add=None, source="the cavalry study's scale")
    if not e:
        return None
    return dict(factor=e["factor"], size=e["size"], tier=e["tier"], note=e["note"], target=e["target"],
                now=ROWS[key]["power_reg"] if e["reg"] else PER_MODEL[key],
                keep=e["keep"], price_only=e["target"] is None and not e["keep"] and e["price_add"] is None,
                hold_price=e["hold_price"], price_add=e["price_add"],
                source="the ladder (regiment power)" if e["reg"] else "the ladder")


# ---------------------------------------------------------------------------------------------------- per unit

def price_round(x):
    return int(round(x / 25.0) * 25)


def propose(key):
    x = ROWS[key]
    c = UM.card(key)
    out = dict(key=key, name=x["name"], faction=x["faction"], caste=x["caste"], men=c["men"], cost=x["cost"],
               campaign_cost=x["campaign_cost"], upkeep=x["upkeep"], residual=x["residual"], power_reg=x["power_reg"],
               action="none", note="", before=snapshot(c))
    a, slope = caste_line(x["caste"])

    if key in UNREVIEWED:
        out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
        out.update(note="unreviewed: new since the ladder was written (unreviewed.txt), kept as vanilla", k=1.0, drift=0.0,
                   new_cost=x["cost"], new_campaign_cost=x["campaign_cost"], new_upkeep=x["upkeep"])
        return out
    if key in decided.STATS:
        s = decided.STATS[key]
        v = dict(c)
        v.update(ma=float(s["melee_attack"]), md=float(s["melee_defence"]), cb=float(s["charge_bonus"]), morale=float(s["morale"]))
        v["hp"] = c["hp"] - float(UM.LU[key]["bonus_hit_points"]) + float(s["bonus_hit_points"])
        v["armour"] = UM.AR.get(s["armour"], c["armour"]); v["armour_key"] = s["armour"]
        out.update(action="decided", note=s.get("why", ""), after=snapshot(v), k=None,
                   new_cost=s["cost"], new_campaign_cost=s["cost"], new_upkeep=int(s["cost"] * 0.25), drift=UM.identity_drift(c, v))
        out["after"]["power_reg"] = UM.regiment_power(v)
        return out

    L = lore_target(key, c)
    if L and L["keep"]:
        out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
        out.update(action="none", note="lore: as vanilla. %s" % L["note"], new_cost=x["cost"], new_campaign_cost=x["campaign_cost"],
                   new_upkeep=x["upkeep"], k=1.0, drift=0.0, lore=True)
        return out
    if L and L.get("price_add") is not None:
        new_cost = x["cost"] + L["price_add"] if x["cost"] else x["cost"]
        out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
        out.update(action="lore", note="community: price %+d. %s" % (L["price_add"], L["note"]), k=1.0, drift=0.0, lore=True,
                   new_cost=new_cost, new_campaign_cost=(x["campaign_cost"] + L["price_add"] if x["campaign_cost"] else x["campaign_cost"]),
                   new_upkeep=int(round(x["upkeep"] * new_cost / x["cost"])) if x["cost"] else x["upkeep"])
        return out
    if x["caste"] in PRICE_CASTES and not FLAT_CASTES_MOVE:
        out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
        out.update(new_cost=x["cost"], new_campaign_cost=x["campaign_cost"], new_upkeep=x["upkeep"], k=1.0, drift=0.0, lore=bool(L),
                   note="%s: kept as vanilla (monsters, beasts, chariots and machines are community questions)" % x["caste"].replace("_", " "))
        return out
    elite = bool(L) and bool(ELITE.search(key)) and not L["keep"]
    if L:
        v = dict(c)
        if L["size"] and (RESIZE or elite):
            v["men"] = L["size"]
        if L["price_only"]:
            v, k, p1 = c, 1.0, x["power_reg"]
        else:
            per_model_now = UM.regiment_power(c) / c["men"]
            factor = L["factor"] if (RESIZE or elite) else max(math.exp(-POWER_LIMIT), min(math.exp(POWER_LIMIT), L["factor"]))
            v, k = solve(v, per_model_now * factor * v["men"])
            if v["men"] < c["men"] and k < c["men"] / v["men"]:
                # fewer models never means less health: at least the vanilla regiment's total
                base = dict(c, men=v["men"])
                k = c["men"] / v["men"]
                v = scaled(base, k)
            v = rounded(v, c)
            p1 = UM.regiment_power(v)
        move = math.log(p1 / x["power_reg"])
        res = x["residual"] if x["residual"] is not None else 0.0
        if abs(move) < 0.02 and abs(res) <= TOLERANCE and v["men"] == c["men"]:
            out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
            out.update(new_cost=x["cost"], new_campaign_cost=x["campaign_cost"], new_upkeep=x["upkeep"], k=1.0, drift=0.0, lore=True,
                       note="%s: the target is where vanilla already is (x%.2f). %s" % (L["tier"], L["factor"], L["note"]))
            return out
        # the price: where the caste's line is trusted (infantry, cavalry) it is what the valuation says the unit is now
        # worth, within LORE_PRICE_CAP of vanilla; in the flat-priced castes it is the unit's own price moved along the
        # caste's line, with the residual corrected up to the price cap, so CA's monster prices keep their structure
        xx = dict(x, men=v["men"])
        if L.get("hold_price"):
            price_move = 0.0
        elif x["caste"] in STAT_CASTES:
            want = fair_log_cost(xx, p1) - math.log(max(1.0, x["cost"])) if x["cost"] else 0.0
            cap = ELITE_PRICE_CAP if elite else LORE_PRICE_CAP
            price_move = max(-cap, min(cap, want))
            if not L["price_only"]:                    # a stronger unit never gets cheaper, a weaker one never dearer
                price_move = max(0.0, price_move) if move >= 0 else min(0.0, price_move)
            if elite and move > 0:                     # the price never rises faster than the power
                price_move = min(price_move, move)
        else:
            # flat-priced castes: the price follows the power along the caste's line and the residual is corrected
            # up to the cap, as before, but the result is never above vanilla (docs/COMMUNITY_RESEARCH.md): a Bloodthirster
            # x1.7 stronger that was over-priced ends near its old price, a stronger Great Eagle stays at 750
            price_move = min(0.0, slope * move + max(-PRICE_CAP, min(PRICE_CAP, -res)))
        new_cost = price_round(x["cost"] * math.exp(price_move)) if x["cost"] else x["cost"]
        how = ("the stats are the lore; the price moves to what they are worth" if L["price_only"]
               else "target %.2f per model on %s (vanilla %.2f, x%.2f)" % (L["target"], L["source"], L["now"], L["factor"]))
        out.update(action="lore", note="%s: %s. %s" % (L["tier"], how, L["note"]), after=snapshot(v), k=k,
                   drift=UM.identity_drift(c, v) if k != 1.0 else 0.0, lore=True, elite=elite)
        out["after"]["power_reg"] = p1
        out.update(new_cost=new_cost, new_campaign_cost=(price_round(x["campaign_cost"] * new_cost / x["cost"]) if x["campaign_cost"] and x["cost"] else x["campaign_cost"]),
                   new_upkeep=int(round(x["upkeep"] * new_cost / x["cost"])) if x["cost"] else x["upkeep"])
        return out

    res = x["residual"]
    if res is None or abs(res) <= TOLERANCE:
        out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
        out.update(new_cost=x["cost"], new_campaign_cost=x["campaign_cost"], new_upkeep=x["upkeep"], k=1.0, drift=0.0)
        return out

    # split the residual: stats (up to the cap) for castes whose prices track power, price (up to its cap) for the rest
    want = res / slope                                   # log power change that would make the price right
    if x["caste"] in STAT_CASTES and key not in VETO:
        move = max(-CAP, min(CAP, want))
    else:
        move = 0.0
    left = res - slope * move                            # what the stats do not absorb goes to the price
    price_move = max(-PRICE_CAP, min(PRICE_CAP, -left))
    if move:                                             # one lever: a unit whose stats move keeps its price
        price_move = 0.0
    if x["caste"] in PRICE_CASTES and res < 0:
        # a "bargain" in a flat-priced caste is the model over-rating a unit whose weakness is behaviour it cannot
        # see (accuracy, mobility, breath in melee, crumbling); the price is never raised there
        out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
        out.update(new_cost=x["cost"], new_campaign_cost=x["campaign_cost"], new_upkeep=x["upkeep"], k=1.0, drift=0.0,
                   note="residual %+.2f in a flat-priced caste: not raised (the model's blind spot, docs/COMMUNITY_RESEARCH.md)" % res)
        return out
    unresolved = -left - price_move
    v, k = (solve(c, x["power_reg"] * math.exp(move)) if move else (c, 1.0))
    v = rounded(v, c) if move else c
    p1 = UM.regiment_power(v) if move else x["power_reg"]
    new_cost = price_round(x["cost"] * math.exp(price_move)) if abs(price_move) > 1e-9 else x["cost"]
    if move and new_cost != x["cost"]:
        action, note = "stats+price", "residual %+.2f: power x%.2f (capped), price to %d" % (res, math.exp(move), new_cost)
    elif move:
        action, note = "stats", "residual %+.2f: power x%.2f to what the price pays for" % (res, math.exp(move))
    elif new_cost != x["cost"]:
        action, note = "price", "residual %+.2f: price to what the stats are worth%s" % (res, "" if x["caste"] in STAT_CASTES else " (%s: a flat-priced caste, stats stay)" % x["caste"].replace("_", " "))
    else:
        action, note = "none", ""
    if abs(unresolved) > 0.02:
        note += "; %+.0f%% of price still unresolved after the caps" % ((math.exp(-unresolved) - 1) * 100)
    if abs(want) > CAP + 0.3 and x["caste"] in STAT_CASTES:
        note += "; REVIEW: the model may be missing something (wanted x%.2f), held out of the pack" % math.exp(want)
        out["held"] = True
    out.update(action=action, note=note, after=snapshot(v), k=k, drift=UM.identity_drift(c, v) if move else 0.0)
    out["after"]["power_reg"] = p1
    out.update(new_cost=new_cost,
               new_campaign_cost=(price_round(x["campaign_cost"] * new_cost / x["cost"]) if x["campaign_cost"] and x["cost"] else x["campaign_cost"]),
               new_upkeep=int(round(x["upkeep"] * new_cost / x["cost"])) if x["cost"] else x["upkeep"])
    return out


def snapshot(c):
    s = dict(men=c["men"], ma=c["ma"], md=c["md"], cb=c["cb"], hp=c["hp"], armour=c["armour"], armour_key=c.get("armour_key", ""),
             morale=c["morale"], base=c["base"], ap=c["ap"], bvl=c["bvl"], bvi=c["bvi"])
    if c.get("missile"):
        m = c["missile"]
        s["missile"] = dict(base=m["base"], ap=m["ap"], bvl=m["bvl"], bvi=m["bvi"], key=m["key"], projectile=m["projectile"])
    return s


# ------------------------------------------------------------------------------------------------- the writing

def weapon_text(s):
    t = "%.0f+%.0f" % (s["base"], s["ap"])
    if s["bvl"]:
        t += " vL+%.0f" % s["bvl"]
    if s["bvi"]:
        t += " vI+%.0f" % s["bvi"]
    if s.get("missile"):
        m = s["missile"]
        t += " · shot %.0f+%.0f" % (m["base"], m["ap"])
        if m["bvl"]:
            t += " vL+%.0f" % m["bvl"]
        if m["bvi"]:
            t += " vI+%.0f" % m["bvi"]
    return t


def delta(a, b, fmt="%.0f", eps=0.5):
    if abs(a - b) < eps:
        return fmt % a
    return (fmt + " → **" + fmt + "**") % (a, b)


HEAD = ("| unit | caste | action | residual | n | MA / MD | HP | weapon | reg power | price (mp) | campaign | drift | why |\n" + "|---" * 13 + "|\n")


def row(o):
    b, a = o["before"], o["after"]
    men = delta(b["men"], a["men"], "%d")
    mad = "%s / %s" % (delta(b["ma"], a["ma"]), delta(b["md"], a["md"]))
    if o["action"] == "decided":
        mad += " / cb %s, Ld %s, arm %s" % (delta(b["cb"], a["cb"]), delta(b["morale"], a["morale"]), delta(b["armour"], a["armour"]))
    wp = weapon_text(b) if weapon_text(b) == weapon_text(a) else "%s → **%s**" % (weapon_text(b), weapon_text(a))
    return "| %s `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %.3f | %s |\n" % (
        o["name"], o["key"], o["caste"].replace("_", " "), o["action"], ("%+.2f" % o["residual"]) if o["residual"] is not None else "n/a",
        men, mad, delta(b["hp"], a["hp"]), wp, delta(o["power_reg"], a["power_reg"], "%.2f", 0.005),
        delta(o["cost"], o["new_cost"], "%d"), delta(o["campaign_cost"], o["new_campaign_cost"], "%d"), o.get("drift", 0.0), o["note"])


def vanilla_prop(o, note):
    """back to vanilla, keeping the record of why"""
    x = ROWS[o["key"]]
    c = UM.card(o["key"])
    o.update(action="none", note=note, after=snapshot(c), k=1.0, drift=0.0, new_cost=x["cost"],
             new_campaign_cost=x["campaign_cost"], new_upkeep=x["upkeep"])
    o["after"]["power_reg"] = x["power_reg"]
    o.pop("held", None)


def base_of(o, by_name):
    """a regiment of renown's base unit: 'Black-Horn's Ravagers (Gor Herd – Shields)' -> 'Gor Herd (Shields)'"""
    m = re.match(r"^(.*) \((.+)\)$", o["name"])
    if not m:
        return None
    inner = m.group(2)
    for name in (inner, re.sub(r" – (.+)$", r" (\1)", inner)):
        for b in by_name.get(name, []):
            if b["faction"] == o["faction"] and b["caste"] == o["caste"] and b is not o:
                return b
    return None


def follow_bases(props):
    """a regiment of renown moves with its base unit: the same power ratio and the same price ratio, so CA's premium for
    the renown stays as it was. If the base did not change, neither does the regiment."""
    by_name = {}
    for o in props:
        by_name.setdefault(o["name"], []).append(o)
    n = 0
    for o in props:
        if o["action"] == "decided" or o["key"] in UNREVIEWED or o.get("elite"):
            continue
        b = base_of(o, by_name)
        if not b or b is o or base_of(b, by_name):
            continue
        n += 1
        x = ROWS[o["key"]]
        if b["action"] == "none":
            vanilla_prop(o, "regiment of renown: follows %s, which is unchanged" % b["name"])
            continue
        ratio = b["after"]["power_reg"] / b["power_reg"]
        price_ratio = (b["new_cost"] / b["cost"]) if b["cost"] else 1.0
        c = UM.card(o["key"])
        v, k = solve(c, x["power_reg"] * ratio) if abs(math.log(ratio)) > 0.005 else (c, 1.0)
        v = rounded(v, c) if k != 1.0 else c
        new_cost = price_round(x["cost"] * price_ratio) if x["cost"] else x["cost"]
        o.update(action="lore" if b["action"] == "lore" else ("stats" if k != 1.0 else "price"), after=snapshot(v), k=k,
                 drift=UM.identity_drift(c, v) if k != 1.0 else 0.0, new_cost=new_cost,
                 new_campaign_cost=(price_round(x["campaign_cost"] * new_cost / x["cost"]) if x["campaign_cost"] and x["cost"] else x["campaign_cost"]),
                 new_upkeep=int(round(x["upkeep"] * new_cost / x["cost"])) if x["cost"] else x["upkeep"],
                 note="regiment of renown: follows %s (power x%.2f, price x%.2f)" % (b["name"], ratio, price_ratio))
        o["after"]["power_reg"] = UM.regiment_power(v) if k != 1.0 else x["power_reg"]
        o.pop("held", None)
        if o["drift"] > 0.03:                           # the same factor would change how this regiment fights
            vanilla_prop(o, "regiment of renown: kept as vanilla, scaling it with %s would change how it fights" % b["name"])
    return n


def inversions(props, after):
    """pairs in one faction and caste where the dearer unit is more than 15% weaker (regiments of renown left out)"""
    groups = {}
    for o in props:
        cost = o["new_cost"] if after else o["cost"]
        if cost and not base_of_cache.get(o["key"]):
            groups.setdefault((o["faction"], o["caste"]), []).append(o)
    out = set()
    for grp in groups.values():
        for i, a in enumerate(grp):
            for b in grp[i + 1:]:
                ca, cb = (a["new_cost"], b["new_cost"]) if after else (a["cost"], b["cost"])
                pa, pb = (a["after"]["power_reg"], b["after"]["power_reg"]) if after else (a["power_reg"], b["power_reg"])
                if abs(ca - cb) < 50:
                    continue
                if (ca > cb and pb > pa * 1.15) or (cb > ca and pa > pb * 1.15):
                    out.add((a["key"], b["key"]))
    return out


base_of_cache = {}


def guard(props):
    """revert, one at a time, the change behind every 'pay more, get less' pair the patch creates that vanilla did not have"""
    by_key = {o["key"]: o for o in props}
    before = inversions(props, False)
    reverted = []
    while True:
        new = [pair for pair in inversions(props, True) if pair not in before]
        if not new:
            return reverted
        blame = {}
        for a, b in new:
            for k in (a, b):
                o = by_key[k]
                if o["action"] not in ("none", "decided", "gunpowder") and not o.get("elite") and not o.get("gun"):
                    blame[k] = blame.get(k, 0) + 1
        if not blame:
            return reverted
        worst = max(blame, key=lambda k: (blame[k], abs(math.log(by_key[k]["after"]["power_reg"] / by_key[k]["power_reg"]))))
        vanilla_prop(by_key[worst], "reverted: this change made a dearer unit weaker than a cheaper one in the same roster")
        reverted.append(by_key[worst]["name"])


def apply_gunpowder(props):
    """the gunpowder rule (gunpowder.py) on top of whatever else the unit got: a heavier volley, a slower reload. It is a
    design rule, not a balance correction, so the price stays where the rest of the solver put it."""
    n = 0
    for o in props:
        if o["key"] in UNREVIEWED or o["action"] == "decided":
            continue
        c = UM.card(o["key"])
        if not GP.applies(c, o["caste"]):
            continue
        a = o["after"]
        v = dict(c, men=a["men"], ma=a["ma"], md=a["md"], hp=a["hp"], base=a["base"], ap=a["ap"], bvl=a["bvl"], bvi=a["bvi"])
        if a.get("missile"):
            v["missile"] = dict(c["missile"], **{d: a["missile"][d] for d in ("base", "ap", "bvl", "bvi")})
        v = GP.apply(v)
        o["gun"] = [GP.DAMAGE, GP.RELOAD]
        o["after"]["missile"] = dict(a["missile"], **{d: v["missile"][d] for d in ("base", "ap", "bvl", "bvi")}, reload=v["missile"]["reload"])
        before_gun = o["after"]["power_reg"]
        o["after"]["power_reg"] = UM.regiment_power(v)
        # the price follows what the rule adds (never below vanilla: a stronger unit does not get cheaper)
        x = ROWS[o["key"]]
        if x["cost"]:
            # the whole change against vanilla decides the price, in the same direction and within the limit
            total = o["after"]["power_reg"] / o["power_reg"]
            want = price_round(o["new_cost"] * o["after"]["power_reg"] / before_gun)
            lo, hi = (x["cost"], x["cost"] * math.exp(PRICE_LIMIT)) if total >= 1 else (x["cost"] * math.exp(-PRICE_LIMIT), x["cost"])
            o["new_cost"] = int(min(hi, max(lo, want)))
            o["new_cost"] = price_round(o["new_cost"]) if lo <= price_round(o["new_cost"]) <= hi else o["new_cost"]
            o["new_campaign_cost"] = price_round(x["campaign_cost"] * o["new_cost"] / x["cost"]) if x["campaign_cost"] else x["campaign_cost"]
            o["new_upkeep"] = int(round(x["upkeep"] * o["new_cost"] / x["cost"]))
        if o["action"] == "none":
            o["action"] = "gunpowder"
            o["note"] = "gunpowder: volley x%.2f, reload x%.2f. %s" % (GP.DAMAGE, GP.RELOAD, o["note"])
        else:
            o["note"] += "; gunpowder: volley x%.2f, reload x%.2f" % (GP.DAMAGE, GP.RELOAD)
        n += 1
    return n


def main():
    keys = [k for k in UM.recruitable() if k in ROWS]
    props = [propose(k) for k in keys]
    by_name = {}
    for o in props:
        by_name.setdefault(o["name"], []).append(o)
    base_of_cache.update({o["key"]: base_of(o, by_name) for o in props})
    print("regiments of renown following their base:", follow_bases(props))
    reverted = guard(props)
    print("reverted by the pay-more-get-less guard: %d %s" % (len(reverted), reverted[:12]))
    print("gunpowder rule applied:", apply_gunpowder(props))
    reverted = guard(props)
    print("reverted after the gunpowder rule: %d %s" % (len(reverted), reverted[:12]))
    by_action = {}
    for o in props:
        by_action.setdefault(o["action"], []).append(o)
    changed = [o for o in props if o["action"] != "none"]
    held = [o for o in changed if o.get("held")]
    drift = [o["drift"] for o in changed if o.get("drift") is not None]
    with open(OUT_MD, "w") as out:
        w = out.write
        w("# Community Balance Patch: every change\n\n")
        w("Generated by `tools/rebalance_solve.py` from `_survey.json` (`rebalance_survey.py`) and the cavalry study. "
          "See `docs/METHOD.md` for the method and `reports/survey.md` for the measurements.\n\n")
        w("| | units |\n|---|---|\n")
        for k in ("none", "decided", "lore", "stats", "stats+price", "price", "gunpowder"):
            w("| %s | %d |\n" % (k, len(by_action.get(k, []))))
        w("| lore: as vanilla (kept on purpose) | %d |\n" % sum(1 for o in props if o["action"] == "none" and o.get("lore")))
        w("| **changed** | **%d** of %d |\n" % (len(changed), len(props)))
        w("| of which held for review (not in the pack) | %d |\n" % len(held))
        w("\nRules: tolerance ±%.2f on the residual (one robust sigma); power moves at most ×%.2f per unit in one pass (stats), "
          "the rest goes to price, which moves at most ×%.2f; stats move for %s; price alone moves for %s. Attack and defence move by "
          "%.0f × ln k with the damage-and-HP factor k. **drift** is 1 − cosine similarity of the matchup-and-share vector before and "
          "after (0 = fights exactly the same way).\n\n"
          % (TOLERANCE, math.exp(CAP), math.exp(PRICE_CAP), ", ".join(sorted(s.replace("_", " ") for s in STAT_CASTES)), ", ".join(sorted(s.replace("_", " ") for s in PRICE_CASTES)), K_ATTACK))
        if drift:
            w("Identity drift over the %d changed units: mean %.4f, max %.4f (%s).\n\n" % (
                len(drift), sum(drift) / len(drift), max(drift), max(changed, key=lambda o: o["drift"])["name"]))
        w("Price residual before and after, by faction (mean log price / fair price; 0 is balanced):\n\n| faction | before | after | changed |\n|---|---|---|---|\n")
        for fac in sorted(UM.FACTION_NAMES, key=lambda x: UM.FACTION_NAMES[x]):
            ps = [o for o in props if o["faction"] == fac and o["residual"] is not None]
            if not ps:
                continue
            before = sum(o["residual"] for o in ps) / len(ps)
            after = []
            for o in ps:
                xx = dict(ROWS[o["key"]], men=o["after"]["men"])
                after.append(math.log(max(1, o["new_cost"])) - fair_log_cost(xx, o["after"]["power_reg"]))
            w("| %s | %+.3f | %+.3f | %d |\n" % (UM.FACTION_NAMES[fac], before, sum(after) / len(after), sum(1 for o in ps if o["action"] != "none")))
        for fac in sorted(UM.FACTION_NAMES, key=lambda x: UM.FACTION_NAMES[x]):
            ps = [o for o in props if o["faction"] == fac]
            if not ps:
                continue
            w("\n## %s\n\n" % UM.FACTION_NAMES[fac] + HEAD)
            for o in sorted(ps, key=lambda o: (o["action"] == "none", o["caste"], -o["power_reg"])):
                w(row(o))
    json.dump(dict(weights=S["weights"], tolerance=TOLERANCE, cap=CAP, units=props), open(OUT_JSON, "w"), indent=1)
    # the beta: every proposal is published, but only the design rules go into the pack; the rest waits for players
    import copy
    beta = copy.deepcopy(props)
    by_name = {}
    for o in beta:
        by_name.setdefault(o["name"], []).append(o)
    def elite_infantry(o):
        """beta theme 2: elite infantry worth its price (the complaint the community and CA agree on)"""
        if o["action"] != "lore" or o["caste"] != "melee_infantry":
            return False
        if o["note"].startswith(("elite:", "champion:")):
            return True
        b = base_of(o, by_name)
        return bool(b) and b is not o and b["note"].startswith(("elite:", "champion:"))
    import community                           # a unit on the community's list takes their numbers, not the model's
    named = {k for _, _, _, keys in community.resolve([o["key"] for o in beta], UM.name, UM.faction) for k in keys}
    for o in beta:
        o.pop("gun", None)
        if o["key"] in named and not o.get("elite"):
            vanilla_prop(o, "community list (community.py): " + o["note"] if o["action"] != "none" else o["note"])
            o["community"] = True
        elif elite_infantry(o):
            o["theme"] = "elite infantry"
        elif not o.get("elite"):
            vanilla_prop(o, "proposal only (not in the beta): " + o["note"] if o["action"] != "none" else o["note"])
    # a themed change can make an untouched roster mate the dearer-but-weaker one; take that mate's draft change too
    # (the full draft is consistent), and only if the draft has none, let the guard revert the themed change
    full = {o["key"]: o for o in props}
    by_key = {o["key"]: o for o in beta}
    before = inversions(beta, False)
    while True:
        adopt = {k for pair in inversions(beta, True) if pair not in before for k in pair
                 if by_key[k]["action"] == "none" and full[k]["action"] == "lore" and not by_key[k].get("community")}
        if not adopt:
            break
        for k in adopt:
            by_key[k].update(copy.deepcopy(full[k]), theme="elite infantry (roster fit)")
    print("beta: roster mates taken from the draft:", sorted(o["name"] for o in beta if o.get("theme") == "elite infantry (roster fit)"))
    print("beta: gunpowder rule applied:", apply_gunpowder(beta), "| elites:", sum(1 for o in beta if o.get("elite")),
          "| elite infantry:", sum(1 for o in beta if o.get("theme") == "elite infantry"))
    print("beta: reverted by the guard:", guard(beta))
    json.dump(dict(weights=S["weights"], tolerance=TOLERANCE, cap=CAP, units=beta), open(BETA_JSON, "w"), indent=1)
    print("proposals:", {k: len(v) for k, v in by_action.items()})
    print("wrote", OUT_MD, "and", OUT_JSON)


if __name__ == "__main__":
    main()
