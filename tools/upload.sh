#!/bin/bash
# Upload a build to its Steam Workshop item with steamcmd: the pack, the preview image, the change note and the
# description (workshop/patch_description.txt or logger_description.txt, written by tools/workshop_text.py). The title
# and the visibility are left as they are on the page.
#
#   tools/upload.sh                    show what would be uploaded, upload nothing
#   tools/upload.sh --upload           upload the patch          (item 3810476227)
#   tools/upload.sh --upload logger    upload the Battle Logger  (item 3810476307)
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPID=1142710
STEAMCMD="${STEAMCMD:-$HOME/steamcmd/steamcmd.sh}"
WHAT="patch"; UPLOAD=0
for a in "$@"; do
    case "$a" in --upload) UPLOAD=1 ;; logger) WHAT="logger" ;; patch) WHAT="patch" ;; *) echo "unknown argument: $a"; exit 1 ;; esac
done
VERSION="$(cat "$ROOT/VERSION")"
if [ "$WHAT" = "patch" ]; then
    ID=3810476227; PACK="$ROOT/build/beta/community_balance_patch.pack"; PNG="$ROOT/workshop/community_balance_patch.png"
    NOTE="$ROOT/workshop/change_note.txt"; DESC="$ROOT/workshop/patch_description.txt"
else
    ID=3810476307; PACK="$ROOT/build/community_balance_patch_battle_logger.pack"; PNG="$ROOT/workshop/community_balance_patch_battle_logger.png"
    NOTE="$ROOT/workshop/logger_change_note.txt"; DESC="$ROOT/workshop/logger_description.txt"
fi
[ -f "$DESC" ] || { echo "no description: $DESC (run tools/patch_day.sh)"; exit 1; }
# the description goes into the .vdf as one quoted value: it may hold newlines, but not a double quote or a backslash
if grep -q '["\\]' "$DESC"; then echo "$DESC contains a double quote or a backslash, which the .vdf cannot carry"; exit 1; fi
[ -f "$PACK" ] || { echo "not built: $PACK (run tools/patch_day.sh)"; exit 1; }
[ -f "$PNG" ] || { echo "no preview image: $PNG"; exit 1; }
[ -f "$NOTE" ] || { echo "no change note: $NOTE (run python3 tools/workshop_text.py)"; exit 1; }
PROBLEMS=""
if [ "$WHAT" = "patch" ]; then
    # the pack must be the one tools/patch_day.sh checked and stamped, for this VERSION, with a note for this VERSION
    STAMP="$ROOT/build/beta/CHECKED"
    SUM="$(shasum -a 256 "$PACK" | cut -d' ' -f1)"
    if [ ! -f "$STAMP" ] || [ "$(cat "$STAMP")" != "$SUM  $VERSION" ]; then
        PROBLEMS="$PROBLEMS\n  the pack is not the one the checks stamped for version $VERSION: run tools/patch_day.sh"
    fi
    grep -q "^Beta $VERSION\. " "$NOTE" || PROBLEMS="$PROBLEMS\n  the change note is not for version $VERSION: run tools/patch_day.sh"
    grep -q "^## $VERSION (.*not uploaded yet" "$ROOT/CHANGELOG.md" && PROBLEMS="$PROBLEMS\n  CHANGELOG.md still says '$VERSION (... not uploaded yet)': put the date there and run tools/patch_day.sh"
    [ -n "$(git -C "$ROOT" status --porcelain 2>/dev/null)" ] && PROBLEMS="$PROBLEMS\n  uncommitted changes: commit, tag (git tag beta-$VERSION) and push first, so the pages the description links to exist"
else
    grep -q "not uploaded yet" "$NOTE" && PROBLEMS="$PROBLEMS\n  the Battle Logger's CHANGELOG.md entry still says 'not uploaded yet': put the date there and run tools/patch_day.sh"
fi
CONTENT="$ROOT/build/workshop/$WHAT"
rm -rf "$CONTENT"; mkdir -p "$CONTENT"            # the whole folder is published: nothing stale in it
cp "$PACK" "$CONTENT/"; cp "$PNG" "$CONTENT/"
VDF="$ROOT/build/workshop/$WHAT.vdf"
CHANGENOTE="$(tr '\n' ' ' < "$NOTE" | sed 's/"/'"'"'/g; s/  */ /g')"
cat > "$VDF" <<VDF
"workshopitem"
{
    "appid"            "$APPID"
    "publishedfileid"  "$ID"
    "contentfolder"    "$CONTENT"
    "previewfile"      "$CONTENT/$(basename "$PNG")"
    "changenote"       "$CHANGENOTE"
    "description"      "$(cat "$DESC")"
}
VDF
echo "item $ID ($WHAT), version $VERSION"
ls -la "$CONTENT" | tail -n +4 | sed 's/^/    /'
echo "change note: $(echo "$CHANGENOTE" | cut -c1-200)..."
echo "description: $DESC ($(wc -c < "$DESC" | tr -d ' ') characters)"
echo "vdf: $VDF"
if [ -n "$PROBLEMS" ]; then
    printf "\nnot ready to upload:$PROBLEMS\n"
fi
if [ "$UPLOAD" != 1 ]; then
    echo
    echo "nothing uploaded. Follow docs/RELEASING.md, then: tools/upload.sh --upload $WHAT"
    exit 0
fi
[ -z "$PROBLEMS" ] || exit 1
[ -x "$STEAMCMD" ] || { echo "steamcmd not found at $STEAMCMD (set STEAMCMD)"; exit 1; }
read -r -p "Steam username: " STEAMUSER
LOG="$ROOT/build/workshop/$WHAT.log"
# steamcmd asks for the password and the Steam Guard approval itself: its output goes to the screen and to a log
"$STEAMCMD" +login "$STEAMUSER" +workshop_build_item "$VDF" +quit 2>&1 | tee "$LOG" || true
if grep -q "Success" "$LOG"; then
    echo "UPLOADED $WHAT $VERSION to item $ID. Now: git push, git push --tags, and the release on GitHub (docs/RELEASING.md)."
else
    echo "NOT uploaded: the reason is in the lines above (a Steam Guard prompt left unanswered times out after about a minute)."
    exit 1
fi
