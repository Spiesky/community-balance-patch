# The community's balance list in the patch

The patch takes the multiplayer community's own peer-reviewed list and puts it in as written: their numbers, no model
in between.

**Source:** [Community sourced, peer-reviewed balance recommendations list (patch 7.1+)](https://community.creative-assembly.com/total-war/total-war-warhammer/forums/15-total-war-warhammer/threads/13577-community-sourced-peer-reviewed-balance-recommendations-list-patch-7-1),
Total Tavern and Vermin League discords, 2 March 2026. The line numbers below point into that thread as I copied it.

**What CA has done since.** 7.2, 8.0 and 9.0 had no numbered balance changes. Patch 8.1 (9 July 2026) adopted about
60 of the list's recommendations almost word for word, most of the Norsca, Nurgle, Slaanesh and Tzeentch sections
(Chimera, Dread Maw, Kurgan Horsemen, Feral Mammoth, Soulcrusher, Toad Dragon, Rot Flies, Plague Ogres, Nurglings,
Great Unclean One, Slaangors, Champions of Slaanesh, Seeker Chariots, Hellflayers, Exalted Seeker Chariot,
Daemonettes, Screamers, Shrieking Skyrays, Flamers, Blazing Squealers, Mutalith, Celestial Dragon Guard, The Green
Guardian). Those are already in the game and are left out here. The Sky Lantern was reworked in 8.0, so its entry is
left out too.

**How it sits with the rest of the patch.** A unit on this list takes the community's change and nothing from the
patch's model: the list is peer-reviewed and has been played, the model's numbers have not. So for the elite infantry
the list names (Chaos Warriors, Chosen, Temple Guard, Phoenix Guard, Black Guard, White Lions, Grave Guard, Infernal
Guard, Hammerers, Black Orcs), the patch ships the list's +2 attack style of change, not the lore ladder's larger one;
the ladder's numbers for them stay in `reports/changelog.md` as proposals, and its elite-infantry theme covers the
elite infantry the list does not mention. The lore elites (Blood Knights, Grail Knights, Grail Guardians, Swords of
Chaos) keep the patch's own design.

**Regiments of renown and campaign twins follow their base unit.** The list was written unit by unit and mostly leaves
regiments of renown out, so applying it to the letter leaves Keepers of the Flame behind the Phoenix Guard they are a
better version of. The patch's rule everywhere else is that a regiment of renown moves with its base, so here too:
where the list changes a unit and does not name its regiment of renown, the regiment takes the same changes to how it
fights (not the price change, and not a remodel written for one unit). A campaign twin (the Grudge Settlers copies)
is the same unit under another key and takes everything. `python3 tools/community.py` lists them as "follows ...".
The other way round, a unit whose regiment of renown the list remodels (Swordmasters of Hoeth, for the Blades of
Hoeth) stays out of the patch's own elite-infantry theme, so the list's remodel keeps the relation it was written for.
A list entry that changes a unit's shot changes its alternate ammunition the same way.

**Guns.** The gunpowder rule applies on top (Handgunners, Thunderers, Streltsi, Deck Gunners, Slayer Pirates). The
list's numbers were written for the vanilla weapon, so on a gun they go through the same rule: a reload change is
multiplied by the rule's reload factor, a missile damage change by its damage factor, and an ammunition change is made
to the vanilla count before the rule cuts it. Deck Gunners, where the list asks for one second off the reload, end at
(11 - 1) x 1.5 = 15 seconds against their neighbours' 16.5: still faster, as the list wanted. The rule itself does not
move a gun's price, so a price change on a gun is the list's alone.

**It was written for multiplayer.** The entries held for campaign are at the end of this page. Everything else is in
as written, including a few nerfs campaign players never asked for (Zombies +25 gold, Skeleton Horse Archers +25 gold,
Wrathmongers -4 melee defence). If one of them is wrong for campaign, that is a suggestion worth posting.

`tools/community.py` holds every entry; `tools/community_check.py` builds the patch with and without the list and
checks that every unit changes exactly as the list says and nothing else moves, the artillery pieces, mounts and
alternate ammunition included. `tools/community_resolved.json` records which units each entry names and the numbers it
applies: the entries are matched by the unit's English name, so if CA renames a unit, adds one with a matching name, or
a number in the list is edited, the build fails until someone has looked.

## Crewed artillery (line 373: more responsive artillery)

| line | engines | change |
|---|---|---|
| 378 | Great Cannons, Helblaster Volley Guns, Mortars, Helstorm Rocket Battery | walk speed 2.2, turn speed 60, fire arc close 60 |
| 380 | Trebuchet & Blessed Field Trebuchet | walk speed 2.2, turn speed 60, fire arc close 60 |
| 381 | Goblin Bolt Throwa & Hobgoblin Bolt Thrower | walk speed 2.4, turn speed 60, fire arc close 60 |
| 382 | Reaper Bolt Throwers & Eagle Claw Bolt Throwers | walk speed 2.4, turn speed 70, fire arc close 60 |
| 383 | Bolt Throwers (Dwarfs) | walk speed 2.4, turn speed 70, fire arc close 70 |
| 384 | Grudge Throwers, Cannons, Organ Guns | walk speed 2.2, turn speed 60, fire arc close 60 |
| 385 | Flame Cannon | walk speed 2.6, turn speed 70, fire arc close 70 |
| 386 | Goblin Hewers | turn speed 70, fire arc close 70 |
| 387 | Grand Cannons & Fire Rain Rocket Battery | run speed 3.2, turn speed 70 |
| 388 | Goblin Rock Lobbers & Doom Diver Catapults | walk speed 2.2, turn speed 60, fire arc close 60 |
| 389 | Plague Claw Catapult & Warp Lightning Cannon | walk speed 2.2, turn speed 60, fire arc close 60 |
| 390 | Screaming Skull Catapult | walk speed 2.2, turn speed 60, fire arc close 60 |
| 391 | Carronades, Mortars (Vampire Coast) | walk speed 2.2, turn speed 60, fire arc close 60 |
| 392 | Queen Bess | walk speed 2.2, turn speed 45, fire arc close 50 |

## Other entities

| line | what | change |
|---|---|---|
| 460 | Centigor hitbox (radii ratio) | radii ratio 0.5 |
| 576 | Cold One Chariots | acceleration 6, deceleration 7, turn speed 80 |
| 416 | Bretonnian Warhorses, Great Stags, Stags | acceleration 7.0 |

## Units

| line | units | change |
|---|---|---|
| 395 | Chaos Warriors, Chaos Warriors of Khorne, Chaos Warriors of Nurgle, Chaos Warriors of Slaanesh, Chaos Warriors of Tzeentch | +2 CB, +2 MA |
| 396 | Chaos Warriors (Great Weapons), Chaos Warriors of Nurgle (Great Weapons) | +2 AP WS, +2 MA |
| 397 | Chaos Warriors (Halberds), Chaos Warriors of Khorne (Halberds), Chaos Warriors of Tzeentch (Halberds) | +2 AP WS, +2 MD |
| 398 | Chaos Warriors of Khorne (Dual Weapons) | +2 MA, +3 BvI |
| 399 | Chaos Warriors of Slaanesh (Hellscourges) | +2 CB, +2 MA |
| 401 | Chosen, Chosen of Khorne, Chosen of Nurgle, Chosen of Slaanesh, Chosen of Tzeentch | +2 CB, +2 AP WS, +60 mass |
| 402 | Chosen (Great Weapons), Chosen of Nurgle (Great Weapons) | +4 CB, +1 base WS, +3 AP WS, +60 mass |
| 403 | Chosen (Halberds), Chosen of Tzeentch (Halberds) | +2 MD, +2 AP WS, +10 mass |
| 404 | Chosen of Khorne (Dual Weapons) | +2 AP WS, +2 BvI, +60 mass |
| 405 | Chosen of Slaanesh (Hellscourges) | +2 CB, +1 base WS, +1 AP WS, +60 mass |
| 407 | Marauders of Khorne (Dual Weapons) | unit spacing like Bloodletters, -25 gold |
| 408 | Marauders of Tzeentch (Spears) | -25 gold |
| 409 | Chaos Knights, Chaos Knights of Khorne, Chaos Knights of Nurgle, Chaos Knights of Slaanesh, Chaos Knights of Tzeentch | +2 MA |
| 413 | Great Eagle | +5 LD, +217 HP per model, +6 base WS, +14 AP WS |
| 414 | Fell Bats | +1 MA, +2 CB, +3 HP per model |
| 415 | Chaos Warhounds, Chaos Warhounds (Poison), Norscan Warhounds, Norscan Warhounds (Poison) | -25 gold |
| 418 | Harpies | +2 MA, +2 CB |
| 464 | Centigors | -75 gold |
| 465 | Centigors (Great Weapons) | -150 gold |
| 466 | Centigors of Tzeentch | -150 gold |
| 467 | Sons of Ghorros (Centigors – Great Weapons) | -100 gold |
| 468 | Centigors (Throwing Axes), Groghooves of Wolf's Run (Centigors – Throwing Axes) | -25 gold |
| 470 | Gor Herd | -1 base WS, -1 AP WS |
| 471 | Pestigors | +2 CB |
| 472 | Tzaangors | +2 MD |
| 480 | Groghooves of Wolf's Run (Centigors – Throwing Axes) | +27 accuracy |
| 493 | Wardens of Montfort (Mounted Yeomen Archers) | +11 CB, +4 accuracy |
| 499 | Lammasu | +320 HP per model |
| 500 | Infernal Guard (Great Weapons) | +4 MA, +2 CB, +2 AP WS |
| 501 | Infernal Guard | +2 MA, rank depth 5 |
| 502 | Chaos Dwarf Warriors (Great Weapons) | +2 MA |
| 571 | Black Guard of Naggarond | +30 mass, +1 base WS, +3 AP WS, +4 MA, +10 armour |
| 579 | Shades (Greatswords) | -50 gold |
| 587 | Slayer Pirates | +2 ammo, +2 base WS, +2 AP WS |
| 588 | Hammerers | +80 mass |
| 590 | Thunderers (Grudge-Rakers) | -25 gold, shockwave radius 1.0 |
| 592 | Longbeards (Great Weapons) | +2 MA, +2 AP WS |
| 593 | Dwarf Warriors (Great Weapons) | +2 MA |
| 594 | Thunderers | -25 gold |
| 607 | Jade Lion, Jet Lion | +5 MA |
| 611 | Bandits of the Silver Road (Peasant Archers) | +27 accuracy, -25 gold |
| 619 | Nasty Skulkers | +6 MA, +1 base WS, +3 AP WS |
| 620 | Night Goblins | +2 MA, +1 base WS, -25 gold |
| 621 | Da Warlord's Boyz (Night Goblins) | +1 AP WS, -25 gold |
| 622 | Black Orcs (Great Weapons) | +2 MA, +2 AP WS, +40 mass |
| 623 | Black Orcs | +2 MA, +40 mass |
| 624 | Krimson Killerz (Black Orcs) | +2 MA, +2 BvI |
| 626 | Forest Goblin Spider Riders | +1 base WS, +1 AP WS, +3 CB |
| 627 | Forest Goblin Spider Rider Archers | +15 range, +1 missile base dmg, +1 missile AP dmg, +360 HP (unit) |
| 630 | Ruglud's Armoured Orcs | +50 gold, +4 accuracy |
| 635 | Mangler Squigs | +4 base WS, +10 AP WS |
| 636 | Goblin Wolf Riders | +3 CB |
| 637 | Goblin Wolf Rider Archers | +2 missile base dmg |
| 638 | Snotling Pump Wagons (Spiky Rollers) | -75 gold |
| 639 | Spider Hatchlings | +3 CB |
| 643 | Phoenix Guard | +30 mass, +1 base WS, +3 AP WS |
| 644 | Lothern Sea Guard | calibration area 4.4 |
| 645 | White Lions of Chrace | +4 CB, +2 AP WS |
| 646 | Spearmen | +2 MA |
| 647 | Silver Helms, Silver Helms (Shields) | +6 CB, +3 LD |
| 648 | Blades of Hoeth (Swordmasters of Hoeth) | 60 models, 140 HP per model, +10 CB, WS 18 base, 42 AP, rank depth 3 |
| 649 | Lothern Skycutters (Bolt Throwers) | +4 ammo |
| 654 | Sisters of Avelorn | +2 missile AP dmg |
| 661 | Wrathmongers | -4 MD, -5 LD |
| 663 | Skullcrushers of Khorne | +5 LD, +10 armour |
| 664 | Bloodcrushers of Khorne | +10 armour, +4 MD |
| 666 | Slaughterbrute | +1000 HP per model, +40 base WS moved to AP, acceleration 5, deceleration 6 |
| 667 | Bloodthirster | +500 HP per model, +40 base WS moved to AP |
| 670 | Flesh Hounds of Khorne | +400 mass, +2 MA |
| 693 | War Bear Riders | mount turn speed 120, +2 BvL, +5 LD |
| 699 | Kossars, Kossars (Spears), Streltsi | -25 gold |
| 700 | Akshina Ambushers | -50 gold |
| 702 | Dazh's Hearth-Blades (Tzar Guard – Great Weapons) | -50 gold |
| 717 | Temple Guard | +2 MA, +1 base WS, +2 AP WS, +30 mass |
| 718 | Saurus Warriors, Saurus Warriors (Shields) | +4 CB |
| 719 | Saurus Spears, Saurus Spears (Shields) | +2 base WS, +1 AP WS |
| 733 | Feral Cold Ones | +4 speed |
| 779 | Yhetees | +8 speed, +2 MA |
| 788 | Plague Monk Censer Bearers | +3 MA |
| 789 | Death Runners | +2 BvI |
| 790 | Wolf Rats | +1 base WS, +2 AP WS |
| 797 | Council Guard (Stormvermin – Halberds) | -150 gold |
| 798 | The Thing-Thing (Hell Pit Abomination) | -50 gold |
| 833 | Handgunners | -25 gold |
| 834 | War Wagons (Mortars) | -50 gold |
| 835 | Crossbowmen | -25 gold |
| 837 | Steam Tank (Volley Gun) | +9 missile base dmg, +28 missile AP dmg |
| 838 | Demigryph Knights | +10 CB, +2 MA |
| 840 | The White Wolves (Huntsmen) | +12 HP per model |
| 841 | Deathjacks (Archers) | +20 range, +17 accuracy |
| 844 | Skeleton Horse Archers | +25 gold |
| 845 | Tomb Scorpion | +5 MA |
| 846 | Blessed Legion of Phakth (Skeleton Archers) | -25 gold, +10 armour |
| 847 | King Nekhesh's Scorpion Legion (Skeleton Spearmen) | -4 MD, +10 armour, +1 base WS moved to AP, -25 gold |
| 851 | Tomb Guard | +2 MA |
| 852 | Carrion | +4 CB |
| 883 | Deck Gunners | -1 reload (s) |
| 886 | Syreens | +2 MA, +2 MD |
| 887 | Zombie Pirate Gunnery Mob (Hand Cannons) | -25 gold |
| 889 | Rotting Prometheans | -100 gold |
| 894 | The Tide of Skjold (Zombie Pirate Deckhand Mob) | -50 gold |
| 898 | Hexwraiths | +6 mount speed, +4 MA |
| 900 | Black Knights | -100 gold |
| 902 | Zombies | +25 gold |
| 903 | Grave Guard (Halberds) | -50 gold |
| 904 | Grave Guard, Grave Guard (Great Weapons) | +2 MA |
| 923 | Dragon Ogres | acceleration 4, deceleration 5, +3 LD |
| 924 | Dragon Ogre Shaggoth | -100 gold, acceleration 4, deceleration 5 |
| 933 | Hawk Riders | +5 CB, +5 LD |
| 934 | Bladesingers | +2 CB, +2 AP WS |
| 935 | Deepwood Scouts | calibration area 3.4 |
| 941 | Winterheart Guard (Eternal Guard – Shields) | +20 armour |
| 942 | Eternal Guard, Eternal Guard (Shields) | +20 mass |
| 943 | Enigmas of Ghyran (Zoats) | -50 gold |

## Held after a campaign review

The list is written by multiplayer players, and CA's 8.1 drew campaign anger for copying its buffs to units campaign
players already find too strong. These entries wait until battle logs show they are needed:

| line | why it waits |
|---|---|
| 625 | Arachnarok Spider: named among the dominant campaign monsters |
| 730 | Ancient Stegadon: Stegadons are named among the dominant campaign monsters |
| 778 | Ironblaster: the most-cited dominant campaign unit ("may be the most powerful unit in the game") |
| 836 | Helstorm Rocket Battery: rockets are named among the dominant campaign artillery |
| 939 | Treeman: named among the dominant campaign monsters |

## Not in yet

- **Lords and heroes** (Daemon Princes, Hellebron, Be'lakor, Thorgrim, Grimgor, the price cuts on characters and mounts
  and so on). They matter most in multiplayer and custom battles; next pass.
- **Spells, abilities, items, contact effects, army abilities** (the whole spell section, Rally/Stand Your Ground
  durations, potions, scrolls, Nurgle army abilities). Next pass after the lords.
- **Unit caps** are multiplayer-only and not part of a campaign mod.
- **Animation and hitbox fixes** (Daemon Princes, Miao Ying, Mournguls, entity shapes) need animation work, not tables.
- Taken out on purpose: **Grail Guardians** (the patch's own lore elite), **Teutogen Guard and Putrid Blightkings** (new in 9.0, look bugged or mispriced; wait for CA's balance patch), **Bloodwrack Shrine +190 WS** (the list
  does not say base or AP), **Druzhina ammunition** (no unit by that name in the game), **Blessed Field Trebuchet
  explosion damage** and **Poisoned Wind Mortar radius** (explosion tables, next pass), **Reaper/Eagle Claw
  multi-shot ammo** (alternate ammunition, next pass), **War Wagon Mortars fire arc** (line 379: the wagon is a chariot
  engine shared with the other wagons; next pass).

