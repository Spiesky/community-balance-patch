#!/usr/bin/env python3
"""The player-facing changelog: every change in the pack, one line per unit, faction by faction, in plain words.

    python3 rebalance_changelog.py        -> ../reports/changelog.md       the whole draft (_rebalance.json)
    CBP_BETA=1 CBP_PROPOSALS=_beta.json CBP_CHANGELOG=../reports/beta_changelog.md python3 rebalance_changelog.py
                                          -> what the Workshop pack changes: the beta's themes (_beta.json) and the
                                             community list as the builder applied it (build/beta/community_log.json).
                                             tools/patch_day.sh runs this, so the list cannot fall behind the pack.

Nothing here decides anything; it is what a workshop page or a patch note would show.
"""
import json
import os

import unit_model as UM
import community as C
import gunpowder as GP

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.environ.get("CBP_CHANGELOG") or os.path.join(ROOT, "reports", "changelog.md")
COMMUNITY_LOG = os.environ.get("CBP_COMMUNITY_LOG") or os.path.join(ROOT, "build", "beta", "community_log.json")
VERSION = open(os.path.join(ROOT, "VERSION")).read().strip()


def pct(a, b):
    return "%+.0f%%" % ((b / a - 1) * 100) if a else ""


def line(o, listed=()):
    """listed: the community list's entries for this unit, so a gun's reload and ammunition are shown as they end up"""
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
    if abs(a["cb"] - b["cb"]) > 0.5 and o["action"] != "decided":
        parts.append("charge bonus %.0f → %.0f" % (b["cb"], a["cb"]))
    if o.get("gun"):
        m0, m1 = b["missile"], a["missile"]
        own = sum(ch.get("reload", 0) for _, ch in listed)
        reload = m1["reload"] + own * o["gun"][1]
        ammo = GP.ammo(m0["ammo"] + sum(ch.get("ammo", 0) for _, ch in listed))
        slower = ("reload %.1fs → %.1fs (the list's %+gs, then %s)" % (m0["reload"], reload, own, pct(1.0, o["gun"][1])) if own
                  else "reload %s slower (%.1fs → %.1fs)" % (pct(1.0, o["gun"][1]), m0["reload"], reload))
        parts.append("each volley %s harder, %s, ammunition %d → %d" % (pct(1.0, o["gun"][0]), slower, m0["ammo"], ammo))
    if o["new_cost"] != o["cost"]:
        parts.append("price %d → %d" % (o["cost"], o["new_cost"]))
    if o["action"] == "decided":
        s = o["before"], o["after"]
        parts = ["attack %d → %d, defence %d → %d, charge %d → %d, HP %.0f → %.0f, leadership %.0f → %.0f, armour %.0f → %.0f, price %d → %d" % (
            b["ma"], a["ma"], b["md"], a["md"], b["cb"], a["cb"], b["hp"], a["hp"], b["morale"], a["morale"], b["armour"], a["armour"], o["cost"], o["new_cost"])]
    note = o["note"]
    if o["action"] == "gunpowder":
        why = "Gunpowder hits hard and reloads slow: fire from position, then pull back or reload in safety"
    elif o.get("community_only"):
        return "- **%s**: %s." % (o["name"], "; ".join(parts))
    elif o["action"] in ("lore", "decided") and ". " in note:
        why = note.split(". ", 1)[1].rstrip(".")           # the ladder's own words, not the arithmetic
    else:
        why = note.split(". ")[0].rstrip(".")
    return "- **%s**: %s. *%s.*" % (o["name"], "; ".join(parts) if parts else "no change", why)


# the community list's change keys in the words a unit card uses (community.py has the keys)
WORDS = dict(ma="melee attack", md="melee defence", cb="charge bonus", ld="leadership", hp="HP per model", hp_total="HP (whole unit)",
             ws_base="weapon damage", ws_ap="armour-piercing damage", bvi="bonus vs infantry", bvl="bonus vs large", armour="armour",
             cost="gold", mass="mass", speed="speed", accuracy="accuracy", ammo="ammunition", missile_base="missile damage",
             missile_ap="missile armour-piercing damage", range="range", reload="s reload", missile_res="% missile resistance",
             mount_speed="mount speed")
SETS = dict(accel="acceleration", decel="deceleration", turn="turn speed", mount_turn="mount turn speed", rank_depth="rank depth",
            men="models", ammo_set="ammunition", calibration_set="calibration area", shockwave="shockwave radius", hp_set="HP per model",
            radii_ratio="hitbox radii ratio", acceleration="acceleration", deceleration="deceleration", turn_speed="turn speed",
            walk_speed="walk speed", run_speed="run speed", fire_arc_close="fire arc", spacing="unit spacing")


def community_words(ch, gun=None):
    """one community entry as text; on a gun the missile numbers go through the gunpowder rule, as the builder applies them"""
    out = []
    for k, v in ch.items():
        if k.startswith("_") or k == "follows":
            continue
        if gun and k in ("missile_base", "missile_ap"):
            v = int(round(v * gun[0]))
        if gun and k == "reload":
            v = v * gun[1]
        if k == "ws_swap":
            out.append("%d weapon damage moved to armour-piercing" % v)
        elif k in ("ws_base_set", "ws_ap_set"):
            out.append("%s set to %s" % ("weapon damage" if k == "ws_base_set" else "armour-piercing damage", v))
        elif k == "spacing":
            out.append("tighter unit spacing")
        elif k in SETS:
            out.append("%s %s" % (SETS[k], ("%g" % v) if isinstance(v, (int, float)) else v))
        elif k == "ammo" and gun:
            out.append("%+d ammunition before the gunpowder rule" % v)
        elif k == "reload" and gun:
            continue                                   # shown on the gun line, as the reload the unit ends with
        elif k in WORDS:
            out.append(("%+g%s" if WORDS[k].startswith(("%", "s ")) else "%+g %s") % (v, WORDS[k]))
        else:
            out.append("%s %s" % (k, v))
    return ", ".join(out)


def beta(R, w):
    """the Workshop pack: the solver's themes plus the community list as the builder applied it"""
    changed = {o["key"]: o for o in R if o["action"] != "none" and not o.get("held")}
    log = json.load(open(COMMUNITY_LOG)) if os.path.exists(COMMUNITY_LOG) else []
    guns = {o["key"]: o["gun"] for o in R if o.get("gun")}
    by_key = {o["key"]: o for o in R}
    listed, skipped = {}, 0
    labels = {ln: what for ln, what, ents, sets in C.ARTILLERY + C.ENTITIES}
    labels[C.MOUNT_ACCEL[0]] = C.MOUNT_ACCEL[1]
    engines = {}
    for ln, key, ch in log:
        if isinstance(ch, str):
            skipped += 1
        elif ln in labels:                             # an engine, mount or other shared entity, changed in place
            engines.setdefault(labels[ln], dict(ch))
        else:
            listed.setdefault(key, []).append((ln, ch))
    units = set(changed) | set(listed)
    n_elite = sum(1 for o in changed.values() if o.get("elite"))
    n_gun = sum(1 for o in changed.values() if o.get("gun"))
    n_theme = sum(1 for o in changed.values() if o.get("theme"))
    w("# Community Balance Patch beta %s: what is in the pack\n\n" % VERSION)
    w("%d units change. Four things are in the pack; everything else in `reports/changelog.md` is still a proposal, waiting "
      "for players to test it and argue about it. This page is generated from the pack's own data by `tools/patch_day.sh`.\n\n" % len(units))
    w("**Lore elites are fewer and far stronger** (%d units). Blood Knights, Grail Knights, Grail Guardians and the Swords of "
      "Chaos. A unit made smaller never has less total health than vanilla, its charge grows with its blows, and its price "
      "never rises faster than the strength it can actually use: a blow that does more damage than its target has hit "
      "points is not counted twice. Fewer riders means fewer swings: they kill chaff more slowly than vanilla and elite "
      "and large targets much faster.\n\n" % n_elite)
    w("**Gunpowder hits hard and reloads slow** (%d units). Handguns, rifles, jezzails, blunderbusses and pistols fire a %.0f%% "
      "heavier volley, take %.0f%% longer to reload and carry less ammunition, so the damage over a whole battle is about "
      "vanilla's and the price does not move. How they are played changes: get them into position, fire, then pull back or let them reload "
      "in safety.\n\n" % (n_gun, (GP.DAMAGE - 1) * 100, (GP.RELOAD - 1) * 100))
    w("**Elite infantry is worth its price** (%d units). Melee infantry the lore ladder rates elite or champion, and "
      "Greatswords, get more health and damage (up to about 17%%) and a point or two of attack and defence, at the "
      "vanilla price. Units the community list already covers take the list's numbers instead.\n\n" % n_theme)
    n_follow = sum(1 for k, es in listed.items() if any(ch.get("follows") for _, ch in es))
    w("**The multiplayer community's balance list** (%d units, and %d list entries for artillery, chariots and mounts). "
      "The peer-reviewed recommendations of the Total Tavern and Vermin League communities for patch 7.1+, as they wrote "
      "them, minus what CA already did in 8.1 and minus %d entries held because campaign players already find those units "
      "too strong (`docs/COMMUNITY_LIST.md`). Where the list changes a unit and does not mention its regiment of renown, "
      "the regiment takes the same changes (%d of the units), so it is not left behind its base. On a gun the list's "
      "missile numbers go through the gunpowder rule.\n\n" % (len(listed), len(engines), len(C.HELD), n_follow))
    w("Not in the pack: auto-resolve changes (a test pack of its own, `docs/AUTORESOLVE.md`), the patch's own proposals "
      "for monsters, war beasts, chariots and war machines, unit sizes other than the lore elites and the list's Blades "
      "of Hoeth, lords and heroes, spells and abilities.\n\n")
    for fac in sorted(UM.FACTION_NAMES, key=lambda x: UM.FACTION_NAMES[x]):
        keys = [k for k in units if (by_key[k]["faction"] if k in by_key else UM.faction(k)) == fac]
        if not keys:
            continue
        w("## %s (%d)\n\n" % (UM.FACTION_NAMES[fac], len(keys)))
        rows = []
        for k in sorted(keys, key=lambda k: by_key[k]["name"]):
            o = by_key[k]
            own = line(o, listed.get(k, ())) if k in changed else None
            com = "; ".join(x for x in (community_words(ch, guns.get(k)) for _, ch in listed.get(k, [])) if x)
            base = next((ch["follows"] for _, ch in listed.get(k, []) if ch.get("follows")), None)
            tag = "Community list, as its base unit %s" % base if base else "Community list"
            if own and com:
                rows.append("%s %s: %s." % (own, tag, com))
            elif own:
                rows.append(own)
            else:
                rows.append("- **%s**: %s. *%s.*" % (o["name"], com, tag))
        for i, r in enumerate(rows):                    # a unit the game has under two keys (campaign copies) reads as one line
            if r in rows[:i]:
                continue
            n = rows.count(r)
            w((r.replace("**: ", "** (%d versions of the unit): " % n, 1) if n > 1 else r) + "\n")
        w("\n")
    if engines:
        w("## Artillery, chariots, mounts and a hitbox (community list)\n\nThese change the shared engine or mount, so "
          "every unit using it moves with it.\n\n")
        for what, sets in sorted(engines.items()):
            w("- **%s**: %s.\n" % (what, ", ".join("%s %g" % (SETS.get(k, k), v) for k, v in sets.items())))
        w("\n")
    print("wrote", OUT, "units:", len(units), "(lore elites %d, gunpowder %d, elite infantry %d, community list %d)" % (n_elite, n_gun, n_theme, len(listed)))


def main():
    R = json.load(open(os.environ.get("CBP_PROPOSALS") or os.path.join(HERE, "_rebalance.json")))["units"]
    changed = [o for o in R if o["action"] != "none" and not o.get("held")]
    with open(OUT, "w") as out:
        w = out.write
        if os.environ.get("CBP_BETA") == "1":
            beta(R, w)
            return
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
