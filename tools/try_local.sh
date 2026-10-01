#!/bin/bash
# Put the freshly built packs where the game on this Mac loads mods from, to test a build before it is uploaded.
# No Steam, no upload.
#
#   tools/try_local.sh            install build/beta/community_balance_patch.pack and the Battle Logger
#   tools/try_local.sh restore    remove the local copies (the launcher links the Workshop versions back in)
#
# ORDER MATTERS on the Feral (macOS) version: its Mod Manager rebuilds the mods folder every time the launcher opens.
#   1. open the launcher   2. LEAVE IT OPEN and run this   3. tick both mods, press Play
# Run it before opening the launcher and the manager replaces the files with the Workshop copies again.
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${CBP_MODS_DIR:-$HOME/Library/Application Support/Feral Interactive/Total War WARHAMMER III/VFS/Local/mods}"
PATCH="community_balance_patch.pack"
LOGGER="community_balance_patch_battle_logger.pack"
[ -d "$DEST" ] || { echo "Not found: $DEST (set CBP_MODS_DIR to the game's mods folder)"; exit 1; }
if [ "${1:-}" = "restore" ]; then
    rm -f "$DEST/$PATCH" "$DEST/$LOGGER"
    echo "removed the local copies. Reopen the launcher and it links the Workshop versions back in."
    exit 0
fi
for src in "$ROOT/build/beta/$PATCH" "$ROOT/build/$LOGGER"; do      # both or neither: never half an install
    [ -f "$src" ] || { echo "not built: $src (run tools/patch_day.sh)"; exit 1; }
done
for pair in "build/beta/$PATCH:$PATCH" "build/$LOGGER:$LOGGER"; do
    src="$ROOT/${pair%%:*}"; name="${pair##*:}"
    rm -f "$DEST/$name"                      # the Workshop copy is a symlink: replace the link, not its target
    cp "$src" "$DEST/$name"
    echo "installed $name ($(wc -c < "$src" | tr -d ' ') bytes, version $(cat "$ROOT/VERSION"))"
done
echo "Now tick both in the launcher and press Play. 'tools/try_local.sh restore' puts the Workshop versions back."
