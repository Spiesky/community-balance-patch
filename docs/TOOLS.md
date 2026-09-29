# Working on the patch

Everything is Python 3 (plus numpy) and runs from `tools/`. The data is the game's own database, exported from the
installed game into `vanilla_db/` (not in git, see below).

## The pipeline

    cd tools
    python3 rebalance_survey.py        # measure every unit, fit the valuation   -> reports/survey.md, _survey.json
    python3 lore_ladder.py             # how much of the roster the ladder covers
    python3 rebalance_solve.py         # the proposals                          -> reports/proposals.md, _rebalance.json
    python3 build_rebalance.py         # the pack                               -> build/community_balance_patch.pack
    python3 refcheck.py                # every foreign key in the pack resolves
    python3 rebalance_check.py         # every pack row matches its proposal
    python3 test_rebalance.py          # the invariants as tests; run after any change
    python3 sense_check.py             # does the patch make sense: sizes, directions, limits, roster order, fairness
    python3 grind_check.py             # elites against chaff: kills per model lost, vanilla and patched
    python3 gunpowder.py               # the units the gunpowder rule covers
    python3 autoresolve_calibrate.py logs/*.txt --write   # learn the auto-resolve rules from fought vs auto-resolved logs
    python3 autoresolve_rules.py       # fairer auto-resolve pack from those rules (starting guesses until there is data)
    python3 rebalance_verify.py        # equal-gold duels, vanilla vs patched
    python3 rebalance_changelog.py     # -> reports/changelog.md, the player-facing list
    python3 rebalance_ladder_view.py   # -> reports/ladder.md, every roster in ladder order
    python3 cavalry_rebalance.py       # -> reports/cavalry_study.md

Battle logs from the Battle Logger add-on: `python3 battle_logs.py log1.txt log2.txt` sums them up per unit, patched and
vanilla separately (`--unit blood_knights` to filter).

One unit end to end: `python3 rebalance_explain.py "Temple Guard"`. What an edit changed: copy `_rebalance.json`
first, re-run, then `python3 rebalance_diff.py before.json _rebalance.json`. `python3 build_rebalance.py <unit key> ...`
builds a pack with only those units, for testing one change at a time.

## Where the judgments live

| file | what |
|---|---|
| `tools/lore_ladder.py` | the lore ladder for infantry, monsters, beasts and machines: one line per unit family |
| `tools/cavalry_rebalance.py` | `LORE`: the cavalry targets from the cavalry study |
| `tools/decided.py` | units set by hand (four Empire knightly orders) |
| `tools/unreviewed.txt` | units the ladder has never judged; kept as vanilla until someone does |
| top of `tools/rebalance_solve.py` | the price layer's rules (`TOLERANCE`, `CAP`, `PRICE_CAP`, `STAT_CASTES`, `K_ATTACK`) and `VETO` |
| top of `tools/unit_model.py` | the combat model's assumptions |

A community suggestion that goes in normally becomes one line in the ladder (or `decided.py`), not a hand edit of
stats.

## Decisions already made

- **Close to vanilla.** The patch adjusts CA's balance, it does not replace it. No unit's strength or price moves
  more than about 20% (`POWER_LIMIT`, `PRICE_LIMIT` at the top of `rebalance_solve.py`), and unit sizes stay vanilla
  (`RESIZE`), with one exception:
- **The lore elites are fewer and far stronger** (`ELITE`): Blood Knights, Grail Knights, Grail Guardians and the Swords
  of Chaos take the lore's size and strength. A unit made smaller never has less total health than vanilla, and its
  price never rises faster than its strength (at most x1.6).
- **Elites grind chaff.** A unit of Grail Knights should be able to kill Skavenslaves more or less for ever.
  `grind_check.py` measures it.
- **Gunpowder hits hard and reloads slow** (`gunpowder.py`): single-shot firearms fire a 60% heavier volley and take
  50% longer to reload, so they are played by getting into position, firing, then pulling back or reloading in
  safety. Damage over time barely moves (+7%).
- **Changes make sense on their own.** A stronger unit never gets cheaper and a weaker one never dearer; a unit whose
  stats move keeps its price. Regiments of renown move with their base unit. A final pass reverts any change that makes
  a dearer unit weaker than a cheaper one in the same roster. `sense_check.py` checks all of it.
- **Monsters, war beasts, chariots and war machines stay vanilla for now** (`FLAT_CASTES_MOVE`). Campaign players say
  they are too strong, multiplayer players say many are too weak, and the model understands them least.
- **Balance means worth its price**: every unit is judged against its own caste's price line.
- **Lore outranks price.** A ladder entry decides; the price layer only touches units with no entry.
- **Identity is a ray**: a change scales HP and every damage figure by one factor and moves attack and defence
  together. Charge, armour, speed, mass, shield, resistances, abilities, weapon type and splash never move.
- **Armour ceiling**: plate 120 for any regiment of mortal knights, 125 only for demigryph riders. The solver never
  touches armour.
- **The scale is pinned** (`PINNED` in `rebalance_survey.py`): the ladder's numbers live on the 2026-09-16 fit.
  `--refit-scale` unpins, after which the ladder needs re-anchoring.
- **Blind spots are `keep`**: where the model cannot see the cause (Wrathmongers' splash, Sky Lantern accuracy),
  the unit stays vanilla.

## Open items

1. **Not played yet.** An earlier build loaded and its unit cards showed the right numbers; this build has not been
   opened in game.
2. **The ladder has not been reviewed.** It is about 200 judgments and none have been argued over yet. `reports/ladder.md` shows
   every roster in the resulting order. The biggest factors (Bloodthirster x1.7, Hell Pit Abomination x1.7, Dread
   Saurian x1.6, White Lions and Wardancers x1.5) deserve the first look.
3. **58 units from the recent updates are unreviewed** (`tools/unreviewed.txt`: Lords of the End Times and others).
   They stay vanilla until they get ladder lines.
4. **Pending decisions**, kept as vanilla until made: Centigors, the Thundertusk.
5. **Guards at 80 models and stronger monsters** are off until the community weighs in.
6. **Pistoliers** lose 16% (the model rates them a bargain) on top of the gunpowder change; worth a look in game.
7. **Artillery and gunpowder war machines** are not covered by the gunpowder rule yet.

## Refreshing the game data (after a patch)

The tools need RPFM's WH3 schema (found in RPFM's config folder, or set `CBP_SCHEMA`). They read TSV exports of 28 tables from the installed game's `data/db.pack`, plus `text/db/land_units__.loc`
from `data/local_en.pack` for unit names, in RPFM's TSV format:

    vanilla_db/<table>_tables/data__.tsv
    vanilla_db/text/db/land_units__.loc.tsv

Export them with RPFM (open the pack, right-click the table, Export TSV). The list of tables is every
`V.table(...)` / `V.index(...)` name in `tools/*.py`. Then run the whole pipeline again. Units that are new in the
patch should be added to `tools/unreviewed.txt` until they are judged. `CBP_DB=/some/other/dump` points the tools
at a different export.
