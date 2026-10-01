#!/usr/bin/env python3
"""Gunpowder: hit hard, reload slow.

Single-shot firearms (handguns, rifles, long rifles, jezzails, blunderbusses, fireglaives, pistols) fire a heavier volley and take
longer to reload, so the play is: get them into position, fire, then pull them back or let them reload in safety.
Damage per volley x DAMAGE, reload time x RELOAD, ammunition / DAMAGE: about the same damage over time (+7% while
firing) and the same damage over a battle, delivered in bigger, rarer bursts. The unit's worth barely moves, so its
price does not; how it is played does. (Without the ammunition cut every gun would do 60% more damage per battle, which
is a buff, not a change of rhythm.)

Not firearms in this sense, left alone: flame weapons (Irondrakes, warpfire, salamanders), rapid fire (ratling guns,
repeaters, clatterguns), throwing stars and spikes, and anything in a caste the patch keeps vanilla (war machines,
chariots, war beasts).

    python3 gunpowder.py        lists the units it applies to
"""
import math
import re

DAMAGE = 1.6
RELOAD = 1.5
AMMO = 1.0 / DAMAGE          # ammunition: about the same total damage per battle as vanilla


def ammo(n):
    """a unit's ammunition under the rule: rounded half up (20 -> 13, not 12), never below 4 volleys"""
    return max(4, int(math.floor(float(n) * AMMO + 0.5))) if float(n) > 0 else int(float(n))
CASTES = {"melee_infantry", "missile_infantry", "monstrous_infantry", "melee_cavalry", "missile_cavalry", "monstrous_cavalry"}
# gunners CA files under a caste the patch otherwise keeps vanilla: zombie gunners on bats carry the same pistols and
# handguns as the gunnery mobs (the bombers, _1, throw grenades and are not covered)
ALSO = re.compile(r"cst_cav_deck_droppers_(0|2)$")
NOT_GUNS = re.compile(r"throwing_star|razordon|spike|ratling|repeater|clattergun|warpfire|flame|drakegun")


def applies(card, caste):
    """True if the unit's primary missile weapon is a single-shot firearm this rule covers"""
    m = card.get("missile")
    if not m or (caste not in CASTES and not ALSO.search(card.get("key", ""))) or m.get("category") != "musket":
        return False
    if NOT_GUNS.search(m.get("projectile", "")):
        return False
    return m.get("volley", 1.0) <= 6.0      # one shot, a brace of pistols, or a blunderbuss blast of pellets


def apply(card):
    """the card with the gunpowder rule applied to its missile weapon"""
    c = dict(card)
    m = dict(c["missile"])
    for d in ("base", "ap", "bvl", "bvi"):
        m[d] = m[d] * DAMAGE
    m["reload"] = m["reload"] * RELOAD
    m["ammo"] = ammo(m["ammo"])
    c["missile"] = m
    return c


if __name__ == "__main__":
    import json, os
    import unit_model as UM
    S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_survey.json")))
    n = 0
    for u in sorted(S["units"], key=lambda u: (u["faction"], u["name"])):
        c = UM.card(u["key"])
        if applies(c, u["caste"]):
            n += 1
            m = c["missile"]
            print("%-4s %-45s %3.0f+%-3.0f every %4.1fs, %2.0f volleys  ->  %3.0f+%-3.0f every %4.1fs, %2d volleys" % (
                u["faction"], u["name"][:45], m["base"], m["ap"], m["reload"], m["ammo"], m["base"] * DAMAGE, m["ap"] * DAMAGE,
                m["reload"] * RELOAD, ammo(m["ammo"])))
    print(n, "units")
