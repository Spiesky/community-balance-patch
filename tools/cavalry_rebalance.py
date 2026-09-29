#!/usr/bin/env python3
"""A lore-first rebalance study of every cavalry unit in the game, plus hypothetical units the lore has and the game
does not. Writes ../CAVALRY_REBALANCE_DATA.md. The combat model is cavalry_model.py.

Per unit:
  profile   everything that decides its fights: size, cost, upkeep, attack, defence, charge, HP, armour, ward and
            resistances, weapon (base, AP, bonus vs large, bonus vs infantry, splash, magical, flaming), mass, speed,
            leadership, damage per second against five real vanilla opponents, survival time against three, and
            missile damage where it has a missile weapon
  power     per model, sqrt(offence x toughness) over those opponents, Empire Knights = 1.00
  lore      a power target per model (the LORE table), from the army books and background
  proposal  stats solved to reach the target, unit size where the lore calls for fewer, rarer riders, and a price
            scaled from the vanilla price by the change in total power

Lore targets were set on an earlier, simpler model; TARGET_EXPONENT maps them onto this one (its scale is compressed
at the top: a target of 3.8 there is 3.3 here, 9 is 7.2).
"""
import math
import os
import re

import cavalry_model as M

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports", "cavalry_study.md")
TARGET_EXPONENT = 0.9
RENOWN = 1.35

FACTIONS = {
    "emp": "The Empire", "brt": "Bretonnia", "cst": "The Damned (Mousillon knights, cst units)", "vmp": "Vampire Counts",
    "tmb": "Tomb Kings", "chs": "Warriors of Chaos", "nor": "Norsca", "kho": "Khorne", "nur": "Nurgle", "sla": "Slaanesh",
    "tze": "Tzeentch", "hef": "High Elves", "def": "Dark Elves", "wef": "Wood Elves", "lzd": "Lizardmen", "grn": "Greenskins",
    "ogr": "Ogre Kingdoms", "ksl": "Kislev", "cth": "Grand Cathay", "chd": "Chaos Dwarfs", "bst": "Beastmen",
}

# (key pattern, power target per model vs Empire Knights on the earlier scale, tier, size or None, lore note)
# Tabletop profiles are from memory of the 6th-8th edition army books and are approximate.
LORE = [
    # --- rabble and scouts
    (r"goblin_wolf_riders|moon_howlers|mogrubbs", 0.45, "rabble", None, "Goblins on wolves: WS2 S3 T3. Numbers and speed, never a fair fight."),
    (r"spider_riders|deff_creepers", 0.6, "rabble", None, "Forest goblins on giant spiders: poisoned, but still goblins."),
    (r"squig_hoppers|durkits", 0.9, "rabble", None, "Bouncing squigs: huge bite, no control, no armour."),
    (r"peasant_horsemen", 0.5, "rabble", None, "Cathay's peasant levies on horseback."),
    (r"mounted_yeomen", 0.55, "rabble", None, "Bretonnian commoners allowed a horse: WS3 at best."),
    (r"hobgoblin_wolf_raiders", 0.5, "rabble", None, "Hobgoblins on wolves: cowardly raiders."),
    (r"skeleton_horsemen", 0.55, "rabble", None, "Skeleton horsemen: WS2 S3 T3, unfeeling but brittle."),
    # --- light cavalry
    (r"marauder_horse|kurgan_horsemen|horsemasters", 0.8, "light", None, "Northmen raised in the saddle: WS4 S3 T3, lightly armoured."),
    (r"dark_riders", 0.75, "light", None, "Dark Riders: WS4 S3 T3, fast raiders in light armour."),
    (r"ellyrian_reavers|heralds_of_the_wind", 0.85, "light", None, "Ellyrian Reavers: WS4 S3 T3 I5, the best light horse in the world."),
    (r"glade_riders", 0.7, "light", None, "Glade Riders: WS4 S3 T3, archers first."),
    (r"horse_archers|horse_raiders", 0.65, "light", None, "Kislev's Ungol-descended horse archers and raiders."),
    (r"pistoliers|outriders", 0.75, "light", None, "Young nobles and veteran gunners: WS3-4, pistols first."),
    (r"nehekhara_horsemen", 0.85, "light", None, "Nehekharan horsemen: skeletal, a cut above the rank and file."),
    (r"hellstriders", 0.9, "light", None, "Slaanesh's mortal riders: fast, cruel, lightly armoured."),
    (r"seekers_of_slaanesh", 1.3, "light", None, "Daemonettes on steeds of Slaanesh: WS5 but fragile, the fastest things alive."),
    (r"heartseekers|pleasureseekers", 2.6, "daemonic", None, "Exalted daemonettes: deadly but still thin-skinned."),
    # --- line knights
    (r"knights_errant", 0.95, "line", None, "Knights Errant: WS3 S3, young, reckless, proving themselves."),
    (r"knights_of_the_realm", 1.3, "line", None, "Knights of the Realm: WS4 S3 T3, the Lady's blessing, the lance wedge."),
    (r"empire_knights\b|emp_cav_empire_knights$", 1.0, "line", None, "Empire Knights: WS4 S3 T3, the order's rank and file."),
    (r"silver_helms", 1.25, "line", None, "Silver Helms: WS4 S3 T3 I5, young nobles in ithilmar."),
    (r"black_knights", 1.35, "line", None, "Black Knights: WS3 S4 T4 wights on skeletal steeds, ethereal-adjacent dread."),
    (r"orc_boar_boyz", 1.1, "line", None, "Orc Boar Boyz: WS3 S3 T4 on thick-skinned boars."),
    (r"jade_lancers", 1.2, "line", None, "Cathay's Jade Lancers: disciplined, well-armoured."),
    (r"cold_ones_1|cold_ones_feral", 1.8, "line", None, "Saurus on cold ones: scaly skin, stupid mounts."),
    # --- elite mortals
    (r"reiksguard", 1.9, "elite", None, "Reiksguard: the most powerful order of the Empire, finest arms and armour."),
    (r"knights_blazing_sun|empire_knights_ror", 1.7, "elite", None, "A great knightly order: veterans in the finest plate."),
    (r"black_rose", 1.9, "elite", None, "Knights of the Black Rose: grim, fearless, heavily armoured."),
    (r"questing_knights", 2.1, "elite", None, "Questing Knights: WS4 S3 great weapons, sworn to find the Grail."),
    (r"orc_boar_boy_big_uns|broken_tusks", 1.6, "elite", None, "Boar Boy Big 'Uns: WS4 S4 T4, the biggest orcs get the best boars."),
    (r"savage_orc_boar", 1.3, "elite", None, "Savage Orc boar boyz: frenzy, war paint, no armour."),
    (r"dragon_princes|fireborn", 2.7, "elite", None, "Dragon Princes of Caledor: WS5 S3 I6 Ld9, dragon armour, the proudest knights of Ulthuan."),
    (r"cold_one_knights|ebon_claw", 3.0, "elite", None, "Cold One Knights: WS5 S4 riders on T4 cold ones, fear."),
    (r"cold_one_spear", 2.0, "elite", None, "Saurus Cold One Riders with spears."),
    (r"wild_riders", 2.0, "elite", None, "Wild Riders of Kurnous: WS5 S4 I5, frenzy and hatred."),
    (r"gryphon_legion", 2.0, "elite", None, "Kislev's Gryphon Legion: the Tzarina's elite winged heavy horse."),
    (r"winged_lancers", 1.4, "elite", None, "Kislev's winged lancers: shock cavalry of the oblast."),
    (r"doomfire_warlocks", 1.1, "elite", None, "Doomfire Warlocks: sorcerers in the saddle, not fighters."),
    (r"slaanesh_harvesters|knights_of_the_ebon", 2.6, "elite", None, "Dark Elf regiment of renown."),
    (r"outriders_morr", 0.9, "light", None, "Morr's outriders."),
    (r"hexwraiths", 2.6, "elite", None, "Hexwraiths: ethereal wraiths whose scythes pass through armour and flesh alike."),
    (r"chillgheists|vereks_reavers", 2.4, "elite", None, "Vampire Counts regiment of renown."),
    (r"centigors", 1.2, "elite", None, "Centigors: WS4 S4 T4 half-beast raiders, drunk and savage."),
    (r"jade_longma", 4.5, "monstrous", None, "Longma: celestial horse-dragons of Cathay, magical and strong."),
    (r"things_in_the_woods", 2.8, "monstrous", None, "Kislev's forest spirits of the oblast."),
    # --- champions and the blessed: the crazy tier
    (r"grail_knights", 5.5, "champion", 32, "Grail Knights have drunk from the Grail and are more than mortal: WS5 S4 I5 A2 with the Lady's full blessing. A handful routs whole regiments."),
    (r"grail_guardians", 7.5, "champion", 24, "Grail Guardians: Grail Knights sworn to guard a Grail Chapel, the Lady's own wardens."),
    (r"chaos_knights", 3.5, "champion", None, "Chaos Knights: WS5 S5 T4 A2 in Chaos armour on daemonic steeds, the most favoured warriors of the gods."),
    (r"pro04_chs_cav_chaos_knights_ror", 18.0, "champion", 16, "The Swords of Chaos: Archaon's own retinue, the Everchosen's knights. Very few ride with him, each a champion who has survived the gods' favour for lifetimes; their Apocalyptic Charge breaks armies."),
    (r"doom_knights", 4.5, "champion", None, "Tzeentch's Doom Knights on discs and steeds of change."),
    (r"blood_knights", 8.5, "champion", 24, "Blood Knights of the Blood Dragon order: every rider is a vampire, WS5 S5 T5 W2 A2 in plate. One is worth a regiment of mortal knights."),
    (r"royal_pegasus|pegasus_knights", 3.0, "monstrous", None, "Pegasus Knights: knights on winged horses, W3 T4 mounts."),
    (r"royal_hippogryph", 11.0, "monstrous", None, "Royal Hippogryph Knights: knights on hippogryphs, monsters in their own right."),
    (r"hawk_riders", 2.0, "monstrous", None, "Wood elf hawk riders: fliers, not a battle line."),
    (r"griffon_knights", 26.0, "monstrous", None, "Mistwalker griffon knights: elves on griffons."),
    # --- monstrous cavalry
    (r"demigryph", 3.8, "monstrous", None, "Demigryph Knights: order knights on W3 T4 half-griffon beasts."),
    (r"royal_altdorf_gryphites", 5.0, "monstrous", None, "The Royal Altdorf Gryphites: Altdorf's household demigryph elite."),
    (r"great_stag_knights", 3.6, "monstrous", None, "Great Stag Knights: wild riders on the great stags of Athel Loren."),
    (r"necropolis_knights", 5.0, "monstrous", None, "Necropolis Knights on necroserpents: T5 W3 constructs that crush chariots."),
    (r"horned_ones", 3.2, "monstrous", None, "Saurus on horned ones: faster, fiercer than cold ones."),
    (r"ripperdactyl", 5.5, "monstrous", None, "Skinks on ripperdactyls: frenzied fliers."),
    (r"skullcrushers", 7.5, "monstrous", None, "Skullcrushers: WS5 S5 Chaos Knights of Khorne on T5 W3 juggernauts of brass."),
    (r"bloodcrushers", 6.5, "monstrous", None, "Bloodcrushers: bloodletters on juggernauts, daemonic ward."),
    (r"rot_knights", 6.0, "monstrous", None, "Rot Knights: Nurgle's chosen on rot flies, bloated and near unkillable."),
    (r"pox_riders", 3.8, "monstrous", None, "Pox Riders of Nurgle: plaguebearers on giant toads."),
    (r"plague_drones", 7.5, "monstrous", None, "Plague Drones: plaguebearers on rot flies, W3 T5 daemons."),
    (r"war_bear_riders", 8.0, "monstrous", None, "War Bear Riders: Kislevite warriors on great bears."),
    (r"mournfang", 9.0, "monstrous", None, "Mournfang Cavalry: ogres (W3 T4) on mournfang (W4 T5), a wall of fur and iron."),
    (r"ogr_cav_crushers", 13.0, "monstrous", None, "Crushers: ogres on rhinox-sized beasts, the heaviest cavalry of the Mountains of Mourn."),
    (r"bull_centaurs", 7.5, "monstrous", None, "Bull Centaurs: WS4 S4 T5 W3 A2 Ld9, Hashut's taurus-blooded sons."),
    (r"razorgor", 3.0, "monstrous", None, "Razorgors: great tusked beasts of the Beastmen herds."),
]


# ---- hypothetical units: in the lore, not in the game. Built on a vanilla unit, with changes, solved to a target.
# target is on THIS model's scale (no exponent). price scales from the template's price by total power.
HYPOTHETICAL = [
    dict(label="Chosen Chaos Knights", faction="chs", template="wh_main_chs_cav_chaos_knights_0", men=32, target=4.2, keep=True,
         changes=dict(ma_add=6, md_add=6, morale=85, attrs=["causes_fear", "immune_to_psychology"]),
         note="The Chosen of the Chaos Knights: warriors the gods have marked for greatness, each a would-be champion. "
              "Fewer than Chaos Knights, far more dangerous."),
    dict(label="Chosen Knights of Khorne", faction="chs", template="wh_main_chs_cav_chaos_knights_0", men=32, target=4.4, keep=True,
         changes=dict(ma_add=12, md_add=0, bvi=12, res_magic=35, morale=85, attrs=["causes_fear", "frenzy", "mark_khorne"]),
         note="Khorne's chosen riders: the Blood God's favour is killing, so the gift goes into the blade (bonus vs infantry, frenzy)."),
    dict(label="Chosen Knights of Nurgle", faction="chs", template="wh_main_chs_cav_chaos_knights_0", men=32, target=4.4, keep=True,
         changes=dict(ma_add=2, md_add=8, res_physical=15, res_flame=-20, morale=85, attrs=["causes_fear", "mark_nurgle"]),
         note="Nurgle's chosen: bloated, rotting, and very hard to kill (physical resistance)."),
    dict(label="Chosen Knights of Slaanesh", faction="chs", template="wh_main_chs_cav_chaos_knights_0", men=32, target=4.2, keep=True,
         changes=dict(ma_add=4, md_add=12, speed_bonus=1.0, morale=85, attrs=["causes_fear", "immune_to_psychology", "devastating_flanker", "mark_slaanesh"]),
         note="Slaanesh's chosen: impossibly fast and graceful, first into the fight (defence, speed)."),
    dict(label="Chosen Knights of Tzeentch", faction="chs", template="wh_main_chs_cav_chaos_knights_0", men=32, target=4.2, keep=True,
         changes=dict(ma_add=4, md_add=4, ward=15, magical=True, morale=85, attrs=["causes_fear", "mark_tzeentch"]),
         note="Tzeentch's chosen: warded by sorcery, their blades wreathed in change (ward save, magical attacks)."),
    dict(label="Knights Panther", faction="emp", template="wh_main_emp_cav_reiksguard", men=60, target=1.75,
         changes=dict(), note="A great secular order born in the crusades against Araby, famed across the Empire."),
    dict(label="White Wolves", faction="emp", template="wh_main_emp_cav_empire_knights", men=60, target=1.8,
         changes=dict(base=14, ap=30, bvi=8, armour=100, attrs=["frenzy"]),
         note="Templars of Ulric from Middenheim: bareheaded, wolf pelts, cavalry hammers instead of lances (armour-piercing, anti-infantry)."),
]


def faction(key):
    m = re.search(r"_(emp|brt|cst|vmp|tmb|chs|nor|kho|nur|sla|tze|hef|def|wef|lzd|grn|ogr|ksl|cth|chd|bst)_", key)
    return m.group(1) if m else "?"


def lore(key):
    hits = [e for e in LORE if re.search(e[0], key)]
    if not hits:
        return None
    pat, target, tier, size, note = max(hits, key=lambda e: len(e[0]))
    target = target ** TARGET_EXPONENT
    if "ror" in key and "ror" not in pat:
        return target * RENOWN, tier + " (renown)", size, note
    return target, tier, size, note


EK = None


def power(c):
    return M.profile(c)["power"] / EK


def solve(c, target, keep_attack_defence=False):
    """attack and defence first (up to +15 / -10), then HP and all damage together"""
    v = dict(c)
    for _ in range(600):
        p = power(v)
        if abs(p - target) / target < 0.01:
            break
        up = p < target
        s = 1 if up else -1
        if keep_attack_defence:
            pass
        elif (up and v["ma"] < c["ma"] + 15 and v["ma"] < 75) or (not up and v["ma"] > c["ma"] - 10 and v["ma"] > 10):
            v["ma"] += s; v["md"] += s
            if abs(power(v) - target) / target < 0.01:
                break
        k = 1.03 if up else 0.97
        v["hp"] *= k
        for d in ("base", "ap", "bvl", "bvi"):
            v[d] *= k
    return v


QUALITY = 1.25   # price grows a little faster than power per model: few great models win fights outright and lose fewer men


def price(cost, men0, p0, men1, p1):
    if not cost:
        return "n/a"
    return int(round(cost * (men1 * p1 ** QUALITY) / (men0 * p0 ** QUALITY) / 25.0) * 25)


def res_text(c):
    parts = []
    for name, field in (("ward", "ward"), ("phys", "res_physical"), ("magic", "res_magic"), ("missile", "res_missile"), ("flame", "res_flame")):
        if c[field]:
            parts.append("%s %+.0f" % (name, c[field]))
    return " ".join(parts) or "-"


def weapon_text(c):
    t = "%.0f+%.0f" % (c["base"], c["ap"])
    if c["bvl"]:
        t += " vL+%.0f" % c["bvl"]
    if c["bvi"]:
        t += " vI+%.0f" % c["bvi"]
    if c["splash_size"] and c["splash_mult"] and c["splash_n"] > 1:
        t += " splash %s×%.1f" % (c["splash_size"], c["splash_mult"])
    if c["magical"]:
        t += " mag"
    if c["flaming"]:
        t += " fire"
    return t


def profile_row(c, prof, value):
    o, t = prof["offence"], prof["toughness"]
    rng = "-"
    if c.get("missile"):
        m = c["missile"]
        rng = "%.1f / %.1f · %.0fm · %.0f" % (prof["ranged"]["light infantry"], prof["ranged"]["cavalry"], m["range"], m["ammo"])
    extra = ", ".join(a for a in c["attrs"] if a not in ("hide_forest",))
    return "| %s | %d | %s | %s | %.0f | %.0f | %.0f | %.0f | %.0f | %s | %s | %.0f | %.1f | %.0f | %.1f / %.1f / %.1f / %.1f / %.1f | %.0f / %.0f / %.0f | %s | **%.2f** | %s | %s |\n" % (
        c["label"], c["men"], c["cost"] or "n/a", c["upkeep"] or "-", c["ma"], c["md"], c["cb"], c["hp"], c["armour"], res_text(c),
        weapon_text(c), c["mass"], c["speed"], c["morale"],
        o["cavalry"], o["anti-large infantry"], o["heavy infantry"], o["light infantry"], o["monster"],
        t["cavalry"], t["anti-large infantry"], t["heavy infantry"], rng, power(c), value, extra)


PROFILE_HEAD = ("| unit | men | cost | upkeep | MA | MD | CB | HP/model | armour | ward & resist % | weapon | mass | speed | Ld | "
                "dps vs cav / halb / chaos warr / spear / giant | survives vs cav / halb / chaos warr (s) | ranged dps vs inf / cav · range · ammo | "
                "power | value | attributes |\n" + "|---" * 22 + "|\n")
PROPOSAL_HEAD = ("| unit | power now | lore target | men | MA | MD | CB | HP/model | weapon | cost | lore |\n" + "|---" * 11 + "|\n")


def main():
    global EK
    EK = M.profile(M.card("wh_main_emp_cav_empire_knights"))["power"]
    MUx = M.MU
    keys = []
    for k, m in sorted(MUx.items()):
        if m["caste"] not in ("melee_cavalry", "missile_cavalry", "monstrous_cavalry"):
            continue
        if re.search(r"_(qb|dm|mp|summoned|tutorial|boss)|_blessed$|_nakai$|_dechala$|_waaagh_|_pro_|^wh3_main_pro|chieftain|imperial_supply", k):
            continue
        keys.append(k)

    names = {}
    for r in M.V.table("land_units") if False else []:
        pass
    loc = {}
    import glob
    for path in glob.glob(os.path.join(os.path.dirname(M.V.DUMP), "text", "**", "*.tsv"), recursive=True):
        try:
            for line in open(path, encoding="utf-8", errors="replace"):
                if line.startswith("land_units_onscreen_name_"):
                    a = line.rstrip("\n").split("\t")
                    loc[a[0][len("land_units_onscreen_name_"):]] = a[1]
        except OSError:
            pass

    by_faction = {}
    for k in keys:
        c = M.card(k)
        c["label"] = "%s `%s`" % (loc.get(M.MU[k]["land_unit"], k), k)
        by_faction.setdefault(faction(k), []).append(c)

    with open(OUT, "w") as out:
        w = out.write
        w("# Cavalry rebalance: the data\n\n"
          "Generated by `tools/cavalry_rebalance.py` (model: `cavalry_model.py`) from the vanilla database. "
          "Read `CAVALRY_REBALANCE.md` first.\n\n"
          "**Reference opponents** (real vanilla units): cav = Empire Knights, halb = Empire Halberdiers (anti-large), "
          "chaos warr = Chaos Warriors (heavy infantry), spear = Empire Spearmen, giant = Giant (monster). "
          "**dps** is per model, sustained with a charge every 30 s. **survives** is how long one model lasts against one "
          "opposing model. **power** is per model, Empire Knights = 1.00. **value** is men × power per 1000 gold.\n\n"
          "Weapon: base+AP, vL/vI = bonus vs large/infantry, splash = size it splashes up to × power multiplier, "
          "mag = magical, fire = flaming. Ward & resist: ward applies to everything, phys to non-magical attacks.\n\n")
        order = sorted(by_faction, key=lambda f_: FACTIONS.get(f_, f_))
        for fac in order:
            cards = sorted(by_faction[fac], key=lambda c: -M.profile(c)["power"])
            w("## %s\n\n### Profiles\n\n" % FACTIONS.get(fac, fac) + PROFILE_HEAD)
            for c in cards:
                p = power(c)
                value = "%.1f" % (c["men"] * p / (c["cost"] / 1000.0)) if c["cost"] else "n/a"
                w(profile_row(c, M.profile(c), value))
            w("\n### Lore proposal\n\n" + PROPOSAL_HEAD)
            for c in cards:
                L = lore(c["key"])
                p = power(c)
                if not L:
                    w("| %s | %.2f | not rated | | | | | | | | |\n" % (c["label"], p)); continue
                target, tier, size, note = L
                if c["caste"] == "missile_cavalry" or c.get("missile"):
                    w("| %s | %.2f | %s %.2f | ranged: not solved | | | | | | | %s |\n" % (c["label"], p, tier, target, note)); continue
                v = solve(c, target)
                if size:
                    v["men"] = size
                p1 = power(v)
                w("| %s | %.2f | **%s %.2f** | %d | %.0f | %.0f | %.0f | %.0f | %s | %s | %s |\n" % (
                    c["label"], p, tier, target, v["men"], v["ma"], v["md"], v["cb"], v["hp"], weapon_text(v),
                    price(c["cost"], c["men"], p, v["men"], p1), note))
            hyps = [h for h in HYPOTHETICAL if h["faction"] == fac]
            if hyps:
                w("\n### Hypothetical units (in the lore, not in the game)\n\n" + PROPOSAL_HEAD.replace("power now", "template"))
                for h in hyps:
                    base = M.card(h["template"])
                    pb = power(base)
                    c = dict(base)
                    ch = dict(h["changes"])
                    attrs = ch.pop("attrs", None)
                    speed_bonus = ch.pop("speed_bonus", 0.0)
                    for field in ("ma", "md", "hp", "cb"):
                        if field + "_add" in ch:
                            c[field] += ch.pop(field + "_add")
                    c.update(ch)
                    c["speed"] += speed_bonus
                    if attrs:
                        c["attrs"] = attrs
                    c["men"] = h["men"]
                    v = solve(c, h["target"], keep_attack_defence=h.get("keep", False))
                    p1 = power(v)
                    w("| **%s** | %s | **%.2f** | %d | %.0f | %.0f | %.0f | %.0f | %s | %s | %s |\n" % (
                        h["label"], loc.get(M.MU[h["template"]]["land_unit"], h["template"]), h["target"], v["men"], v["ma"],
                        v["md"], v["cb"], v["hp"], weapon_text(v), price(base["cost"], base["men"], pb, v["men"], p1), h["note"]))
            w("\n")
    print("wrote", OUT, "units:", sum(len(v) for v in by_faction.values()), "hypothetical:", len(HYPOTHETICAL))


if __name__ == "__main__":
    main()
