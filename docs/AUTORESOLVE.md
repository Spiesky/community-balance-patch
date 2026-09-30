# Auto-resolve

Auto-resolve decides most campaign battles, and it runs entirely on data tables, so a balance patch can fix it.

## How it works

The game gives every unit a kill rate from its stats and simulates the battle in steps (about 4 seconds each). Melee
units form the front, then ranged, then artillery, and the enemy hits the front first. Each step's losses are shared
out by "combat potential": units the game counts as high value (heroes, mages, most ranged units and artillery) get a
large bonus and push their losses onto the rest, while line infantry and chaff soak them. That is why a heroic victory
can still cost you whole regiments of spearmen.

CA has never documented it; this is from a reverse-engineering of the Warhammer II auto-resolver and still matches the
9.0 tables. The Battle Logger is how we check it against real results.

## What the patch changes

1. **A CA bug, fixed.** `wh_moderate_kps_multiplier_bonus` has two identical missile rows (+7.5%) and no melee row; its
   spell twin has one of each. One of the two now adds to melee instead. Still present in the 9.0 data.
2. **Back-line units lose models more slowly** (`cbp_protect_back_line`): field artillery takes 70% fewer kills, missile
   infantry 35% fewer, missile cavalry 25% fewer. Units you'd keep safe at the back of a real battle stop dying like
   your front line.

## Open question: is rule 2 needed?

The game already shelters ranged units and artillery through combat potential, so rule 2 might be doubling a bias
vanilla already has. The one test so far (mortar 100%, missile infantry 67%, front line 45-58%) had no run without the
patch to compare with. Until the test below is done, rule 2 is the part of the patch most likely to change.

### The test

1. Turn on the Battle Logger. Make a save on the pre-battle screen of a battle with artillery and missile units on your
   side (the same save for every run).
2. Auto-resolve it five times **without** the patch (reload the save each time).
3. Auto-resolve it five times **with** the patch.
4. Fight it once yourself, if you can, as the "real" answer.
5. Upload the log. `tools/battle_logs.py` and `tools/autoresolve_calibrate.py` compare the runs per unit class.

If back-line losses with the patch come out closer to the fought battle than without it, rule 2 stays; if vanilla was
already close, rule 2 goes or gets smaller. Logs from many players tune the numbers per class automatically
(`autoresolve_calibrate.py`).

## Also known, not changed yet

- `wh_strong_ranged_kps_multiplier_penalty`: AI missile units get -20% kill rate against the player. It is a hidden
  handicap in your favour; removing it would make auto-resolve harder, so it stays until logs say otherwise.
- The losing army is usually wiped out instead of retreating (retreat thresholds in `campaign_variables`).
- Spells and abilities count for very little (their auto-resolve buff is capped at 0.10).
- Melee and shock cavalry get +50% melee kill rate in most battle types (value from an older export; re-check first).
- `ai_usage_group` sets both a unit's battle AI role and its auto-resolve protection, so changing one changes the other.
