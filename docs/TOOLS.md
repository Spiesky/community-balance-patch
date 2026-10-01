# Working on the patch

Everything is Python 3 and runs from `tools/`. The data is the game's own database, read from the installed game into
`vanilla_db/` (not in git, see the end of this page).

    python3 -m venv ~/Tools/venvs/wh3 && ~/Tools/venvs/wh3/bin/pip install -r tools/requirements.txt

## Patch day: the one way to build the Workshop pack

After a CA update, or after any change to the rules, one command re-reads the game's data, rebuilds the beta, runs every
check and regenerates the pages that describe the pack. It stops at the first check that fails.

    tools/patch_day.sh                 # everything
    tools/patch_day.sh --no-refresh    # vanilla_db/ is already current

It needs the installed game (`CBP_GAME`, the folder that holds `data/db.pack`; the usual Steam places on Linux, macOS
and Windows are found without it) and RPFM's WH3 schema (`CBP_SCHEMA`, or `tools/schema_wh3.ron`, or RPFM's config folder). `CBP_PYTHON` picks the interpreter; the
default is `~/Tools/venvs/wh3/bin/python` if it exists, else `python3`.

What comes out: `build/beta/community_balance_patch.pack` (the Workshop pack, with `VERSION` stamped into it),
`build/community_balance_patch_battle_logger.pack`, `build/cbp_autoresolve_test.pack` (a test pack, not part of the
patch), the regenerated `reports/beta_changelog.md`, unit pages, Workshop texts and draft reports, and, only when every
check has passed, `build/beta/CHECKED`: the stamp `tools/upload.sh` asks for. `CBP_` variables left in the shell are
ignored: the script decides its own inputs. Then read the "changed:" lines (the
tables CA touched), drop anything CA fixed itself from `community.py`, and follow [RELEASING.md](RELEASING.md).

The pack file is always called `community_balance_patch.pack`. Renaming it would switch the mod off for every
subscriber, so the version lives inside it (one localisation entry, `cbp_version`) and in `VERSION`.

## The pieces, one at a time

`patch_day.sh` runs these in order; they are listed for working on one of them.

    cd tools
    python3 refresh_vanilla.py         # re-read the game's tables into ../vanilla_db, list what CA changed
    python3 rebalance_survey.py        # measure every unit, fit the valuation   -> reports/survey.md, _survey.json
    python3 rebalance_solve.py         # the draft and the beta                  -> reports/proposals.md, _rebalance.json, _beta.json
    python3 community.py               # which units every list entry names; fails if that differs from community_resolved.json
    CBP_PROPOSALS=$PWD/_beta.json CBP_COMMUNITY=1 CBP_OUT=$PWD/../build/beta/community_balance_patch.pack python3 build_rebalance.py
    python3 refcheck.py <pack>         # every foreign key in the pack resolves
    python3 sense_check.py             # does the patch make sense: sizes, directions, limits, roster order, fairness
    python3 community_check.py         # every unit changes exactly as the community list says, nothing else moves
    python3 rebalance_check.py <pack>  # every pack row matches its proposal (run on build/check/without.pack: the beta without the list)
    python3 test_rebalance.py          # the invariants as tests (CBP_PROPOSALS and CBP_OUT pick the beta)
    python3 test_logs.py               # the battle log parser and tools, on sample logs
    python3 build_logger.py            # the Battle Logger pack from logger/*.lua
    python3 autoresolve_rules.py       # the optional auto-resolve test pack
    CBP_BETA=1 CBP_PROPOSALS=$PWD/_beta.json CBP_CHANGELOG=../reports/beta_changelog.md python3 rebalance_changelog.py
    python3 unit_pages.py              # the numbers on units/*.md and the table on docs/AUTORESOLVE.md
    python3 workshop_text.py           # the Workshop descriptions and change notes -> ../workshop/*.txt
    python3 final_check.py             # the Workshop pack is the build the checks verified; stamps it for upload

Without `CBP_PROPOSALS`, `build_rebalance.py`, `rebalance_check.py`, `sense_check.py` and `rebalance_changelog.py` work
on the whole draft (`_rebalance.json`, `build/draft/community_balance_patch_DRAFT.pack`, `reports/changelog.md`). **That
pack is the draft, not the Workshop pack**, and carries a different file name so it cannot be uploaded by mistake.
Only `patch_day.sh` builds what ships.

Also:

    python3 grind_check.py             # elites against chaff: kills per model lost and per minute, vanilla and patched
    python3 gunpowder.py               # the units the gunpowder rule covers, before and after
    python3 rebalance_verify.py        # equal-gold duels on the regiment simulator, vanilla vs patched
    python3 rebalance_explain.py "Temple Guard"            # one unit end to end
    python3 rebalance_diff.py before.json _rebalance.json  # what an edit changed (copy _rebalance.json first)
    python3 build_rebalance.py <unit key> ...              # a pack with only those units, to test one change
    python3 rebalance_ladder_view.py   # -> reports/ladder.md, every roster in ladder order
    python3 cavalry_rebalance.py       # -> reports/cavalry_study.md

Battle logs: `python3 fetch_logs.py` pulls the logs out of the repo's test reports into `../logs/`;
`python3 battle_logs.py ../logs/*.txt` sums them up per unit (`--unit blood_knights` filters, `--csv` writes a table);
`python3 autoresolve_calibrate.py ../logs/*.txt` compares fought and auto-resolved battles. The format is in
[LOG_FORMAT.md](LOG_FORMAT.md).

## Where the judgments live

| file | what |
|---|---|
| `tools/lore_ladder.py` | the lore ladder for infantry, monsters, beasts and machines: one line per unit family |
| `tools/cavalry_rebalance.py` | `LORE`: the cavalry targets from the cavalry study |
| `tools/decided.py` | units set by hand (four Empire knightly orders) |
| `tools/community.py` | the community's list, entry by entry, and the entries held for campaign (`HELD`) |
| `tools/community_resolved.json` | which units each list entry names today and the numbers it applies; a difference fails the build until someone has looked (`python3 community.py --write` accepts it) |
| `tools/gunpowder.py` | the gunpowder rule (`DAMAGE`, `RELOAD`, `AMMO`) and which weapons count |
| `tools/unreviewed.txt` | units the ladder has never judged; kept as vanilla until someone does |
| top of `tools/rebalance_solve.py` | the limits, `ELITE_FAMILIES`, `THEME_ALSO`, the price layer's rules and `VETO`; `make_beta` is what the beta takes |
| top of `tools/unit_model.py` | the combat model's assumptions |
| `VERSION` | the version stamped into the pack and written on every release |

A suggestion that goes in normally becomes one line in the ladder (or `decided.py`), not a hand edit of stats.

## Decisions already made

- **Close to vanilla.** The patch adjusts CA's balance, it does not replace it. No unit's strength or price moves
  more than about 20% (`POWER_LIMIT`, `PRICE_LIMIT` at the top of `rebalance_solve.py`), and unit sizes stay vanilla
  (`RESIZE`), with one exception:
- **The lore elites are fewer and far stronger** (`ELITE_FAMILIES`): Blood Knights, Grail Knights, Grail Guardians and
  the Swords of Chaos take the lore's size and strength. A unit made smaller never has less total health than vanilla.
  Its charge bonus scales with its damage, so the charge stays what it was next to the unit's own blows (written as
  a factor on the database value: Frenzy multiplies the charge, and a difference would count it twice). Its price
  follows its **usable** strength (below), never rises faster than it (at most x1.6), and units CA prices together
  (the two Blood Knights, Grail Knights and Grail Guardians) move by one ratio, the lowest either earns.
- **Overkill is not strength.** A blow never does more than its target has hit points: a 188-damage swing into a 50-HP
  Skavenslave kills one Skavenslave. `cavalry_model.blow(usable=True)` and `unit_model.usable_power` take the overkill
  out, and the lore elites and `grind_check.py` are measured that way. The survey's scale is fitted without the cap
  and stays pinned; fitting it with the cap is an open item.
- **Fewer and stronger trades speed for staying power.** `grind_check.py` prints both: chaff killed per model lost
  (how long the unit can keep it up) and chaff killed per minute by the whole unit (how fast). The lore elites do much
  better on the first; Blood Knights do worse on the second, Grail Knights about the same.
- **Gunpowder hits hard and reloads slow** (`gunpowder.py`): single-shot firearms fire a 60% heavier volley, take 50%
  longer to reload and carry 1/1.6 of the ammunition (rounded half up), so the damage over a battle is about vanilla's
  and the rule does not move the price. They are played by getting into position, firing, then pulling back or reloading in safety.
- **The beta is four themes** (`make_beta`): the lore elites, gunpowder, elite infantry and the community list.
  Elite infantry is melee infantry the ladder rates elite or champion (and `THEME_ALSO`: Greatswords), with rules of
  its own: the theme moves strength only and the price stays vanilla's (the complaint it answers is that elite
  infantry is not worth its price; the draft's price for the unit stays a proposal); a regiment of renown is in it
  only with its base unit; and a unit whose regiment of renown the community list remodels waits.
- **The community list wins where it speaks.** A unit the list names takes the list's numbers and nothing from the
  model (the lore elites excepted). The list is peer-reviewed and has been played; the model's numbers have not. On a
  gun the list's missile numbers go through the gunpowder rule ([COMMUNITY_LIST.md](COMMUNITY_LIST.md)).
- **A regiment of renown moves with its base unit, everywhere.** In the model's layer it takes its base's own factor,
  so it gains the same share of health and damage. Under the community list it takes the changes the list makes to
  its base, unless the list names it. A campaign twin (a Grudge Settlers copy) takes everything its original does, and
  a campaign copy that shares a unit's stats row is repriced with it.
- **Auto-resolve is not in the patch.** `autoresolve_rules.py` builds an optional test pack; `CBP_AUTORESOLVE=1` is
  the only way the rows get into the main pack, and `rebalance_check.py` fails a pack that has them without it.
- **Changes make sense on their own.** A stronger unit never gets cheaper and a weaker one never dearer; a unit whose
  stats move keeps its price. Regiments of renown move with their base unit. A final pass reverts any change that makes
  a dearer unit weaker than a cheaper one in the same roster. `sense_check.py` checks all of it.
- **Monsters, war beasts, chariots and war machines stay vanilla in the model's layer** (`FLAT_CASTES_MOVE`). Campaign
  players say they are too strong, multiplayer players say many are too weak, and the model understands them least.
  The community list's entries for them are in, apart from the held ones.
- **Balance means worth its price**: every unit is judged against its own caste's price line.
- **Lore outranks price.** A ladder entry decides; the price layer only touches units with no entry.
- **Identity is a ray**: a change scales HP and every damage figure by one factor and moves attack and defence
  together. Armour, speed, mass, shield, resistances, abilities, weapon type and splash never move, and neither does the
  charge bonus except for the lore elites.
- **Armour ceiling**: plate 120 for any regiment of mortal knights, 125 only for demigryph riders. The solver never
  touches armour.
- **The scale is pinned** (`PINNED` in `rebalance_survey.py`): the ladder's numbers live on the 2026-09-16 fit.
  `--refit-scale` unpins, after which the ladder needs re-anchoring.
- **Blind spots are `keep`**: where the model cannot see the cause (Wrathmongers' splash, Sky Lantern accuracy),
  the unit stays vanilla.

## Open items

1. **Not played yet.** An earlier build loaded and its unit cards showed the right numbers; this build has not been
   opened in game. The first tests wanted are on the unit pages (`units/`).
2. **The Battle Logger's version 2 has been run against mock game objects, not in the game.** One fought battle and one
   auto-resolved battle with it installed, then a look at `cbp_battle_log.txt`, is the check it still needs.
3. **The ladder has not been reviewed.** It is about 200 judgments and none have been argued over yet. `reports/ladder.md` shows
   every roster in the resulting order. The biggest factors (Bloodthirster x1.7, Hell Pit Abomination x1.7, Dread
   Saurian x1.6, White Lions and Wardancers x1.5) deserve the first look.
4. **The overkill cap is not in the survey.** It would lower every monster's and monstrous unit's measured strength
   against infantry and so move the scale the ladder is written on. Until the scale is refitted with it, treat the
   draft's numbers for those castes with more caution than the rest.
5. **The lore elites keep their vanilla mass.** 24 riders push less than 60. Whether the charge still breaks a block
   is the first question on `units/blood_knights.md`; if it does not, raising the mount's mass is the next lever.
6. **The Community Bug Fix Mod and Slayer Pirates.** Their land rows go in a file that sorts after its fix
   (`YIELD_TO_BUGFIX`), so with that mod installed the Slayer Pirates stay vanilla (its fix and nothing of the
   patch's), and without it the patch's rows apply. Merging its changed columns into the patch's row would give both;
   it needs its pack at build time.
   The load-order rule itself has been checked against its file names, not in game.
7. **58 units from the recent updates are unreviewed** (`tools/unreviewed.txt`: Lords of the End Times and others).
   They stay vanilla until they get ladder lines.
8. **Pending decisions**, kept as vanilla until made: Centigors (the list's price cuts and hitbox are in; the ladder's
   raise is not), the Thundertusk. And one made for now that a test could change: the Swords of Chaos at 2400 gold
   (x1.6, for a unit the model rates at x1.7 usable strength).
9. **Guards at 80 models and stronger monsters** are off until players weigh in.
10. **Artillery and gunpowder war machines** are not covered by the gunpowder rule yet.
11. **No licence file.** Until there is one, nobody else can legally reuse the tools; choosing it is the maintainer's call.

## The game data

`refresh_vanilla.py` reads every table the tools read or write straight from the installed game's `data/db.pack`, and
the unit names from `data/local_en.pack`, into

    vanilla_db/<table>_tables/<file>.tsv
    vanilla_db/text/db/land_units__.loc.tsv

keeping the previous export in `vanilla_db.prev/` and listing every table whose version or row count changed. It needs
RPFM's WH3 schema to decode the tables (`CBP_SCHEMA`); when CA adds a column the schema does not know yet, the layout
goes in `tools/schema_patch.json` until RPFM catches up. The same export can be made by hand with RPFM (open the pack,
right-click the table, Export TSV). Units that are new in a patch should be added to `tools/unreviewed.txt` until they
are judged. `CBP_DB=/some/other/dump` points the tools at a different export.
