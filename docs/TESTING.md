# How to test

One page. The point of a fixed recipe is that your result and mine can be put side by side.

**The test wanted now:** Blood Knights (Lances) against Demigryph Knights. The recipe is on [the Blood Knights page](../units/blood_knights.md): three short custom battles, about twenty minutes.

Post results on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227): open its Discussions tab and start a thread named after the test ("Blood Knights against Demigryph Knights"), or reply in one that already has that name. Or use the [test report form](https://github.com/Spiesky/community-balance-patch/issues/new?template=test_report.yml) on GitHub. Both count the same.

## Settings for every test

| setting | value |
|---|---|
| mode | Custom battle, land battle, against the AI |
| unit size | **Ultra** (the numbers on the unit pages are for Ultra) |
| battle difficulty | **Normal** (harder settings give the AI's units stat bonuses) |
| map | **Crossroads – Multiplayer** (the flat one of the two Crossroads maps), or any flat, open map. Say which one you used. |
| time limit | **60 Minutes**. This puts a clock at the top of the screen. It counts down. |
| lords | The game needs a lord on each side. The unit page names them. No mount, no spells, no items, on both lords: untick every spell on the AI's lord too, or it will heal or blast the test unit. |
| not used | lord abilities, spells, items, unit abilities you have to click |
| other mods | none, apart from the patch and the Battle Logger |

**You set up both armies** on the custom battle screen: yours and the AI's. Each is a lord and the units the recipe names, nothing else.

**The lords.** Your lord gets one order at the start: attack the enemy lord. That keeps the two of them busy with each other. If the enemy lord gets to your test unit anyway, say so on that run ("lord joined").

**Timing.** Use a stopwatch on your phone. Or read the clock: it starts at 60:00, so 57:00 is three minutes in.

**Patch on or off.** Say which. The same test with the patch off is the baseline, and just as useful. To switch it off, untick it in the mod manager of the game's launcher and start the game again.

A unit page may change any of this (more units, a longer time, standing side-on). The page's recipe wins.

## A unit duel

1. One unit per side, plus the lords, unless the unit page says otherwise.
2. Opening order: charge the enemy unit head on. Then **no further orders** to that unit. Start the stopwatch.
3. Let it run until one of the two test units is dead or routs for good.
4. Pause. Write down: **who won, the winner's hit points left** (the health bar on its unit card, as a share: "about half") **and its models left, and the time.**
5. Quit the battle (Esc, Quit Battle). The lords are still standing, so the battle is not over.
6. Do it **three times**. If you have time, swap sides (you take the other unit) and do it three more times: the AI does not charge the way you do, so both ways are worth having.

A result looks like this (made-up numbers, to show the form):

    Blood Knights (Lances) vs Demigryph Knights, patch 0.2.0, Ultra, Normal, Crossroads – Multiplayer
    me as Blood Knights: won, about 60%, 14 models, 2:10 / won, about half, 11 models, 2:40 / lost, enemy about 20%, 3:05
    me as Demigryphs:    lost, enemy about half, 2:20 / lost, enemy about 70%, 1:55 / lost, enemy 40%, lord joined, 2:50

## A missile test

1. You take the **target**. The AI has the missile unit.
2. Walk the target into range, halt it facing the shooters, and stand still.
3. Start the stopwatch at the first volley. At **60 seconds**, pause the game.
4. Read the target's **models left** on its unit card and its **health bar as a share** (about three quarters, about half). Write both down.
5. Quit the battle straight away (Esc, Quit Battle).
6. Three runs. Throw a run away if the shooters walk off or charge instead of shooting, or if the enemy lord reaches the target before the 60 seconds are up.

## A campaign report

Campaign is what the mod is for, so these matter most, even though no two are alike. Note:

- the **turn** and the **campaign difficulty and battle difficulty**,
- **what fought what** (the armies, roughly: "my 6 Handgunners, 8 Halberdiers, 2 Great Cannons against a full Chaos Warrior stack"),
- whether you **fought it or auto-resolved it**,
- what happened to the unit you are reporting on, and what you expected.

## The Battle Logger backs up what you wrote

The optional [Battle Logger](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476307) add-on writes every battle to `cbp_battle_log.txt` in your game folder (in Steam: right-click the game, Manage, Browse local files). It writes once, when the battle ends: each unit, the hit points it had at that moment, how long the battle ran, and which version of the patch was loaded. For campaign battles it also notes the turn and the campaign difficulty, fought or auto-resolved. The format is in [LOG_FORMAT.md](LOG_FORMAT.md). Nothing leaves your PC until you share it.

Whether the game lets it write when you **quit** a battle, I have not yet been able to check. If it does, the log holds the exact hit points behind your "about half" (and may name a winner: a quit can count as a defeat). If it does not, nothing appears in the file for that battle, and that is not a fault on your side: tell me, it is useful to know. Either way the line you wrote by hand is the result, and the log is the evidence under it.

The log does not know the unit size setting, the battle difficulty, the map, or which of the two test units won. **Always post the one-line result yourself: who won, hit points left, time, and the unit size, battle difficulty, map and whether the patch was on.**

To add the log, open the [upload page](https://spiesky.github.io/community-balance-patch/) and drop the file on it. Then either:

- press **Copy summary** and paste it under your result in the Workshop thread (no account needed beyond Steam). The summary is totals per unit, not who won each battle, so it cannot stand in for your line. Or
- press **Send my log**, which opens the GitHub form with the log filled in.

## What not to conclude from one battle

- **One battle is an anecdote.** The same duel can go either way on a lucky charge. That is why it is three runs each way.
- **A duel is not a campaign.** It says nothing about upkeep, recruitment, healing, lord skills or the rest of the army.
- **A unit that wins its duel is not overpowered,** and one that loses is not useless. The question is whether it is worth its price.
- **Different settings cannot be compared.** A result at Large or on Very Hard is still welcome, but say so, and I keep it apart.
- **Kills are not strength.** A unit that chased routers has many kills; a unit that held the line for ten minutes has few.
