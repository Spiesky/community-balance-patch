#!/usr/bin/env python3
"""The survey: measure every recruitable unit with unit_model.py, then fit the game's own prices to the measurements.

    python3 rebalance_survey.py            -> ../reports/survey.md, _survey.json, and the fitted weights

Why fit prices at all. Total War balance is not "every unit equal"; it is "every unit worth its price". CA sets the
multiplayer price of each unit by hand and by testing, so the prices are the best record there is of what a point of
damage, a point of armour, a flying mount or a single-entity monster is worth in their game. A regression of price on
the measured power recovers that valuation (the "revealed valuation"). Against it every unit has a residual:

    residual = log(actual price) - log(price the valuation predicts)

A residual of +0.3 means the unit costs 35% more than units of its power usually do (over-priced, or carrying value the
model cannot see); -0.3 means it is a bargain (under-priced, or its stats are wrong for its price). The survey lists
the residuals; rebalance_solve.py acts on them.

The regression. In logs, with y = log(multiplayer cost):

    y = a + b log(entities) + c log(power per model) + sum_i w_i trait_i

so the entity exponent of unit_model.regiment_power is b / c, and the traits (flying, fear, terror, unbreakable,
regeneration, stalk, vanguard, speed, active abilities, single entity, regiment of renown) each carry a price premium.
The composition weights inside power (how much a point of missile dps is worth against a point of melee dps, how much
toughness against missiles counts, how range and ammunition are valued) are chosen by grid search to minimise the
residual variance: the valuation is the one that makes CA's prices most consistent. The fit is robust (Huber weights,
iteratively reweighted least squares) so that a few oddly priced units do not pull the line.

What it cannot see is what the residuals then show: healing, magic, breath attacks, poison, the value of a cannon's
range on a siege map, a chariot's actual collision behaviour, animations. A large residual is a question, not an answer.
"""
import json
import math
import os
import sys

import numpy as np

import unit_model as UM

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_MD = os.path.join(ROOT, "reports", "survey.md")
OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_survey.json")
USA = UM.V.index("unit_special_abilities")

TRAITS = ["flying", "causes_fear", "causes_terror", "unbreakable", "immune_to_psychology", "regeneration", "stalk",
          "vanguard", "single", "renown", "log_speed", "active_abilities", "contact", "undead", "expendable"]


def traits(c):
    a = set(c["attrs"])
    active = sum(1 for ab in c["abilities"] if USA.get(ab, {}).get("passive") != "true" and "formation" not in ab)
    return dict(
        flying=float(c["flying"]), causes_fear=float("causes_fear" in a and "causes_terror" not in a),
        causes_terror=float("causes_terror" in a), unbreakable=float("unbreakable" in a),
        immune_to_psychology=float("immune_to_psychology" in a and "unbreakable" not in a),
        regeneration=float(any("regen" in ab for ab in c["abilities"])), stalk=float("stalk" in a),
        vanguard=float("guerrilla_deploy" in a), single=float(c["men"] <= 1), renown=float(c["renown"]),
        log_speed=math.log(max(2.0, c["speed"])), active_abilities=float(min(3, active)),
        contact=float(bool(c["missile"] and c["missile"]["contact"]) or bool(UM.MW.get(c["weapon"], {}).get("contact_phase"))),
        undead=float("undead" in a or "daemonic" in a or "construct" in a), expendable=float("expendable" in a),
    )


def measure():
    """the raw pieces of every unit, before composition, so the weight search can recompose without re-profiling"""
    rows = []
    for k in UM.recruitable():
        c = UM.card(k)
        m = c["missile"]
        rows.append(dict(
            key=k, name=c["label"], faction=c["faction"], factions=c["factions"], caste=c["caste"], tier=c["tier"],
            men=c["men"], crew=c["crew"], cost=int(UM.f(UM.MU[k]["multiplayer_cost"])), campaign_cost=c["cost"], upkeep=c["upkeep"],
            ma=c["ma"], md=c["md"], cb=c["cb"], hp=c["hp"], armour=c["armour"], shield=c["shield"], morale=c["morale"],
            speed=c["speed"], mass=c["mass"], radius=c["radius"], base=c["base"], ap=c["ap"], bvl=c["bvl"], bvi=c["bvi"],
            ward=c["ward"], res_physical=c["res_physical"], res_missile=c["res_missile"], res_magic=c["res_magic"], res_flame=c["res_flame"],
            missile=dict(range=m["range"], ammo=m["ammo"], reload=m["reload"], base=m["base"], ap=m["ap"], key=m["key"], projectile=m["projectile"]) if m else None,
            pieces=UM.pieces(c), traits=traits(c), attrs=[a for a in c["attrs"] if a != "hide_forest"],
        ))
    return rows


def compose(rows, W):
    """regiment power for every row under composition weights W; the Empire Knights regiment = 1.00"""
    for r in rows:
        r["prof"] = UM.compose(r["pieces"], W)
    p = np.array([r["prof"]["power_reg"] for r in rows])
    ek = next(i for i, r in enumerate(rows) if r["key"] == "wh_main_emp_cav_empire_knights")
    return p / p[ek]


CASTE_IDX = {c: i for i, c in enumerate(UM.CASTES)}


def design(rows, p, per_caste=True):
    """columns: 1, log entities, log regiment power, the traits, then (per_caste) a caste intercept and a caste slope
    on log regiment power for every caste but the first (melee infantry is the reference caste)"""
    n = len(rows)
    lp = np.log(p)
    X = [np.ones(n), np.log([r["men"] for r in rows]), lp]
    for t in TRAITS:
        X.append(np.array([r["traits"][t] for r in rows]))
    if per_caste:
        for caste in UM.CASTES[1:]:
            d = np.array([1.0 if r["caste"] == caste else 0.0 for r in rows])
            X.append(d)
            X.append(d * lp)
    return np.vstack(X).T


def column_names(per_caste=True):
    names = ["intercept", "log_entities", "log_power"] + TRAITS
    if per_caste:
        for caste in UM.CASTES[1:]:
            names += ["caste:" + caste, "slope:" + caste]
    return names


def huber_fit(X, y, k=0.6, iters=30):
    """iteratively reweighted least squares with Huber weights; returns coefficients, residuals, weights"""
    w = np.ones(len(y))
    beta = None
    for _ in range(iters):
        Xw = X * w[:, None]
        beta_new = np.linalg.lstsq(Xw.T @ X, Xw.T @ y, rcond=None)[0]
        res = y - X @ beta_new
        s = 1.4826 * np.median(np.abs(res - np.median(res))) or 1e-6
        u = np.abs(res) / s
        w = np.where(u <= k, 1.0, k / u)
        if beta is not None and np.max(np.abs(beta_new - beta)) < 1e-7:
            beta = beta_new
            break
        beta = beta_new
    res = y - X @ beta
    return beta, res, w


def fit(rows, W, per_caste=True):
    mask = np.array([r["cost"] > 0 for r in rows])
    p = compose(rows, W)
    X = design(rows, p, per_caste)
    y = np.log(np.array([max(1.0, r["cost"]) for r in rows]))
    beta, res, w = huber_fit(X[mask], y[mask])
    full_res = y - X @ beta
    spread = 1.4826 * np.median(np.abs(res - np.median(res)))
    return dict(beta=beta, res=full_res, weights=w, mask=mask, p=p, X=X, y=y, mad=spread, rms=float(np.sqrt(np.mean(res ** 2))),
                per_caste=per_caste, names=column_names(per_caste))


def cross_validate(rows, W, folds=5, seed=1):
    """rms of out-of-sample residuals, to show the per-caste fit is not just memorising prices"""
    rng = np.random.default_rng(seed)
    mask = np.array([r["cost"] > 0 for r in rows])
    p = compose(rows, W)
    X = design(rows, p)
    y = np.log(np.array([max(1.0, r["cost"]) for r in rows]))
    idx = np.where(mask)[0]
    rng.shuffle(idx)
    out = []
    for k in range(folds):
        test = idx[k::folds]
        train = np.setdiff1d(idx, test)
        beta, _, _ = huber_fit(X[train], y[train])
        out.extend((y[test] - X[test] @ beta).tolist())
    return float(np.sqrt(np.mean(np.square(out))))


GRID = dict(ranged=[0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0], impact=[0.0, 0.5, 1.0, 2.0, 4.0, 8.0], ability=[0.0, 0.25, 0.5, 1.0, 2.0, 4.0],
            missile_tough=[0.0, 0.15, 0.3, 0.45], range_exp=[0.0, 0.25, 0.5, 0.75, 1.0], window=[120.0, 180.0, 240.0, 360.0],
            reach=[1.0, 1.5, 2.0, 3.0, 4.0, 6.0, 8.0])


# The scale-defining weights (reach, impact, ranged, missile_tough, range_exp, window) were fitted on 2026-09-16 and
# then pinned: the lore ladder's targets and every number in the documents are on that scale, and a refit that moves
# reach or impact moves the scale under them (a Bloodthirster measured 2.2 on it and 1.3 on an unpinned refit). Only
# weights added since (ability) are searched. Unpin with --refit-scale, and re-anchor the ladder afterwards.
PINNED = ("reach", "impact", "ranged", "missile_tough", "range_exp", "window")


def search(rows, verbose=True, passes=4):
    """the composition weights that make the prices most consistent (least robust spread of residuals):
    coordinate descent over GRID, one weight at a time, until a full pass changes nothing"""
    W = dict(UM.WEIGHTS)
    grid = dict(GRID)
    if "--refit-scale" not in sys.argv:
        for k in PINNED:
            grid[k] = [W[k]]
    for k in grid:
        if W[k] not in grid[k]:
            W[k] = grid[k][len(grid[k]) // 2]
    best = fit(rows, W)
    for _ in range(passes):
        changed = False
        for k, values in grid.items():
            for v in values:
                if v == W[k]:
                    continue
                Wt = dict(W, **{k: v})
                r = fit(rows, Wt)
                if r["mad"] < best["mad"] - 1e-6:
                    best, W, changed = r, Wt, True
        if verbose:
            print("  pass: %s  spread %.4f" % (W, best["mad"]))
        if not changed:
            break
    if verbose:
        print("best weights: %s  robust spread %.4f  rms %.4f" % (W, best["mad"], best["rms"]))
    return W, best


def coefficients(r):
    return dict(zip(r["names"], [float(b) for b in r["beta"]]))


def caste_line(co, caste):
    """(intercept, slope on log regiment power) of the caste's own price line"""
    return co["intercept"] + co.get("caste:" + caste, 0.0), co["log_power"] + co.get("slope:" + caste, 0.0)


def fair_log_cost(co, x, p_reg):
    """log of the price the valuation gives this unit at regiment power p_reg"""
    a, s = caste_line(co, x["caste"])
    return a + co["log_entities"] * math.log(x["men"]) + s * math.log(max(1e-9, p_reg)) + sum(co[t] * x["traits"][t] for t in TRAITS)


def power_for_price(co, x, cost):
    """the regiment power at which this unit would be fairly priced at cost"""
    a, s = caste_line(co, x["caste"])
    rest = a + co["log_entities"] * math.log(x["men"]) + sum(co[t] * x["traits"][t] for t in TRAITS)
    return math.exp((math.log(cost) - rest) / s)


def write_report(rows, W, r, pooled, cv_rms):
    co = coefficients(r)
    po = coefficients(pooled)
    n_fit = int(r["mask"].sum())
    with open(OUT_MD, "w") as out:
        w = out.write
        w("# The rebalance survey: every unit measured against the game's own prices\n\n")
        w("Generated by `tools/rebalance_survey.py` (model: `unit_model.py`) from the vanilla database. "
          "%d recruitable units, %d with a multiplayer price. See `docs/METHOD.md` for the method.\n\n" % (len(rows), n_fit))
        w("## The valuation\n\n")
        w("Composition weights, chosen by coordinate descent to make the prices most consistent:\n\n")
        w("| weight | value | meaning |\n|---|---|---|\n")
        w("| ranged | %.2f | a point of missile dps, against a point of melee dps |\n" % W["ranged"])
        w("| impact | %.2f | a point of collision dps |\n" % W["impact"])
        w("| ability | %.2f | a point of breath-attack or bombardment dps |\n" % W["ability"])
        w("| missile_tough | %.2f | share of toughness that is toughness against missiles |\n" % W["missile_tough"])
        w("| range_exp | %.2f | missile dps × (range / 150 m) ^ range_exp |\n" % W["range_exp"])
        w("| window | %.0f s | shooting time a battle affords; ammunition beyond it is worth nothing |\n" % W["window"])
        w("| reach | %.1f | ranks of attackers that reach the exposed edge of a regiment (engagement geometry) |\n\n" % W["reach"])
        w("Price regression, log(multiplayer cost) on the measurements, one price line per caste (robust fit, %d units). "
          "Residual spread: robust σ %.3f (a typical unit is priced within ±%.0f%% of its caste's line), rms %.3f, "
          "5-fold cross-validated rms %.3f.\n\n" % (n_fit, r["mad"], (math.exp(r["mad"]) - 1) * 100, r["rms"], cv_rms))
        w("| caste | price ∝ regiment power ^ | at power 1.00 (one Empire Knights regiment) | pooled line says |\n|---|---|---|---|\n")
        for caste in UM.CASTES:
            a, s = caste_line(co, caste)
            pa, ps = caste_line(po, caste)
            idx = [i for i, x in enumerate(rows) if x["caste"] == caste and r["mask"][i]]
            men = float(np.exp(np.mean([math.log(rows[i]["men"]) for i in idx]))) if idx else 60
            base = math.exp(a + co["log_entities"] * math.log(men) + co["log_speed"] * math.log(6.0))
            pbase = math.exp(pa + po["log_entities"] * math.log(men) + po["log_speed"] * math.log(6.0))
            w("| %s | %.2f | %.0f gold (typical size %.0f) | %.0f gold, ^ %.2f |\n" % (caste.replace("_", " "), s, base, men, pbase, ps))
        w("\nThe pooled column is one line through every caste: where it disagrees with the caste's own line, CA prices that caste "
          "differently from what the square-law model says it is worth (flatter for monsters, artillery and chariots: the top of "
          "those castes is cheap for its measured power, the bottom dear). The rebalance judges each unit against its own caste's "
          "line, so a monster is compared with monsters; the pooled line is the cross-caste question for the lore layer.\n\n")
        w("Trait premiums (shared by every caste):\n\n| term | coefficient | read as |\n|---|---|---|\n")
        w("| log entities | %+.3f | at equal regiment power, price ∝ entities ^ %.2f (negative: concentration is worth more) |\n" % (co["log_entities"], co["log_entities"]))
        for t in TRAITS:
            if t == "log_speed":
                w("| log speed | %.3f | price ∝ speed ^ %.2f |\n" % (co[t], co[t]))
            elif t == "active_abilities":
                w("| active abilities (each, up to 3) | %+.3f | %+.0f%% per ability |\n" % (co[t], (math.exp(co[t]) - 1) * 100))
            else:
                w("| %s | %+.3f | %+.0f%% |\n" % (t.replace("_", " "), co[t], (math.exp(co[t]) - 1) * 100))

        res = r["res"]
        w("\n## Residuals by caste\n\n| caste | units | spread | bargains (< −0.25) | over-priced (> +0.25) |\n|---|---|---|---|---|\n")
        for caste in UM.CASTES:
            idx = [i for i, x in enumerate(rows) if x["caste"] == caste and r["mask"][i]]
            if not idx:
                continue
            w("| %s | %d | %.3f | %d | %d |\n" % (caste.replace("_", " "), len(idx), float(np.std(res[idx])), sum(1 for i in idx if res[i] < -0.25), sum(1 for i in idx if res[i] > 0.25)))
        w("\n## By faction\n\n| faction | units | mean residual | bargains (< −0.25) | over-priced (> +0.25) |\n|---|---|---|---|---|\n")
        for fac in sorted(UM.FACTION_NAMES, key=lambda x: UM.FACTION_NAMES[x]):
            idx = [i for i, x in enumerate(rows) if x["faction"] == fac and r["mask"][i]]
            if not idx:
                continue
            m = float(np.mean(res[idx]))
            w("| %s | %d | %+.3f | %d | %d |\n" % (UM.FACTION_NAMES[fac], len(idx), m, sum(1 for i in idx if res[i] < -0.25), sum(1 for i in idx if res[i] > 0.25)))

        order = sorted([i for i in range(len(rows)) if r["mask"][i]], key=lambda i: res[i])
        w("\n## The forty biggest bargains (fight furthest above their price, against their caste's line)\n\n")
        w(TABLE_HEAD)
        for i in order[:40]:
            w(table_row(rows[i], r["p"][i], res[i], co))
        w("\n## The forty most over-priced (or carrying value the model does not see)\n\n")
        w(TABLE_HEAD)
        for i in order[::-1][:40]:
            w(table_row(rows[i], r["p"][i], res[i], co))

        w("\n## Every unit, by faction\n\n")
        w("**reg** is the regiment's power (the Empire Knights regiment = 1.00), **power** per model on the same scale "
          "(reg / entities × 60, so a 60-model unit of Empire Knight quality reads 1.00). **fair** is the price the valuation "
          "gives; **residual** is log(price / fair): + over-priced, − bargain. **reg@price** is the regiment power at which "
          "the unit would be worth its current price, the target the price-consistency rebalance uses.\n\n")
        for fac in sorted(UM.FACTION_NAMES, key=lambda x: UM.FACTION_NAMES[x]):
            idx = [i for i, x in enumerate(rows) if x["faction"] == fac]
            if not idx:
                continue
            w("### %s\n\n" % UM.FACTION_NAMES[fac])
            w(TABLE_HEAD)
            for i in sorted(idx, key=lambda i: (rows[i]["caste"], -r["p"][i])):
                w(table_row(rows[i], r["p"][i], res[i] if r["mask"][i] else None, co))
            w("\n")
    print("wrote", OUT_MD)


TABLE_HEAD = ("| unit | caste | n | price | MA/MD/CB | HP | arm | melee dps | ranged dps | lasts (s) | power | reg | fair | residual | reg@price |\n"
              + "|---" * 15 + "|\n")


def table_row(x, p, res, co):
    pr = x["prof"]
    fair = math.exp(fair_log_cost(co, x, p))
    pfp = power_for_price(co, x, x["cost"]) if x["cost"] > 0 else None
    return "| %s `%s` | %s | %d | %s | %.0f/%.0f/%.0f | %.0f | %.0f | %.1f | %s | %.0f | %.2f | **%.2f** | %.0f | %s | %s |\n" % (
        x["name"], x["key"], x["caste"].replace("_", " "), x["men"], x["cost"] or "n/a", x["ma"], x["md"], x["cb"], x["hp"], x["armour"],
        pr["off_melee"], ("%.1f" % pr["off_ranged"]) if pr["off_ranged"] else "-", pr["tough_melee"], p / x["men"] * 60, p,
        fair, ("%+.2f" % res) if res is not None else "n/a", ("%.2f" % pfp) if pfp else "n/a")


def main():
    rows = measure()
    print("measured", len(rows), "units")
    if "--no-search" in sys.argv:
        W = dict(UM.WEIGHTS)
        r = fit(rows, W)
        print("weights (from unit_model): %s  robust spread %.4f  rms %.4f" % (W, r["mad"], r["rms"]))
    else:
        W, r = search(rows)
    UM.WEIGHTS.update(W)
    UM.reset()
    pooled = fit(rows, W, per_caste=False)
    cv = cross_validate(rows, W)
    co = coefficients(r)
    print("coefficients:")
    for k, v in co.items():
        print("   %-28s %+.3f" % (k, v))
    print("per-caste rms %.4f  pooled rms %.4f  cross-validated rms %.4f" % (r["rms"], pooled["rms"], cv))
    p = r["p"]
    for i, x in enumerate(rows):
        x["power_reg"] = float(p[i])
        x["power"] = float(p[i] / x["men"] * 60)
        x["fair_cost"] = float(math.exp(fair_log_cost(co, x, p[i])))
        x["residual"] = float(r["res"][i]) if r["mask"][i] else None
        x["pooled_residual"] = float(pooled["res"][i]) if r["mask"][i] else None
        x["reg_at_price"] = float(power_for_price(co, x, x["cost"])) if x["cost"] > 0 else None
        x["prof"] = {k: v for k, v in x["prof"].items()}
    json.dump(dict(weights=W, coefficients=co, pooled=coefficients(pooled), traits=TRAITS,
                   spread=r["mad"], rms=r["rms"], cv_rms=cv, units=rows), open(OUT_JSON, "w"), indent=1)
    print("wrote", OUT_JSON)
    write_report(rows, W, r, pooled, cv)


if __name__ == "__main__":
    main()
