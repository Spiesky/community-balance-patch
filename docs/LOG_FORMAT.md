# The battle log format

`cbp_battle_log.txt` is written by the Battle Logger add-on into the game folder. It is plain text, append-only,
one record per line, fields separated by `;`. This page is the contract between the logger (`logger/*.lua`), the
upload page (`docs/index.html`) and the tools (`tools/battle_logs.py`, `tools/autoresolve_calibrate.py`).

## Rules for every version

- A block starts with a header line beginning with `#` and ends with `#end`. Header fields after the block name and
  the version are `key=value` (except the date, which is the third field).
- **New fields are only ever appended.** Parsers must accept extra trailing fields and unknown `key=value` pairs, and
  must skip line types they do not know.
- The third header field is the local date and time, to the minute.
- A value never contains `;` or `|` (the logger replaces them with `,`), so a line always splits cleanly.
- A value the game could not give is written as `?`. Parsers treat `?` as missing, never as a number.
- `mods=` is always the **last** header field: the enabled pack names joined with `|`, names only, never paths
  (`none` when no mods, `unknown` when the list could not be read).
- Lines starting with `#error;` or `#debug;` are diagnostics (`#error;v2;<where>;<message>`, with folder paths removed
  from the message). Parsers skip them; they are never sent by the upload page.
- The first line of a new file is a `# Community Balance Patch Battle Logger...` comment with the share link.

## Version 2 (logger 2, current)

### `#battle`: a battle the player fought (written by the battle script when the battle ends)

    #battle;v2;2026-10-02 21:14;campaign=1;type=land_normal;multiplayer=0;siege=0;player=1;attacker=1;winner=1;secs=612;cbp=0.2.0;mods=a.pack|b.pack
    u;1;1;1;wh_main_emp_inf_swordsmen;120;87;64;0;0;0.713;0;0;0;0;?;17
    ...
    #end

Header fields:

| field | meaning |
|---|---|
| `campaign` | `1` if the battle was launched from a campaign, `0` for custom, quick and multiplayer lobby battles |
| `type` | the game's battle type (`land_normal`, `land_ambush`, `settlement_standard`, ...) |
| `multiplayer`, `siege` | as in version 1 |
| `player` | the player's alliance number (1 or 2) |
| `attacker` | `1` if the player is the attacker |
| `winner` | the winning alliance number, `0` for no winner (draw, quit) |
| `secs` | length of the fighting in seconds, counted from the end of deployment |
| `cbp` | the Community Balance Patch version loaded (`0.2.0`); `none` if the patch is not loaded or is the first beta (0.1), which carries no version |

Unit line: `u;alliance;army;player;unit_key;initial_men;men_alive;kills;routing;shattered` (the ten fields of
version 1, unchanged) followed by:

| # | field | meaning |
|---|---|---|
| 11 | `hp` | fraction of the unit's hit points left, 0 to 1, three decimals. **The loss measure for every unit, including single entities.** |
| 12 | `ammo` | ammunition left (`0` for a unit that carries none) |
| 13 | `ammo_start` | ammunition at the start |
| 14 | `general` | `1` if this is the army's commanding unit |
| 15 | `ever_routed` | `1` if the unit was seen routing at any time during the fighting (it is looked at every 10 seconds, and once more when the battle ends), `0` if never, `?` if the logger could not watch (no deployment phase seen, or the watcher failed) |
| 16 | `first_rout_s` | second of the fighting at which it was first seen routing, `?` if never |
| 17 | `uid` | the unit's id within the battle (stable within one battle only), `?` if the game did not give one |

`player` on a unit line is `1` for units of the player's alliance. `routing` and `shattered` are the state when the
battle ended; at that moment nearly every unit of the losing side is routing, so **use `ever_routed` together with
`winner` for anything about morale**.

### `#result`: the campaign's view of a battle the player took part in (written by the campaign script after the battle)

Written for **every** player battle in single-player campaigns, fought or auto-resolved.

    #result;v2;2026-10-02 21:15;mode=fought;winner=attacker;turn=37;difficulty=hard;type=land_normal;ambush=0;night=0;settlement=0;quest=;campaign=main_warhammer;player_side=1;cbp=0.2.0;mods=a.pack|b.pack
    r;1;1;1;wh_main_emp_inf_swordsmen;100;72.5;3;wh_main_emp_empire
    ...
    #end

| field | meaning |
|---|---|
| `mode` | `fought` or `auto` (auto-resolved) |
| `winner` | `attacker`, `defender`, `draw`, or `?` if the game said none of the three |
| `turn` | campaign turn number |
| `difficulty` | campaign difficulty (`easy`, `normal`, `hard`, `very hard`, `legendary`) |
| `type`, `ambush`, `night` | the pending battle's type and flags |
| `settlement` | `1` if the battle is over a settlement |
| `quest` | the set-piece battle key for quest battles, empty otherwise |
| `campaign` | the campaign's name (`main_warhammer` is Immortal Empires) |
| `player_side` | `1` if the player attacked, `2` if the player defended |

Unit line: `r;side;army;player;unit_key;strength_before;strength_after;xp;faction`

| field | meaning |
|---|---|
| `side` | `1` attacker, `2` defender |
| `army` | index of the army on that side (1 is the main army, 2 and up are reinforcements) |
| `player` | `1` if the unit belongs to a human player |
| `strength_before`, `strength_after` | percent of full strength before and after the battle, at most two decimals; a destroyed unit is `0` |
| `xp` | experience level (chevrons) before the battle, 0 to 9 |
| `faction` | the faction key of the unit's army |

Unit lines are ordered attackers first, then defenders, the main army before reinforcements. For a fought battle the
game's campaign script is unloaded while the battle runs, so `strength_before` and `xp` are carried across in the
game's script memory; if that did not survive, or does not list the same units the game's own record of the battle
does, they are `?`. They are also `?` when the before-battle reading failed.

Not written: battles between AI factions, a battle that was not fought (retreat, maintain siege, declined), anything
in a multiplayer campaign. (The `#battle` block is written for multiplayer battles too, with `multiplayer=1` and both
players' units.)

A `#result` with `mode=fought` describes the same battle as the `#battle` block written just before it in the same
file. Tools pair the two only when all of this holds: the `#battle` block is the nearest one before the result and has
`campaign=1` and no result of its own; the result is dated at, or up to 30 minutes after, the battle; and at least half
of the result's unit keys are in the battle. Otherwise both stay unpaired.

### What tools derive

- **Unit size.** The game does not tell scripts the unit-size setting. For a `#battle` block it is the median, over
  the unit types with 20 or more models in vanilla, of `initial_men / (vanilla num_men x strength_before / 100)`
  (`strength_before` from the paired `#result`, 100 for custom battles), rounded to the nearest of 0.25, 0.5, 0.75, 1.
  A campaign battle with no paired result has no size: its units may have been under strength.
- **Whose units.** In a `#battle` block `player` marks the player's alliance, so an allied AI army counts as the
  player's side. In a `#result` block it marks units of a human faction only.
- **Duplicates.** The same file is often shared more than once. A block's identity is the hash of its header line and
  unit lines; tools count each block once.
- **Who built the numbers.** `cbp` says which patch version was loaded. Where there is no `cbp` field (logger 1) or
  it is `none`, a battle still counts as patched when `community_balance_patch.pack` is in `mods`: that is the first
  beta (0.1), version unknown. When neither can be read, the battle is labelled unknown, never vanilla.
- **Distinct players.** A file fetched from a GitHub report is named after the report and its author; files from one
  author count as one player. Hand-saved files do not count towards "enough players" unless the tool is told to trust them.

## What the logger keeps besides the file

Two notes in the game's script memory, which lasts until the game closes and is never saved: the units' ids with their
strength and experience before a battle (so a fought battle's `#result` can say what the units had going in), and one
flag saying a campaign battle was loaded. Nothing else is set, and nothing is written into a save game.

## Version 1 (logger 1, 30 September 2026, still read)

    #battle;v1;<date>;multiplayer=0|1;siege=0|1;mods=...
    u;alliance;army;player;unit_key;initial_men;men_alive;kills;routing;shattered
    #end

    #autoresolve;v1;<date>;winner=attacker|defender|draw|?;mods=...
    a;side;player;unit_key;strength_before;strength_after
    #end

`#autoresolve` is the version 1 form of `#result;mode=auto` (no turn, difficulty, experience or faction). Version 1
`#battle` blocks have no winner, no hit points and no campaign flag; tools report them separately and never mix their
"models lost" with version 2 hit-point losses.

## Mod packs in `mods=`

| pack name | what it is | counted as |
|---|---|---|
| `community_balance_patch.pack` | the patch | patched |
| `community_balance_patch_battle_logger.pack` | the Battle Logger | no effect on battles |
| `cbp_autoresolve_test.pack` | the optional auto-resolve test pack | auto-resolve rules active |
| anything else | another mod | "other mods loaded": kept apart, since it may change how units fight |
