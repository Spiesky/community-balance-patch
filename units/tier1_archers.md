# Cheap archers against armoured infantry (round 1: test first)

**Status:** not in the patch. Nothing is decided until the test below has been run.

Post results on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227) (Discussions tab: start a thread named after the test, or reply in one that has that name) or with the [test report form](https://github.com/Spiesky/community-balance-patch/issues/new?template=test_report.yml).

## Test first

The test wanted now is the one on the [Blood Knights page](blood_knights.md); if you only have time for one, do that one. This is the only step of the archers' round, and it stays open until it has been run. The numbers further down say most cheap bows barely pierce armour, and that shields and flanking fire may be the real story. So before anything changes: measure it.

**Kossars against shielded Chaos Warriors, from the front and from the side.**

1. Custom battle, unit size Ultra, battle difficulty Normal, time limit 60 Minutes, map Crossroads – Multiplayer (or any flat, open map, say which). The full settings are in [docs/TESTING.md](../docs/TESTING.md).
2. You set up both armies. Yours (Warriors of Chaos): a Chaos Lord and one unit of Chaos Warriors (the plain ones, with shields). The AI's (Kislev): a Boyar and one unit of Kossars (the plain ones, not Spears). Both lords on foot, no items.
3. Order your lord to attack the enemy lord.
4. **Front-on:** walk the Chaos Warriors into bow range, halt them facing the Kossars, stand still. Start a stopwatch at the first volley. At **90 seconds**, pause. Write down the Chaos Warriors' models left (100 at the start) and their health bar as a share (about three quarters, about half). Then quit the battle (Esc, Quit Battle).
5. **From the flank:** a new battle, the same, but halt the Chaos Warriors side-on to the Kossars, so the arrows come in from the flank. 90 seconds, models left and health bar as a share, then quit.
6. **Three runs of each.** Throw a run away if the Kossars walk off or charge instead of shooting, or if the Boyar reaches the Chaos Warriors before the 90 seconds are up.

I have not run this recipe in game yet. If a step cannot be done as written, say which one; that is a result too.

The patch on or off makes no difference to the bows here, but say which it was.

What the result decides:

- Front-on losses small, flank losses large: the shield works and the complaint is about being flanked. That points to **A**.
- Front-on losses large as well: cheap bows really do too much to armour. That points to **B**.
- Either way it says nothing about Marauder Hunters, who are a different weapon (see **C**). They need the same test run with them.

A battle log from a full battle does not answer this one: the log records what each unit lost and killed, not who shot whom. Only a one-against-one test does.

## The complaint

Campaign players say basic archers delete armoured infantry they should barely scratch. "Basic archers should absolutely NOT burst down shielded Chaos Warriors." One player reports tier-1 Kossars inflicting 50% casualties on shielded Chaos Warriors. Also named: Goblin Archers, Marauder Hunters. ([CA forum, 26 Mar 2025: "Ranged units are absolutely overpowered"](https://community.creative-assembly.com/total-war/total-war-warhammer/forums/8-general-discussion/threads/9383-ranged-units-are-absolutely-overpowered-and-need-to-be-severely-toned-down))

The evidence is one strong thread plus older ones, so this gets tested before anything goes into the patch.

## What the numbers say (game data, 9.0)

Most cheap bows already do almost no armour-piercing damage, so cutting AP would change little:

| unit | gold (custom battle) | damage + AP per arrow | reload (s) | range |
|---|---|---|---|---|
| Archers (Empire) | 350 | 17 + 2 | 10 | 130 |
| Peasant Bowmen | 400 | 16 + 3 | 11 | 160 |
| Kossars | 450 | 16 + 3 | 11 | 140 |
| Archers (High Elves) | 450 | 16 + 3 | 11 | 180 |
| Goblin Archers | 375 | 10 + 1 | 8 | 115 |
| Skeleton Archers | 425 | 10 + 1 | 8 | 140 |
| Marauder Hunters | 550 | 6 + 22 | 8 | 80 |

Gold is the custom battle cost. Campaign recruitment cost is the same, except Archers (High Elves) at 475; Skeleton Archers have no gold cost in a campaign.

Marauder Hunters are the exception: short range, mostly armour-piercing. The rest kill armour by volume, not by penetration. Shields should block most of it from the front, so flanking fire and the Chaos Warriors' own weakness may be the real story. The community list already buffs Chaos Warriors (+2 melee attack, +2 charge) and cuts Kossars' price by 25.

## What the test decides between

- **A. No change.** The Chaos Warrior buffs and the patch's other changes are enough; wait for battle logs.
- **B. Slower cheap bows.** Tier-1 bows (not crossbows, not gunpowder) reload 20% slower. Same damage per arrow, less fire over a battle.
- **C. Weaker against armour only.** Marauder Hunters and other short-range AP throwers: 20% of their AP damage moves to base damage. **This does not touch Kossars**, the complaint's main example; it only answers the Marauder Hunters part.
- **Your numbers here.** Post exact numbers on the Workshop page or in an issue.

How the choice is made is in [docs/HOW_DECISIONS_ARE_MADE.md](../docs/HOW_DECISIONS_ARE_MADE.md): I post the option I'd take with the test results as the reason, and a test result of your own can reopen it.
