#!/usr/bin/env python3
"""Calibrate the fairer auto-resolve rules from players' battle logs.

The question: does auto-resolve take its losses from the same unit classes a fought battle does? Where it takes too
much from a class (artillery and archers are kept safe at the back when the battle is fought), the rule for that
class slows the enemy's kill rate against it; where auto-resolve is too kind, it speeds it up.

    python3 autoresolve_calibrate.py logs/*.txt              prints the tables and the proposed rules
    python3 autoresolve_calibrate.py --write logs/*.txt      also writes autoresolve_rules.json (autoresolve_rules.py reads it)
    --include-modded                                         also count battles where other mods were loaded
    --trust-files                                            count hand-saved files as one player each (see below)

What is compared. Only the player's own units count (that is the side whose placement the rule models).
  auto side    auto-resolved battles (#result mode=auto, #autoresolve v1) WITHOUT the auto-resolve test pack: a
               battle resolved with the rules loaded is the rules' own output and cannot calibrate them. Battles
               with the patch itself are kept: the patch (0.1 and 0.2) carries no auto-resolve rules. A battle whose
               mod list could not be read is never used here: the test pack may have been loaded.
  fought side  the campaign's result of fought battles (#result mode=fought): strength before and after, the same
               measure as the auto side. Version 1 fought battles only have model counts and no campaign flag (they
               may be custom battles); they get a table of their own and never make a rule.

The statistic is the class loss index: within one battle, the share of the army's losses a class took, divided by the
share of the army's strength it held. 1 means the class lost in proportion, 2 means it lost twice its share. Summed
over battles (sum of loss shares / sum of strength shares). It is taken inside each battle, so how hard the battle
was cancels to first order; the plain loss percentages are printed too but they do not cancel it.
The rule for a class is fought index / auto index - 1, within LIMITS.

A class gets a rule only with at least MIN_FILES distinct players and MIN_BATTLES distinct battles on each side,
and only when the bootstrap interval of the rule value excludes zero. The bootstrap (seeded) resamples players, not
battles: one player's battles are alike, so few players give a wide interval however many battles they sent.

Who is a distinct player. Files written by fetch_logs.py (issue_<number>_<author>.txt) count one per GitHub author.
Any other file is one source per file, and does NOT count towards MIN_FILES: one player's log saved under five names
would otherwise pass as five players. --trust-files counts them, for files you know came from different people.

--write only writes back-line classes (BACK_LINE: the test pack is about the units kept at the back). A rule that
passes for another class is printed and not written. The file holds every back-line rule: the calibrated ones over
the rules autoresolve_rules.py has now, so a class without enough data keeps its value instead of losing its rule.
"""
import json, os, sys
import numpy as np
import vanilla as V
from battle_logs import load

HERE = os.path.dirname(os.path.abspath(__file__))
RULES_JSON = os.path.join(HERE, "autoresolve_rules.json")
MIN_FILES = 5               # distinct players (see the docstring) needed per class on each side
MIN_BATTLES = 20            # distinct battles needed per class on each side
LIMITS = (-0.9, 0.5)        # the most a rule may slow down or speed up the enemy's kill rate
DRAWS = 2000                # bootstrap resamples
SEED = 1
BACK_LINE = {"art_fld": -0.70, "inf_mis": -0.35, "cav_mis": -0.25}  # the classes the test pack covers, and the starting
                            # guesses of autoresolve_rules.py (used here only if that file cannot be imported)

HEADER = """Players choose which battles to fight and which to auto-resolve (close ones are fought, easy ones resolved),
so the two sides are different battles and the comparison is indicative, not a measurement. The class loss index is
taken within each battle, which cancels battle difficulty to first order; the loss percentages do not."""


def unit_class():
    lu = V.index("land_units")
    mu = V.index("main_units", "unit")
    return {k: lu[m["land_unit"]]["class"] for k, m in mu.items() if m["land_unit"] in lu}


def army(units, cls, had, left):
    """class -> [strength before, strength lost] for the player's units of one battle"""
    out = {}
    for u in units:
        c = cls.get(u["key"])
        before, after = u.get(had), u.get(left)
        if u["player"] is not True or not c or not before or after is None or before <= 0:
            continue
        s = out.setdefault(c, [0.0, 0.0])
        s[0] += before
        s[1] += min(before, max(0.0, before - after))
    return out


def samples(blocks, cls, with_mods=False):
    """side -> list of (battle id, source, {class: [before, lost]}); and why blocks were left out"""
    out, skipped = {"fought": [], "auto": [], "v1": []}, {}

    def skip(why):
        skipped[why] = skipped.get(why, 0) + 1

    for b in blocks:
        if b["kind"] == "battle" and b["version"] >= 2:
            continue                                    # its campaign result, if there is one, is the block used
        if b["kind"] == "result" and b["mode"] == "auto" and not b["mods_known"]:
            skip("auto-resolved with a mod list that could not be read (the test pack may have been loaded)")
            continue                                    # whatever --include-modded says
        if not with_mods and not b["clean"]:
            skip("other mods loaded, or the mod list could not be read (--include-modded counts them)")
            continue
        if b["kind"] == "battle":
            if b["head"].get("multiplayer") == "1":
                skip("version 1 multiplayer battles")
                continue
            side, a = "v1", army(b["units"], cls, "men", "alive")
        elif b["mode"] == "auto":
            if b["ar_rules"]:
                skip("auto-resolved with the auto-resolve test pack loaded (the rules' own output)")
                continue
            side, a = "auto", army(b["units"], cls, "before", "after")
        elif b["mode"] == "fought":
            side, a = "fought", army(b["units"], cls, "before", "after")
        else:
            skip("results with an unknown mode")
            continue
        if not a:
            skip("no player units that could be read")
        elif sum(s[1] for s in a.values()) <= 0:
            skip("the player's army lost nothing (no loss shares to take)")
        else:
            out[side].append((b["id"], b["source"], a))
    return out, skipped


def counted(src, trust=False):
    """Does this source count as a distinct player? Only files named by fetch_logs.py, unless trusted."""
    return trust or src.startswith("author:")


def shares(side_samples, c, trust=False):
    """For the battles a class took part in: its loss and strength shares summed per source (one row per source,
    the unit the bootstrap resamples), the number of battles, and the sources that count as distinct players"""
    by_src, n, had, lost = {}, 0, 0.0, 0.0
    for _, src, a in side_samples:
        if c not in a:
            continue
        s = by_src.setdefault(src, [0.0, 0.0])
        s[0] += a[c][1] / sum(x[1] for x in a.values())
        s[1] += a[c][0] / sum(x[0] for x in a.values())
        n += 1
        had += a[c][0]
        lost += a[c][1]
    srcs = sorted(by_src)
    return dict(loss=np.array([by_src[k][0] for k in srcs]), strength=np.array([by_src[k][1] for k in srcs]),
                files=sum(counted(k, trust) for k in srcs), sources=len(srcs), n=n, rate=lost / had if had else None)


def index(s):
    return float(s["loss"].sum() / s["strength"].sum()) if s["n"] else None


def interval(f, a, rng):
    """95% bootstrap interval of fought index / auto index - 1, resampling sources (players) on each side.
    None with fewer than two sources on a side: one player cannot say how much players differ."""
    if f["sources"] < 2 or a["sources"] < 2:
        return None

    def draw(s):
        i = rng.integers(0, s["sources"], (DRAWS, s["sources"]))
        return s["loss"][i].sum(1) / s["strength"][i].sum(1)
    with np.errstate(divide="ignore", invalid="ignore"):
        v = draw(f) / draw(a) - 1.0
    v = v[np.isfinite(v)]
    if not len(v):
        return None
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def calibrate(blocks, cls, with_mods=False, trust=False):
    """(rows, rules, skipped, counts): one row per class with both sides' numbers, and the rules that pass"""
    data, skipped = samples(blocks, cls, with_mods)
    rng = np.random.default_rng(SEED)
    rows, rules = [], {}
    for c in sorted(set(k for side in data.values() for _, _, a in side for k in a)):
        f, a, old = shares(data["fought"], c, trust), shares(data["auto"], c, trust), shares(data["v1"], c, trust)
        r = dict(cls=c, fought=f, auto=a, v1=old, fi=index(f), ai=index(a), v1i=index(old), value=None, ci=None)
        enough = all(s["n"] >= MIN_BATTLES and s["files"] >= MIN_FILES for s in (f, a))
        if not f["n"] or not a["n"]:
            r["rule"] = "no data on one side"
        elif not r["ai"]:
            r["rule"] = "no auto losses"
        else:
            r["value"] = r["fi"] / r["ai"] - 1.0
            r["ci"] = interval(f, a, rng)
            if not enough:
                r["rule"] = "not enough data"
            elif r["ci"] is None or r["ci"][0] <= 0.0 <= r["ci"][1]:
                r["rule"] = "not clear"
            elif abs(r["value"]) < 0.05:
                r["rule"] = "matches"
            else:
                rules[c] = round(max(LIMITS[0], min(LIMITS[1], r["value"])), 2)
                r["rule"] = "%+.2f" % rules[c]
        rows.append(r)
    return rows, rules, skipped, {k: len(v) for k, v in data.items()}


def current_rules():
    """The back-line rules autoresolve_rules.py uses now (its starting guesses, or the file written last time)"""
    try:
        import autoresolve_rules
        now = dict(autoresolve_rules.RULES)
    except Exception:
        now = dict(BACK_LINE)
    return {c: v for c, v in now.items() if c in BACK_LINE}


def to_write(rules, now):
    """(the rules file's content, the passing rules left out of it). Calibrated back-line classes go over the rules
    in use now; classes outside BACK_LINE are never written."""
    mine = {c: v for c, v in rules.items() if c in BACK_LINE}
    merged = dict(now)
    merged.update(mine)
    content = dict(rules=merged, calibrated=sorted(mine), kept_from_before=sorted(set(merged) - set(mine)),
                   source="battle logs", statistic="class loss index, fought / auto - 1",
                   min_files=MIN_FILES, min_battles=MIN_BATTLES)
    return content, {c: v for c, v in rules.items() if c not in BACK_LINE}


def pct(x):
    return "-" if x is None else "%.0f%%" % (100 * x)


def fmt(x, f="%.2f"):
    return "-" if x is None else f % x


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit(__doc__)
    cls = unit_class()
    if not cls:
        sys.exit("vanilla_db not found: the unit classes come from it (see docs/TOOLS.md)")
    blocks, info = load(args)
    trust = "--trust-files" in sys.argv
    rows, rules, skipped, counts = calibrate(blocks, cls, "--include-modded" in sys.argv, trust)
    print(HEADER)
    print("\nread %d blocks from %d files: %d duplicates left out, %d distinct log files"
          % (info["blocks"], info["files"], info["duplicates"], info["distinct files"]))
    print("used: %d fought battles with a campaign result, %d auto-resolved battles, %d version 1 fought battles"
          % (counts["fought"], counts["auto"], counts["v1"]))
    for why, n in sorted(skipped.items()):
        print("left out: %d  %s" % (n, why))
    print("\nStrength on both sides (campaign results). A rule needs %d players and %d battles per class on each side."
          % (MIN_FILES, MIN_BATTLES))
    if trust:
        print("bat/pl: battles / players. --trust-files: every hand-saved file is counted as one player.")
    else:
        print("bat/pl: battles / players. A player is a GitHub author of files fetched by fetch_logs.py; hand-saved files")
        print("are used for the numbers, one source per file, but are not counted as players (--trust-files counts them).")
    print("The interval resamples players (sources), not battles.")
    print("%-12s %14s %14s %8s %8s %8s %8s %7s %15s  %s" % ("class", "fought bat/pl", "auto bat/pl", "fought %",
          "auto %", "f index", "a index", "value", "95% interval", "rule"))
    for r in rows:
        if not r["fought"]["n"] and not r["auto"]["n"]:
            continue
        ci = "-" if r["ci"] is None else "%+.2f to %+.2f" % r["ci"]
        print("%-12s %14s %14s %8s %8s %8s %8s %7s %15s  %s" % (
            r["cls"], "%d/%d" % (r["fought"]["n"], r["fought"]["files"]), "%d/%d" % (r["auto"]["n"], r["auto"]["files"]),
            pct(r["fought"]["rate"]), pct(r["auto"]["rate"]), fmt(r["fi"]), fmt(r["ai"]), fmt(r["value"], "%+.2f"), ci, r["rule"]))
    if counts["v1"]:
        print("\nVersion 1 fought battles (models, may include custom battles): shown for reference, never used for a rule.")
        print("%-12s %14s %8s %8s" % ("class", "battles/pl", "lost %", "index"))
        for r in rows:
            if r["v1"]["n"]:
                print("%-12s %14s %8s %8s" % (r["cls"], "%d/%d" % (r["v1"]["n"], r["v1"]["files"]), pct(r["v1"]["rate"]), fmt(r["v1i"])))
    print("\nproposed rules:", rules or "none yet")
    now = current_rules()
    content, front = to_write(rules, now)
    if front:
        print("not for the test pack (it only covers the back line, %s): %s" % (", ".join(sorted(BACK_LINE)), front))
    if "--write" not in sys.argv:
        return
    if not content["calibrated"]:
        print("nothing written: no back-line class has a rule yet")
        return
    with open(RULES_JSON, "w") as fh:
        json.dump(content, fh, indent=1)
    print("wrote", RULES_JSON)
    print("  calibrated: %s" % ", ".join("%s %+.2f" % (c, content["rules"][c]) for c in content["calibrated"]))
    if content["kept_from_before"]:
        print("  kept as they were (not enough data to calibrate): %s"
              % ", ".join("%s %+.2f" % (c, content["rules"][c]) for c in content["kept_from_before"]))


if __name__ == "__main__":
    main()
