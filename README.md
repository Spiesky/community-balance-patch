# Community Balance Patch

A crowd-sourced unit balance mod for Total War: WARHAMMER III.

This is a community effort. There's no balance team behind it, just players working on it together. Every suggestion, test result and discussion helps shape where it goes, so if something feels off in your battles, come share it.

Every recruitable unit (over a thousand of them) has been measured on one combat model and compared with what CA charges for it. That is the starting point. The rest comes from you: what you see in your own battles, what feels wrong, and what you think a unit should be.

The community is not always right, and neither is the model. A change goes in when the reasoning, the numbers and the test results agree.

**Workshop:** [Community Balance Patch (Beta)](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227) · optional [Battle Logger](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476307)

## How to take part

- **Suggest a change:** [open a suggestion](../../issues/new?template=suggestion.yml). One unit (or one unit family) per suggestion.
- **Report a test:** [post a test result](../../issues/new?template=test_report.yml). Tell us what you fought, at what settings, and what happened. Replays and screenshots are gold.
- **Share a battle log:** run the optional Battle Logger add-on, then drop your `cbp_battle_log.txt` on [the upload page](https://spiesky.github.io/community-balance-patch/). Thank you, it helps a lot.
- **Argue about it:** use [Discussions](../../discussions) for the big questions ("what should Blood Knights be?").

## How changes are decided

See [HOW_DECISIONS_ARE_MADE.md](docs/HOW_DECISIONS_ARE_MADE.md). In short:

1. **Lore sets the direction.** What should this unit be?
2. **Price is the yardstick.** Two armies of equal gold should be an even fight.
3. **Battles decide.** A model can be wrong. In-game test results beat spreadsheets.

## Units under review

| unit | status | page |
|---|---|---|
| Blood Knights | in the patch, open for feedback | [units/blood_knights.md](units/blood_knights.md) |
| Cheap archers vs armour | open proposal, round 1 | [units/tier1_archers.md](units/tier1_archers.md) |

## What's in here

| folder | what |
|---|---|
| `units/` | one page per unit under review, with the proposal and the open questions |
| `reports/changelog.md` | every change in the current draft, one line per unit, in plain words |
| `reports/ladder.md` | every faction's roster in order after the changes |
| `reports/proposals.md` | every change with before and after numbers and the reason |
| `docs/COMMUNITY_LIST.md` | the community's peer-reviewed balance list, what of it is in the patch and what CA already did |
| `docs/AUTORESOLVE.md` | how auto-resolve works, what the patch changes, and the test that decides the back-line rule |
| `docs/METHOD.md` | how units are measured and valued |
| `docs/COMMUNITY_RESEARCH.md` | what the community has said about balance, and how the draft compares |
| `docs/CAVALRY_STUDY.md` | the cavalry study behind the cavalry targets |
| `docs/TOOLS.md` | how to run the tools and build the pack |
| `tools/` | the combat model, the solver and the pack builder |

## Status

Pre-release. The first draft stays close to vanilla: it adjusts 367 units by at most about 20%. The exceptions are the lore elites (Blood Knights, Grail Knights, Grail Guardians, Swords of Chaos), which are fewer and far stronger, and gunpowder, which now hits hard and reloads slow. Monsters and war machines are unchanged for now. It hasn't been played yet. Units added in the latest updates stay vanilla until they're reviewed.
