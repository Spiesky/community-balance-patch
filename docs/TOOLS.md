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
    python3 rebalance_verify.py        # equal-gold duels, vanilla vs patched
    python3 rebalance_changelog.py     # -> reports/changelog.md, the player-facing list
    python3 rebalance_ladder_view.py   # -> reports/ladder.md, every roster in ladder order
    python3 cavalry_rebalance.py       # -> reports/cavalry_study.md

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

- **Balance means worth its price**: every unit is judged against its own caste's price line.
- **Lore outranks price.** A ladder entry decides; the price layer only touches units with no entry.
- **Identity is a ray**: a change scales HP and every damage figure by one factor and moves attack and defence
  together. Charge, armour, speed, mass, shield, resistances, abilities, weapon type and splash never move.
- **Armour ceiling**: plate 120 for any regiment of mortal knights, 125 only for demigryph riders. The solver never
  touches armour.
- **Flat-priced castes are never made dearer.** Monsters, war beasts, chariots and war machines only ever get cheaper
  from the price layer; the community says their weaknesses are behaviour the database does not hold.
- **The scale is pinned** (`PINNED` in `rebalance_survey.py`): the ladder's numbers live on the 2026-09-16 fit.
  `--refit-scale` unpins, after which the ladder needs re-anchoring.
- **Blind spots are `keep`**: where the model cannot see the cause (Wrathmongers' splash, Sky Lantern accuracy),
  the unit stays vanilla.

## Open items

1. **No in-game test yet.** Install the pack, recruit a changed unit (Temple Guard, Chaos Warriors, Greatswords),
   check its card against `reports/proposals.md`, fight.
2. **The ladder has not been reviewed.** It is about 200 judgments and none have been argued over yet. `reports/ladder.md` shows
   every roster in the resulting order. The biggest factors (Bloodthirster x1.7, Hell Pit Abomination x1.7, Dread
   Saurian x1.6, White Lions and Wardancers x1.5) deserve the first look.
3. **58 units from the recent updates are unreviewed** (`tools/unreviewed.txt`: Lords of the End Times and others).
   They stay vanilla until they get ladder lines.
4. **Pending decisions**, kept as vanilla until made: Centigors, the Thundertusk.
5. **Blood Knights**: the two models disagree on 24 riders. See `units/blood_knights.md`.

## Refreshing the game data (after a patch)

The tools need RPFM's WH3 schema (found in RPFM's config folder, or set `CBP_SCHEMA`). They read TSV exports of 28 tables from the installed game's `data/db.pack`, plus `text/db/land_units__.loc`
from `data/local_en.pack` for unit names, in RPFM's TSV format:

    vanilla_db/<table>_tables/data__.tsv
    vanilla_db/text/db/land_units__.loc.tsv

Export them with RPFM (open the pack, right-click the table, Export TSV). The list of tables is every
`V.table(...)` / `V.index(...)` name in `tools/*.py`. Then run the whole pipeline again. Units that are new in the
patch should be added to `tools/unreviewed.txt` until they are judged. `CBP_DB=/some/other/dump` points the tools
at a different export.
