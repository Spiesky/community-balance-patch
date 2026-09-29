#!/usr/bin/env python3
"""The solver: turn the survey's residuals and the lore targets into stat and price proposals that keep every unit's
identity.

    python3 rebalance_solve.py            -> ../REBALANCE_DATA.md and _rebalance.json (what build_rebalance.py writes)

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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SURVEY = os.path.join(HERE, "_survey.json")
OUT_MD = os.path.join(ROOT, "reports", "proposals.md")
OUT_JSON = os.path.join(HERE, "_rebalance.json")

TOLERANCE = 0.15            # |residual| inside this band (one robust sigma): the unit is fine, nothing moves
CAP = math.log(1.25)        # the most a unit's regiment power moves in one pass (x1.25 or /1.25); the rest goes to price
PRICE_CAP = math.log(1.25)  # the most a price moves in one pass; what is left over is reported as unresolved
LORE_PRICE_CAP = math.log(1.6)   # a lore unit's price goes to what the valuation says it is worth, within this of vanilla
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
    v["ma"] = min(MA_BOUNDS[1], max(MA_BOUNDS[0], c["ma"] + d))
    v["md"] = min(MD_BOUNDS[1], max(MD_BOUNDS[0], c["md"] + d))
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
    if L:
        v = dict(c)
        if L["size"]:
            v["men"] = L["size"]
        if L["price_only"]:
            v, k, p1 = c, 1.0, x["power_reg"]
        else:
            per_model_now = UM.regiment_power(c) / c["men"]
            v, k = solve(v, per_model_now * L["factor"] * v["men"])
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
            price_move = max(-LORE_PRICE_CAP, min(LORE_PRICE_CAP, want))
        else:
            # flat-priced castes: the price follows the power along the caste's line and the residual is corrected
            # up to the cap, as before, but the result is never above vanilla (COMMUNITY_BALANCE.md): a Bloodthirster
            # x1.7 stronger that was over-priced ends near its old price, a stronger Great Eagle stays at 750
            price_move = min(0.0, slope * move + max(-PRICE_CAP, min(PRICE_CAP, -res)))
        new_cost = price_round(x["cost"] * math.exp(price_move)) if x["cost"] else x["cost"]
        how = ("the stats are the lore; the price moves to what they are worth" if L["price_only"]
               else "target %.2f per model on %s (vanilla %.2f, x%.2f)" % (L["target"], L["source"], L["now"], L["factor"]))
        out.update(action="lore", note="%s: %s. %s" % (L["tier"], how, L["note"]), after=snapshot(v), k=k,
                   drift=UM.identity_drift(c, v) if k != 1.0 else 0.0, lore=True)
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
    if x["caste"] in PRICE_CASTES and res < 0:
        # a "bargain" in a flat-priced caste is the model over-rating a unit whose weakness is behaviour it cannot
        # see (accuracy, mobility, breath in melee, crumbling); the price is never raised there
        out["after"] = snapshot(c); out["after"]["power_reg"] = x["power_reg"]
        out.update(new_cost=x["cost"], new_campaign_cost=x["campaign_cost"], new_upkeep=x["upkeep"], k=1.0, drift=0.0,
                   note="residual %+.2f in a flat-priced caste: not raised (the model's blind spot, COMMUNITY_BALANCE.md)" % res)
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


def main():
    keys = [k for k in UM.recruitable() if k in ROWS]
    props = [propose(k) for k in keys]
    by_action = {}
    for o in props:
        by_action.setdefault(o["action"], []).append(o)
    changed = [o for o in props if o["action"] != "none"]
    held = [o for o in changed if o.get("held")]
    drift = [o["drift"] for o in changed if o.get("drift") is not None]
    with open(OUT_MD, "w") as out:
        w = out.write
        w("# The great rebalance: every proposal\n\n")
        w("Generated by `tools/rebalance_solve.py` from `_survey.json` (`rebalance_survey.py`) and the cavalry study. "
          "Read `GREAT_REBALANCE.md` for the method and `REBALANCE_SURVEY.md` for the measurements.\n\n")
        w("| | units |\n|---|---|\n")
        for k in ("none", "decided", "lore", "stats", "stats+price", "price"):
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
    print("proposals:", {k: len(v) for k, v in by_action.items()})
    print("wrote", OUT_MD, "and", OUT_JSON)


if __name__ == "__main__":
    main()
