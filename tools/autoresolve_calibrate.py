#!/usr/bin/env python3
"""Calibrate the fairer auto-resolve rules from players' battle logs.

For every unit class, compare how much of a unit is lost in battles players actually fight with how much auto-resolve
takes. Where auto-resolve kills a class faster than real battles do (artillery and archers are kept safe at the back),
the rule for that class slows the enemy's kill rate against it by the same factor; where auto-resolve is too kind, it
speeds it up. Only the player's own units count (that is the side whose placement we are modelling), and only classes
with enough data on both sides.

    python3 autoresolve_calibrate.py logs/*.txt              prints the table and the proposed rules
    python3 autoresolve_calibrate.py --write logs/*.txt      also writes autoresolve_rules.json (autoresolve_rules.py reads it)
    --include-modded                                         also count battles where other mods were loaded
"""
import json, os, sys
import vanilla as V
from battle_logs import read, clean

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_JSON = os.path.join(HERE, "autoresolve_rules.json")
MIN_UNITS = 30              # unit appearances needed on each side before a class gets a rule
LIMITS = (-0.9, 0.5)        # the most a rule may slow down or speed up the enemy's kill rate


def unit_class():
    lu = V.index("land_units")
    mu = V.index("main_units", "unit")
    return {k: lu[m["land_unit"]]["class"] for k, m in mu.items() if m["land_unit"] in lu}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    cls = unit_class()
    agg = {}                # class -> {"fought": [lost, had, n], "auto": [...]}
    with_mods = "--include-modded" in sys.argv
    skipped = 0
    for b in read(args):
        if not with_mods and not clean(b["mods"]):
            skipped += 1                # other mods may change how units fight: clean battles only, unless asked
            continue
        kind = "auto" if b.get("auto") else "fought"
        for u in b["units"]:
            if u.get("player") not in (None, "1"):
                continue
            c = cls.get(u["key"])
            try:
                had, left = float(u["men"]), float(u["alive"])
            except ValueError:
                continue
            if not c or had <= 0:
                continue
            s = agg.setdefault(c, {"fought": [0.0, 0.0, 0], "auto": [0.0, 0.0, 0]})[kind]
            s[0] += max(0.0, had - left)
            s[1] += had
            s[2] += 1
    rules = {}
    print("%-10s %8s %8s %9s %9s %8s" % ("class", "fought n", "auto n", "fought %", "auto %", "rule"))
    for c, s in sorted(agg.items()):
        f, a = s["fought"], s["auto"]
        fr = f[0] / f[1] if f[1] else None
        ar = a[0] / a[1] if a[1] else None
        rule = "not enough data"
        if f[2] >= MIN_UNITS and a[2] >= MIN_UNITS and ar and fr is not None:
            value = max(LIMITS[0], min(LIMITS[1], fr / ar - 1.0))
            rule = "matches"
            if abs(value) >= 0.05:
                rules[c] = round(value, 2)
                rule = "%+.2f" % value
        print("%-10s %8d %8d %8s %8s %8s" % (c, f[2], a[2], "%.0f%%" % (100 * fr) if fr is not None else "-",
                                             "%.0f%%" % (100 * ar) if ar is not None else "-", rule))
    print("\n%d battles with other mods left out (--include-modded counts them)" % skipped if skipped else "")
    print("proposed rules:", rules or "none yet")
    if "--write" in sys.argv:
        json.dump(dict(rules=rules, source="battle logs", min_units=MIN_UNITS), open(RULES_JSON, "w"), indent=1)
        print("wrote", RULES_JSON)


if __name__ == "__main__":
    main()
