#!/usr/bin/env python3
"""The player-facing changelog: every change in the pack, one line per unit, faction by faction, in plain words.

    python3 rebalance_changelog.py        -> ../reports/changelog.md

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
    if o.get("gun"):
        parts.append("each volley %s harder, reload %s slower" % (pct(1.0, o["gun"][0]), pct(1.0, o["gun"][1])))
    if o["new_cost"] != o["cost"]:
        parts.append("price %d → %d" % (o["cost"], o["new_cost"]))
    if o["action"] == "decided":
        s = o["before"], o["after"]
        parts = ["attack %d → %d, defence %d → %d, charge %d → %d, HP %.0f → %.0f, leadership %.0f → %.0f, armour %.0f → %.0f, price %d → %d" % (
            b["ma"], a["ma"], b["md"], a["md"], b["cb"], a["cb"], b["hp"], a["hp"], b["morale"], a["morale"], b["armour"], a["armour"], o["cost"], o["new_cost"])]
    note = o["note"]
    if o["action"] == "gunpowder":
        why = "Gunpowder hits hard and reloads slow: fire from position, then pull back or reload in safety"
    elif o["action"] in ("lore", "decided") and ". " in note:
        why = note.split(". ", 1)[1].rstrip(".")           # the ladder's own words, not the arithmetic
    else:
        why = note.split(". ")[0].rstrip(".")
    return "- **%s**: %s. *%s.*" % (o["name"], "; ".join(parts) if parts else "no change", why)


def main():
    R = json.load(open(os.path.join(HERE, "_rebalance.json")))["units"]
    changed = [o for o in R if o["action"] != "none" and not o.get("held")]
    with open(OUT, "w") as out:
        w = out.write
        w("# Community Balance Patch: what changed\n\n")
        w("%d units across every faction. This is vanilla, adjusted: apart from the lore elites below no unit changes size, "
          "no unit's strength or price moves more than about 20%%, a stronger unit never gets cheaper and a weaker one never dearer, and regiments of "
          "renown move with their base unit. Every change keeps the unit's shape: charge, armour, speed, abilities, weapon "
          "type and splash never move; attack, defence, HP and damage move together. Percentages are against vanilla. "
          "See `docs/METHOD.md` for how units are measured.\n\n" % len(changed))
        w("**The headlines.** Elite infantry and elite cavalry are worth their price: Chaos Warriors, Chosen, Greatswords, "
          "Grave Guard, Temple Guard, Phoenix Guard, Grail Knights and Blood Knights all get a real step up over the line "
          "troops below them. Blood Knights, Grail Knights, Grail Guardians and the Swords of Chaos are fewer and far stronger, "
          "never with less total health than vanilla. Gunpowder hits hard and reloads slow: handguns, rifles, jezzails, "
          "blunderbusses and pistols fire a much heavier volley and take half again as long to reload. Chaff stays chaff "
          "and stays cheap. Monsters, war beasts, chariots and war machines are "
          "unchanged for now; they are open questions for the community, as are unit sizes.\n\n")
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
