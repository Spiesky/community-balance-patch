# The method

> The numbers in this page are from the first run (2026-09-16, patch 7.1). The current numbers, on the current
> patch, are in `reports/`. The method has not changed.

Every recruitable unit in Total War: WARHAMMER III (1,042 of them, every caste, every faction), measured on one
combat model, judged against the game's own prices, rated against the lore, and moved without losing what it is.
Started 2026-09-16 on top of the cavalry study ([CAVALRY_STUDY.md](CAVALRY_STUDY.md)), whose targets are the cavalry half of the
lore layer.

- **This file:** the method, the ladder, the results, the decisions, what the model cannot see.
- **`reports/survey.md`:** every unit measured; the valuation (`tools/rebalance_survey.py`).
- **`reports/proposals.md`:** every proposal, before and after, with the reason (`tools/rebalance_solve.py`).
- **`tools/lore_ladder.py`:** the lore ladder for infantry, monsters, beasts and machines: the judgments, one line each.
- **`reports/changelog.md`:** what changed, one line per unit, in plain words.
- **`reports/ladder.md`:** every faction's roster in ladder order, the page to review the judgments on.
- **`build/community_balance_patch.pack`:** the build (`tools/build_rebalance.py`). **Not yet tested in a campaign.**

---

## 1. What balance means here

Total War balance is not "every unit equal". A Zombie is not a Grail Knight and must not become one. Balance is
**every unit worth its price**: two armies of equal gold should be an even fight whatever they are made of, and
a player who pays more should get more. So the question for each unit is not "is it strong" but "is it as strong as
what it costs, compared with everything else"; and the yardstick for "everything else" is CA's own pricing of the
other thousand units, which is the largest body of balance decisions there is.

Lore is the second question, and it comes first in authority: what *should* this unit be? A hundred Temple Guard at
line quality is CA's convenience, not the Slann's bodyguard. Where the lore says a unit is something other than
what vanilla sells, the ladder (§5) says what, the solver makes it so, and the valuation then says what it is worth.

Two things follow. First, the measure of strength has to work across castes: a cannon battery, a giant, a chariot
squadron and a block of spearmen all have to land on one scale. Second, a unit that is off its price can be fixed two
ways, by moving its stats to what the price pays for or by moving its price to what the stats are worth, and which
is right depends on how much the price line for its caste can be trusted (§3).

## 2. The model (`unit_model.py`)

Everything is read from the vanilla database. The melee rules are the cavalry study's (hit chance 35 + attack −
defence clamped to 8–90 %; armour blocks a random 50–100 % of its value from base damage, armour-piercing ignores it;
bonus vs large against cavalry, monsters and monstrous infantry, bonus vs infantry against the rest; the charge
bonus on attack and damage for the opening blow, one charge every 30 s; ward and physical, magic, flame resistances;
splash; the weapon's own attack interval; permanent passives folded in). What the other castes needed:

| | |
|---|---|
| **entities** | the thing that fights and dies. Chariots and war machines: the vehicle (`num_engines`), whose HP is the health bar, with two crew striking on a chariot. A monster with a crew (a Stegadon, a Sky Lantern) is one entity. |
| **shields** | `missile_block_chance`, applied to half the shots (the front arc) |
| **missiles** | the unit's projectile or its engine's. Hit chance from calibration against the target: a block is hit unless the weapon is wild (rockets, mortars), a single entity with chance 2R / calibration. Explosions spread over the models in the radius with falloff (35 % of them, at most 15). Penetration through up to three ranks. Volley from projectiles × shots × burst, at most three shots a second. Ammunition worth nothing beyond a shooting window; longer range worth more volleys before contact. |
| **collision** | mass and charge speed against the target's mass, capped by the game's `collision_damage_maximum`, over the weapon's `collision_attack_max_targets` |
| **abilities** | breath attacks, dropped rocks and bound bolts (`unit_special_abilities` with a projectile or a bombardment): the projectile's damage per use, the uses a battle window affords (one plus the window over the recharge, capped by the number of uses), per entity where every entity fires it and once per unit otherwise. A Star Dragon's breath measures about as much damage as its bite; what it is worth is the valuation's question (§3). |
| **reference regiments** | five melee targets (Empire Knights, Halberdiers, Chaos Warriors, Spearmen, a Giant), three melee attackers, two missile attackers (Crossbowmen for base damage, Handgunners for armour-piercing) |

**Engagement.** The cavalry study measured one model against one model. That breaks the moment a giant is on the
table: one giant against one halberdier lasts twenty minutes; against a regiment, a fraction of that. So the model
fights regiment against regiment, with the attackers that can fight at once limited by the room around the
target: `reach` ranks lining the exposed half of the target regiment's footprint. A block of 120 swordsmen is fought
by about 40 halberdiers at once (a third of one per swordsman); a giant by about a dozen; a knight by two. This is
Lanchester's square law (everyone fights, numbers count twice) and linear law (a frontage decides) side by side,
without choosing between them: the geometry chooses, and `reach` is fitted from the prices (§3). Long monsters use
the geometric mean of their two axes, so a Dread Saurian is not a circle twelve metres across.

**Power.** For a regiment: offence = melee dps (geometric mean over the five targets) + `ranged` × missile dps +
`impact` × collision dps + `ability` × breath and bombardment dps; toughness = seconds the regiment lasts, blended between melee and missile attackers;
regiment power = √(offence × toughness), with the Empire Knights regiment = 1.00. Per model = regiment / entities
× 60, so a 60-model unit of Empire Knight quality reads 1.00 per model and an Empire Swordsman about 0.5.

**Identity.** A unit's shape is its matchup profile (how its damage divides between cavalry, halberdiers, heavy
infantry, light infantry and monsters), its shares of melee, missile and collision power, its base-to-AP and
charge-to-sustained ratios, and its offence-to-toughness ratio. `identity_drift` is 1 − cosine similarity of that
vector before and after a change. Over the 479 changed units the mean drift is 0.0001 and the maximum 0.007: every
unit fights the way it did.

## 3. The valuation (`rebalance_survey.py`)

CA sets the multiplayer price of each unit by hand and by testing; the multiplayer price is the balance price
(Tomb Kings pay 0 gold in campaign). A regression of log price on the measurements recovers what a point of power
is worth in their game (the revealed valuation):

    log price = a_caste + s_caste · log(regiment power) + b · log(entities) + Σ trait premiums

one line per caste, robust (Huber weights, iteratively reweighted least squares, so a few oddly priced units do not
pull the line). The composition weights inside power are chosen by coordinate descent to make the prices most
consistent: the valuation is the one under which CA's prices make the most sense.

| weight | value | meaning |
|---|---|---|
| ranged | 1.00 | a point of missile dps against a point of melee dps |
| impact | 0.50 | a point of collision dps |
| ability | 0.00 | a point of breath-attack or bombardment dps: measured, but on this scale the prices give it no premium (see below) |
| missile_tough | 0.30 | share of toughness that is toughness against missiles |
| range_exp | 0.50 | missile dps × (range / 150 m) ^ 0.5 |
| window | 240 s | shooting time a battle affords |
| reach | 2.0 | ranks of attackers that reach the exposed edge of a regiment |

The scale-defining weights (reach, impact, ranged, missile_tough, range_exp, window) were fitted once and are
**pinned**: the ladder's targets and every number here are on that scale, and a refit that moves reach or impact
moves the scale under them (an unpinned refit after the ability term was added preferred reach 6 and impact 8, a
marginally better fit, on which a Bloodthirster measures 1.3 instead of 2.2). Weights added since are fitted with
the scale held; the ability term came out at 0: given everything else the model sees, CA's prices show no premium
for a breath attack, which matches the multiplayer view that breaths are hard to use. `rebalance_survey.py
--refit-scale` unpins, and the ladder would then need re-anchoring.

| caste | price ∝ regiment power ^ | one Empire Knights regiment's worth of it costs |
|---|---|---|
| melee infantry | 0.79 | 510 |
| missile infantry | 0.57 | 554 |
| monstrous infantry | 0.53 | 669 |
| melee cavalry | 0.72 | 743 |
| missile cavalry | 0.56 | 683 |
| monstrous cavalry | 0.62 | 747 |
| war beast | 0.36 | 553 |
| monster | 0.37 | 913 |
| chariot | 0.41 | 762 |
| war machine | 0.30 | 968 |

Trait premiums: terror +12 %, fear +7 %, stalk +19 %, regiment of renown +14 %, each active ability +7 %, single
entity +10 %, unbreakable +5 %, price ∝ speed ^ 0.14; expendable −20 %, vanguard −7 %. Fit quality: a typical unit is
priced within ±18 % of its caste's line (robust σ 0.164, rms 0.200); the 5-fold cross-validated rms is 0.208, so
the fit is not memorising prices. Within each caste the line explains 58–89 % of the price variance.

**What the slopes say.** For infantry and cavalry the price tracks measured power nearly one to one: the model
understands those castes, and a unit off the line is a real finding. For monsters, war beasts, chariots and war
machines the line is flat (0.3–0.4): CA's prices spread a third as much as the measured power does. Either CA prices
those castes by feel or the model misses what they do (a chariot's real collision behaviour, a cannon's range on a
siege map, terror routing a block); both, probably. The pooled line through every caste (in the survey) puts the
same fact the other way round: the top of those castes is cheap for its measured power and the bottom dear.

## 4. The solver (`rebalance_solve.py`)

Three layers, in order of authority:

| layer | units | rule |
|---|---|---|
| **decided** | 4 | `tools/decided.py`: Reiksguard, Blazing Sun, Black Rose, Gryphites, written as decided |
| **lore** | 420 changed, 350 kept | cavalry: the study's `LORE` targets, carried over as a ratio over vanilla (the study measured "how much stronger than vanilla the lore wants this unit" on its own model; the ratio survives the change of scale), with its unit-size changes; everything else: `lore_ladder.LADDER` (§5). Units the study left ("ranged: not solved") go to the price layer; a Blessed Spawning keeps a ×1.25 edge over its base, as the study's regiments of renown do. |
| **price** | 55 | the residual against the caste's line, for units with no lore entry. Inside ±0.15 (one robust σ) nothing moves. Outside it: infantry and cavalry have their stats moved to what the price pays for, at most ×1.25 per pass, the rest to the price, at most ×1.25; monsters, war beasts, chariots and war machines have their price cut where they are over-priced and never raised. A unit asking for more than ×1.7 is **held for review** and left out of the pack. |

**Moving a unit.** Every change is a move along the unit's own ray: HP and every damage figure (melee base, AP,
bonus vs large, bonus vs infantry; the same four for the missile) scale by one factor k, attack and defence move
together by 9 · ln k, and nothing else changes. Charge bonus, armour, speed, mass, size, shield, resistances,
abilities, weapon type, splash and attack interval are the unit's shape and stay. The solver bisects k until the
regiment reaches its target. The pack is written as deltas and factors against the vanilla rows, never as the
model's absolute figures (the model folds permanent passives into its card: Swords of Ulric read 44 attack where
the database says 34), once per land unit (several main units can share one), with a copy of the weapon carrying
the vanilla damage times k (weapons are shared between units; a shared row is never edited), the same for the
projectile and for every alternate ammunition the unit carries.

**Pricing a lore change.** Where the caste's line is trusted (infantry, cavalry) the price becomes what the
valuation says the new unit is worth, within ×1.6 of vanilla: a unit that was a bargain and is now stronger pays
for both, unless the entry holds the price (Chosen, Daemonettes: the community says they are dear already). In the
flat-priced castes the price follows the power along the caste's line with the residual corrected up to ×1.25, but
never ends above vanilla: a "bargain" there is the model over-rating a unit whose weakness is behaviour it cannot
see (accuracy, mobility, breath in melee, crumbling), so a stronger Great Eagle stays at 750, while a Bloodthirster
×1.7 stronger that was over-priced ends near its old price. The price layer in those castes only ever cuts.
[COMMUNITY_RESEARCH.md](COMMUNITY_RESEARCH.md) is where that rule came from.

## 5. The lore ladder (`lore_ladder.py`)

Rated directly on the model's per-model scale, with vanilla anchors that already sit where the lore puts them:

| tier | per model | anchors |
|---|---|---|
| rabble | 0.10–0.30 | Zombies 0.15, Skavenslaves 0.14, Peasant Mob 0.17, Skeleton Warriors 0.25, Gnoblars 0.25 |
| levy | 0.30–0.45 | Empire Spearmen 0.31/0.39, Men-at-Arms 0.4, Night Goblins 0.38, Clanrats 0.28 |
| line | 0.45–0.75 | Swordsmen 0.49, Halberdiers 0.52, Marauders 0.5, Orc Boyz 0.51, Dreadspears 0.45 |
| veteran | 0.75–1.40 | Dwarf Warriors 0.85, Longbeards 1.2, Saurus 1.1, Chaos Warriors 1.1, Bestigors 1.4 |
| elite | 1.40–3.00 | Black Orcs 1.75, Hammerers 2.2, Ironbreakers 2.4, Chosen 2.9, Tzar Guard 1.8 |
| champion | 3.00+ | Skullreapers 3.3 (60), Depth Guard 2.7 (60), Wrathmongers 7.3 (32), Aspiring Champions 14 (16) |
| monstrous | 3–15 | Trolls 6.4, Minotaurs 10–12, Kroxigor 9, Ironguts 9.7 (16 each) |
| monsters | regiment 1–5 | Giant 2.9, Stegadon 3.5, Treeman 4.1, Star Dragon 3.1 vanilla; rated as whole regiments |

An entry names a family by key pattern and says where its plain member should sit; weapon variants, marks and
regiments of renown keep their vanilla ratio to it, so a family moves together. A size means the lore insists on
fewer, better models. Two kinds of entry the cavalry study did not need: **keep** (the vanilla unit is the lore and
so is its price: chaff is cheap because it is fodder, snipers are dear for what the model cannot see) and **as
vanilla, priced fairly** (the stats are the lore, the price is not).

The judgments that matter most:

- **Guards become guards.** Temple Guard, Phoenix Guard, Swordmasters and the Black Guard of Naggarond go to 80
  models at Chosen-class quality (2.5–2.8 per model); Sisters of Avelorn to 60. Temple Guard: 100 → 80, 36/38 →
  40/42, 107 → 161 HP, a 13+29 halberd → 20+44, 1200 → 1250 gold.
- **Chaos Warriors are worth three state troops**, not two: ×1.33, 750 → 925. Chosen ×1.2 above them at the same 1250.
- **The heavy dead**: Grave Guard and Tomb Guard from levies in plate to S4 T4 killing-blow veterans (×1.4).
- **Elves fight like elves**: White Lions ×1.5, Wardancers ×1.5, Eternal Guard ×1.4, Executioners ×1.5.
- **Orcs are tougher than men**: Orc Boyz ×1.2, Big 'Uns ×1.15.
- **Daemons**: Bloodletters ×1.4 (a hellblade kills on a touch; T3 W1 is the price), Exalted Bloodletters only ×1.15
  (campaign players already call them the strongest infantry in the game), Daemonettes and Plaguebearers ×1.15.
- **Ogre Bulls are ogres**: ×1.35, so a Bull is half an Irongut, not a third.
- **The great beasts the lore is unambiguous about**: Bloodthirster ×1.7 (a match for a Star Dragon, not below a
  Giant), Dread Saurian ×1.6, Hell Pit Abomination ×1.7, Carnosaur ×1.4, War Hydra ×1.5, Stonehorn ×1.6, Shaggoth
  ×1.4, Keeper of Secrets ×1.5, Great Unclean One ×1.3, Star Dragon ×1.25, Manticore ×1.4, Great Eagle ×1.3.
- **Kept on purpose** (350 units): every chaff unit, every sniper and every weapon the model over-counts
  (Irondrakes, warpfire, poisoned wind, grenades), most missile troops, the trolls, and the model's blind spots
  the community named (Thundertusk, Sky Lantern, Brood Horror, Beast of Nurgle, bats, the elf bolt throwers,
  Wrathmongers). Centigors are kept pending a decision: the cavalry study wants them at elite, the multiplayer
  list has called them overperformers since 6.3. Squig Hoppers and Pegasus Knights are kept because the study's
  model and this one disagree about their vanilla standing by a factor of two, and a ratio carried across that
  disagreement would move them the wrong way. Kislev's Kossars, Streltsi and Akshina take the community's
  price cuts instead, since the model over-rates hybrids.

The ladder is the part of this work that is judgment, not measurement. It is one line per family in
`lore_ladder.py`, and it is meant to be corrected.

## 6. The outcome (`reports/proposals.md`)

| | units |
|---|---|
| lore (changed) | 420 |
| lore (kept as vanilla, on purpose) | 350 |
| price layer: price only | 46 |
| price layer: stats and price | 9 |
| decided | 4 |
| held for review, out of the pack | 0 |
| **changed** | **479 of 1,042; 479 in the pack** |

Stat factors run from ×0.59 to ×2.11 (median ×1.18); prices from −35 % to +61 % (median +11 %). Thirteen units
change size. The flat-priced castes are no longer pushed toward zero residual on purpose (their "bargains" are
left alone), so their factions keep a small negative mean; the infantry and cavalry factions sit within ±0.06.

Landmarks (multiplayer price):

| unit | before | after |
|---|---|---|
| Temple Guard | 100, 36/38, 107 HP, 13+29 vL+16, 1200 | 80, 40/42, 161 HP, 20+44 vL+24, 1250 |
| Black Guard of Naggarond | 100, 36/48, 90 HP, 1300 | 80, 40/52, 137 HP, 1325 |
| Phoenix Guard | 100, 46/52, 84 HP, 1300 | 80, 48/54, 105 HP, 1400 |
| Chaos Warriors | 36/44, 90 HP, 26+10, 750 | 38/46, 111 HP, 32+12, 925 |
| Chosen | 46/60, 131 HP, 34+14, 1250 | 47/61, 155 HP, 40+17, 1250 |
| Greatswords | 32/30, 76 HP, 10+25 vI+14, 850 | 34/32, 90 HP, 12+30 vI+17, 800 |
| Grail Knights (study) | 48, 38/34, 152 HP, 1850 | 32, 41/37, 219 HP, 1750 |
| Blood Knights (study) | 60, 42/42, 120 HP, 1650 | 24, 47/47, 217 HP, 1625 |
| Bloodthirster | 60/44, 7,732 HP, 128+304 vL+35, 2000 | 64/48, 12,277 HP, 203+483 vL+56, 1950 |
| Dread Saurian | 57/32, 15,000 HP, 3100 | 61/36, 22,294 HP, 2950 |
| War Hydra | 52/32, 10,400 HP, 1550 | 55/35, 15,057 HP, 1625 |
| Zombies, Skavenslaves, Peasant Mob | | kept: fodder, priced as fodder |
| Empire Knights, Saurus, Ironbreakers, Kislev | | kept: vanilla is the lore |

## 7. A second opinion (`rebalance_verify.py`)

The regiment simulator from the cavalry study (`cavalry_sim.py`: abilities, fatigue, morale, crumbling, second by
second) is a different model. Equal-gold duels, vanilla against vanilla and rebalanced against rebalanced:

| A | B (scaled to A's gold) | vanilla | rebalanced |
|---|---|---|---|
| Temple Guard | Chaos Warriors | Chaos Warriors, 57 % left | Temple Guard, 28 % left |
| Phoenix Guard | Black Guard | Phoenix Guard, 35 % left | Phoenix Guard, 41 % left |
| Chaos Warriors | Longbeards | Chaos Warriors, 53 % left | Chaos Warriors, 75 % left |
| Greatswords | Chaos Warriors | Chaos Warriors, 32 % left | Greatswords, 52 % left |
| Chosen | Ironbreakers | Chosen, 67 % left | Chosen, 85 % left (held at 1250) |
| Bloodthirster | Giant | Giant, 21 % left | Bloodthirster, 46 % left |
| Dread Saurian | Star Dragon | Dread Saurian, 21 % left | Dread Saurian, 62 % left |
| Grail Knights | Chaos Knights | Chaos Knights, 57 % left | Chaos Knights, 63 % left |
| Blood Knights | Demigryph Knights | Demigryphs, 38 % left | Demigryphs, 76 % left |
| Swordsmen | Clanrats | Clanrats, 53 % left | Clanrats, 69 % left |
| Empire Knights | Silver Helms | Silver Helms, 44 % left | unchanged |

It agrees on direction wherever the ladder raised a unit in place, and disagrees on the study's fewer-but-better
regiments (Grail Knights, Blood Knights): the simulator assumes everyone fights at once (the square law), under
which 24 vampires against 32 demigryphs are simply outnumbered, while the frontage model says the demigryphs cannot
all reach them. The truth is between the two and only a battle in the game decides it. The Greatswords flip is why
the price layer's per-pass cap is ×1.25 and not more.

`rebalance_verify.py --sweep` fights every changed unit against its caste's reference at equal gold, vanilla and
rebalanced, and lists the largest swings. Of 460 units, 19 flip from losing clearly to winning clearly. They are of
three kinds, and none is a build error: single entities (Ghorgon, Hell Pit Abomination, Bloodthirster, Dread
Saurian, Necrosphinx, Zoats), where the simulator's square law turns a ×1.5 into a rout of two Giants and the frontage
model is the one to trust; the study's smaller regiments (Blood Knights); and units whose price rose because they
were bargains (Skeleton Horsemen, Spearmen), which is the valuation doing its job. The sweep is a diagnostic, not a
verdict: a rout in the simulator is binary, so a small change can flip it.

## 8. Decisions

- **Lore first, then price.** A ladder entry outranks the residual; the residual outranks nothing but silence.
- **Judge each unit against its own caste.** A monster is compared with monsters.
- **Stats for the castes the model understands, price for the rest.** Slopes above 0.5: infantry and cavalry.
- **One robust sigma is balanced.** ±0.15 on the residual, about ±16 % on the price.
- **Caps per pass** on the price layer, ×1.25 on power and on price; the remainder reported, not applied.
- **Held for review**: a unit asking for more than ×1.7 with no lore entry stays out of the pack.
- **The armour ceiling stands** (plate 120 for mortal knights, 125 for demigryph riders); the solver never touches armour.
- **The cavalry study's ladder stands**; the four hand-set Empire knights are written from `decided.py`.
- **Families move together**; a regiment of renown keeps its vanilla edge over its base unit.
- **Identity is a ray**, and drift is measured and reported for every change.

## 9. What the model cannot see

Healing and spells (an active ability without a projectile is +7 % and no more; breath attacks and bombardments are
measured since 2026-09-16); poison and other contact effects;
the Luminark's beam and the Solar Engine's hits are modelled as artillery and probably over-counted; accuracy
against moving targets; a chariot's real collision behaviour and cycle charging; a cannon's value on a siege map;
terror routing a block before the fight; formations; who a sniper aims at; animations, which no database model
sees. Every one of these shows up as a residual. The ladder's **keep** entries are where they pile up on purpose:
chaff, snipers, explosion and poison weapons, weapon teams. The two units the price layer once held (the Bull
Centaur Renders of renown, the Amethyst Outriders, both shooting cavalry the model rates far above their price) are
kept as vanilla by the ladder now.

## 10. Running it

See [TOOLS.md](TOOLS.md).

## 11. Next

See the open items in [TOOLS.md](TOOLS.md).
