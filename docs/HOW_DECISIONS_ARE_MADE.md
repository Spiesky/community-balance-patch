# How decisions are made

## What balance means here

Not "every unit equal". A Zombie must never become a Grail Knight. Balance means **every unit is worth its price**: two armies of equal gold should be an even fight whatever they are made of, and paying more should get you more.

## Campaign first

The mod is balanced for campaign play. That is where most battles are fought, and where a unit's price, upkeep and place in a building chain matter.

Custom battles are the test bench: the same two units, the same settings, as often as it takes (see [TESTING.md](TESTING.md)). A custom battle result is evidence about a unit, not a goal in itself.

Changes that only make sense in multiplayer wait. The multiplayer community's own peer-reviewed list is in the pack as they wrote it, with credit, minus what CA has already done and minus the entries held back after a campaign review ([COMMUNITY_LIST.md](COMMUNITY_LIST.md)).

## The three inputs

| input | what it answers | its blind spots |
|---|---|---|
| **Lore** | what the unit *should* be | says nothing about gold |
| **The combat model** | how strong the unit is for its price, compared with every other unit | cannot see behaviour: accuracy, pathing, splash into blobs, AI handling, micro |
| **Community tests** | what actually happens in battles | one battle is an anecdote; settings and micro vary |

## What makes a suggestion likely to go in

- It names the unit and the problem clearly.
- It says what you'd change, and why (lore, price, or what you saw in battle).
- It comes with test results, or someone else confirms it with theirs.
- It keeps the unit what it is. Buffs that turn one unit into another won't go in.

## What won't go in

- "Make my faction stronger" with no reasoning.
- Changes that only make sense in multiplayer (see "Campaign first"). I note them and they wait.
- Changes that break the game, break another rule on this page, or can't be built. I say which.

## Who decides today

I do: Spiesky, the maintainer. The mod is new and has a handful of subscribers. A vote needs voters, and a rule that nobody can satisfy only means nothing gets decided, or that I decide anyway without saying so. So until there are enough testers, I decide, in public, with the reason written down, and anyone can make me look again.

This page says "I" for the same reason. When a second person has contributed, it will say "we".

## How a change goes in

1. **Posted with its reason.** Every change is posted before it ships: the exact numbers, and why. It goes in a discussion thread on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227) and in a GitHub issue. My own changes go through this step like anyone else's. From the release after 0.2 on, nothing goes in that was not posted first.
2. **One week to object.** Anyone can object, on the Workshop page or in the issue.
3. **Build and release.** If nothing reopened it, it goes into the next release.

**What is already in the pack.** What is in 0.1 and 0.2 went in before this process existed, without a week to object. It is all listed in [reports/beta_changelog.md](../reports/beta_changelog.md) and [COMMUNITY_LIST.md](COMMUNITY_LIST.md), and a test result can reopen any of it the same way.

**What an objection needs to reopen a decision:** a test result. One test run the way [TESTING.md](TESTING.md) describes, or a battle log, or a campaign report, that shows the change does not do what its reason says. That is enough, from one person. The change is then held back (or, if it already shipped, goes back on the list), I run the same test myself, post both results and decide again, with the reason.

An objection without a test is still read and answered. It does not reopen the decision by itself, because "I don't like it" against "I do" settles nothing.

This holds after release too. There is no deadline on a test result.

## Proposing a change

Anyone can propose. A proposal needs **exact numbers** ("+4 melee attack, -25 gold", not "a bit stronger"). "I don't know the numbers, but it's off" is still worth posting: someone may pick it up.

You do not build anything. I build it, and if it helps I make a small test pack with only that change.

A **sponsor** is a tester: someone who plays the change in game and posts what happened. A proposal with a sponsor's result moves ahead of one without. You can sponsor your own proposal or someone else's.

## Rounds

Changes are posted in batches, so everyone knows when to speak up. A round is one batch: posted together, one week to object, then released together.

**If a round gets no proposals from anyone else,** the changes I posted go in after the week, unless a test reopened them. If I posted nothing either, there is no release. The patch does not change for the sake of changing.

After a CA balance patch the numbers are rebuilt on the new game data first. What CA fixes itself comes out of the patch.

## Credit

Every release note names who proposed each change and who tested it. If the names are all mine, it says so.

## Without a GitHub account

You don't need one. The front door is Steam: the comments and the discussion threads on the [Workshop page](https://steamcommunity.com/sharedfiles/filedetails/?id=3810476227). Proposals, objections, test results and battle logs posted there count exactly as much as a GitHub issue. I copy them into issues myself, with your Steam name, unless you ask me not to.

GitHub is the ledger: the place where every decision, its reason and its evidence are kept in one list. The forms there are for people who like forms.

## Where this is going: the vote

The plan is for the people who test to decide. The vote switches on when **20 different people** have each posted at least one test result or battle log. I keep the count here, on this page, with the date:

**Testers so far: 0** (1 October 2026; I do not count myself).

From then on:

- Proposals and counter-proposals for the same unit sit side by side.
- **Approval voting:** you approve every option you could live with, as many as you like. The option with the most approvals wins.
- **Big changes need two thirds** of the people voting: a unit's role, its size, or anything touching a whole faction.
- The maintainer keeps a veto only for changes that break the game, break a rule on this page, or can't be built, and always says why.

Until then, the steps above are the whole process.

## Labels

`suggestion`, `test-report`, `needs-testing`, `accepted`, `rejected`, `in-build`, and one label per faction.

Every accepted or rejected suggestion gets a short reason.
