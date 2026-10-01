# Release notes

One entry per Workshop upload of the patch. What each release changes unit by unit is in `reports/beta_changelog.md`
at that release's tag (tags start with 0.2.0). The Battle Logger has its own notes at the end.

## 0.2.0 (1 October 2026)

Built for game version 9.0.

New in the pack:

- **Elite infantry is worth its price.** Infantry the lore rates elite (Greatswords, Bestigors, Slayers, Ironbreakers,
  Infernal Ironsworn, Exalted Bloodletters, Exalted Plaguebearers, Exalted Daemonettes, Wildwood Rangers and others)
  gets more health and damage, up to about 17%, and a point or two of attack and defence, at the vanilla price.
- **The multiplayer community's balance list** (Total Tavern and Vermin League, patch 7.1+), as written, minus what CA
  did in 8.1 and minus five entries held for campaign. Where the list changes a unit and does not mention its regiment
  of renown, the regiment takes the same changes. It includes more responsive artillery, and a few nerfs written for
  multiplayer: Zombies +25 gold, Skeleton Horse Archers +25, Ruglud's Armoured Orcs +50, Wrathmongers -4 melee defence
  and -5 leadership, Gor Herd -1 weapon damage and -1 armour-piercing.
- **The version is in the pack** (`cbp_version`), so a battle log says which build it was fought with.

Changed since 0.1:

- **Lore elites charge like what they are.** Their charge bonus now scales with their damage (Blood Knights 53 to 132,
  Grail Knights 75 to 112). In 0.1 a rider hit two and a half times as hard and charged no harder than before.
- **Lore elites are priced on strength they can use.** A blow that does more damage than its target has hit points
  was counted in full. With that taken out, and with units CA prices together moving together: Blood Knights 2025
  (0.1: 2475), Blood Knights with lances 2150 (0.1: 2250, and now dearer than sword and shield again, as in vanilla),
  Grail Knights 1875 (1850), Grail Guardians 1875 (2225). The Swords of Chaos stay at 2400, up from 1500 in vanilla:
  they are nearly twice the unit.
- **Gunpowder: less ammunition, vanilla prices.** In 0.1 the heavier volley came with vanilla ammunition, so every gun
  did 60% more damage per battle, and prices rose by 25 to 125 gold. Now ammunition is cut to 1/1.6 (Handgunners 22 to
  14 volleys): about the same damage over a battle as vanilla, in bigger, rarer volleys, at the vanilla price. Deck
  Droppers with pistols and handguns are now covered too.

Not in the pack, on purpose: auto-resolve. A draft of this build carried auto-resolve rules; they are now a separate
test pack (`docs/AUTORESOLVE.md`) until they have been tested against vanilla.

Proposed and built by Spiesky; the community list is the Total Tavern and Vermin League communities' work. Tested in
game by: nobody yet.

## 0.1 (30 September 2026)

"Public beta 1: lore elites and gunpowder". 43 units: Blood Knights (both), Grail Knights, Grail Guardians and the
Swords of Chaos fewer and far stronger; 38 gunpowder units with a 60% heavier volley and a 50% longer reload.

## Battle Logger

- **2** (1 October 2026): hit points left for every unit, the winner, the battle type, whether a unit ever
  routed, ammunition, and the patch version; a campaign record for every battle the player fights or auto-resolves
  (turn, difficulty, strength before and after, experience). `docs/LOG_FORMAT.md` has every field. Checked against mock
  game objects, not yet in the game.
- **1** (30 September 2026): models at the start and end, kills and routing for fought battles; strength before and
  after for auto-resolved battles.
