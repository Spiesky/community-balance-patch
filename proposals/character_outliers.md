# Character outliers (open proposal, round 1)

**Status:** open for proposals and votes. Not in the patch. Game data checked on build 25546563.

## Scope

The loudest campaign complaint is lords and heroes that make regular units irrelevant. But many players also say a
level 40 lord *should* be a one-man army, and a general cut to every character would punish the lords nobody
complains about. So this page is only about **named outliers** and one family of **XP traits**, not a general
character nerf.

Nothing here touches Legendary Lords' unique campaign mechanics (currencies, rituals, buildings). That is outside a
unit balance patch.

## 1. Nagash early in the campaign

**The complaint.** "You can take on three full Skaven armies by yourself with him alone." "Early on in the game
you're best off using him with no army." Several threads, one week after release. Players agree his faction's
economy is weak, so the power sits in the character.

**What the data says.** Nagash is a caster, but in melee he is as tough as the biggest monster lords:

| | health | armour | resistances | weapon (base + AP) | hits up to | vs |
|---|---|---|---|---|---|---|
| Nagash | 9408 | 100 | 20% physical, 20% missile | 200 + 320, magical | 5 models | infantry-sized |
| Kholek Suneater | 8988 | 95 | 25% missile | 160 + 440 | 6 models | large |
| Be'lakor | 9304 | 45 | 20% physical, 25% missile | 150 + 350 | 5 models | large |
| Arkhan the Black | 4840 | 90 | 15% missile | 290 + 160 | | |

His splash is tuned to infantry (`splash_attack_target_size medium`), which is exactly what early armies are made
of. Lore is on his side: he is the Great Necromancer. So the options keep his magic and his health bar, and aim at
how fast he clears infantry.

**Options**

- **A. No change.** Lore says he can do this.
- **B. Fewer models per swing.** Weapon `wh3_dlc29_vmp_nagash_sword_and_staff`: `splash_attack_max_attacks` 5 -> **3**.
  His damage against a single target, a monster or a lord is unchanged.
- **C. Less health.** `land_units` `wh3_dlc29_vmp_cha_nagash`: `bonus_hit_points` 9400 -> **8400** (health 9408 -> 8408,
  still above Kholek).

Hold until CA's balance patch (due mid to late October 2026): CA said it is reviewing the new units, and a change
on top of theirs would overshoot.

## 2. Dechala in melee

**The complaint.** "Dechala ... becomes invulnerable in campaign way too fast." Patch 8.1 buffed her, and campaign
players called that "a complete travesty".

**What the data says.** Her weapon swings about twice as often as the other lords on this page:

| | weapon (base + AP) | seconds between swings | hits up to | bonus vs infantry |
|---|---|---|---|---|
| Dechala | 220 + 330, magical | **2.0** | 6 models at 1.3x | +30 |
| Nagash | 200 + 320 | 4.0 | 5 models | |
| Sea Lord Aislinn | 310 + 150 | 4.0 | 5 models | +28 |
| Kholek Suneater | 160 + 440 | 3.7 | 6 models | |

**Options**

- **A. No change.**
- **B. Slower swings.** Weapon `wh3_dlc27_sla_dechala_swords`: `melee_attack_interval` 2.0 -> **2.5** (about 20% less
  melee damage over time, everything else unchanged).
- **C. Less splash.** Same weapon: `splash_attack_max_attacks` 6 -> **4**, `bonus_v_infantry` 30 -> **15**.

Her XP was also named ("+40% XP for every character"). The current data does not show a +40%: her faction trait
gives her characters **+10%**, the first palace ritual gives the faction leader **+25%**, and the Boon of Slaanesh
gives one army **+50%** while it lasts. Numbers for these need a sponsor who has played her since 9.0.

## 3. Sayl

**The complaint.** "Sayl is a one man army too soon." One thread, no numbers.

**What the data says.** On paper he is modest in melee: 4030 health, light armour, 270 + 110 per swing. The power
most likely sits in his spells and skills, which this page has not measured yet.

**Not ready for a vote.** It needs a sponsor with exact numbers and a battle log or a replay.

## 4. XP traits

**The complaint.** "A 50% increase is too much ... below 30% would be a more appropriate number." (CA forum, with
agreement in the thread.) Characters who roll these traits level far faster than the rest.

**What the data says.** These are the innate traits a new lord or hero can spawn with (`character_skill_level_to_effects_junctions`,
effect `wh3_main_effect_character_campaign_experience_mod`):

| trait | skill keys | vanilla |
|---|---|---|
| Determined, Driven | `wh2_main_skill_innate_all_determined`, `wh3_main_skill_innate_cth_determined` | +30% |
| Intelligent, Wise (Cathay), Superior, Vainglorious | `wh_main_skill_innate_all_intelligent`, `wh2_main_skill_innate_all_intelligent`, `wh_dlc07_brt_skill_innate_all_intelligent`, `wh3_main_skill_innate_cth_intelligent`, `wh3_main_skill_innate_cth_intelligent_hero`, `wh3_dlc23_skill_innate_chd_lord_hero_shared_9_superior`, `wh3_dlc23_skill_innate_chd_hero_daemonsmith_sorcerer_6_vain` | +50% |
| Knowledgeable, Lettered | `wh2_main_skill_innate_all_knowledgeable`, `wh3_main_skill_innate_cth_knowledgeable`, `wh3_main_skill_innate_cth_knowledgeable_hero`, `wh3_cp1_skill_innate_cth_knowledgeable`, `wh3_cp1_skill_innate_cth_knowledgeable_hero` | +75% |

Left alone: traits you earn or that belong to one character (Third Generation, Dream Big, Aspirant, Mentor,
Infernal Dominance, Leadership Qualities, the "Empowered" reward versions).

**Options**

- **A. No change.**
- **B. As the thread asks.** +30% -> **+20%**, +50% -> **+25%**, +75% -> **+40%**. The order between the traits stays.
- **C. Softer.** +30% unchanged, +50% -> **+35%**, +75% -> **+50%**.

This touches every faction: needs two thirds of the votes.

## Evidence that helps

For Nagash and Dechala: a battle log or replay of the lord alone against a full army, early in the campaign (turn
count and level in the report). For the traits: how many turns a +50% or +75% character took to reach level 20 or
30 compared with one without the trait.
