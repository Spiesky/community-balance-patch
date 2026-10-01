# Auto-resolve

Auto-resolve decides most campaign battles, and it runs entirely on data tables, so a mod can change it.

**The patch does not change auto-resolve.** The two rules on this page are in a separate pack, `cbp_autoresolve_test.pack`, and they stay there until the test below has been run. With only the patch loaded, the auto-resolve rules are vanilla's.

**Where to get the test pack.** It is not on the Workshop. From 0.2.0 on it is attached to each release on the [GitHub releases page](https://github.com/Spiesky/community-balance-patch/releases) (`tools/patch_day.sh` builds it). Put the file in the game's `data` folder and tick it in the launcher's mod manager. If the release has no such file yet, ask on the Workshop page and I will send it.

## How it works

The game gives every unit a kill rate from its stats and simulates the battle in steps (about 4 seconds each). Melee
units form the front, then ranged, then artillery, and the enemy hits the front first. Each step's losses are shared
out by "combat potential": units the game counts as high value (heroes, mages, most ranged units and artillery) get a
large bonus and push their losses onto the rest, while line infantry and chaff soak them. That is why a heroic victory
can still cost you whole regiments of spearmen.

CA has never documented it. This is from a reverse-engineering of the Warhammer II auto-resolver, and the tables in 9.0
still have the same shape. The Battle Logger is how I check it against real results.

## What the test pack changes

1. **A possible bug.** `wh_moderate_kps_multiplier_bonus` has two identical rows (missile kill rate +7.5%, all classes)
   and no melee row. Its spell twin, `wh_spell_moderate_kps_multiplier_bonus`, has one of each. The test pack turns
   one of the two missile rows into a melee row. The game uses this group in one place only: for an army
   defending in fortify stance. So the change reaches those battles and no others. Whether it is a fix is an open
   question (below). In the test pack, not in the patch.
2. **The player's back-line units lose models more slowly** (`cbp_protect_back_line`): the AI's kill rate against the
   player's field artillery is 70% lower, against missile infantry 35% lower, against missile cavalry 25% lower. The
   idea is that units you would keep safe at the back of a real battle should not die like your front line. The three
   values are a first guess.

## What the game's tables show

Rule 2 is attached the way CA attaches its own one-sided rule. `wh_strong_ranged_kps_multiplier_penalty` (missile kill
rate -20%) is attached with `player_type` set to `ai_vs_human`, and the test pack attaches `cbp_protect_back_line` with
the same value, in the same battle types. I read `ai_vs_human` as "the AI's units, when they fight a human player". If
that is right, the rule lowers only the AI's kill rate against the player's back line: the AI's own artillery and
archers are as easy to kill as before, and battles between two AI factions are not touched.

`wh_moderate_kps_multiplier_bonus` is attached once: battle type `fortify_battle`, `player_type` `defender_target`,
with no difficulty condition. I read `defender_target` as the defending army, whoever plays it. If so it applies to
the player and the AI alike, and it is not a difficulty handicap.

The rows, from the game's `autoresolver_modifier_group_lookups` table:

<!-- AUTORESOLVE_LOOKUPS -->
From the game's own tables (`autoresolver_modifier_group_to_modifiers`, `autoresolver_modifier_group_lookups`), as read by `tools/refresh_vanilla.py`:

| group | modifiers | applied to (`player_type`) and where (`battle_type`) |
|---|---|---|
| `wh_moderate_kps_multiplier_bonus` | missile kill rate +0.075 against all_classes, missile kill rate +0.075 against all_classes | `defender_target` in fortify_battle |
| `wh_strong_kps_multiplier_bonus` | melee kill rate +0.15 against all_classes, missile kill rate +0.15 against all_classes | `attacker_target` in ambush_generic; `defender_target` in settlement_generic_land |
| `wh_strong_ranged_kps_multiplier_penalty` | missile kill rate -0.2 against all_classes | `ai_vs_human` in ambush_generic, bridge_generic, fortify_battle, generic_battle, minor_settlement_generic_land, minor_settlement_generic_naval, settlement_generic_land, settlement_generic_naval; `defender_target` in ambush_generic |
| `wh_settlement_human_v_ai_bonus` | melee kill rate +0.05 against all_classes, missile kill rate +0.05 against all_classes | `defending_human_vs_ai` in minor_settlement_generic_land, settlement_generic_land |
| `wh_settlement_human_v_ai_penalty` | missile kill rate -0.05 against all_classes, melee kill rate -0.05 against all_classes | `attacking_ai_vs_human` in minor_settlement_generic_land, settlement_generic_land |

Every `player_type` the game uses: `ai_vs_human`, `any`, `attacker_target`, `attacking_ai_vs_human`, `defender_target`, `defending_human_vs_ai`, `human_vs_ai_easy`, `human_vs_ai_hard`, `human_vs_ai_legendary`, `human_vs_ai_normal`, `human_vs_ai_vhard`.

What this shows. `wh_moderate_kps_multiplier_bonus` is used in one place, for the defender in a fortify battle, and its two rows are the same missile row twice; its stronger sibling `wh_strong_kps_multiplier_bonus` has one melee and one missile row. And the game has one-sided `player_type` values: CA's own handicap on AI missiles (`wh_strong_ranged_kps_multiplier_penalty`) is attached with `ai_vs_human`, which the test pack's rule copies, so that it lowers only the AI's kill rate against the player's back line.
<!-- /AUTORESOLVE_LOOKUPS -->

## What I don't know yet

**Does `ai_vs_human` mean what I think?** The name is all I have. CA has not documented it. The paired test below
checks it: if the pack changes nothing, or changes the AI's losses as well, the reading is wrong.

**Is the doubled missile row a bug?** The table shows where the group is used, not what CA meant. Two identical rows
look like a slip, but +15% missile kill rate for an army defending in fortify stance may be exactly the intent. That is
a guess either way, so rule 1 stays "possible bug".

**Is rule 2 needed at all?** The game already shelters ranged units and artillery through combat potential, so rule 2
might double a bias vanilla already has. The one result so far (mortar 100% left, missile infantry 67%, front line
45-58%) had nothing without the rule to compare with, so it shows nothing.

## The test

As far as I know, the auto-resolver gives the same result every time you reload the same save. I have not tested that
myself. If it holds, repeating a run adds nothing: ten reloads of one save are one data point, and what counts is the
number of **different battles**.

**Check it first:** auto-resolve your first save twice. If the two results differ, tell me, and do three runs per save
each way instead of one.

The design:

1. Turn on the Battle Logger. It notes for every battle which packs were loaded, so a run with the test pack and a
   run without can never be mixed up.
2. Collect **at least ten different pre-battle saves**: battles where your army has artillery or missile units as well
   as a front line. Save on the pre-battle screen, or just before you attack if the game will not let you save there.
3. For each save: auto-resolve it **once without the test pack**, and **once with `cbp_autoresolve_test.pack`
   added**. Nothing else may differ: keep the patch either on for all twenty runs or off for all twenty, because the
   auto-resolver works from unit stats and the patch changes those. Adding or removing a pack means restarting the
   game, so do all ten one way, then all ten the other way.
4. Where you can spare the time, **fight the battle yourself** from the same save as well. That is the "real" answer
   the two auto-resolves are measured against.
5. Share the log (see [TESTING.md](TESTING.md)).

What is compared: **the share of your army's losses that each class took** (front line, missile infantry, missile
cavalry, artillery), with the pack and without, save by save. Also the army's total losses and who won, because a rule
that makes back lines die more slowly can make the whole battle longer and costlier, not just move the losses around.

What decides it:

- If the back line's share of the losses with the pack is closer to the fought battles than without it, rule 2 has a
  case, at the values the test supports.
- If vanilla was already close, rule 2 goes.
- Either way it only goes into the patch through the public step in
  [HOW_DECISIONS_ARE_MADE.md](HOW_DECISIONS_ARE_MADE.md), and only if the test shows it touches the player's side alone.

Auto-resolved battles logged with the test pack loaded must never be used as the baseline: the log's `mods=` field
names the pack ([LOG_FORMAT.md](LOG_FORMAT.md)), and `tools/autoresolve_calibrate.py` is to count only auto-resolves
without it.

## Also known, not changed

From the same reverse-engineering. Only the first and the fourth have been checked against the 9.0 tables.

- `wh_strong_ranged_kps_multiplier_penalty`: missile kill rate -20%, all classes, attached with `ai_vs_human` (the
  lookups above). If that is a handicap in the player's favour, removing it would make auto-resolve harder.
- The losing army is usually wiped out instead of retreating (retreat thresholds in `campaign_variables`).
- Spells and abilities count for very little (their auto-resolve buff is capped at 0.10).
- Shock and melee cavalry get +50% melee kill rate (`wh_global_cavalry_melee_kps_multiplier_bonus`).
- `ai_usage_group` sets both a unit's battle AI role and its auto-resolve protection, so changing one changes the other.
