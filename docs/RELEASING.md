# Releasing: how a build becomes a Workshop update

A release is one Workshop upload of the patch. It has a version, a tag, an entry in `CHANGELOG.md` and a page that
says what is in it (`reports/beta_changelog.md`). Nothing is uploaded that those do not describe, and the order below
is there so that a player who clicks any link on the Workshop page finds what the page promised.

## Before the upload

1. **Bump `VERSION`** and **write the `CHANGELOG.md` entry** for it: `## <version> (<date>)`, the game version, and
   what changed since the last upload in plain words. Name who proposed and who tested each change. If the Battle
   Logger changed, give its entry a date too. (`tools/patch_day.sh` stops if the entry is missing, and
   `tools/upload.sh` refuses while an entry still says "not uploaded yet".)
2. **`tools/patch_day.sh`.** Every check has to pass. It builds `build/beta/community_balance_patch.pack`,
   `build/community_balance_patch_battle_logger.pack` and `build/cbp_autoresolve_test.pack`, regenerates
   `reports/beta_changelog.md`, the unit pages and the Workshop texts (`workshop/*.txt`), and stamps the pack
   (`build/beta/CHECKED`).
3. **Open it in game.** `tools/try_local.sh` (on a Mac) installs both packs. Then:
   - Custom battle: read the cards of one unit from each theme against `reports/beta_changelog.md`: Blood Knights (24
     models at Ultra), Handgunners (ammunition 14), Greatswords, Chaos Warriors.
   - Fight that custom battle to the end, then a second one that you quit half way. Open `cbp_battle_log.txt`: there
     should be a `#battle;v2` block for the first with `cbp=<version>`, hit points and a winner. Note whether the quit
     wrote a block at all, and what its `winner=` says; `docs/TESTING.md` tells players what to expect, so correct it
     if it is wrong.
   - Campaign: auto-resolve one battle and fight one. Each should leave a `#result;v2` block: `mode=auto` for the
     first, `mode=fought` for the second, with `strength_before` different from `strength_after` and destroyed units
     at 0. A fought battle written as `mode=auto` with before equal to after means the game fires the battle's start
     event again on the way back; an `#error` line says what else went wrong.
   - `python3 tools/battle_logs.py cbp_battle_log.txt`: the fought campaign battle should be "paired with a campaign
     result" and show the unit size you play at.
4. **Commit, tag and push**: `git tag beta-<VERSION>`, `git push`, `git push --tags`. The Workshop description links
   to pages in the repository and to the upload page; they have to exist before the description says so. Check that
   [the upload page](https://spiesky.github.io/community-balance-patch/) shows the "Copy summary" button.
5. **Create the GitHub release** for the tag and attach `build/beta/community_balance_patch.pack`,
   `build/cbp_autoresolve_test.pack` (`docs/AUTORESOLVE.md` sends players there for it) and `reports/beta_changelog.md`.
6. **Start the test thread** in the Workshop page's discussions, with the recipe pasted in full (the lead test of
   `units/blood_knights.md`), and post your own runs in it first. The description links to the recipe; the thread is
   where results go.

## The upload

    tools/upload.sh                    # shows what would be uploaded and anything that is not ready; uploads nothing
    tools/upload.sh --upload           # the patch (asks for the Steam login; approve it on the phone)
    tools/upload.sh --upload logger    # the Battle Logger, only when logger/ changed

`upload.sh` sends the pack, the preview image, the change note and the description (`workshop/*_description.txt`);
the title and visibility stay as they are on the page. It refuses a pack `patch_day.sh` did not stamp for
this `VERSION`, a change note for another version, an undated `CHANGELOG.md` entry, and uncommitted changes.

## After the upload

- Subscribe and check that the game loads the Workshop copy (`tools/try_local.sh restore` removes the local one).
- After a CA patch: run `patch_day.sh` again and read its "changed:" lines (the rows CA changed, by key) and its
  "LOOK:" lines (units CA changed that the community list also changes: if CA did what the list asked, drop the entry
  from `community.py`, or the change is made twice). Release even if nothing else changed, so the pack never overrides
  CA's new numbers with old ones.
