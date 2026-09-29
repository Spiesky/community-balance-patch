#!/usr/bin/env python3
"""The lore ladder for everything that is not cavalry: what each unit family should be, per model, on the model's scale.

The cavalry study (cavalry_rebalance.LORE) rated cavalry on its own scale; rebalance_solve carries those targets over
as ratios. This ladder rates infantry, missile infantry and monstrous infantry directly on unit_model's scale:

    per-model power = regiment power / entities x 60, the Empire Knights regiment = 1.00
    (so a 60-model unit of Empire Knight quality reads 1.00 per model; an Empire Swordsman reads about 0.5)

The tiers, with vanilla anchors that already sit where the lore puts them:

    rabble     0.10-0.30   fodder: Zombies 0.15, Skavenslaves 0.14, Peasant Mob 0.17, Skeleton Warriors 0.25, Gnoblars 0.25
    levy       0.30-0.45   spearmen and militia: Empire Spearmen 0.31/0.39, Men-at-Arms 0.4, Night Goblins 0.38, Clanrats 0.28
    line       0.45-0.75   the trained rank and file: Swordsmen 0.49, Halberdiers 0.52, Marauders 0.5, Orc Boyz 0.51, Dreadspears 0.45
    veteran    0.75-1.40   heavy and seasoned: Dwarf Warriors 0.85, Longbeards 1.2, Saurus 1.1, Chaos Warriors 1.1, Bestigors 1.4
    elite      1.40-3.00   orders, guards, the best mortals: Black Orcs 1.75, Hammerers 2.2, Ironbreakers 2.4, Chosen 2.9, Tzar Guard 1.8
    champion   3.00+       few and terrible: Skullreapers 3.3 (60), Depth Guard 2.7 (60), Wrathmongers 7.3 (32), Aspiring Champions 14 (16)
    monstrous  3-15        ogres, trolls, minotaurs, kroxigors: Trolls 6.4, Minotaurs 10-12, Kroxigor 9, Ironguts 9.7 (all 16)

An entry is matched on the unit key. Its target is where the family's base member (the cheapest non-renown one in the
same caste, which is the plain unit) should sit; every variant (great weapons, halberds, marks) keeps its vanilla ratio to that,
so a family moves together and its internal differences survive. Regiments of renown are not rated separately: a regiment of renown moves with its family and keeps its vanilla edge over it. A size means the lore
insists on fewer, better models, as the cavalry study did for Grail Knights.

Four kinds of entry that the cavalry study did not need:
    keep=True        the vanilla unit is the lore, and its price is part of that (chaff is cheap because it is fodder;
                     snipers are dear for what the model cannot see). Nothing moves, whatever the survey says.
    target=None      the stats are the lore; the price is not. Stats stay, the price goes to what the valuation says.
    hold_price=True  the stats move to the target, the price stays at vanilla (the community says it is dear already).
    price_add=-25    the stats are the lore, the price moves by a fixed amount (the community's number, where the
                     model is blind: Kislev's hybrids).
An entry here outranks the cavalry study's table for the same key (docs/COMMUNITY_RESEARCH.md: Centigors).

Tabletop profiles quoted in the notes are from memory of the 6th-8th edition army books and are approximate.
"""
import re
import statistics

def L(pattern, target=None, tier="", size=None, note="", keep=False, reg=False, hold_price=False, price_add=None):
    """reg=True: the target is the regiment's power (the Empire Knights regiment = 1.00), which reads better for
    single entities and small packs than a per-model figure. hold_price=True: the stats move, the price stays at
    vanilla (the community says the unit is already dear). price_add: the stats stay, the price moves by this much."""
    return dict(pattern=pattern, target=target, tier=tier, size=size, note=note, keep=keep, reg=reg, hold_price=hold_price, price_add=price_add)


LADDER = [
    # ------------------------------------------------------------------------------------------------ The Empire
    L(r"emp_inf_swordsmen|emp_inf_sigmars_sons", 0.50, "line", note="State troops with sword and shield: WS3 S3 T3, drilled, not heroic."),
    L(r"emp_inf_halberdiers", 0.55, "line", note="Halberdiers: the same men with a heavier weapon and no shield."),
    L(r"emp_inf_spearmen", 0.38, "levy", note="Spearmen: the cheapest state troop, a wall that holds if nothing pushes."),
    L(r"emp_inf_greatswords", 1.00, "veteran", note="Greatswords: the Empire's elite infantry, veterans in full plate with zweihanders, stubborn. Twice a swordsman, and vanilla has them at 1.7x."),
    L(r"emp_inf_flagellants|emp_inf_tattersouls", keep=True, note="Flagellants: mad, unbreakable, unarmoured. Vanilla has the shape right."),
    L(r"emp_inf_handgunners|emp_inf_silver_bullets|emp_inf_crossbowmen|emp_inf_archers|emp_inf_huntsmen|emp_inf_free_company|emp_inf_stirlands|emp_inf_nuln_ironsides", keep=True, note="Empire missile troops: vanilla sits on the line."),
    L(r"emp_inf_hochland_long_rifles", keep=True, note="Hochland Long Rifles: snipers. The model does not see who they aim at; the price stays."),
    # -------------------------------------------------------------------------------------------------- Bretonnia
    L(r"brt_inf_men_at_arms|brt_inf_spearmen_at_arms|brt_peasant_mob|brt_inf_peasant_bowmen", keep=True, note="Bretonnian peasantry: WS2, fed on turnips. Fodder is priced as fodder."),
    L(r"brt_inf_foot_squires", 0.80, "veteran", note="Foot Squires: the knights' own retainers, trained and armoured; a step above men-at-arms that vanilla barely takes."),
    L(r"brt_inf_battle_pilgrims", 0.70, "line", note="Battle Pilgrims: fanatics who follow a Grail Knight's relics; brave, not skilled."),
    L(r"brt_inf_grail_reliquae", keep=True, note="Grail Reliquae: a relic on a bier, not a fighting unit."),
    # ------------------------------------------------------------------------------------------------------ Dwarfs
    L(r"dwf_inf_dwarf_warrior|dwf_inf_warriors_dragonfire", 0.85, "veteran", note="Dwarf Warriors: WS4 S3 T4, gromril-grade discipline. Every dwarf is a veteran of something."),
    L(r"dwf_inf_longbeards|dwf_inf_old_grumblers", 1.25, "veteran", note="Longbeards: WS5 S4 T4, the eldest and the grumpiest."),
    L(r"dwf_inf_hammerers|dwf_inf_peak_gate_guard", 2.40, "elite", note="Hammerers: the King's guard, WS5 S4 T4, great hammers, stubborn."),
    L(r"dwf_inf_ironbreakers|dwf_inf_norgrimlings_ironbreakers", 2.50, "elite", note="Ironbreakers: gromril from crown to boot, the Underway's wardens; nothing gets past them."),
    L(r"dwf_inf_slayers$|dwf_inf_slayers_grudge|dwf_inf_dragonback", 1.80, "elite", note="Slayers: WS4 S3 T4 unbreakable, seeking a good death; each one has already killed something large."),
    L(r"dwf_inf_giant_slayers", 2.40, "elite", note="Giant Slayers: the ones who have not died yet."),
    L(r"dwf_inf_doomseekers", keep=True, note="Doomseekers: whirling death, few. Vanilla is right."),
    L(r"dwf_inf_miners|dwf_inf_ekrund", keep=True, note="Miners: warriors with picks; vanilla."),
    L(r"dwf_inf_thunderers|dwf_inf_quarrellers|dwf_inf_rangers|dwf_inf_bugmans|dwf_inf_ulthars|dwf_inf_slayer_pirates", keep=True, note="Dwarf missile troops: on the line."),
    L(r"dwf_inf_irondrakes|dwf_inf_norgrimlings_irondrakes", keep=True, note="Irondrakes: drakefire. The model over-counts the flame; the price stays."),
    # -------------------------------------------------------------------------------------------------- Greenskins
    L(r"grn_inf_orc_boyz$|grn_inf_orc_boyz_spear", 0.60, "line", note="Orc Boyz: WS3 S3 T4 A1 with choppas. Tougher than any man, and vanilla rates them like one."),
    L(r"grn_inf_orc_big_uns", 1.00, "veteran", note="Big 'Uns: the biggest orcs get the best kit, WS4 S4 T4."),
    L(r"grn_inf_savage_orcs$", 0.75, "line", note="Savage Orcs: frenzied, warpaint for armour."),
    L(r"grn_inf_savage_orc_big_uns", 1.20, "veteran", note="Savage Orc Big 'Uns: frenzy and size."),
    L(r"grn_inf_black_orcs|grn_inf_krimson", 1.90, "elite", note="Black Orcs: WS4 S4 T4 in heavy armour, the only orcs that drill. Vanilla is close."),
    L(r"grn_inf_goblin|grn_inf_night_goblin|grn_inf_nasty_skulkers|grn_inf_da_warlords|grn_inf_da_eight_peaks|grn_inf_da_rusty", keep=True, note="Goblins: WS2 S3 T3 and lots of them. Vanilla."),
    L(r"grn_inf_orc_arrer|grn_inf_savage_orc_arrer|grn_inf_rugluds", keep=True, note="Orc archers: vanilla."),
    L(r"grn_mon_trolls|grn_mon_river_trolls|grn_mon_stone_trolls", keep=True, note="Trolls: S5 T4 W3 regeneration, stupid. Vanilla has the ladder right."),
    # -------------------------------------------------------------------------------------- Warriors of Chaos and the gods
    L(r"chs_inf_chaos_marauders|nor_inf_chaos_marauders|sla_inf_marauders|nor_inf_marauder_spearman|nor_inf_marauder_bearmen", 0.55, "line", note="Marauders: WS4 S3 T3, northmen who fight from birth; a little above a state trooper."),
    L(r"chs_inf_chaos_warriors|kho_inf_chaos_warriors", 1.45, "elite", note="Chaos Warriors: WS5 S4 T4 A2 in Chaos plate, each one worth three state troops. Vanilla rates them at two."),
    L(r"chs_inf_chosen|kho_inf_chosen", 3.40, "champion", hold_price=True, note="Chosen: the gods' favourites, WS6 S5 T4 A2, on the road to daemonhood. A fifth above vanilla, at the vanilla price: the 7.1 list calls them too expensive already."),
    L(r"chs_inf_forsaken|nur_inf_forsaken|tze_inf_forsaken|sla_inf_forsaken", 1.35, "veteran", note="Forsaken: mutated warriors, all fury and no formation."),
    L(r"chs_inf_aspiring_champions", keep=True, note="Aspiring Champions: sixteen would-be lords. Vanilla."),
    L(r"chs_mon_dragon_ogre$|chs_mon_dragon_ogre_ror", 11.0, "monstrous", note="Dragon Ogres: S5 T5 W4 A3, older than the mountains; the strongest monstrous infantry the north has, rated by vanilla like a troll."),
    L(r"chs_mon_chaos_spawn|kho_mon_spawn|nur_mon_spawn|sla_mon_spawn|tze_mon_spawn|bst_mon_chaos_spawn", keep=True, note="Chaos Spawn: mindless flailing meat. Vanilla."),
    L(r"chs_mon_trolls|nor_mon_chaos_trolls|throgg_mon|nor_mon_norscan_ice_trolls|nur_mon_bile_trolls", keep=True, note="Chaos, Norscan and bile trolls: vanilla."),
    L(r"nor_inf_marauder_champions", keep=True, note="Marauder Champions: vanilla sits right."),
    L(r"nor_inf_marauder_berserkers", 1.20, "veteran", note="Berserkers: frenzied, half-naked, twice the attacks."),
    L(r"nor_inf_marauder_hunters|nor_mon_skinwolves|nor_mon_fimir", keep=True, note="Norscan hunters, skin wolves and fimir: vanilla."),
    L(r"bst_inf_khorngors|kho_inf_khorngors|bst_inf_pestigors|nur_inf_pestigors|bst_inf_slaangors|sla_inf_slaangors|bst_inf_tzaangors|tze_inf_tzaangors", 0.85, "veteran", note="Marked gors: bigger and meaner than the herd."),
    # ---------------------------------------------------------------------------------------------------- daemons
    L(r"kho_inf_bloodletters_0", 1.20, "veteran", note="Bloodletters: WS5 S5 hellblades that kill on a touch, T3 W1. A glass cannon that vanilla rates below a Chaos Warrior."),
    L(r"kho_inf_bloodletters_1|kho_inf_bloodletters_ror", 1.55, "elite", note="Exalted Bloodletters: the same, older and angrier. Only x1.15: campaign players already call them the strongest infantry in the game."),
    L(r"nur_inf_plaguebearers_0", 1.20, "veteran", note="Plaguebearers: T4 and a ward, poisoned plagueswords, slow and patient."),
    L(r"nur_inf_plaguebearers_1|nur_inf_plaguebearers_ror", 2.00, "elite", note="Exalted Plaguebearers."),
    L(r"sla_inf_daemonette_0", 1.05, "veteran", hold_price=True, note="Daemonettes: WS5 A2, claws that ignore armour, fast, thin-skinned. Price held: every list since 6.2 calls them dear for what they do."),
    L(r"sla_inf_daemonette_1|sla_inf_daemonette_ror", 2.10, "elite", note="Exalted Daemonettes."),
    L(r"tze_inf_pink_horrors|tze_inf_blue_horrors", keep=True, note="Horrors: sorcery in a body; the model sees the bolts, not the spells. Vanilla."),
    L(r"tze_mon_flamers_0$", None, "monstrous", note="Flamers: the survey says a bargain at 800; the stats are the lore, the price moves."),
    L(r"tze_mon_flamers_changebringers", None, "monstrous", note="Changebringers: over-priced Flamers with a name; the stats are the lore, the price moves."),
    L(r"tze_mon_screamers|inf_chaos_furies|nur_inf_nurglings|nur_mon_plague_toads|nur_inf_plague_ogres|nur_mon_rot_flies", keep=True, note="Lesser daemons and beasts: vanilla."),
    L(r"sla_mon_fiends_of_slaanesh", 7.50, "monstrous", note="Fiends: daemon-beasts, S4 T4 W3 and four attacks each, faster than horses; vanilla has them as slow trolls."),
    L(r"sla_mon_champions_of_slaanesh|sla_inf_devotees", keep=True, note="Slaanesh's champions and devotees: vanilla."),
    L(r"kho_inf_skullreapers|kho_inf_wrathmongers|kho_mon_khornataurs|kho_mon_bloodbeast", keep=True, note="Khorne's chosen: vanilla sits right."),
    L(r"mon_soul_grinder|kho_mon_slaughterbrute", keep=True, note="Soul Grinders and the Slaughterbrute: daemon engines, one entity each; the monster ladder's business, vanilla until then."),
    # ---------------------------------------------------------------------------------------------------- High Elves
    L(r"hef_inf_spearmen|hef_inf_the_scions", 0.50, "line", note="High Elf Spearmen: WS4 I5, citizen levies who have trained for a century."),
    L(r"hef_inf_archers|hef_inf_lothern_sea_guard|hef_inf_the_storm_riders|hef_inf_shadow_warriors|hef_inf_the_grey|hef_inf_shadow_walkers|hef_inf_mistwalkers_spire|hef_inf_mistwalkers_sentinels|hef_inf_mistwalkers_skyhawks|hef_inf_gate_guard|hef_inf_rangers|hef_inf_ships_company", keep=True, note="High Elf archers, sea guard and rangers: vanilla."),
    L(r"hef_inf_white_lions|hef_inf_the_silverpelts", 1.70, "elite", note="White Lions of Chrace: the Phoenix King's guard, WS5 S4 with great axes and lion cloaks; vanilla has them as heavy line."),
    L(r"hef_inf_swordmasters", 2.80, "elite", size=80, note="Swordmasters of Hoeth: WS6 A2, the finest blades in the world, and few; a scholar's guard, not a regiment."),
    L(r"hef_inf_phoenix_guard|hef_inf_keepers_of_the_flame", 2.60, "elite", size=80, note="Phoenix Guard: the silent wardens of Asuryan's shrine who have seen their own deaths, WS5 halberds and a ward; rare."),
    L(r"hef_inf_sisters_of_avelorn|hef_inf_everqueens", 2.40, "elite", size=60, note="Sisters of Avelorn: the Everqueen's handmaidens with bows of Avelorn; a handful, not a company."),
    L(r"hef_inf_silverin_guard", 0.90, "veteran", note="Silverin Guard: Yvresse's shore wardens."),
    L(r"hef_inf_mistwalkers_faithbearers", 1.10, "veteran", note="Faithbearers."),
    L(r"hef_inf_dryads|hef_mon_treekin|hef_inf_oceanids", keep=True, note="Avelorn's spirits and the sea's: vanilla."),
    # ---------------------------------------------------------------------------------------------------- Dark Elves
    L(r"def_inf_dreadspears|def_inf_the_hellebronai", 0.50, "line", note="Dreadspears: WS4 levies of Naggaroth, drilled by fear."),
    L(r"def_inf_bleakswords", 0.55, "line", note="Bleakswords."),
    L(r"def_inf_black_ark_corsairs_0", 0.85, "veteran", note="Corsairs: sea-dragon cloaks and two blades, raiders of every coast."),
    L(r"def_inf_witch_elves|def_inf_sisters_of_the_singing", 1.00, "veteran", note="Witch Elves: frenzied, poisoned, A2, no armour at all."),
    L(r"def_inf_sisters_of_slaughter", 1.60, "elite", note="Sisters of Slaughter: arena-trained, unhittable."),
    L(r"def_inf_har_ganeth|def_inf_blades_of_the_blood", 2.20, "elite", note="Executioners of Har Ganeth: WS5 with the draich, one blow one head."),
    L(r"def_inf_black_guard", 2.60, "elite", size=80, note="Black Guard of Naggarond: Malekith's tower guard, WS5 A2 halberds, stubborn, eternal hatred; the deadliest infantry of Naggaroth and the rarest. Vanilla prices them as elite and rates them as line."),
    L(r"def_inf_shades|def_inf_darkshards|def_inf_the_bolt_fiends|def_inf_black_ark_corsairs_1|def_inf_harpies", keep=True, note="Dark Elf missile troops and harpies: vanilla."),
    # ---------------------------------------------------------------------------------------------------- Wood Elves
    L(r"wef_inf_eternal_guard", 0.90, "veteran", note="Eternal Guard: the King's Glade's wardens, WS5 with the saearath; vanilla makes them a spear wall of levies."),
    L(r"wef_inf_wildwood_rangers", 1.50, "elite", note="Wildwood Rangers: hunters of the things in the Wildwood, great blades."),
    L(r"wef_inf_wardancers", 1.30, "veteran", note="Wardancers of Loec: WS6 A2, dancing blades, a ward for armour; vanilla rates them as line."),
    L(r"wef_inf_bladesingers", 1.70, "elite", note="Bladesingers: the Wardancers' masters."),
    L(r"wef_inf_dryads_0|wef_inf_dryads_ror", 0.90, "veteran", note="Dryads: S4 T4 spirits with a ward, hating everything with an axe."),
    L(r"wef_inf_malicious_dryads", 1.00, "veteran", note="Malevolent Dryads."),
    L(r"wef_mon_treekin_0|wef_mon_treekin_ror|wef_mon_malicious_treekin", 7.00, "monstrous", note="Tree Kin: S5 T5 W3 walking oaks."),
    L(r"wef_mon_zoats", 8.50, "monstrous", note="Zoats: ancient, T5 W4, and rated by vanilla as expensive trolls."),
    L(r"wef_inf_glade_guard|wef_inf_deepwood_scouts|wef_mon_giant_spiders|wef_mon_harpies", keep=True, note="Glade Guard, scouts, spiders: vanilla."),
    L(r"wef_inf_waywatchers", keep=True, note="Waywatchers: the model does not see whom they pick off; stats and price stay."),
    # ---------------------------------------------------------------------------------------------------- Lizardmen
    L(r"lzd_inf_saurus_warriors|lzd_inf_saurus_warriors_blessed", 1.15, "veteran", note="Saurus Warriors: S4 T4 A2 with scaly skin, spawned to fight; vanilla is close."),
    L(r"lzd_inf_saurus_spearmen", 0.95, "veteran", note="Saurus Spears."),
    L(r"lzd_inf_temple_guards", 2.50, "elite", size=80, note="Temple Guard: the spawned guardians of the Slann, WS4 halberds in heavy scale, stubborn; a bodyguard, not a regiment. Vanilla has a hundred of them at line quality."),
    L(r"lzd_inf_skink_cohort|lzd_inf_skink_skirmishers", keep=True, note="Skinks: fast, small, poisoned, numerous. Vanilla."),
    L(r"lzd_inf_skink_red_crested", 0.70, "line", note="Red Crested Skinks: the fiercest skinks."),
    L(r"lzd_inf_chameleon_skinks", 0.85, "veteran", note="Chameleon Skinks: the best skirmishers in the world, and invisible."),
    L(r"lzd_inf_chameleon_stalkers", keep=True, note="Chameleon Stalkers: already the skinks' elder cousins; vanilla."),
    L(r"lzd_mon_kroxigors|lzd_mon_sacred_kroxigors|lzd_mon_razordon|lzd_mon_salamander", keep=True, note="Kroxigor and hunting packs: vanilla."),
    # ---------------------------------------------------------------------------------------------------- Skaven
    L(r"skv_inf_clanrats|skv_inf_clanrat_spearmen", keep=True, note="Clanrats: WS3 and numberless. Vanilla."),
    L(r"skv_inf_skavenslaves|skv_inf_skavenslave", keep=True, note="Skavenslaves: fodder, and priced as it."),
    L(r"skv_inf_stormvermin", 0.70, "line", note="Stormvermin: black-furred, heavy armour, WS4; the elite of the clanrats, still numerous."),
    L(r"skv_inf_plague_monks$", 0.70, "line", note="Plague Monks: frenzied, diseased, no armour."),
    L(r"skv_inf_plague_monk_censer", 1.10, "veteran", note="Censer Bearers: the same, with a ball of plague on a chain."),
    L(r"skv_inf_death_runners", 1.50, "elite", note="Death Runners: Eshin adepts, weeping blades."),
    L(r"skv_inf_eshin_triads", 1.30, "veteran", note="Eshin Triads."),
    L(r"skv_inf_night_runners|skv_inf_gutter_runner|skv_inf_warplock|skv_art_warplock|skv_inf_ratling|skv_inf_poison_wind_globadiers|skv_inf_death_globe|skv_inf_warp_grinder", keep=True, note="Skaven skirmishers and weapon teams: vanilla."),
    L(r"skv_inf_warpfire_thrower|skv_inf_poison_wind_mortar", keep=True, note="Warpfire and poisoned wind: the model counts every gout and gas cloud at full; the price stays."),
    L(r"skv_mon_rat_ogres", 6.50, "monstrous", note="Rat Ogres: S5 T4 W3 A3 of Moulder's making."),
    # ---------------------------------------------------------------------------------------------------- Tomb Kings
    L(r"tmb_inf_skeleton_warriors|tmb_inf_skeleton_spearmen|tmb_inf_skeleton_archers", keep=True, note="Skeletons: dust that fights. Vanilla."),
    L(r"tmb_inf_nehekhara_warriors", 0.60, "line", note="Nehekharan Warriors: the legions as they were in life, WS3 in bronze."),
    L(r"tmb_inf_tomb_guard", 1.10, "veteran", note="Tomb Guard: the kings' own, S4 T4 with killing blow, bound to their masters; vanilla rates them as line."),
    L(r"tmb_inf_crypt_ghouls", keep=True, note="Ghouls: vanilla."),
    L(r"tmb_mon_ushabti_0$", 8.00, "monstrous", note="Ushabti: statues of the gods given motion, S5 T4 W3; vanilla has them as trolls."),
    L(r"tmb_mon_ushabti_1|tmb_mon_ushabti_ror|tmb_mon_sepulchral", keep=True, note="Ushabti with bows and stalkers: vanilla."),
    # ---------------------------------------------------------------------------------------------------- Vampire Counts
    L(r"vmp_inf_zombie|vmp_inf_tithe|vmp_inf_skeleton_warriors|vmp_inf_konigstein", keep=True, note="Zombies and skeletons: fodder raised for free; the price is the lore."),
    L(r"vmp_inf_crypt_ghouls|vmp_inf_feasters", 0.70, "line", note="Crypt Ghouls: T4, poisoned claws, A2."),
    L(r"vmp_inf_grave_guard|vmp_inf_sternsmen", 1.10, "veteran", note="Grave Guard: wights in ancient armour, S4 T4 killing blow; vanilla rates them as levies in plate."),
    L(r"vmp_inf_cairn_wraiths|vmp_inf_handgunners|vmp_inf_crossbowmen", keep=True, note="Wraiths and Sylvanian levies: vanilla."),
    L(r"vmp_cav_chillgheists", 2.75, "elite", note="The Chillgheists: the Hexwraiths' regiment of renown, which the cavalry study rated below its base unit; a fifth above the Hexwraiths' 2.3 instead."),
    L(r"vmp_mon_crypt_horrors", 7.50, "monstrous", note="Crypt Horrors: T5 W3 with regeneration and poison."),
    L(r"vmp_mon_vargheists|vmp_mon_devils_swartzhafen", 6.50, "monstrous", note="Vargheists: vampires gone to the beast, S5 T4 W3 A3 and flying."),
    # ---------------------------------------------------------------------------------------------------- Vampire Coast
    L(r"cst_inf_zombie_deckhands|cst_inf_zombie_gunnery|cst_inf_sartosa", keep=True, note="Zombie pirates and Sartosans: fodder with cutlasses. Vanilla."),
    L(r"cst_inf_depth_guard|cst_inf_syreens|cst_inf_deck_gunners|cst_mon_rotting_prometheans|cst_mon_mournguls", keep=True, note="Depth Guard, syreens, gunners, prometheans, mournguls: vanilla."),
    L(r"cst_mon_animated_hulks", None, "monstrous", note="Animated Hulks: big stitched brutes; the survey says a bargain at 500. The stats are the lore, the price moves."),
    # ---------------------------------------------------------------------------------------------------- Kislev
    L(r"ksl_inf_armoured_kossars|ksl_inf_kislevite|ksl_inf_ice_guard|ksl_inf_tzar_guard", keep=True, note="Kislev: vanilla sits on the line."),
    L(r"ksl_inf_kossars_\d$", price_add=-25, note="Kossars: the model over-rates hybrids; the community's -25g (6.3 list)."),
    L(r"ksl_inf_kossars_tutorial", keep=True, note="Armoured Kossars (Spears): vanilla."),
    L(r"ksl_inf_streltsi", price_add=-25, note="Streltsi: the community's -25g (6.3 list)."),
    L(r"ksl_inf_akshina", price_add=-50, note="Akshina Ambushers: the community's -50g (6.3 list)."),
    # ---------------------------------------------------------------------------------------------------- Grand Cathay
    L(r"cth_inf_jade_warriors|cth_inf_peasant|cth_inf_jade_warrior_cross|cth_inf_crane|cth_inf_iron_hail|cth_inf_dragon_guard_cross|cth_inf_onyx", keep=True, note="Cathay: vanilla."),
    L(r"cth_inf_grenadiers", keep=True, note="Nan-Gau Grenadiers: the model over-counts the bombs; vanilla."),
    L(r"cth_inf_dragon_guard_0|cth_inf_dragon_guard_ror", 1.90, "elite", note="Celestial Dragon Guard: the Dragon Emperor's own, in celestial armour; vanilla rates them as heavy line."),
    # ---------------------------------------------------------------------------------------------------- Chaos Dwarfs
    L(r"chd_inf_chaos_dwarf_warriors|chd_inf_hobgoblin|chd_inf_orc_labourers|chd_inf_goblin_labourers|chd_inf_chaos_dwarf_blunder|chd_inf_infernal_guard_fire|chd_mon_kdaai", keep=True, note="Chaos Dwarf warriors, hobgoblins, labourers, blunderbusses, fireglaives, K'daai: vanilla."),
    L(r"chd_inf_infernal_guard$|chd_inf_infernal_guard_great", 1.70, "elite", note="Infernal Guard: the Tower of Zharr's oath-bound, faceless in blackshard armour."),
    L(r"chd_inf_infernal_ironsworn", 2.90, "elite", note="Infernal Ironsworn: the Guard's champions."),
    # ---------------------------------------------------------------------------------------------------- Beastmen
    L(r"bst_inf_ungor|bst_inf_minotaurs|bst_mon_harpies|bst_inf_cygor", keep=True, note="Ungors, minotaurs, harpies, cygors: vanilla."),
    L(r"grn_cav_squig_hoppers|grn_cav_durkits", keep=True, note="Squig Hoppers: the cavalry study's model rates them as rabble, this one as line; the two disagree about vanilla, so nothing moves until a test."),
    L(r"brt_cav_pegasus_knights|brt_cav_royal_pegasus", keep=True, note="Pegasus Knights: the study's model rates them at half of what this one does; the two disagree about vanilla, so nothing moves until a test."),
    L(r"bst_inf_centigors|tze_inf_centigors", keep=True, note="Centigors: the cavalry study wants them at elite; the multiplayer list has called them overperformers since 6.3. Kept until the community decides."),
    L(r"bst_inf_gor_herd_1|bst_inf_gor_herd_ror", 0.80, "veteran", note="Gors: WS4 S3 T4, the herd's warriors, tougher than men."),
    L(r"bst_inf_gor_herd_0", keep=True, note="Gor Herd (dual weapons): the 7.1 list calls them overperformers against dearer infantry; vanilla."),
    L(r"bst_inf_bestigor", 1.60, "elite", note="Bestigors: the biggest gors in the best looted armour, great axes."),
    # ---------------------------------------------------------------------------------------------------- Ogre Kingdoms
    L(r"ogr_inf_ogres_", 4.50, "monstrous", note="Ogre Bulls: S4 T4 W3 A3, an ogre is an ogre whatever it carries; vanilla makes a Bull a third of an Irongut."),
    L(r"ogr_inf_ironguts|ogr_inf_maneaters|ogr_inf_golgfags|ogr_inf_leadbelchers|ogr_mon_gorgers|ogr_inf_gnoblars|ogr_inf_pigback", keep=True, note="Ironguts, Maneaters, Leadbelchers, Gorgers, Gnoblars: vanilla."),
    L(r"ogr_mon_yhetees", 8.50, "monstrous", note="Yhetees: S5 T4 W3 A3 and faster than anything their size."),
    L(r"ogr_inf_eshin_maneater", None, "champion", note="The Eshin Maneater: one ogre assassin; the stats are the lore, the price moves to what they are worth."),
    # ---------------------------------------------------------------------------------------------------- Daemons of Chaos
    L(r"dae_inf_chaos_furies", keep=True, note="Furies: vanilla."),
    # ------------------------------------------------------- the model's blind spots (docs/COMMUNITY_RESEARCH.md section 3)
    L(r"chd_cav_bull_centaurs_dual_axe_ror", keep=True, note="Hashut's Dark Ravagers: a regiment of renown with a blunderbuss the model counts at full; kept rather than held."),
    L(r"emp_cav_outriders_morr", keep=True, note="Amethyst Outriders: the model rates them far above their price (110 armour on outriders); nobody else does. Kept rather than held."),
    L(r"ogr_mon_thundertusk", keep=True, note="Thundertusk: the model calls it over-priced, the multiplayer list calls it over-performing; kept until the community decides."),
    L(r"cth_veh_sky_lantern", keep=True, note="Sky Lantern: the model sees its damage, not its misses; the community calls it over-priced and inaccurate."),
    L(r"skv_mon_brood_horror", keep=True, note="Brood Horror: weak for its price in every list; the model's 'bargain' is a blind spot."),
    L(r"nur_mon_beast_of_nurgle", keep=True, note="Beast of Nurgle: slow, weak damage, no role; the model's 'bargain' is a blind spot."),
    L(r"mon_fell_bats|mon_cave_bats", keep=True, note="Bats: crumble too fast; the 7.1 list wants them stronger, not dearer."),
    L(r"def_art_reaper_bolt_thrower|hef_art_eagle_claw_bolt_thrower", keep=True, note="Bolt throwers: see no use for their mobility and arc, which the model cannot see."),
    # ======================================================================= monsters, beasts, chariots, machines
    # Rated as regiments (reg=True): a single entity's regiment power, the Empire Knights regiment = 1.00. The survey's
    # price lines for these castes are flat, so the price layer only moves prices; these entries are where the lore is
    # unambiguous that vanilla sells a creature short. Vanilla anchors: Giant 2.9, Stegadon 3.5, Treeman 4.1, Rogue Idol
    # 4.3, Star Dragon 3.1, Bloodthirster 2.2, Hydra 1.6, Manticore 1.2, Great Eagle 1.0.
    # ---------------------------------------------------------------------------------------------- greater daemons
    L(r"kho_mon_bloodthirster", 3.8, "greater daemon", reg=True, note="Bloodthirster: the greatest of Khorne's daemons, S7 T6 W7, a match for a Star Dragon; vanilla has it below a Giant."),
    L(r"sla_mon_keeper_of_secrets", 3.5, "greater daemon", reg=True, note="Keeper of Secrets: WS10, faster than anything its size."),
    L(r"nur_mon_great_unclean_one", 3.5, "greater daemon", reg=True, note="Great Unclean One: T7 W10, a hill of rot that does not die."),
    L(r"tze_mon_lord_of_change", 2.8, "greater daemon", reg=True, note="Lord of Change: a sorcerer first, but S6 T6 W6 and winged."),
    L(r"chs_mon_dragon_ogre_shaggoth", 3.5, "monster", reg=True, note="Dragon Ogre Shaggoth: the eldest of the dragon ogres, S7 T6 W7, kin to storms."),
    # -------------------------------------------------------------------------------------------------------- dragons
    L(r"hef_mon_star_dragon", 3.8, "dragon", reg=True, note="Star Dragon: the eldest of Caledor's dragons, S7 T6 W7, the strongest monster an elf can wake."),
    L(r"hef_mon_moon_dragon", 2.8, "dragon", reg=True, note="Moon Dragon."),
    L(r"hef_mon_sun_dragon", 2.2, "dragon", reg=True, note="Sun Dragon: the youngest, and still a dragon."),
    L(r"def_mon_black_dragon|hef_mon_black_dragon_imrik", 2.8, "dragon", reg=True, note="Black Dragon: bred in the Black Spine, noxious breath."),
    L(r"hef_mon_forest_dragon|wef_forest_dragon", 2.2, "dragon", reg=True, note="Forest Dragon."),
    L(r"nor_mon_frost_wyrm_0$|ksl_mon_frost_wyrm", 2.3, "dragon", reg=True, note="Frost dragons and wyrms of the north."),
    L(r"nur_mon_toad_dragon", 3.0, "dragon", reg=True, note="Toad Dragon: a bloated plague-wyrm, T7 W8."),
    # ----------------------------------------------------------------------------------------------- the great beasts
    L(r"lzd_mon_dread_saurian", 4.5, "monster", reg=True, note="Dread Saurian: the apex predator of Lustria, T7 W8, which no other beast of the jungle survives; vanilla rates it as a Giant."),
    L(r"lzd_mon_carnosaur|dwf_mon_carnosaur_thorek", 3.0, "monster", reg=True, note="Carnosaur: S7 T5 W5 and frenzied; beats a Giant in the lore and loses to one in vanilla."),
    L(r"lzd_mon_stegadon_0$", 2.2, "monster", reg=True, note="Feral Stegadon: the beast without its howdah is still T6 W6 with horns, and still below the Ancient Stegadon (2.45)."),
    L(r"skv_mon_hell_pit_abomination", 2.6, "monster", reg=True, note="Hell Pit Abomination: Moulder's masterpiece, T6 W6, regenerating, too stupid to die; vanilla has it as a slow troll."),
    L(r"def_mon_war_hydra|def_mon_chill_of_sontar", 2.4, "monster", reg=True, note="War Hydra: seven heads and regeneration, T5 W6."),
    L(r"def_mon_kharibdyss", 2.6, "monster", reg=True, note="Kharibdyss: the hydra's sea-born cousin, T6 W6."),
    L(r"mon_terrorgheist", 2.8, "monster", reg=True, note="Terrorgheist: a giant undead bat whose scream kills; the model does not hear it."),
    L(r"vmp_mon_varghulf", 2.0, "monster", reg=True, note="Varghulf: a vampire lost to the beast, S5 T5 W5 regenerating."),
    L(r"mon_ghorgon", 3.2, "monster", reg=True, note="Ghorgon: a minotaur the size of a giant, S7 T6 W6; it should out-fight a Giant."),
    L(r"mon_jabberslythe", 2.0, "monster", reg=True, note="Jabberslythe: a horror whose look drives men mad; vanilla prices it as a great beast and rates it as a lesser one."),
    L(r"mon_chimera", 2.4, "monster", reg=True, note="Chimera: three heads, wings, S6 T5 W6."),
    L(r"grn_mon_arachnarok_spider|grn_mon_venom_queen", 2.5, "monster", reg=True, note="Arachnarok: T6 W8 and poisoned, the great spider of the forest goblins."),
    L(r"grn_mon_colossal_squig", 2.2, "monster", reg=True, note="Colossal Squig."),
    L(r"grn_mon_wyvern", 1.6, "monster", reg=True, note="Wyvern: a poor cousin of the dragons, still S5 T5 W5 with a poison sting."),
    L(r"grn_cav_mangler_squig", 1.6, "monster", reg=True, note="Mangler Squigs: two chained squigs the size of ogres, a wrecking ball on legs."),
    L(r"nor_mon_war_mammoth_1|nor_mon_war_mammoth_2|nor_mon_war_mammoth_ror_0", 2.4, "monster", reg=True, note="War Mammoth: T6 W6+, a walking hill of tusk and fur."),
    L(r"nor_mon_war_mammoth_0$|def_mon_war_mammoth_0$", 2.0, "monster", reg=True, note="Feral Mammoth."),
    L(r"ogr_mon_stonehorn", 2.6, "monster", reg=True, note="Stonehorn: a living avalanche, T6 W6, that regrows its own stone; vanilla measures it as an Ancient Stegadon's lesser cousin."),
    L(r"chd_mon_kdaai_destroyer", 4.2, "monster", reg=True, note="K'daai Destroyer: a daemon of fire bound in iron, the strongest thing the Chaos Dwarfs field."),
    L(r"chd_mon_bale_taurus", 3.0, "monster", reg=True, note="Bale Taurus."),
    L(r"chd_mon_great_taurus", 2.2, "monster", reg=True, note="Great Taurus."),
    L(r"chd_mon_lammasu", 1.6, "monster", reg=True, note="Lammasu: a sorcerous beast, magic-resistant."),
    L(r"tmb_mon_necrosphinx", 3.5, "construct", reg=True, note="Necrosphinx: a decapitating construct of Nehekhara, S7 T8 W5."),
    L(r"tmb_veh_khemrian_warsphinx", 2.6, "construct", reg=True, note="Khemrian Warsphinx."),
    L(r"tmb_mon_tomb_scorpion", 1.6, "construct", reg=True, note="Tomb Scorpion: a burrowing construct with a killing sting."),
    L(r"cth_mon_celestial_lion", 2.4, "monster", reg=True, note="Celestial Lion."),
    L(r"ksl_mon_elemental_bear", 2.5, "monster", reg=True, note="Elemental Bear: the spirit of the Kislev forest given form, T6 W7."),
    L(r"feral_manticore", 1.6, "beast", reg=True, note="Manticore: S5 T5 W4 with a poisoned sting, flying; vanilla has it as a Great Eagle."),
    L(r"mon_cockatrice", 1.4, "beast", reg=True, note="Cockatrice: a petrifying gaze the model cannot see."),
    L(r"mon_great_eagle", 1.3, "beast", reg=True, note="Great Eagle: the fastest thing in the sky, S4 T4 W3."),
    L(r"hef_mon_phoenix_frostheart", 2.2, "beast", reg=True, note="Frostheart Phoenix."),
    L(r"hef_mon_phoenix_flamespyre", 1.6, "beast", reg=True, note="Flamespyre Phoenix: it burns, it dies, it rises."),
]


def entry(key):
    """the ladder entry for a unit key, or None; the longest matching pattern wins"""
    hits = [e for e in LADDER if re.search(e["pattern"], key)]
    if not hits:
        return None
    return max(hits, key=lambda e: len(e["pattern"]))


def family(e, key, keys, castes):
    """the non-renown members of an entry's family among keys, in the same caste as key"""
    return [k for k in keys if re.search(e["pattern"], k) and "ror" not in k and castes.get(k) == castes.get(key)]


def lore(key, rows):
    """what the ladder says about key: dict(factor, size, tier, note, keep, target, reg) or None.

    rows: {key: survey row} with power (per model), power_reg, cost, caste, men. factor is the per-model multiplier
    over vanilla: the family's base member (the cheapest non-renown one in the same caste, the plain unit) lands on
    the target and every other member, weapon variants and regiments of renown alike, keeps its vanilla ratio to it."""
    e = entry(key)
    if not e or key not in rows:
        return None
    out = dict(tier=e["tier"], note=e["note"], keep=e["keep"], size=e["size"], target=e["target"], factor=1.0, reg=e["reg"],
               hold_price=e["hold_price"], price_add=e["price_add"])
    if e["keep"] or e["target"] is None:
        return out
    caste = rows[key]["caste"]
    fam = [k for k in rows if re.search(e["pattern"], k) and "ror" not in k and rows[k]["caste"] == caste] or [key]
    base_key = min(fam, key=lambda k: (rows[k]["cost"] or 1e9, rows[k]["power"]))
    base = rows[base_key]["power_reg"] if e["reg"] else rows[base_key]["power"]
    out["factor"] = e["target"] / base if base > 0 else 1.0
    out["base"] = base_key
    return out


if __name__ == "__main__":
    import json, os
    S = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "_survey.json")))
    rows = {u["key"]: u for u in S["units"]}
    for castes, label in ((("melee_infantry", "missile_infantry", "monstrous_infantry"), "infantry"),
                          (("monster", "war_beast", "chariot", "warmachine", "missile_cavalry"), "the rest")):
        keys = [k for k, u in rows.items() if u["caste"] in castes]
        rated = [k for k in keys if entry(k) and entry(k)["target"] is not None and not entry(k)["keep"]]
        kept = [k for k in keys if entry(k) and entry(k)["keep"]]
        print("%s: %d units, %d rated, %d kept as vanilla, %d left to the price layer" % (label, len(keys), len(rated), len(kept), len(keys) - len(rated) - len(kept)))
