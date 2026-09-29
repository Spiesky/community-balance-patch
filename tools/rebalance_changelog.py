#!/usr/bin/env python3
"""The player-facing changelog: every change in the pack, one line per unit, faction by faction, in plain words.

    python3 rebalance_changelog.py        -> ../REBALANCE_CHANGELOG.md

Reads _rebalance.json. Nothing here decides anything; it is what a workshop page or a patch note would show.
"""
import json
import os

import unit_model as UM

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(os.path.dirname(HERE), "reports", "changelog.md")


def pct(a, b):
    return "%+.0f%%" % ((b / a - 1) * 100) if a else ""


def line(o):
    a, b = o["after"], o["before"]
    parts = []
    if a["men"] != b["men"]:
        parts.append("%d → %d models" % (b["men"], a["men"]))
    dma, dmd = round(a["ma"] - b["ma"]), round(a["md"] - b["md"])
    if dma or dmd:
        parts.append("attack %+d, defence %+d" % (dma, dmd))
    if round(a["hp"]) != round(b["hp"]):
        parts.append("HP %s" % pct(b["hp"], a["hp"]))
    k = o.get("k") or 1.0
    if abs(k - 1) > 1e-9:
        parts.append("damage %s" % pct(1.0, k))
    if o["new_cost"] != o["cost"]:
        parts.append("price %d → %d" % (o["cost"], o["new_cost"]))
    if o["action"] == "decided":
        s = o["before"], o["after"]
        parts = ["attack %d → %d, defence %d → %d, charge %d → %d, HP %.0f → %.0f, leadership %.0f → %.0f, armour %.0f → %.0f, price %d → %d" % (
            b["ma"], a["ma"], b["md"], a["md"], b["cb"], a["cb"], b["hp"], a["hp"], b["morale"], a["morale"], b["armour"], a["armour"], o["cost"], o["new_cost"])]
    note = o["note"]
    if o["action"] in ("lore", "decided") and ". " in note:
        why = note.split(". ", 1)[1].rstrip(".")           # the ladder's own words, not the arithmetic
    else:
        why = note.split(". ")[0].rstrip(".")
    return "- **%s**: %s. *%s.*" % (o["name"], "; ".join(parts) if parts else "no change", why)


def main():
    R = json.load(open(os.path.join(HERE, "_rebalance.json")))["units"]
    changed = [o for o in R if o["action"] != "none" and not o.get("held")]
    with open(OUT, "w") as out:
        w = out.write
        w("# The great rebalance: what changed\n\n")
        w("%d units across every faction. Every change keeps the unit's shape: charge, armour, speed, abilities, weapon "
          "type and splash never move; attack, defence, HP and damage move together, and prices follow. Percentages are "
          "against vanilla. Read `GREAT_REBALANCE.md` for why.\n\n" % len(changed))
        w("**The headlines.** Elite guards are guards: Temple Guard, Phoenix Guard, Swordmasters and the Black Guard of "
          "Naggarond are 80 models of Chosen quality; Sisters of Avelorn are 60. Chaos Warriors are worth three state "
          "troops. Grail Knights are 32 and Blood Knights 24, each worth what the lore says. Greatswords, Grave Guard, "
          "Tomb Guard, White Lions, Wardancers and Eternal Guard rise to what they are. The great beasts the lore is "
          "unambiguous about (Bloodthirster, Dread Saurian, Hell Pit Abomination, Carnosaur, Hydra, Stonehorn) rise "
          "without getting dearer. Chaff stays chaff and stays cheap.\n\n")
        for fac in sorted(UM.FACTION_NAMES, key=lambda x: UM.FACTION_NAMES[x]):
            os_ = [o for o in changed if o["faction"] == fac]
            if not os_:
                continue
            w("## %s (%d)\n\n" % (UM.FACTION_NAMES[fac], len(os_)))
            for o in sorted(os_, key=lambda o: (o["caste"], o["name"])):
                w(line(o) + "\n")
            w("\n")
    print("wrote", OUT, "units:", len(changed))


if __name__ == "__main__":
    main()
