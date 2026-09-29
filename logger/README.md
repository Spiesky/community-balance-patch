# Battle Logger

The optional Battle Logger add-on is two scripts: `cbp_battle_logger.lua` (`script/battle/mod/` in the pack) logs battles you fight, and `cbp_autoresolve_logger.lua` (`script/campaign/mod/`) logs your own auto-resolved battles (strength of each unit before and after; single player only). It is here so anyone can read exactly what it records. At the end of each battle it appends a few lines to `cbp_battle_log.txt` in the game folder; nothing is sent anywhere.

To sum up shared logs: `python3 tools/battle_logs.py log1.txt log2.txt ...`
