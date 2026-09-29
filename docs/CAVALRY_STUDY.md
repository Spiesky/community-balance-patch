# A lore-first rebalance of every cavalry unit

A thought experiment and the source of the patch's cavalry targets. What would Total War: WARHAMMER III's cavalry look
like if every unit were as strong as the lore says it is: Grail Knights who have drunk from the Grail,
Blood Dragons who are vampires to the last rider, Archaon's Swords of Chaos?

- **This file:** the model, the lore ladder, the headline changes, the hypothetical units.
- **`reports/cavalry_study.md`:** every recruitable cavalry, missile cavalry and monstrous cavalry unit
  (177), faction by faction. For each: a full combat profile, then the lore proposal. Plus 10 hypothetical units.
- **`tools/cavalry_model.py`:** the combat model. **`cavalry_rebalance.py`:** the lore table and the
  generator.

---

## 1. The model

Everything comes from the game database (vanilla).

### What a unit card holds

| | |
|---|---|
| size and price | men, recruitment cost, upkeep |
| fighting stats | melee attack, melee defence, charge bonus, leadership |
| body | HP per model (rider + mount + bonus HP, which matches the in-game health bar exactly), armour, **mass**, **speed**, entity size |
| protection | **ward save**, **physical**, **magic**, **missile** and **flame** resistance (flame weakness counts as negative) |
| melee weapon | base damage, armour-piercing damage, **bonus vs large**, **bonus vs infantry**, **splash** (target size, max targets, power multiplier), **magical**, **flaming**, attack interval |
| missile weapon | damage, AP, bonus vs large/infantry, projectiles × shots per volley × burst, reload, range, ammunition |
| permanent passives | folded in: Blessing of the Lady (15% ward), Martial Prowess, Hellblade, regeneration's flame weakness |

### How damage is worked out

| rule | |
|---|---|
| hit chance | 35 + attack − defence, between 8% and 90% |
| **bonuses** | **bonus vs large is added to base damage against large targets** (cavalry, monsters, monstrous infantry); **bonus vs infantry against everything else**. A lance's bonus vs large does nothing against halberdiers; a greatsword's bonus vs infantry does nothing against knights. |
| charge | the charge bonus adds to attack and to damage (split between base and AP); counted as one charge every 30 seconds on top of sustained melee (cycle charging) |
| armour | blocks a random 50–100% of its value (as a percentage) of base damage; AP ignores it |
| resistance | ward always; physical resistance against non-magical attacks, magic resistance against magical ones; flame resistance against flaming ones. Capped at 90%. |
| splash | if the target is small enough, a blow is spread over several models; total damage × the splash power multiplier |
| speed of attack | the weapon's own attack interval (Empire Knights 5.1 s, Mournfang 3.2 s) |

### The opponents: real vanilla units

Damage per second is measured against **Empire Knights** (cavalry), **Empire Halberdiers** (anti-large
infantry), **Chaos Warriors** (heavy infantry), **Empire Spearmen** (light infantry) and a **Giant** (monster).
Survival time is measured against Empire Knights, Halberdiers and Chaos Warriors. So a lance unit, a
greatsword unit and a monster each show where they are strong and where they are weak.

**Power per model** = √(offence × toughness), each the geometric mean over those opponents, relative to
**Empire Knights = 1.00**. **Value** = men × power per 1000 gold.

**Proposals** keep each unit's role and weapon. A solver moves attack and defence first (up to 15 points),
then HP and every damage figure together, bonuses included, until the unit reaches its lore target. Unit
size changes only where the lore insists on rarity. Prices scale from each unit's vanilla price by the
change in total power, with a small premium for quality (power per model to the 1.25), so CA's premiums
for flight, mass, magic and ranged attacks carry over.

### What it still does not see

Mass and knock-back are listed but not simulated, and neither are speed, flight, leadership and fear,
fatigue, formations, active abilities, regeneration's healing, or ranged power in the power figure
(missile cavalry gets its ranged damage profiled but no proposal). Splash is read as "total damage ×
multiplier"; a few vanilla values look odd under that reading (Rot Knights splash infantry at ×0.4).
Tabletop profiles quoted below are from memory of the 6th–8th edition army books and are approximate.

---

## 2. Bonuses vs large and vs infantry

The model counts each bonus only against the targets it applies to.

**Built to fight large targets.** Lances and halberds with bonus vs large gain against cavalry and
monsters and nothing against infantry: Blood Knights (lances) +22, the Royal Altdorf Gryphites and
Demigryph halberds +25, Grail Knights +18, Knights of the Realm +12. On a 30–50 damage weapon that is a
40–70% boost against the right target.

**Built to fight infantry.** Bloodcrushers and dual-axe Bull Centaurs +18, sword-and-shield Blood Knights +16,
The Things in the Woods +16, Kurgan Horsemen (dual weapons) +15, Black Knights +12.

**In the proposals** every damage figure scales together, so a unit keeps its role: an anti-large unit
stays anti-large, only stronger or weaker. The profile tables in the data file show each unit's damage
against all five opponents side by side.

---

## 3. The lore ladder

Targets sit on the game's own measured scale, anchored on units whose vanilla place already fits the lore.

| tier | power per model | what it is | tabletop feel | anchors (target) |
|---|---|---|---|---|
| **Rabble** | 0.5–0.9 | goblins, peasants, skeletons, squigs | WS2–3 | Wolf Riders 0.49, Yeomen 0.58 |
| **Light** | 0.65–1.25 | raiders and horse archers | WS3–4 S3 | Marauder Horsemen 0.82, Ellyrian Reavers 0.86 |
| **Line** | 0.95–1.7 | the knightly rank and file | WS4 S3 T3 | **Empire Knights 1.0**, Knights of the Realm 1.27, Silver Helms 1.22 |
| **Elite** | 1.5–2.7 | orders, princes, the best mortal cavalry | WS4–5 S3–4 | Reiksguard 1.78, Questing 1.95, Dragon Princes 2.44, Cold One Knights 2.69 |
| **Champion** | 3–13.5 | more than mortal: chosen of the gods, the Grail, the undead | WS5+ S4–5 A2 | Chaos Knights 3.09, **Grail Knights 4.64**, **Grail Guardians 6.13**, **Blood Knights 6.86**, **Swords of Chaos 13.5** |
| **Monstrous** | 2.5–10 | riders on monsters | T4–5 W3+ | Demigryphs 3.32, Gryphites 4.26, Skullcrushers 6.13, Mournfang 7.22, Crushers 10.1 |

Regiments of renown stand 35% above their base unit.

---

## 4. The champion tier

| unit | vanilla | power | lore target | proposal |
|---|---|---|---|---|
| **Swords of Chaos** (Archaon's retinue) | 24 riders, 52/61, 328 HP, 24+56 flaming, 1500 | 7.56 | **13.48** | **16 riders**, **66/75**, **496 HP**, **36+85** flaming, ~2075 |
| **Blood Knights** (lances) | 60, 42/42, 120 HP, 35+19 vL+22, 1700 | 2.06 | **6.86** | **24 vampires**, 57/57, **291 HP**, **85+45 vL+53**, ~3075 |
| **Blood Knights** (sword & shield) | 60, 46/54, 120 HP, 38+21 vI+16, 1600 | 2.95 | **6.86** | **24**, 61/69, 217 HP, 70+38 vI+29, ~1825 † |
| **Grail Guardians** | 32, 42/58, 252 HP, 24+36 splash, magical, 1900 | 5.38 | **6.13** | **24**, 45/61, 267 HP, 25+38, ~1675 |
| **Grail Knights** | 48, 38/34, 152 HP, 18+28 vL+18 splash, magical, 1850 | 2.44 | **4.64** | **32**, **51/47**, **223 HP**, 26+41 vL+26, ~2725 |
| **Doom Knights** | 24, 44/36, 245 HP, 56+24 splash, magical, 1600 | 3.28 | **3.87** | 24, 48/40, 267 HP, 61+26, ~2000 |
| **Chaos Knights** (swords) | 60, 42/50, 135 HP, 37+16, 1400 | 2.42 | **3.09** | 60, 46/54, 152 HP, 42+18, ~1900 |
| **Chaos Knights** (lances) | 60, 42/38, 135 HP, 36+17, 1500 | 2.05 | **3.09** | 60, 50/46, 176 HP, 47+22, ~2275 |

† Prices scale from each unit's vanilla gold per power. Vanilla prices sword-and-shield Blood Knights low
for their stats, so theirs comes out low too; one champion price scale would put both near 3000.

**The Swords of Chaos.** Archaon's own knights, who ride with the Everchosen himself. Very few are
admitted, and each has survived the gods' favour for lifetimes; their Apocalyptic Charge breaks armies.
Vanilla already makes them the strongest mortal cavalry (7.56). The proposal goes further: **16 riders,
each nearly twice as strong as now**, the pinnacle of mortal cavalry, above Grail Guardians and Blood
Knights. Only a legendary lord should outfight one.

**Blood Knights.** The largest gap in the game. Every rider of the Blood Dragon order is a vampire
(around WS5 S5 T5 W2 A2 on the tabletop), frenzied, in plate, on a nightmare steed. Vanilla gives them the
HP of a mortal knight and 60 of them. The proposal: **24 vampires, each worth more than three vanilla
Blood Knights**, and their lances' bonus vs large grows with them (+53).

**Grail Knights.** They have completed the Grail Quest and drunk from the Lady's cup: more than mortal,
the finest knights of the Old World. Vanilla rates them at 2.44, **barely above Questing Knights (1.95) and
well below their own Grail Guardians (5.38)**. The proposal: 32 knights at 4.64 each.

**Chaos Knights.** The most favoured warriors of the gods (WS5 S5 T4 A2). Vanilla is near the lore; the
proposal lifts them about a quarter. The lance variants gain most, because their charge is only partly
counted.

---

## 5. Hypothetical units

Built on a vanilla template with lore changes, then solved to a target. The marks of Chaos keep their own
attack and defence profile; only HP and damage are solved.

| unit | template | target | proposal | the idea |
|---|---|---|---|---|
| **Chosen Chaos Knights** | Chaos Knights | 4.20 | 32 riders, 48/56, 204 HP, 56+24, ~1500 | the Chosen of the Chaos Knights: fewer, far deadlier |
| **Chosen Knights of Khorne** | Chaos Knights | 4.40 | 32, **54**/50, 223 HP, 61+26 **vI+20**, magic resist 35%, frenzy, ~1600 | the gift goes into the blade |
| **Chosen Knights of Nurgle** | Chaos Knights | 4.40 | 32, 44/**58**, 197 HP, **physical resist 15%**, flame weakness, ~1600 | bloated and near unkillable |
| **Chosen Knights of Slaanesh** | Chaos Knights | 4.20 | 32, 46/**62**, 186 HP, faster, devastating flanker, ~1500 | first into the fight, impossible to pin |
| **Chosen Knights of Tzeentch** | Chaos Knights | 4.20 | 32, 46/54, 192 HP, **ward 15%**, **magical attacks**, ~1475 | warded by sorcery |
| **Knights Panther** | Reiksguard | 1.75 | 60, 39/36, 134 HP, ~1450 | the great secular order of the Araby crusades |
| **White Wolves** | Empire Knights | 1.80 | 60, 33/37, 132 HP, **cavalry hammers 17+37 vI+10**, frenzy, ~1800 | Ulric's templars: no lances, hammers and fury |

---

## 6. The biggest mismatches elsewhere

**Under the lore:**

| unit | power | target | |
|---|---|---|---|
| Slaanesh's Harvesters (Dark Elf renown) | 1.40 | 3.19 | a renowned unit weaker than plain Cold One Knights |
| Razorgor Herd | 1.35 | 2.69 | great tusked monsters rated like elite horsemen |
| Rot Knights | 2.95 | 5.02 | Nurgle's chosen on rot flies, below Demigryph Knights |
| Bloodcrushers (renown) | 4.15 | 7.28 | |
| Cold One Knights (swords) | 1.61 | 2.69 | WS5 S4 riders on T4 cold ones |
| Wild Riders | 1.21 | 1.87 | frenzied hunters of Kurnous, rated near Empire Knights |
| Centigors | 0.76 | 1.18 | T4 S4 half-beasts rated like light horse |

**Over the lore:**

| unit | power | target | |
|---|---|---|---|
| Nehekharan Horsemen (renown) | 2.05 | 1.17 | skeleton horsemen above Reiksguard |
| Damned Knights (Mousillon) | 1.39–1.83 | 0.95–1.27 | undead copies stronger than the living Bretonnians they copy |
| Pleasureseekers | 3.54 | 2.36 | daemonettes are deadly but thin-skinned |
| Kurgan Horsemen | 1.11–1.15 | 0.82 | light raiders rated above Empire Knights |
| Ripperdactyl Riders | 5.89 | 4.64 | skinks on ripperdactyls |

---

## 7. Regenerating

    cd tools && python3 cavalry_rebalance.py

Edit `LORE` (pattern, target, tier, unit size, lore note) or `HYPOTHETICAL` (template, changes, target) at the
top of the script. `cavalry_model.py` holds the combat rules and reference opponents.
