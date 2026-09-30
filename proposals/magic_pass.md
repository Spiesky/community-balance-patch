# Magic pass (open proposal, round 1)

**Status:** open for proposals and votes. Not in the patch. Game data checked on build 25546563.

## The complaint

Campaign players want more and better magic, not less. Two things come up again and again:

- Buff and hex spells take **5 seconds** to cast, which the community's peer-reviewed list (patch 6.2) called
  "cumbersome" and asked to cut to 3. By the time the buff lands, the fight it was for has moved.
- Lore of Death feels poor after the vortex nerfs: "Spending 22 winds to kill a single unit is actually terrible."

## 1. Cast time of buffs and hexes

**What the data says.** Most buffs and hexes in the game already cast in 3 seconds or less (89 buffs, 72 hexes).
These 34 still take 5:

| lore | spells (normal and overcast) |
|---|---|
| Life | Regrowth |
| Shadows | Okkam's Mindrazor |
| Light | Birona's Timewarp |
| Metal | Transmutation of Lead (also the Kihar copy) |
| Beasts | The Curse of Anraheir |
| Wild | Mantle of Ghorok |
| High Magic | Arcane Unforging |
| Stealth | Brittle Bone |
| Nehekhara | Usekhp's Incantation of Desiccation |
| Ice | Crystal Sanctuary |
| Great Maw | Trollguts |
| Nurgle | Fleshy Abundance |
| Slaanesh | Phantasmagoria |
| Yang | Might of Heaven & Earth |
| Big Waaagh | 'Ere We Go |
| Little Waaagh | Night Shroud |
| Hags | Malediction of Madness, Incantation of Mania |

Exact keys (`unit_special_abilities`, `wind_up_time` 5.0): `wh_dlc05_spell_life_regrowth`(`_upgraded`),
`wh_dlc05_spell_shadow_okkams_mindrazor`(`_upgraded`), `wh_main_spell_light_bironas_timewarp`(`_upgraded`),
`wh_main_spell_metal_transmutation_of_lead`(`_upgraded`), `wh_dlc08_spell_metal_transmutation_of_lead_kihar`,
`wh_dlc03_spell_beasts_the_curse_of_anraheir`(`_upgraded`), `wh_dlc03_spell_wild_mantle_of_ghorok`,
`wh2_dlc17_spell_wild_mantle_of_ghorok_upgraded`, `wh2_main_spell_high_magic_arcane_unforging`(`_upgraded`),
`wh2_dlc14_spell_stealth_brittle_bone`(`_upgraded`), `wh2_dlc09_spell_nehekhara_usekhps_incantation_of_desiccation`(`_upgraded`),
`wh3_main_spell_ice_crystal_sanctuary`(`_upgraded`), `wh3_main_spell_great_maw_trollguts`(`_upgraded`),
`wh3_main_spell_nurgle_fleshy_abundance`(`_upgraded`), `wh3_main_spell_slaanesh_phantasmagoria`(`_upgraded`),
`wh3_main_spell_yang_might_of_heaven_and_earth`(`_upgraded`), `wh_main_spell_big_waaagh_ere_we_go`,
`wh_main_spell_lil_waaagh_night_shroud`(`_upgraded`), `wh3_dlc24_spell_hags_malediction_of_madness`(`_upgraded`).

Left at 5 seconds on purpose: damage-over-time spells (The Fate of Bjuna, Curse of Years, Final Transmutation,
Soul Stealer, Flensing Ruin), vortexes, bombardments, summons and the endgame "cataclysm" spells.

**Options**

- **A. No change.**
- **B. As the community list asked.** `wind_up_time` 5.0 -> **3.0** on the keys above.
- **C. Halfway.** `wind_up_time` 5.0 -> **4.0** on the keys above.

## 2. Lore of Death costs

**What the data says.** The Fate of Bjuna is the second most expensive spell in the game:

| spell | winds | cast time (s) | cooldown (s) |
|---|---|---|---|
| The Harbinger (Undeath) | 23 | 5 | 47 |
| **The Fate of Bjuna** (Death) | **22** | 5 | 52 |
| Heart of Winter (Ice) | 22 | 5 | 54 |
| Vangheist's Revenge, The Dreaded Thirteenth Spell | 20 | 5 | 52-54 |
| **The Purple Sun of Xereus** (Death) | **18** (overcast 24) | 5 | 54 |
| Foot of Gork, The Maw, Blizzard, Flames of Azgorh | 18 | 5 | 52-54 |

**Options**

- **A. No change.**
- **B. Cheaper Death.** The Fate of Bjuna 22 -> **18** (`wh_main_spell_death_the_fate_of_bjuna` and the Arzik copy
  `wh_dlc08_spell_death_the_fate_of_bjuna_arzik`). The Purple Sun of Xereus 18 -> **16**, overcast 24 -> **21**.
- **C. Bjuna only.** The Fate of Bjuna 22 -> **18**, Purple Sun unchanged.

## Not in this round

- **The 100 Winds of Magic reserve.** The most popular magic mod raises it. It is a campaign effect, not a spell
  value, and would change every faction at once. Worth its own round.
- **Older community numbers for spell costs and durations.** The 2024 list has dozens, but some were adopted by CA
  between 6.x and 9.0, so each has to be checked against current data before it can be proposed.
- **Spells in auto-resolve.** See [autoresolve_retreat_and_spells.md](autoresolve_retreat_and_spells.md), question 2.

## Evidence that helps

For cast times: a replay of a buff landing late, or a note of how often you skip a 5-second buff. For Death: how
many models a Fate of Bjuna or Purple Sun takes in a typical campaign battle, against what the winds could have
bought elsewhere.
