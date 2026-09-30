# Archetype pass: the units every roster skips (open proposal, round 1)

**Status:** open for proposals and votes. Not in the patch. Game data checked on build 25546563. Numbers below are
on top of the current beta, which already gives Fell Bats, Harpies, Carrion and Goblin Wolf Riders small buffs
from the community list and cuts Chaos and Norscan Warhounds by 25 gold.

## The complaint

Faction by faction, the "never build" lists name the same kinds of unit: light melee cavalry, small fliers,
war-dogs, chariots, and weapon variants that lose to a sibling from the same building.

## What the numbers say

The combat model does **not** call most of these over-priced. For the gold, they fight about as well as other units
of their caste, and some (Skeleton Horsemen, Fell Bats, Carrion, Goblin Wolf Chariots, Seeker Chariots) come out as
bargains:

| archetype | units checked | price against the model's fair price |
|---|---|---|
| light melee cavalry | Dark Riders, Ellyrian Reavers, Marauder Horsemen, Skeleton Horsemen, Mounted Yeomen, Peasant Horsemen, Goblin Wolf Riders | -27% to -2%, most around -9% |
| small fliers | Fell Bats, Harpies, Chaos Furies, Carrion | -36% to +7% |
| war-dogs | Chaos and Norscan Warhounds, Dire Wolves, Hunting Hounds, Khorne Warhounds | -11% to +3% |
| chariots | Seeker, Chaos, Orc Boar, Tuskgor, Goblin Wolf, Ithilmar Chariots | -40% to -4% |

(`reports/survey.md` has every unit. Minus means cheaper than the model says it is worth.)

So a price cut is not what these units are missing. In a campaign, an army has 20 slots, and a cheap unit that
dies fast still costs a whole slot. What they lack is a job they do well enough to earn that slot: catching
artillery and missile units, surviving the ride there, finishing routers. The options below give each archetype
that job, and a campaign-only upkeep cut as the alternative for those who think the price is the problem after all.

## 1. Light melee cavalry

- **A. No change.**
- **B. Survive the job.** +4 melee defence and +10% health per model:

  | unit | melee defence | health per model |
  |---|---|---|
  | Dark Riders | 24 -> **28** | 84 -> **92** |
  | Ellyrian Reavers | 26 -> **30** | 87 -> **96** |
  | Marauder Horsemen (Chaos, Norsca) | 20 -> **24** | 83 -> **91** |
  | Skeleton Horsemen | 26 -> **30** | 81 -> **89** |
  | Mounted Yeomen | 26 -> **30** | 84 -> **92** |
  | Peasant Horsemen | 26 -> **30** | 84 -> **92** |
  | Goblin Wolf Riders | 22 -> **26** | 51 -> **56** |

  Price unchanged. Against missile infantry in melee they now win clearly; against real cavalry they still lose.
- **C. Cheaper to keep.** Upkeep -20% (campaign only; multiplayer price unchanged): Dark Riders 113 -> **90**,
  Ellyrian Reavers 138 -> **110**, Marauder Horsemen 125 / 131 -> **100 / 105**, Mounted Yeomen and Peasant Horsemen
  100 -> **80**, Goblin Wolf Riders 75 -> **60**. (Skeleton Horsemen have no upkeep.)

## 2. Small fliers

They are the only thing that can reach artillery behind a battle line, and they melt to missile fire on the way.

- **A. No change.**
- **B. Missile resistance.** 25% missile resistance (`damage_mod_missile` **25**) for Fell Bats (Vampire Counts,
  Vampire Coast, Tomb Kings; the Tomb Kings version has 15 now), Harpies (Dark Elves, Beastmen, Wood Elves), Chaos
  Furies (all five) and Carrion. Nothing else changes.
- **C. Cheaper to keep.** Upkeep -20%: Fell Bats 88 -> **70**, Harpies 150 -> **120**, Chaos Furies 125 -> **100**,
  Chaos Furies of Khorne 163 -> **130**, the other god-aligned Furies 138 -> **110**.

## 3. War-dogs

- **A. No change.** The beta's -25 gold on Chaos and Norscan Warhounds is enough; see what logs say.
- **B. Bite harder.** +4 melee attack: Chaos and Norscan Warhounds (both versions) 26 -> **30**, Dire Wolves
  (Vampire Counts) 26 -> **30**, Dire Wolves (Tomb Kings) 31 -> **35**, Hunting Hounds 28 -> **32**, Chaos Warhounds of
  Khorne 26 -> **30**. They chase down routers and missile units faster.
- **C. Cheaper to keep.** Upkeep -20%: Warhounds 100 -> **80** (poison versions 113 -> **90**), Dire Wolves 125 ->
  **100**, Hunting Hounds 100 -> **80**, Khorne Warhounds 113 -> **90**.

Flesh Hounds of Khorne are not in this group: they are elite daemons, and the model already rates them as
over-priced for what it can see (their ward save and magic resistance may be why).

## 4. Chariots

The model rates them as bargains already, so their problem is what happens after the charge: they get stuck and
die. That points at health, not price.

- **A. No change.**
- **B. Last longer after the charge.** +10% health per chariot: Seeker Chariots 1224 -> **1346**, Chaos Chariots,
  Orc Boar Chariots, Tuskgor Chariots and Ithilmar Chariots 1394 -> **1533**, Goblin Wolf Chariots 520 -> **572**.
- **C. Hit harder on the charge.** +10 charge bonus on the same six units.

## 5. Sibling variants

**Bull Centaur Renders.** Three versions from the same building at 1500 / 1550 / 1550 gold, all with the same
34 + 80 weapon. The shield version has a 35% shield, Dual Axes have +18 bonus vs infantry, Great Weapons +25 bonus
vs large. The model rates Dual Axes and plain Renders as bargains (-15%, -17%) and Great Weapons as closest to
fair (-8%), and players report picking one and ignoring the rest.

- **A. No change.**
- **B. Clear jobs.** Great Weapons (`wh2_dlc23_chd_bull_centaur_great_axe`): bonus vs large 25 -> **40**.
  Dual Axes (`wh2_dlc23_chd_bull_centaur_dual_axe`): bonus vs infantry 18 -> **28** (also reaches the regiment of
  renown, Hashut's Dark Ravagers, which shares the weapon).

**Pox Riders vs Plague Toads, Sky Lantern vs Sky-junk, Skullcracker vs Iron Daemon:** not ready for a vote. The
model cannot see what decides these (the Sky Lantern's bombs and support role, the Iron Daemon's ranged fire in
campaign use), so they need a sponsor with numbers and battle logs.

## How to vote

Each archetype is voted on its own. B and C can both win for the same archetype only if the sponsor tests them
together. Several factions at once: needs two thirds of the votes.

## Evidence that helps

Battle logs of battles with these units in them, and a line in the test report saying what job you gave them.
