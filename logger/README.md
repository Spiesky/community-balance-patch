# Battle Logger

The optional Battle Logger add-on is two scripts. It is here so anyone can read exactly what it records. After each battle it appends a few lines to `cbp_battle_log.txt` in the game folder; nothing is sent anywhere. The format is in [docs/LOG_FORMAT.md](../docs/LOG_FORMAT.md).

`cbp_battle_logger.lua` (`script/battle/mod/` in the pack) logs the battles you fight, campaign or custom. For the battle: the date and time, its type, whether it came from a campaign, which side you were on, who won, how long it lasted. Battles fought in multiplayer are logged too, with both players' units. For each unit: models at the start and at the end, kills, the fraction of its hit points left (the loss measure that also works for lords, heroes and monsters), ammunition left and at the start, whether it is the general, whether it was routing or shattered at the end, and whether it was seen routing at any time during the battle (it looks every 10 seconds) and when.

`cbp_autoresolve_logger.lua` (`script/campaign/mod/`) logs the campaign's view of every battle you take part in, fought or auto-resolved, single player only. For the battle: fought or auto-resolved, who won, turn, difficulty, battle type, ambush, night, settlement, quest battle, campaign. For each unit on both sides: strength in percent before and after, experience level, faction. Nothing is written for battles between AI factions, for a battle that was not fought (retreat, maintain siege), or in multiplayer campaigns.

Both write which Community Balance Patch version was loaded (`none` without the patch) and the names of the mod packs in use: names only, never folder paths. No Steam name, nothing personal.

Both only read the game. The one thing they set is two notes of their own in the game's script memory, kept between campaign and battle: the unit ids with their strength and experience level before the battle, and one flag saying a battle was loaded. They are gone when the game closes and are never saved. Every game call is wrapped, so a failure can never affect a battle or a campaign: a value the game does not give is written as `?`, and anything else that goes wrong becomes one `#error` line in the log.

To sum up shared logs: `python3 tools/battle_logs.py log1.txt log2.txt ...`

To test the scripts outside the game, against mock game objects in Lua 5.1: `python3 logger/tests/run_mock.py` (needs `pip install lupa`).
