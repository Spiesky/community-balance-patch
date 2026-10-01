# Blood Knights

**Status:** in the patch, under test. Both variants: Blood Knights (sword and shield) and Blood Knights (Lances).

Post results on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227) (Discussions tab: start a thread named after the test, or reply in one that has that name) or with the [test report form](https://github.com/Spiesky/community-balance-patch/issues/new?template=test_report.yml).

## The test wanted now

**Blood Knights (Lances) against Demigryph Knights: who wins, and with how much left?**

1. Custom battle, unit size Ultra, battle difficulty Normal, time limit 60 Minutes, map Crossroads – Multiplayer (or any flat, open map, say which). The full settings are in [docs/TESTING.md](../docs/TESTING.md).
2. You set up both armies. Yours (Vampire Counts): a Vampire Lord and one unit of Blood Knights (Lances). The AI's (The Empire): a General of the Empire and one unit of Demigryph Knights (the plain ones, not Halberds). Both lords on foot, no spells, no items (untick every spell on the AI's lord too).
3. Order your lord to attack the enemy lord. Charge the Demigryph Knights head on with the Blood Knights and start a stopwatch. Then no further orders.
4. When one of the two cavalry units is dead or routs for good: pause. Write down who won, the winner's hit points left (the health bar, as a share) and models left, and the time.
5. Quit the battle (Esc, Quit Battle). The lords are still standing; that is fine.
6. Three runs. If you have time, swap sides and do three more.

If you have time for more, run the same six with the patch switched off (untick it in the launcher's mod manager and start the game again). That is the baseline everything is compared with.

Two things this test does not do:

- **It does not isolate the Blood Knights.** The patch also changes Demigryph Knights (+10 charge bonus, +2 melee attack, from the community list), so patch on against patch off compares both units.
- **It measures the fight, not the price.** One unit against one unit is not equal gold: in vanilla Blood Knights (Lances) cost 1650 and Demigryph Knights 1400, and the patch raises the Blood Knights' price ([reports/beta_changelog.md](../reports/beta_changelog.md)). Whether they are worth it is a second question, answered with this result and the others below together.

## The idea

Every rider of the Blood Dragon order is a vampire (tabletop around WS5 S5 T5 W2 A2), frenzied, in plate, on a nightmare steed. Vanilla gives each one the health of a mortal knight and fields 60 of them. The patch fields **24**, each one far tougher and harder-hitting, and their charge bonus rises with their weapon damage so they stay shock cavalry.

The rule for every unit made smaller: **it never ends up with less total health than vanilla.**

## What "fewer and stronger" costs, and what it buys

It is a trade, not a free buff.

What it costs:

- **Slower against chaff.** One swing kills one model, however much damage is behind it. A vanilla Blood Knight already kills a Skavenslave in one hit, so the extra damage is wasted there, and 24 riders swing less often than 60.
- **Under fire it may lose health faster.** A shot that would have finished off a 120-health rider and wasted the rest now spends all its damage. On the other hand 24 riders are a smaller target than 60. Which of the two wins is not known until the under-fire test below has been run.
- **Campaign bonuses per model are worth less.** A technology or lord skill that adds a flat amount to each model is collected by 24 riders instead of 60.

What stays the same:

- **Healing.** In the game's data a healing spell restores a share of the unit's total health each second (Invocation of Nehek: 0.8% a second for 18 seconds), not a fixed number of hit points. So a heal is worth the same in hit points. It brings back fewer riders, because each rider is more health. Whether that matters in a campaign is a question for the campaign test below.

What it buys:

- **Each rider wins its own fight.** Higher melee attack, melee defence and health per rider.
- **Damage that is not wasted on tough targets.** Against elite infantry, other cavalry and monsters the heavier hits land in full.
- **The unit keeps its punch longer.** A unit hits less hard with every model it loses, and these lose models slowly.

## The numbers

Game data 9.0, unit size Ultra. Melee attack, charge bonus and weapon damage include Frenzy (+10 melee attack, +10% damage and charge bonus), which the unit has while its leadership is high. Vanilla and the patch side by side; the table is written by the build, so it always matches the pack. The reasons are in [reports/beta_changelog.md](../reports/beta_changelog.md).

<!-- BETA_NUMBERS:blood_knights -->
| | models | melee attack / defence | charge bonus | HP per model | total HP | weapon damage | price (custom battle) | campaign: recruit / upkeep |
|---|---|---|---|---|---|---|---|---|
| Blood Knights, vanilla | 60 | 46 / 54 | 53 | 120 | 7200 | 38 + 21 AP, +16 vs infantry | 1550 | 1600 / 400 |
| patch | **24** | 54 / 62 | 132 | **300** | 7200 | 96 + 52 AP, +40 vs infantry | **2025** | 2100 / 523 |
| Blood Knights (Lances), vanilla | 60 | 42 / 42 | 79 | 120 | 7200 | 35 + 19 AP, +22 vs large | 1650 | 1700 / 425 |
| patch | **24** | 50 / 50 | 198 | **300** | 7200 | 88 + 47 AP, +55 vs large | **2150** | 2225 / 554 |

Attack, defence and charge are what the unit card shows with the unit's permanent passives on. Models are at Ultra unit size; smaller settings scale both versions the same way.
<!-- /BETA_NUMBERS:blood_knights -->

Against chaff, from the combat model (an estimate, not a measurement):

<!-- GRIND:blood_knights -->
**Blood Knights**: about 180 Skavenslaves killed for every rider lost (vanilla: about 57), and about 270 a minute by the whole unit (vanilla: about 530).
**Blood Knights (Lances)**: about 93 Skavenslaves killed for every rider lost (vanilla: about 28), and about 220 a minute by the whole unit (vanilla: about 420).

These are the combat model's estimates (`tools/grind_check.py`), not measurements: sustained melee, no charges, Skavenslaves that never rout, and one swing killing at most the models it can reach.
<!-- /GRIND:blood_knights -->

## More tests, same settings

Each is a measurement: who won, hit points left as a share, models left, time. Each side needs a lord: take the faction's plain melee lord on foot (for Bretonnia the Lord, for Warriors of Chaos the Chaos Lord, for Skaven the Warlord), no spells, no items, and handle them as in the test above.

- Against **Grail Knights** and **Chaos Knights**, one unit each. The patch changes these opponents too (Grail Knights are made smaller and stronger, Chaos Knights get +2 melee attack).
- **Does the charge still break a block?** Charge one unit of Halberdiers head on, no further orders. Note whether the Halberdiers rout, when, and the Blood Knights' hit points left. Then the same into Chaos Warriors (the patch changes those too: +2 charge bonus, +2 melee attack).
- **The grind.** One unit against four units of Skavenslaves, charge the nearest, no further orders. Three minutes after the charge order (stopwatch, or 57:00 on the clock), pause and note the Blood Knights' kills (hover over the unit card), models left and health bar as a share. Then quit. With the patch and without.
- **Under fire.** The missile test from [docs/TESTING.md](../docs/TESTING.md): stand in front of one unit of Crossbowmen for 60 seconds (not a gunpowder unit: the patch changes those too, and that would mix two changes). Riders left and health bar as a share, with the patch and without.
- **Campaign.** If you field them in a campaign: turn, difficulty, what they fought, and what healing did for them: how much of the unit a heal brought back, and whether that was enough to keep them in the fight. This is the part a custom battle cannot show.

The size (24) and the price are mine to decide from what these show. An opinion on either is welcome; a test result can change them (see [how decisions are made](../docs/HOW_DECISIONS_ARE_MADE.md)).
