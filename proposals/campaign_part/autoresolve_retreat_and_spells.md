# Auto-resolve: retreats, spells and two hidden modifiers (open proposal, round 1)

**Status:** open for proposals and votes. Not in the patch. Game data checked on build 25546563.

Four separate questions, each voted on its own. All of them are data rows, so they can go in or come out without
touching saves. Every option here also changes AI-against-AI battles, which decide which factions snowball, so
"no change" is a real option on each one.

How auto-resolve works, and what the patch already changes, is in [docs/AUTORESOLVE.md](../../docs/AUTORESOLVE.md).

## 1. The loser is wiped out instead of retreating

**The complaint.** When you lose an auto-resolved battle, or win one against you, the losing army is usually
destroyed outright instead of falling back with what it has left.

**What the data says.** These `campaign_variables` rows decide it. CA has never documented them, so what each one
does is read from its name and still needs the A/B test below.

| row | vanilla | what the name says |
|---|---|---|
| `autoresolver_wipe_out_army_force_unary_lost` | 0.92 | an army that has lost 92% of its strength is wiped out |
| `autoresolver_unit_wipe_out_threshold` | 0.20 | a unit below 20% is destroyed, not left as a remnant |
| `autoresolver_unit_base_retreat_threshold` | 0.25 | units try to retreat below 25% |
| `autoresolver_num_units_multiplier_vs_enemy_to_allow_retreat` | 0.75 | retreat only allowed with at least 0.75x the enemy's unit count |
| `autoresolver_min_battle_time_before_retreat` | 20 | seconds before anyone may retreat |
| `autoresolver_chase_down_maximum_damage_unary` | 0.20 | the winner's pursuit can take up to 20% more |
| `autoresolver_alliance_wipe_out_winner_loser_strength_multiple` | 7.0 | a side 7x stronger wipes the other out |

**Options**

- **A. No change.**
- **B. Losers get away more often.** `autoresolver_wipe_out_army_force_unary_lost` 0.92 -> **0.97**,
  `autoresolver_chase_down_maximum_damage_unary` 0.20 -> **0.12**,
  `autoresolver_alliance_wipe_out_winner_loser_strength_multiple` 7.0 -> **10.0**.
- **C. Pursuit only.** `autoresolver_chase_down_maximum_damage_unary` 0.20 -> **0.12**. Nothing else.

Big change (touches every faction): needs two thirds of the votes.

## 2. Spells and abilities count for almost nothing

**The complaint.** Magic-heavy armies (Tzeentch, Slaanesh, Lizardmen, mage stacks) do badly in auto-resolve,
because the game barely counts what their spells would do.

**What the data says.** A buff or a hex can change a unit's kill rate by at most 10% in auto-resolve, and a damage
spell's contribution is capped at 30:

| row | vanilla |
|---|---|
| `autoresolver_special_ability_buff_kps_modifier_maximum` | 0.10 |
| `autoresolver_special_ability_debuff_kps_modifier_maximum` | 0.10 |
| `autoresolver_special_ability_damage_damage_maximum` | 30 |

**Options**

- **A. No change.**
- **B. Double the caps.** Buff and debuff maximum 0.10 -> **0.20**, damage maximum 30 -> **45**.
- **C. Half again.** Buff and debuff maximum 0.10 -> **0.15**, damage maximum unchanged.

## 3. A hidden 20% handicap on AI missiles

**What the data says.** `wh_strong_ranged_kps_multiplier_penalty` (missile kill rate -20%) is applied to the AI's
army whenever it fights the player (`player_type ai_vs_human`, 8 battle types: generic, settlement, minor settlement,
their naval versions, bridge, fortify, ambush). The same group is also used for the ambushed side in an ambush
(`defender_target`), which is a sensible rule and stays whatever the vote.

It is a gift to the player that nobody is told about. Removing it makes auto-resolve harder for you.

**Options**

- **A. No change.**
- **B. Halve it against the player.** A new group `cbp_ai_ranged_penalty_half` (missile kill rate **-0.10**, all
  classes) replaces the CA group on the 8 `ai_vs_human` lookup rows. The ambush row keeps the CA group.
- **C. Remove it against the player.** The 8 `ai_vs_human` lookup rows point to a group with **0.0**.

Wait for battle logs before voting on this one: if the Battle Logger shows auto-resolve already costs players
more than fought battles, B and C make that worse.

## 4. Cavalry kill 50% faster in auto-resolve

**What the data says.** `wh_global_cavalry_melee_kps_multiplier_bonus` gives melee cavalry (`cav_mel`) and shock
cavalry (`cav_shk`) **+0.50** melee kill rate, in 9 battle types, for every army (checked in the 9.0 data; the
older note that called it unverified is out of date). Nothing else gets a flat bonus that large. It may exist to
stand in for charges, which auto-resolve does not simulate.

**Options**

- **A. No change.**
- **B. Smaller.** +0.50 -> **+0.35** on both rows (ids 1215071991 and 1694349735).
- **C. Much smaller.** +0.50 -> **+0.25** on both rows.

## Evidence that settles these

The test in [docs/AUTORESOLVE.md](../../docs/AUTORESOLVE.md): one save on the pre-battle screen, five auto-resolves
without the option, five with it, one fought battle if you can, Battle Logger on. For question 1, a battle you
expect to lose. For question 2, an army with two or more casters. For question 4, a cavalry-heavy army against
infantry.
