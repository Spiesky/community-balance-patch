#!/usr/bin/env python3
"""Build the Battle Logger pack from logger/*.lua.

    python3 build_logger.py            -> ../build/community_balance_patch_battle_logger.pack

Two scripts and nothing else: the battle script goes to script/battle/mod/, the campaign script to script/campaign/mod/.
The pack's name is the one on the Workshop and must not change (the game's mod list is kept by pack name).
"""
import os

import packwrite

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.environ.get("CBP_LOGGER_OUT") or os.path.join(ROOT, "build", "community_balance_patch_battle_logger.pack")
FILES = [("script/battle/mod/cbp_battle_logger.lua", "cbp_battle_logger.lua"),
         ("script/campaign/mod/cbp_autoresolve_logger.lua", "cbp_autoresolve_logger.lua")]


def main():
    entries = []
    for path, name in FILES:
        data = open(os.path.join(ROOT, "logger", name), "rb").read()
        if b"\r\n" in data:
            raise SystemExit("%s has Windows line endings; save it with Unix ones" % name)
        entries.append((path, data))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "wb").write(packwrite.build_pack(entries))
    print("written: %s  %d bytes; %s" % (OUT, os.path.getsize(OUT), ", ".join("%s %d" % (p.split("/")[-1], len(d)) for p, d in entries)))


if __name__ == "__main__":
    main()
