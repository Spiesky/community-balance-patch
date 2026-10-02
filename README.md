# Community Balance Patch

A campaign balance mod for Total War: WARHAMMER III that stays close to vanilla. Units should be worth what they
cost, lore elites should feel elite, and guns should hit like guns. All the numbers are here so anyone can check
them and argue.

I'm Spiesky and I run it. The "community" part is everyone who posts a test, a battle log or a number.
[How changes get decided](docs/HOW_DECISIONS_ARE_MADE.md) is written down, including who decides while the mod is small.

Workshop: [Community Balance Patch (Alpha)](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227) · optional [Battle Logger](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476307)

It only changes regular units: their stats and prices. Lords, heroes, spells, auto-resolve and other campaign
stuff are for a separate mod later ([proposals/campaign_part](proposals/campaign_part/README.md)).

Every change, unit by unit: [reports/beta_changelog.md](reports/beta_changelog.md). Release notes: [CHANGELOG.md](CHANGELOG.md).

## What's in the alpha

Four things for now. Everything else in [the full draft](reports/changelog.md) is still a proposal.

- Lore elites are fewer but way stronger. Blood Knights are 24 vampires instead of 60 riders, Grail Knights and Grail
  Guardians work the same way, Swords of Chaos get a big buff, and Depth Guard are 32 instead of 60, like the Lahmian Handmaidens. They kill elites and big targets much faster and
  chaff slower, and never have less total health than vanilla.
- Guns hit harder and reload slower: 60% more per volley, 50% longer reload, less ammo. Damage over a battle and the
  price stay about the same. Fire from position, then pull back or reload somewhere safe.
- Elite infantry gets up to about 17% more health and damage plus a point or two of attack and defence, same price.
- Changes players have been asking for, inspired by the Total Tavern and Vermin League balance list (7.1+) and
  general player complaints. Skipped: what CA already did, and a few entries that don't fit campaign
  ([docs/COMMUNITY_LIST.md](docs/COMMUNITY_LIST.md)).

It's balanced for campaign, and custom battles are where I test it.

## What's next

One theme per release, roughly in this order:

1. See if the alpha holds up: Blood Knights and Grail Knights at their new size, guns at the new pace, elite infantry.
   The knight tests are on the unit pages. For guns and elite infantry, campaign reports are what I need.
2. The rest of the cavalry ([docs/CAVALRY_STUDY.md](docs/CAVALRY_STUDY.md)).
3. Cheap archers against armour. Test first ([units/tier1_archers.md](units/tier1_archers.md)), change only if needed.
4. Chaff, monsters and war machines, where campaign and multiplayer players disagree the most.

When CA puts out a balance patch, I rebuild on their new numbers before anything else.

## How to help

No GitHub account needed.

- Play it and tell me what you saw, in the comments or discussions on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227).
- Run a test. [docs/TESTING.md](docs/TESTING.md) has the steps: three short custom battles, about 20 minutes.
  The one I need now is on the [Blood Knights page](units/blood_knights.md).
- Share a battle log. The optional Battle Logger writes `cbp_battle_log.txt` in your game folder. Drop it on
  [the upload page](https://spiesky.github.io/community-balance-patch/) to see what's in it, then paste the summary on
  Steam or send the whole log to GitHub.
- Suggest a change with numbers: [open a suggestion](../../issues/new?template=suggestion.yml), one unit or unit
  family at a time, or post it on the Workshop page and I'll copy it over.
- Post a test result on GitHub: [test report](../../issues/new?template=test_report.yml).

## How changes get decided

Full version in [HOW_DECISIONS_ARE_MADE.md](docs/HOW_DECISIONS_ARE_MADE.md). Short version: lore says what a unit
should be, price is the yardstick (equal gold should be an even fight), and in-game tests beat spreadsheets.

## Units under review

| unit | status | page |
|---|---|---|
| Blood Knights | in the patch, tests wanted | [units/blood_knights.md](units/blood_knights.md) |
| Grail Knights and Grail Guardians | in the patch, tests wanted | [units/grail_knights.md](units/grail_knights.md) |
| Cheap archers against armour | open question, test first | [units/tier1_archers.md](units/tier1_archers.md) |
| Skipped archetypes (light cavalry, fliers, dogs, chariots, siblings) | open proposal, round 1 | [proposals/archetype_pass.md](proposals/archetype_pass.md) |

Lords, heroes, magic and auto-resolve proposals are parked in [proposals/campaign_part](proposals/campaign_part/README.md).

## What's in here

- `reports/beta_changelog.md`: what the Workshop pack changes, generated from the pack
- `units/` and `proposals/`: units and topics under review (`proposals/campaign_part/` is the later campaign mod), with the test wanted and the numbers
- `docs/`: how testing, decisions, auto-resolve, the logger and the measuring work
- `reports/`: the full draft and the numbers behind it, every unit measured
- `logger/`: the Battle Logger scripts, so you can see exactly what they record
- `tools/`: the combat model, the pack builder and the checks

## Status

Public alpha, a work in progress. The version is in [VERSION](VERSION) and every Workshop upload gets a tagged release and a
[CHANGELOG](CHANGELOG.md) entry. Nobody has played a full campaign with it and reported back yet, which is what the
alpha is for. Units from CA's latest DLC stay vanilla until I've looked at them (`tools/unreviewed.txt`), apart from
the community changes.
