# Community Balance Patch

A unit balance mod for Total War: WARHAMMER III campaigns, built in the open.

Vanilla, with units that are worth their price: elites you can feel, gunpowder that plays like gunpowder, and every
number measured and argued in public.

I maintain it (Spiesky). The "community" part is everyone who posts a test, a battle log or a number, and the
multiplayer community whose peer-reviewed balance list is in the pack. The plan is for the people who test to decide;
[how that works today](docs/HOW_DECISIONS_ARE_MADE.md) is written down, including who decides while the mod is small.

**Workshop:** [Community Balance Patch (Beta)](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227) · optional [Battle Logger](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476307)

**What the pack changes, unit by unit:** [reports/beta_changelog.md](reports/beta_changelog.md) · release notes: [CHANGELOG.md](CHANGELOG.md)

## What is in the beta

Four things, and nothing else. Everything in [the full draft](reports/changelog.md) beyond them is still a proposal.

- **Lore elites are fewer and far stronger.** Blood Knights are 24 vampires instead of 60 riders; Grail Knights and
  Grail Guardians get the same treatment, and the Swords of Chaos, already few, become far stronger. They kill elite
  and large targets much faster and chaff more slowly, and they never have less total health than vanilla.
- **Gunpowder hits hard and reloads slow.** A 60% heavier volley, a 50% longer reload and less ammunition, so the damage
  over a battle stays about vanilla's and the price does not move. Fire from position, then pull back or reload in safety.
- **Elite infantry is worth its price.** More health and damage (up to about 17%) and a point or two of attack and
  defence for infantry the lore rates elite, at the vanilla price.
- **The multiplayer community's balance list.** The Total Tavern and Vermin League peer-reviewed recommendations
  (7.1+), as written, minus what CA already did and minus a few entries held for campaign
  ([docs/COMMUNITY_LIST.md](docs/COMMUNITY_LIST.md)).

It is a campaign mod first. Custom battles are the test bench. Auto-resolve is not touched: a possible fix for it is a
separate test pack, attached to the GitHub release, until it has been tested ([docs/AUTORESOLVE.md](docs/AUTORESOLVE.md)).

## What comes next

One theme per release, and each release asks one question. In this order, as tests come in:

1. **Do the four themes in the beta hold up?** Blood Knights and Grail Knights at their new size, guns at their new
   rhythm, elite infantry at its new strength. The Blood Knights and Grail Knights tests are on the unit pages; for
   guns and elite infantry no test is written yet, so campaign reports are what I need.
2. **Cavalry.** The cavalry study's targets for the rest of the knights ([docs/CAVALRY_STUDY.md](docs/CAVALRY_STUDY.md)).
3. **Cheap missiles against armour.** A test first ([units/tier1_archers.md](units/tier1_archers.md)), then a change if it shows one is needed.
4. **Chaff, monsters and war machines.** The castes the model understands least, and the ones campaign and multiplayer
   players disagree about most.

After each CA balance patch the pack is rebuilt on CA's new numbers before anything else.

## How to take part

You do not need a GitHub account.

- **Play it and say what you saw**, in the comments or discussions on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227).
- **Run a test.** [docs/TESTING.md](docs/TESTING.md) is the recipe: three short custom battles, about twenty minutes.
  The test wanted now is on the [Blood Knights page](units/blood_knights.md).
- **Share a battle log.** The optional Battle Logger writes `cbp_battle_log.txt` in your game folder. Drop it on
  [the upload page](https://spiesky.github.io/community-balance-patch/): it shows you what is in it, and you can copy a
  summary to paste on Steam or send the whole log to GitHub.
- **Suggest a change with numbers:** [open a suggestion](../../issues/new?template=suggestion.yml), one unit or unit
  family at a time, or post it on the Workshop page and I will copy it over.
- **Report a test on GitHub:** [post a test result](../../issues/new?template=test_report.yml).

## How changes are decided

See [HOW_DECISIONS_ARE_MADE.md](docs/HOW_DECISIONS_ARE_MADE.md). In short:

1. **Lore sets the direction.** What should this unit be?
2. **Price is the yardstick.** Two armies of equal gold should be an even fight.
3. **Battles decide.** A model can be wrong. In-game test results beat spreadsheets.

## Units under review

| unit | status | page |
|---|---|---|
| Blood Knights | in the patch, tests wanted | [units/blood_knights.md](units/blood_knights.md) |
| Grail Knights and Grail Guardians | in the patch, tests wanted | [units/grail_knights.md](units/grail_knights.md) |
| Cheap archers against armour | open question, test first | [units/tier1_archers.md](units/tier1_archers.md) |

## What's in here

| where | what |
|---|---|
| `reports/beta_changelog.md` | **what the Workshop pack changes**, one line per unit, generated from the pack's data |
| `CHANGELOG.md` | release notes, one entry per Workshop upload |
| `units/` | one page per unit under review: the test wanted, the idea, the numbers |
| `docs/TESTING.md` | how to run a test that counts |
| `docs/HOW_DECISIONS_ARE_MADE.md` | who decides, and how a change gets in |
| `docs/COMMUNITY_LIST.md` | the community's peer-reviewed balance list: what of it is in the patch and what CA already did |
| `docs/AUTORESOLVE.md` | how auto-resolve works, the optional test pack, and the test that would justify it |
| `docs/LOG_FORMAT.md` | what the Battle Logger writes, field by field |
| `logger/` | the Battle Logger's two scripts, so anyone can read exactly what they record |
| `reports/changelog.md` | the full draft: every proposal, one line per unit (not in the pack until tested) |
| `reports/proposals.md`, `reports/ladder.md`, `reports/survey.md` | the draft's numbers, every roster in order, every unit measured |
| `docs/METHOD.md` | how units are measured and valued |
| `docs/COMMUNITY_RESEARCH.md` | what players have said about balance, and how the draft compares |
| `docs/CAVALRY_STUDY.md` | the cavalry study behind the cavalry targets |
| `docs/TOOLS.md`, `docs/RELEASING.md` | how to build the pack, and how a build becomes a Workshop release |
| `tools/` | the combat model, the solver, the pack builder and the checks |

## Status

Public beta. The version is in [VERSION](VERSION) and stamped into the pack; from 0.2.0 on, each Workshop upload is a
tagged release with an entry in [CHANGELOG.md](CHANGELOG.md). The tools check every row of the pack against the proposals and the
community list. An earlier build's unit cards were checked in game; nobody has yet played a campaign with the mod and
reported back, and that is what the beta is for. Units added in CA's latest updates stay vanilla until they have been
reviewed (`tools/unreviewed.txt`), apart from what the community list says about them.
