#!/usr/bin/env python3
"""Sum up battle logs from the Battle Logger mod (cbp_battle_log.txt files players share).

    python3 battle_logs.py log1.txt log2.txt ...          per unit: battles, models lost, kills per model lost, routs
    python3 battle_logs.py --unit blood_knights logs...    only units whose key contains the text

Each battle block starts with '#battle;v1;<date>;multiplayer=0|1;siege=0|1;mods=a.pack|b.pack' and has one line per unit:
'u;alliance;army;player;unit_key;initial_men;men_alive;kills;routing;shattered'. Auto-resolved battles start with
'#autoresolve;v1;<date>;winner=...;mods=...' and have 'a;side;player;unit_key;strength_before;strength_after' (percent).
Battles fought without the Community
Balance Patch loaded are counted separately (vanilla baseline).
"""
import collections, sys


def read(paths):
    for path in paths:
        battle = None
        for line in open(path, encoding="utf-8", errors="replace"):
            line = line.strip()
            if line.startswith("#battle;") or line.startswith("#autoresolve;"):
                parts = dict(p.split("=", 1) for p in line.split(";") if "=" in p)
                battle = dict(mods=parts.get("mods", "unknown"), units=[], auto=line.startswith("#autoresolve;"))
            elif line.startswith("u;") and battle is not None:
                f = line.split(";")
                if len(f) >= 10:
                    battle["units"].append(dict(key=f[4], men=f[5], alive=f[6], kills=f[7], routing=f[8]))
            elif line.startswith("a;") and battle is not None:
                f = line.split(";")                 # auto-resolve: strength in percent before and after
                if len(f) >= 6:
                    battle["units"].append(dict(key=f[3], men=f[4], alive=f[5], kills="0", routing="0"))
            elif line == "#end" and battle is not None:
                yield battle
                battle = None


def main():
    args = sys.argv[1:]
    only = None
    if "--unit" in args:
        i = args.index("--unit")
        only = args[i + 1]
        del args[i:i + 2]
    stats = collections.defaultdict(lambda: collections.Counter())
    for b in read(args):
        patched = "community_balance_patch.pack" in b["mods"]
        kind = "auto" if b.get("auto") else "fought"
        for u in b["units"]:
            if only and only not in u["key"]:
                continue
            try:
                men, alive, kills = int(u["men"]), int(u["alive"]), int(u["kills"])
            except ValueError:
                continue
            s = stats[(u["key"], ("patched " if patched else "vanilla ") + kind)]
            s["battles"] += 1
            s["men"] += men
            s["lost"] += men - alive
            s["kills"] += kills
            s["routed"] += u["routing"] == "1"
    print("%-50s %-14s %7s %7s %9s %7s" % ("unit", "version", "battles", "lost %", "kill/loss", "routed"))
    for (key, ver), s in sorted(stats.items()):
        print("%-50s %-14s %7d %6.0f%% %9.1f %6.0f%%" % (key[:50], ver, s["battles"], 100 * s["lost"] / max(1, s["men"]),
              s["kills"] / max(1, s["lost"]), 100 * s["routed"] / s["battles"]))


if __name__ == "__main__":
    main()
