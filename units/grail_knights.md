# Grail Knights and Grail Guardians

**Status:** in the patch, under test.

Post results on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227) (Discussions tab: start a thread named after the test, or reply in one that has that name) or with the [test report form](https://github.com/Spiesky/community-balance-patch/issues/new?template=test_report.yml).

## Next test

The test wanted now is the one on the [Blood Knights page](blood_knights.md). If you only have time for one, do that one. This is the next in line.

**How well do Grail Knights grind through Skavenslaves?**

The first version of the Workshop page said they could do it "more or less forever". That came from a model that counted wasted damage as extra kills. This test replaces the claim with a measurement.

1. Custom battle, unit size Ultra, battle difficulty Normal, time limit 60 Minutes, map Crossroads – Multiplayer (or any flat, open map, say which). The full settings are in [docs/TESTING.md](../docs/TESTING.md).
2. You set up both armies. Yours (Bretonnia): a Lord and one unit of Grail Knights. The AI's (Skaven): a Warlord and four units of Skavenslaves. Both lords on foot, no items.
3. Order your lord to attack the enemy lord. Charge the nearest unit of Skavenslaves head on with the Grail Knights and start a stopwatch. Then no further orders.
4. **Three minutes** after the charge order (57:00 on the clock, which counts down from 60:00): pause. Write down the Grail Knights' kills (hover over the unit card), their models left and their health bar as a share (about three quarters, about half). If the enemy Warlord has been fighting the Grail Knights, say so.
5. Quit the battle (Esc, Quit Battle). 
6. Three runs. There is no swapping sides in this one.

Then, if you can, the same three with the patch switched off (untick it in the launcher's mod manager and start the game again). The comparison is the result. The patch does not change Skavenslaves.

## The idea

A Grail Knight has drunk from the Grail and is more than mortal (tabletop around WS5 S4 I5 A2, with the Lady's full blessing). Grail Guardians are Grail Knights sworn to guard a Grail Chapel. Vanilla fields 48 Grail Knights and 32 Grail Guardians. The patch fields **32** and **24**, each rider tougher and harder-hitting, and their charge bonus rises with their weapon damage so the lance charge stays the point of the unit.

The rule for every unit made smaller: **it never ends up with less total health than vanilla.**

## What "fewer and stronger" costs, and what it buys

It is a trade, not a free buff.

What it costs:

- **Slower against chaff.** One swing kills one model, however much damage is behind it. Fewer riders means fewer swings, so against Skavenslaves or Zombies the smaller unit kills more slowly.
- **Under fire it may lose health faster.** A shot that would have finished off a weaker rider and wasted the rest now spends all its damage. On the other hand fewer riders are a smaller target. Which of the two wins is not known until the under-fire test below has been run.
- **Campaign bonuses per model are worth less.** A technology, a lord skill or a blessing that adds a flat amount to each model is collected by fewer riders.

What stays the same:

- **Healing.** In the game's data a healing spell restores a share of the unit's total health each second (Regrowth: 0.8% a second for 26 seconds), not a fixed number of hit points. So a heal is worth the same in hit points. It brings back fewer riders, because each rider is more health. Whether that matters in a campaign is a question for the campaign test below.

What it buys:

- **Each rider wins its own fight.** Higher melee attack, melee defence and health per rider.
- **Damage that is not wasted on tough targets.** Against elite infantry, other cavalry and monsters the heavier hits land in full.
- **The unit keeps its punch longer.** A unit hits less hard with every model it loses, and these lose models slowly.

## The numbers

Game data 9.0, unit size Ultra. Vanilla and the patch side by side; the table is written by the build, so it always matches the pack. The reasons are in [reports/beta_changelog.md](../reports/beta_changelog.md).

<!-- BETA_NUMBERS:grail_knights -->
| | models | melee attack / defence | charge bonus | HP per model | total HP | weapon damage | price (custom battle) | campaign: recruit / upkeep |
|---|---|---|---|---|---|---|---|---|
| Grail Knights, vanilla | 48 | 38 / 34 | 75 | 152 | 7296 | 18 + 28 AP, +18 vs large | 1850 | 1850 / 462 |
| patch | **32** | 42 / 38 | 112 | **228** | 7296 | 27 + 42 AP, +27 vs large | **1875** | 1875 / 468 |
| Grail Guardians, vanilla | 32 | 42 / 58 | 50 | 252 | 8064 | 24 + 36 AP | 1850 | 1900 / 475 |
| patch | **24** | 45 / 61 | 67 | **336** | 8064 | 32 + 48 AP | **1875** | 1925 / 481 |

Attack, defence and charge are what the unit card shows with the unit's permanent passives on. Models are at Ultra unit size; smaller settings scale both versions the same way.
<!-- /BETA_NUMBERS:grail_knights -->

Against chaff, from the combat model (an estimate, not a measurement):

<!-- GRIND:grail_knights -->
**Grail Knights**: about 100 Skavenslaves killed for every rider lost (vanilla: about 30), and about 370 a minute by the whole unit (vanilla: about 340).
**Grail Guardians**: about 240 Skavenslaves killed for every rider lost (vanilla: about 128), and about 380 a minute by the whole unit (vanilla: about 360).

These are the combat model's estimates (`tools/grind_check.py`), not measurements: sustained melee, no charges, Skavenslaves that never rout, and one swing killing at most the models it can reach.
<!-- /GRIND:grail_knights -->

## More tests, same settings

Each is a measurement: who won, hit points left as a share, models left, time. Each side needs a lord: take the faction's plain melee lord on foot (for Warriors of Chaos the Chaos Lord, for Vampire Counts the Vampire Lord with no spells), no items, and handle them as in the test above. For the Dark Elves take the cheapest lord on foot and say which.

- **Grail Knights against Chaos Knights (Lances)**, one unit each, three runs each way. This measures the fight, not the price (one unit each is not equal gold). The Lances are not in [the changelog](../reports/beta_changelog.md) as I write this (the plain Chaos Knights are, with +2 melee attack), so patch on against patch off changes only the Grail Knights here.
- **Grail Guardians against Blood Knights** (sword and shield), one unit each, three runs each way.
- **Does the charge still break a block?** Grail Knights charge one unit of Chaos Warriors head on, no further orders. Note whether the Chaos Warriors rout, when, and the Grail Knights' hit points left. The patch changes Chaos Warriors too (+2 charge bonus, +2 melee attack, from the community list).
- **Under fire.** The missile test from [docs/TESTING.md](../docs/TESTING.md): stand in front of one unit of Darkshards for 60 seconds. Riders left and health bar as a share, with the patch and without.
- **Campaign.** If you field them in a Bretonnia campaign: turn, difficulty, what they fought, how they did with your lord's skills and blessings on them, and what healing did for them. This is the part a custom battle cannot show.

The sizes (32 and 24) and the prices are mine to decide from what these show. An opinion on either is welcome; a test result can change them (see [how decisions are made](../docs/HOW_DECISIONS_ARE_MADE.md)).
