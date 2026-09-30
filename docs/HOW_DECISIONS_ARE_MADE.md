# How decisions are made

## What balance means here

Not "every unit equal". A Zombie must never become a Grail Knight. Balance means **every unit is worth its price**: two armies of equal gold should be an even fight whatever they are made of, and paying more should get you more.

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
- Changes that only make sense for multiplayer *or* only for campaign, without saying which. We note both and decide deliberately.

## Balance rounds

Changes go in by rounds, so nothing gets lost in a pile of threads and everyone knows when to speak up.

1. **Proposals (2 weeks).** Anyone can post a suggestion. To go to a vote it needs **exact numbers** ("+4 melee attack, -25 gold", not "a bit stronger") and a **sponsor**: someone who commits to building it and testing it in game. Without a sponsor it waits for the next round.
2. **Counter-proposals (1 week).** Other numbers for the same unit go in the same issue.
3. **Vote (1 week).** Thumbs up on every option you'd accept (approval voting, pick as many as you like). An option wins with the most votes and **at least 10**. Big changes (a unit's role, its size, anything touching a whole faction) need **two thirds** of the votes.
4. **Build and release.** Winners go into the next release, each with its reason in the changelog and the name of whoever proposed and sponsored it.

The maintainer keeps a veto for changes that break the game, break other rules on this page, or can't be built, and always says why.

A round starts right after each CA balance patch, so proposals are made on the current numbers. What CA fixes itself comes out of the patch.

You don't need GitHub to take part: Workshop comments and battle logs count too. The maintainer copies Workshop suggestions with numbers into issues.

## Labels

`suggestion`, `test-report`, `needs-testing`, `accepted`, `rejected`, `in-build`, and one label per faction.

Every accepted or rejected suggestion gets a short reason.
