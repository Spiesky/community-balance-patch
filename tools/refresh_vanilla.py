#!/usr/bin/env python3
"""Patch day, step 1: re-read the game's own data into vanilla_db/, straight from the installed packs (no RPFM needed).

Everything the patch writes is a change against these rows, so after a CA update this is all it takes to rebuild the
patch on the new numbers; any stat CA changed is picked up, and rows CA made identical to ours drop out on the build.

    python3 refresh_vanilla.py            # reads <game>/data/db.pack and local_en.pack, writes ../vanilla_db
    CBP_GAME=/path/to/game python3 refresh_vanilla.py

The old export is kept in vanilla_db.prev/ and every table whose version or row count changed is listed, which is the
first thing to look at after a patch. Needs the zstandard module (CA compresses the packs): ~/Tools/venvs/wh3/bin/python.
"""
import glob
import os
import re
import shutil
import struct
import sys

from packread import Pack
from dbread import decode

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, "vanilla_db")
GAME = os.environ.get("CBP_GAME", os.path.expanduser("~/.local/share/Steam/steamapps/common/Total War WARHAMMER III"))


def tables_used():
    """every table any tool reads: V.table("x") / V.index("x") / V.where("x")"""
    names = set()
    for f in glob.glob(os.path.join(HERE, "*.py")):
        names |= set(re.findall(r"""\bV\.(?:table|index|where)\(\s*["']([a-z0-9_]+)["']""", open(f).read()))
    return sorted(n for n in names if len(n) > 2)


def cell(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return "%.4f" % v
    return str(v).replace("\t", " ").replace("\n", "\\n")


def read_loc(data):
    """WH3 .loc: FF FE 'LOC' 00, version, count, then (key, text, tooltip-bool) with u16-length UTF-16 strings"""
    pos = 2 + 4 + 4
    count = struct.unpack_from("<I", data, pos)[0]
    pos += 4
    rows = []
    for _ in range(count):
        out = []
        for _s in range(2):
            n = struct.unpack_from("<H", data, pos)[0]
            pos += 2
            out.append(data[pos:pos + 2 * n].decode("utf-16-le"))
            pos += 2 * n
        out.append("true" if data[pos] else "false")
        pos += 1
        rows.append(out)
    return rows


def old_state():
    st = {}
    for d in glob.glob(os.path.join(OUT, "*_tables")):
        n, ver = 0, None
        for f in glob.glob(os.path.join(d, "*.tsv")):
            with open(f, encoding="utf-8", errors="replace") as fh:
                fh.readline()
                m = fh.readline().split(";")
                ver = m[1] if len(m) > 1 else ver
                n += sum(1 for _ in fh)
        st[os.path.basename(d)] = (ver, n)
    return st


def main():
    db = Pack(os.path.join(GAME, "data", "db.pack"))
    before = old_state()
    if os.path.isdir(OUT):
        shutil.rmtree(OUT + ".prev", ignore_errors=True)
        shutil.copytree(OUT, OUT + ".prev")
    want = tables_used()
    files = {}
    for name, _, _ in db.entries:
        parts = name.split("/")
        if len(parts) == 3 and parts[0] == "db" and parts[1][:-7] in want:
            files.setdefault(parts[1], []).append(name)
    missing = [t for t in want if t + "_tables" not in files]
    after = {}
    for table, names in sorted(files.items()):
        d = os.path.join(OUT, table)
        shutil.rmtree(d, ignore_errors=True)
        os.makedirs(d)
        total, version = 0, None
        for name in names:
            version, cols, rows = decode(db.get(name), table)
            fname = name.split("/")[-1]
            with open(os.path.join(d, fname + ".tsv"), "w", encoding="utf-8") as fh:
                fh.write("\t".join(cols) + "\n")
                fh.write("#%s;%d;%s" % (table, version, name) + "\t" * (len(cols) - 1) + "\n")
                for r in rows:
                    fh.write("\t".join(cell(r[c]) for c in cols) + "\n")
            total += len(rows)
        after[table] = (str(version), total)
    loc = Pack(os.path.join(GAME, "data", "local_en.pack"))
    locname = "text/db/land_units__.loc"
    rows = read_loc(loc.get(locname))
    os.makedirs(os.path.join(OUT, "text", "db"), exist_ok=True)
    with open(os.path.join(OUT, "text", "db", "land_units__.loc.tsv"), "w", encoding="utf-8") as fh:
        fh.write("key\ttext\ttooltip\n#Loc;1;%s\t\t\n" % locname)
        for k, t, tip in rows:
            fh.write("%s\t%s\t%s\n" % (k, t.replace("\t", " ").replace("\n", "\\n"), tip))
    print("read %d tables (%d rows) and %d unit names from %s" % (len(after), sum(n for _, n in after.values()), len(rows), GAME))
    for t in sorted(after):
        if before.get(t) != after[t]:
            print("   changed: %-60s %s -> %s  (version, rows)" % (t, before.get(t), after[t]))
    if missing:
        print("   not in db.pack (kept from the old export if there):", missing)
        for t in missing:
            src = os.path.join(OUT + ".prev", t + "_tables")
            if os.path.isdir(src) and not os.path.isdir(os.path.join(OUT, t + "_tables")):
                shutil.copytree(src, os.path.join(OUT, t + "_tables"))


if __name__ == "__main__":
    main()
