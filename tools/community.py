#!/usr/bin/env python3
"""The community's own balance list, as the community wrote it.

Source: "Community sourced, peer-reviewed balance recommendations list (patch 7.1+)", Total Tavern and Vermin League
discords, posted 2 March 2026 on the CA forums:
https://community.creative-assembly.com/total-war/total-war-warhammer/forums/15-total-war-warhammer/threads/13577
CA's 7.2, 8.0 and 9.0 made no numbered balance changes; 8.1 (9 July 2026) adopted about 60 of these recommendations
(most of Norsca, Nurgle, Slaanesh and Tzeentch). Those are left out here, see docs/COMMUNITY_LIST.md.

Every entry is the list's own numbers, no model in between. `line` is the recommendation's line in our text copy of the
thread (docs/COMMUNITY_LIST.md cites them). This first pass covers recruitable units and crewed artillery only: stat,
price, ammo, accuracy, range and entity changes that live in data tables. Lords, heroes, spells, abilities, contact
effects, unit caps and animation fixes are listed in docs/COMMUNITY_LIST.md as not done yet.

    python3 community.py            -> which units every entry resolves to, and the entries that resolve to nothing

Change keys (all deltas unless marked "set"):
  ma md cb ld          melee attack, melee defence, charge bonus, leadership
  hp                   per entity; hp_total is the unit card's total at ultra size, spread over the models
  ws_base ws_ap        melee weapon damage and AP damage (per hit, as the card shows)
  bvi bvl              melee bonus vs infantry / large
  armour               armour value (moves to the armour type of the same material at the new value)
  cost                 multiplayer gold; campaign cost and upkeep move by the same ratio
  mass speed accel decel turn radii_ratio   the man entity (cloned per unit); speed is the card's (run speed x10)
  mount_speed mount_accel mount_turn        the mount entity, changed in place (every rider of that mount)
  accuracy ammo        land unit accuracy and primary ammunition
  missile_base missile_ap range reload calibration   the primary projectile (reload in seconds)
  missile_res          missile resistance in percent points
  spacing rank_depth men ammo_set   set values
"""
import re

# --- crewed artillery: engine entities, set values, changed in place (every piece using that engine) ---------------
ARTILLERY = [
    (378, "Great Cannons, Helblaster Volley Guns, Mortars, Helstorm Rocket Battery",
     ["wh_main_emp_art_great_cannon", "wh_main_emp_art_helblaster", "wh_main_emp_art_mortar", "wh_main_emp_art_helstorm"],
     dict(walk_speed=2.2, turn_speed=60, fire_arc_close=60)),
    (380, "Trebuchet & Blessed Field Trebuchet", ["wh_main_brt_art_trebuchet"], dict(walk_speed=2.2, turn_speed=60, fire_arc_close=60)),
    (381, "Goblin Bolt Throwa & Hobgoblin Bolt Thrower", ["wh3_dlc26_grn_art_goblin_bolt_throwa"], dict(walk_speed=2.4, turn_speed=60, fire_arc_close=60)),
    (382, "Reaper Bolt Throwers & Eagle Claw Bolt Throwers", ["wh2_main_def_art_reaper_bolt_thrower", "wh2_main_hef_art_eagle_claw_bolt_thrower"],
     dict(walk_speed=2.4, turn_speed=70, fire_arc_close=60)),
    (383, "Bolt Throwers (Dwarfs)", ["wh_dlc06_dwf_art_boltthrower"], dict(walk_speed=2.4, turn_speed=70, fire_arc_close=70)),
    (384, "Grudge Throwers, Cannons, Organ Guns", ["wh_main_dwf_art_grudge_thrower", "wh_main_dwf_art_cannon", "wh_main_dwf_art_organ_gun"],
     dict(walk_speed=2.2, turn_speed=60, fire_arc_close=60)),
    (385, "Flame Cannon", ["wh_main_dwf_art_flame_cannon"], dict(walk_speed=2.6, turn_speed=70, fire_arc_close=70)),
    (386, "Goblin Hewers", ["wh3_dlc25_dwf_art_goblin_hewer"], dict(turn_speed=70, fire_arc_close=70)),
    (387, "Grand Cannons & Fire Rain Rocket Battery", ["wh3_main_cth_art_grand_cannon", "wh3_main_cth_art_fire_rain_rocket_battery"],
     dict(run_speed=3.2, turn_speed=70)),
    (388, "Goblin Rock Lobbers & Doom Diver Catapults", ["wh_main_grn_art_goblin_rock_lobber", "wh_main_grn_art_doomdiver"],
     dict(walk_speed=2.2, turn_speed=60, fire_arc_close=60)),
    (389, "Plague Claw Catapult & Warp Lightning Cannon", ["wh2_main_skv_art_plagueclaw_catapult", "wh3_dlc29_skv_art_plagueclaw_catapult_ror",
                                                           "wh2_main_skv_art_warp_lightning_cannon"],
     dict(walk_speed=2.2, turn_speed=60, fire_arc_close=60)),
    (390, "Screaming Skull Catapult", ["wh2_dlc09_tmb_art_screaming_skull_catapult"], dict(walk_speed=2.2, turn_speed=60, fire_arc_close=60)),
    (391, "Carronades, Mortars (Vampire Coast)", ["wh2_dlc11_cst_art_carronade", "wh2_dlc11_cst_art_mortar"], dict(walk_speed=2.2, turn_speed=60, fire_arc_close=60)),
    (392, "Queen Bess", ["wh2_dlc11_cst_art_queen_bess"], dict(walk_speed=2.2, turn_speed=45, fire_arc_close=50)),
]

MARK = r"( of (Khorne|Nurgle|Slaanesh|Tzeentch))?"

# --- units: (line, name regex over the unit's in-game name, changes) ---------------------------------------------------
UNITS = [
    # Warriors of Chaos and the marks
    (395, r"Chaos Warriors%s" % MARK, dict(cb=2, ma=2)),
    (396, r"Chaos Warriors%s \(Great Weapons\)" % MARK, dict(ws_ap=2, ma=2)),
    (397, r"Chaos Warriors%s \(Halberds\)" % MARK, dict(ws_ap=2, md=2)),
    (398, r"Chaos Warriors of Khorne \(Dual Weapons\)", dict(ma=2, bvi=3)),
    (399, r"Chaos Warriors of Slaanesh \(Hellscourges\)", dict(cb=2, ma=2)),
    (401, r"Chosen%s" % MARK, dict(cb=2, ws_ap=2, mass=60)),
    (402, r"Chosen%s \(Great Weapons\)" % MARK, dict(cb=4, ws_base=1, ws_ap=3, mass=60)),
    (403, r"Chosen%s \(Halberds\)" % MARK, dict(md=2, ws_ap=2, mass=10)),
    (404, r"Chosen of Khorne \(Dual Weapons\)", dict(ws_ap=2, bvi=2, mass=60)),
    (405, r"Chosen of Slaanesh \(Hellscourges\)", dict(cb=2, ws_base=1, ws_ap=1, mass=60)),
    (407, r"Marauders of Khorne \(Dual Weapons\)", dict(spacing="wh3_main_infantry_chaotic_bloodletters", cost=-25)),
    (408, r"Marauders of Tzeentch \(Spears\)", dict(cost=-25)),
    (409, r"Chaos Knights%s" % MARK, dict(ma=2)),
    (413, r"Great Eagle", dict(ld=5, hp=217, ws_base=6, ws_ap=14)),
    (414, r"Fell Bats", dict(ma=1, cb=2, hp=3)),
    (415, r"(Chaos|Norscan) Warhounds( \(Poison\))?", dict(cost=-25)),
    (418, r"Harpies", dict(ma=2, cb=2)),
    # Beastmen: the Centigor hitbox and the price rollback that goes with it
    (464, r"Centigors", dict(cost=-75)),
    (465, r"Centigors \(Great Weapons\)", dict(cost=-150)),
    (466, r"Centigors of Tzeentch", dict(cost=-150)),
    (467, r"Sons of Ghorros.*", dict(cost=-100)),
    (468, r"Centigors \(Throwing Axes\)|Groghooves of Wolf.s Run.*", dict(cost=-25)),
    (470, r"Gor Herd", dict(ws_base=-1, ws_ap=-1)),
    (471, r"Pestigors", dict(cb=2)),
    (472, r"Tzaangors", dict(md=2)),
    (480, r"Groghooves of Wolf.s Run.*", dict(accuracy=27)),
    # Bretonnia
    (493, r"Wardens of Montfort.*", dict(cb=11, accuracy=4)),
    # Chaos Dwarfs
    (499, r"Lammasu", dict(hp=320)),
    (500, r"Infernal Guard \(Great Weapons\)", dict(ma=4, cb=2, ws_ap=2)),
    (501, r"Infernal Guard", dict(ma=2, rank_depth=5)),
    (502, r"Chaos Dwarf Warriors \(Great Weapons\)", dict(ma=2)),
    # Dark Elves
    (571, r"Black Guard of Naggarond", dict(mass=30, ws_base=1, ws_ap=3, ma=4, armour=10)),
    (579, r"Shades \(Greatswords\)", dict(cost=-50)),
    # Dwarfs
    (587, r"Slayer Pirates", dict(ammo=2, ws_base=2, ws_ap=2)),
    (588, r"Hammerers", dict(mass=80)),
    (590, r"Thunderers \(Grudge-Rakers\)", dict(cost=-25, shockwave=1.0)),
    (592, r"Longbeards \(Great Weapons\)", dict(ma=2, ws_ap=2)),
    (593, r"Dwarf Warriors \(Great Weapons\)", dict(ma=2)),
    (594, r"Thunderers", dict(cost=-25)),
    # Grand Cathay
    (607, r"(Jade|Jet) Lion", dict(ma=5)),
    (611, r"Bandits of the Silver Road.*", dict(accuracy=27, cost=-25)),
    # Greenskins
    (619, r"Nasty Skulkers", dict(ma=6, ws_base=1, ws_ap=3)),
    (620, r"Night Goblins", dict(ma=2, ws_base=1, cost=-25)),
    (621, r"Da Warlord.s Boyz.*", dict(ws_ap=1, cost=-25)),
    (622, r"Black Orcs \(Great Weapons\)", dict(ma=2, ws_ap=2, mass=40)),
    (623, r"Black Orcs", dict(ma=2, mass=40)),
    (624, r"Krimson Killerz.*", dict(ma=2, bvi=2)),
    (625, r"Arachnarok Spider( \(Flinger\))?", dict(cost=-50, missile_res=15)),
    (626, r"Forest Goblin Spider Riders", dict(ws_base=1, ws_ap=1, cb=3)),
    (627, r"Forest Goblin Spider Rider Archers", dict(range=15, missile_base=1, missile_ap=1, hp_total=360)),
    (630, r"Ruglud.s Armoured Orcs.*", dict(cost=50, accuracy=4)),
    (635, r"Mangler Squigs", dict(ws_base=4, ws_ap=10)),
    (636, r"Goblin Wolf Riders", dict(cb=3)),
    (637, r"Goblin Wolf Rider Archers", dict(missile_base=2)),
    (638, r"Snotling Pump Wagon \(Spiky Roller\)|Snotling Pump Wagons? \(Spiky Rollers?\)", dict(cost=-75)),
    (639, r"Spider Hatchlings", dict(cb=3)),
    # High Elves
    (643, r"Phoenix Guard", dict(mass=30, ws_base=1, ws_ap=3)),
    (644, r"Lothern Sea Guard", dict(calibration_set=4.4)),
    (645, r"White Lions of Chrace", dict(cb=4, ws_ap=2)),
    (646, r"Spearmen", dict(ma=2, _faction="hef")),
    (647, r"Silver Helms( \(Shields\))?", dict(cb=6, ld=3)),
    (648, r"Blades of Hoeth.*", dict(men=60, hp_set=140, cb=10, ws_base_set=18, ws_ap_set=42, rank_depth=3)),
    (649, r"Lothern Skycutters \(Bolt Throwers\)", dict(ammo=4)),
    (654, r"Sisters of Avelorn", dict(missile_ap=2)),
    # Khorne
    (661, r"Wrathmongers", dict(md=-4, ld=-5)),
    (663, r"Skullcrushers of Khorne", dict(ld=5, armour=10)),
    (664, r"Bloodcrushers of Khorne", dict(armour=10, md=4)),
    (666, r"Slaughterbrute", dict(hp=1000, ws_swap=40, accel=5, decel=6)),
    (667, r"Bloodthirster", dict(hp=500, ws_swap=40)),
    (670, r"Flesh Hounds of Khorne", dict(mass=400, ma=2)),
    # Kislev
    (693, r"War Bear Riders", dict(mount_turn=120, bvl=2, ld=5)),
    (699, r"Streltsi|Kossars|Kossars \(Spears\)", dict(cost=-25)),
    (700, r"Akshina Ambushers", dict(cost=-50)),
    (702, r"Dazh.s Hearth-Blades.*", dict(cost=-50)),
    # Lizardmen
    (717, r"Temple Guard", dict(ma=2, ws_base=1, ws_ap=2, mass=30)),
    (718, r"Saurus Warriors( \(Shields\))?", dict(cb=4)),
    (719, r"Saurus Spears( \(Shields\))?", dict(ws_base=2, ws_ap=1)),
    (730, r"Ancient Stegadon", dict(ammo_set=120)),
    (733, r"Feral Cold Ones", dict(speed=4)),
    # Ogre Kingdoms
    (778, r"Ironblaster", dict(cost=-100)),
    (779, r"Yhetees", dict(speed=8, ma=2)),
    # Skaven
    (788, r"Plague Monk Censer Bearers", dict(ma=3)),
    (789, r"Death Runners", dict(bvi=2)),
    (790, r"Wolf Rats", dict(ws_base=1, ws_ap=2)),
    (797, r"Council Guard.*", dict(cost=-150)),
    (798, r"The Thing-Thing.*", dict(cost=-50)),
    # The Empire
    (833, r"Handgunners", dict(cost=-25, _faction="emp")),
    (834, r"War Wagon \(Mortar\)|War Wagons? \(Mortars?\)", dict(cost=-50)),
    (835, r"Crossbowmen", dict(cost=-25, _faction="emp")),
    (836, r"Helstorm Rocket Battery", dict(cost=-50)),
    (837, r"Steam Tank \(Volley Gun\)", dict(missile_base=9, missile_ap=28)),
    (838, r"Demigryph Knights", dict(cb=10, ma=2)),
    (840, r"The White Wolves.*", dict(hp=12)),
    (841, r"Deathjacks.*", dict(range=20, accuracy=17)),
    # Tomb Kings
    (844, r"Skeleton Horse Archers", dict(cost=25, _faction="tmb")),
    (845, r"Tomb Scorpions?", dict(ma=5)),
    (846, r"Blessed Legion of Phakth.*", dict(cost=-25, armour=10)),
    (847, r"King Nekhesh.s Scorpion Legion.*", dict(md=-4, armour=10, ws_swap=1, cost=-25)),
    (851, r"Tomb Guard", dict(ma=2)),
    (852, r"Carrion", dict(cb=4)),
    # Vampire Coast
    (883, r"Deck Gunners", dict(reload=-1.0)),
    (886, r"Syreens", dict(ma=2, md=2)),
    (887, r"Zombie Pirate Gunnery Mob \(Hand Cannons\)", dict(cost=-25)),
    (889, r"Rotting Prometheans", dict(cost=-100)),
    (894, r"The Tide of Skjold.*", dict(cost=-50)),
    # Vampire Counts
    (898, r"Hexwraiths", dict(mount_speed=6, ma=4, _faction="vmp")),
    (900, r"Black Knights", dict(cost=-100)),
    (902, r"Zombies", dict(cost=25, _faction="vmp")),
    (903, r"Grave Guard \(Halberds\)", dict(cost=-50)),
    (904, r"Grave Guard|Grave Guard \(Great Weapons\)", dict(ma=2)),
    # Warriors of Chaos (monsters)
    (923, r"Dragon Ogres", dict(accel=4, decel=5, ld=3)),
    (924, r"Dragon Ogre Shaggoth", dict(cost=-100, accel=4, decel=5)),
    # Wood Elves
    (933, r"Hawk Riders", dict(cb=5, ld=5)),
    (934, r"Bladesingers", dict(cb=2, ws_ap=2)),
    (935, r"Deepwood Scouts", dict(calibration_set=3.4)),
    (939, r"Treeman", dict(cost=-100)),
    (941, r"Winterheart Guard.*", dict(armour=20)),
    (942, r"Eternal Guard( \(Shields\))?", dict(mass=20)),
    (943, r"Enigmas of Ghyran.*", dict(cost=-50)),
]

# --- other entities changed in place: (line, what, entity keys, set values) ------------------------------------------------
ENTITIES = [
    (460, "Centigor hitbox (radii ratio)", ["wh_dlc03_bst_cav_centigor_blood", "wh2_dlc17_centigor_groghooves_blood"], dict(radii_ratio=0.5)),
    (576, "Cold One Chariots", ["wh2_main_def_cold_one_chariot", "wh2_main_def_cold_one_chariot_articulation"],
     dict(acceleration=6, deceleration=7, turn_speed=80)),
]

# mount entities for the acceleration recommendation (416): Bretonnian warhorses, great stags, stags
MOUNT_ACCEL = (416, "Bretonnian Warhorses, Great Stags, Stags", re.compile(r"^wh_main_brt_mnt_.*warhorse|^wh_dlc05_wef_mnt_(great_)?stag"), 7.0)


# Campaign review (reports/WH3 balance patch research.md, item 5): the list is written by multiplayer players, and CA's 8.1
# drew campaign anger for copying its buffs to units campaign players already find too strong. Where campaign sources
# agree a unit already dominates armies, its buff waits for battle logs.
HELD = {
    625: "Arachnarok Spider: named among the dominant campaign monsters",
    730: "Ancient Stegadon: Stegadons are named among the dominant campaign monsters",
    778: "Ironblaster: the most-cited dominant campaign unit (\"may be the most powerful unit in the game\")",
    836: "Helstorm Rocket Battery: rockets are named among the dominant campaign artillery",
    939: "Treeman: named among the dominant campaign monsters",
}


def resolve(units, name_of, faction_of):
    """entry -> the unit keys it names (full-name match, faction filter where the name is shared); held entries skipped"""
    out = []
    for line, pat, ch in UNITS:
        if line in HELD:
            continue
        rx = re.compile(r"^(%s)$" % pat)
        keys = [k for k in units if rx.match(name_of(k)) and (not ch.get("_faction") or faction_of(k) == ch["_faction"])]
        out.append((line, pat, ch, keys))
    return out


if __name__ == "__main__":
    import unit_model as UM
    rec = UM.recruitable()
    miss = 0
    for line, pat, ch, keys in resolve(rec, UM.name, UM.faction):
        print("%4d %-50s %2d  %s" % (line, pat[:50], len(keys), ", ".join(sorted({UM.name(k) for k in keys}))[:150]))
        miss += not keys
    print("entries with no unit:", miss)


# ------------------------------------------------------------------------------------------------- applying it
ARMOUR_RX = re.compile(r"_(body|bone|chainmail|leather|plate|heavy_metal)_(\d+)$")


def _price(x):
    return int(round(x / 5.0)) * 5


def apply(out, V, coerce, name_of, faction_of, units, skip=()):
    """out: {table: {key: coerced row}} as the builder has them; rows not in it are copied from vanilla on first touch.
    Returns a log of (line, unit or entity, what changed)."""
    LU, MU, MW, MIS, PJ, BE = (V.index("land_units"), V.index("main_units", "unit"), V.index("melee_weapons"),
                               V.index("missile_weapons"), V.index("projectiles"), V.index("battle_entities"))
    MO = V.index("mounts")
    armours = {}
    for r in V.table("unit_armour_types"):
        m = ARMOUR_RX.search(r["key"])
        armours.setdefault((m.group(1) if m else "", int(float(r["armour_value"]))), r["key"])
    armour_value = {r["key"]: int(float(r["armour_value"])) for r in V.table("unit_armour_types")}
    vanilla = dict(land_units=LU, main_units=MU, melee_weapons=MW, missile_weapons=MIS, projectiles=PJ, battle_entities=BE)
    log = []

    def row(table, key):
        t = out.setdefault(table, {})
        if key not in t:
            t[key] = coerce(table, vanilla[table][key])
        return t[key]

    def copy(table, key, new):
        t = out.setdefault(table, {})
        if new not in t:
            r = dict(t.get(key) or coerce(table, vanilla[table][key]))
            r["key"] = new
            t[new] = r
        return t[new]

    for line, what, ents, sets in ARTILLERY + ENTITIES:
        for e in ents:
            r = row("battle_entities", e)
            for col, v in sets.items():
                r[col] = v
            if r["walk_speed"] > r["run_speed"]:
                r["run_speed"] = r["walk_speed"]
            log.append((line, e, sets))
    line, what, rx, accel = MOUNT_ACCEL
    for e in sorted({MO[m]["entity"] for m in MO if rx.search(m) and MO[m]["entity"] in BE}):
        row("battle_entities", e)["acceleration"] = accel
        log.append((line, e, dict(acceleration=accel)))

    done = set()
    for line, pat, ch, keys in resolve(units, name_of, faction_of):
        for key in keys:
            if key in skip:
                log.append((line, key, "skipped: " + skip[key]))
                continue
            mu = row("main_units", key)
            lukey = mu["land_unit"]
            first = (line, lukey) not in done
            done.add((line, lukey))
            lu = row("land_units", lukey)
            men = int(mu["num_men"])
            if "cost" in ch:
                old = mu["multiplayer_cost"]
                mu["multiplayer_cost"] = old + ch["cost"]
                if old:
                    mu["recruitment_cost"] = _price(mu["recruitment_cost"] * mu["multiplayer_cost"] / old)
                    mu["upkeep_cost"] = int(round(mu["upkeep_cost"] * mu["multiplayer_cost"] / old))
            if "men" in ch:
                if lu["num_mounts"] == men:
                    lu["num_mounts"] = ch["men"]
                mu["num_men"] = men = ch["men"]
            log.append((line, key, {k: v for k, v in ch.items() if not k.startswith("_")}))
            if not first:
                continue
            for k, col in (("ma", "melee_attack"), ("md", "melee_defence"), ("cb", "charge_bonus"), ("ld", "morale"),
                           ("accuracy", "accuracy"), ("ammo", "primary_ammo"), ("missile_res", "damage_mod_missile")):
                if k in ch:
                    lu[col] = lu[col] + ch[k]
            for k, col in (("spacing", "spacing"), ("rank_depth", "rank_depth"), ("ammo_set", "primary_ammo")):
                if k in ch:
                    lu[col] = ch[k]
            man = BE[lu["man_entity"]]
            if "hp" in ch or "hp_total" in ch:
                lu["bonus_hit_points"] = max(0, lu["bonus_hit_points"] + ch.get("hp", 0) + int(round(ch.get("hp_total", 0) / max(1, men))))
            if "hp_set" in ch:
                lu["bonus_hit_points"] = ch["hp_set"] - int(float(man["hit_points"]))
            if "armour" in ch:
                a = lu["armour"]
                m = ARMOUR_RX.search(a)
                v = armour_value[a] + ch["armour"]
                lu["armour"] = armours.get((m.group(1) if m else "", v)) or armours.get(("body", v)) or armours[("body", v - v % 5)]
            wkeys = [k for k in ("ws_base", "ws_ap", "bvi", "bvl", "ws_swap", "ws_base_set", "ws_ap_set") if k in ch]
            if wkeys:
                wk = lu["primary_melee_weapon"]
                w = row("melee_weapons", wk) if wk.startswith(("gr_", "cbp_")) else copy("melee_weapons", wk, "cbp_" + lukey)
                lu["primary_melee_weapon"] = w["key"]
                w["damage"] += ch.get("ws_base", 0) - ch.get("ws_swap", 0)
                w["ap_damage"] += ch.get("ws_ap", 0) + ch.get("ws_swap", 0)
                w["bonus_v_infantry"] += ch.get("bvi", 0)
                w["bonus_v_large"] += ch.get("bvl", 0)
                if "ws_base_set" in ch:
                    w["damage"], w["ap_damage"] = ch["ws_base_set"], ch["ws_ap_set"]
            pkeys = [k for k in ("missile_base", "missile_ap", "range", "reload", "calibration_set", "shockwave") if k in ch]
            if pkeys:
                mk = lu["primary_missile_weapon"]
                if mk.startswith(("gr_", "cbp_")):
                    mw = row("missile_weapons", mk)
                else:
                    mw = copy("missile_weapons", mk, "cbp_" + lukey)
                pk = mw["default_projectile"]
                p = row("projectiles", pk) if pk.startswith(("gr_", "cbp_")) else copy("projectiles", pk, "cbp_" + lukey)
                mw["default_projectile"] = p["key"]
                lu["primary_missile_weapon"] = mw["key"]
                p["damage"] += ch.get("missile_base", 0)
                p["ap_damage"] += ch.get("missile_ap", 0)
                p["effective_range"] += ch.get("range", 0)
                p["base_reload_time"] = round(p["base_reload_time"] + ch.get("reload", 0), 2)
                if "calibration_set" in ch:
                    p["calibration_area"] = ch["calibration_set"]
                if "shockwave" in ch:
                    p["shockwave_radius"] = ch["shockwave"]
            ekeys = [k for k in ("mass", "speed", "accel", "decel", "turn") if k in ch]
            if ekeys:
                ek = lu["man_entity"]
                e = row("battle_entities", ek) if ek.startswith("cbp_") else copy("battle_entities", ek, "cbp_%s_man" % lukey)
                lu["man_entity"] = e["key"]
                e["mass"] += ch.get("mass", 0)
                e["run_speed"] = round(e["run_speed"] + ch.get("speed", 0) / 10.0, 2)
                for k, col in (("accel", "acceleration"), ("decel", "deceleration")):
                    if k in ch:
                        e[col] = ch[k]
                if "turn" in ch:
                    e["turn_speed"] = ch["turn"]
            if "mount_speed" in ch or "mount_turn" in ch:
                e = row("battle_entities", MO[lu["mount"]]["entity"])
                e["run_speed"] = round(e["run_speed"] + ch.get("mount_speed", 0) / 10.0, 2)
                if "mount_turn" in ch:
                    e["turn_speed"] = ch["mount_turn"]
    # a row that ended up as vanilla (a price-only unit's land row, say) stays out of the pack: it would only override
    # other mods for nothing
    for table, rows in out.items():
        for key in [k for k, r in rows.items() if k in vanilla.get(table, {}) and r == coerce(table, vanilla[table][k])]:
            del rows[key]
    return log
