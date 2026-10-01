#!/usr/bin/env python3
"""Patch day, step 1: re-read the game's own data into vanilla_db/, straight from the installed packs (no RPFM needed).

Everything the patch writes is a change against these rows, so after a CA update this is all it takes to rebuild the
patch on the new numbers; any stat CA changed is picked up, and rows CA made identical to ours drop out on the build.

    python3 refresh_vanilla.py            # reads <game>/data/db.pack and local_en.pack, writes ../vanilla_db
    CBP_GAME=/path/to/game python3 refresh_vanilla.py

The export is written to a new folder and swapped in only when every table decoded. If anything differs, the old export
moves to vanilla_db.prev/ and every table is listed with the rows CA added, removed or changed (by key), and every unit
CA changed that the community list also changes is named: the first things to look at after a patch. If nothing
differs, nothing is touched. Needs the zstandard module (CA compresses the packs): ~/Tools/venvs/wh3/bin/python.
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
# the folder that holds data/db.pack: CBP_GAME, or the usual Steam places on Linux, macOS (the Feral port) and Windows
GAME = os.environ.get("CBP_GAME") or next(
    (p for p in (os.path.expanduser("~/.local/share/Steam/steamapps/common/Total War WARHAMMER III"),
                 os.path.expanduser("~/Library/Application Support/Steam/steamapps/common/Total War WARHAMMER III/TotalWarhammer3Data"),
                 r"C:\Program Files (x86)\Steam\steamapps\common\Total War WARHAMMER III")
     if os.path.exists(os.path.join(p, "data", "db.pack"))),
    os.path.expanduser("~/.local/share/Steam/steamapps/common/Total War WARHAMMER III"))


def tables_used():
    """every table any tool reads (V.table("x") / V.index("x") / V.where("x")) or writes (coerce("x", ...) /
    gamever.ver("x")): a table the pack writes needs its game version from the export too, or the build cannot stamp it"""
    names = set()
    for f in glob.glob(os.path.join(HERE, "*.py")):
        src = open(f).read()
        names |= set(re.findall(r"""\bV\.(?:table|index|where)\(\s*["']([a-z0-9_]+)["']""", src))
        names |= set(re.findall(r"""\b(?:coerce|gamever\.ver)\(\s*["']([a-z0-9_]+)["']""", src))
        names |= {n[:-7] for n in re.findall(r"""["']db/([a-z0-9_]+_tables)/""", src)}
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


def read_export(root):
    """{table: {row key: row as a tuple}} of an export; the key is the first of key / unit / id the table has, else the row"""
    out = {}
    for d in glob.glob(os.path.join(root, "*_tables")):
        rows = {}
        for f in sorted(glob.glob(os.path.join(d, "*.tsv"))):
            with open(f, encoding="utf-8", errors="replace") as fh:
                cols = fh.readline().rstrip("\n").split("\t")
                marker = fh.readline()
                kc = next((cols.index(c) for c in ("key", "unit", "id") if c in cols), None)
                rows["#version"] = marker.split(";")[1] if ";" in marker else "?"
                for line in fh:
                    cells = tuple(line.rstrip("\n").split("\t"))
                    rows[cells[kc] if kc is not None and kc < len(cells) else cells] = cells
        out[os.path.basename(d)] = rows
    return out


def differences(old, new):
    """per table: (old version, new version, keys added, keys removed, keys whose row changed)"""
    out = {}
    for t in sorted(set(old) | set(new)):
        o, n = old.get(t, {}), new.get(t, {})
        added = sorted(str(k) for k in n if k not in o and k != "#version")
        removed = sorted(str(k) for k in o if k not in n and k != "#version")
        changed = sorted(str(k) for k in n if k in o and k != "#version" and n[k] != o[k])
        if added or removed or changed or o.get("#version") != n.get("#version"):
            out[t] = (o.get("#version"), n.get("#version"), added, removed, changed)
    return out


def main():
    if not os.path.exists(os.path.join(GAME, "data", "db.pack")):
        raise SystemExit("no data/db.pack under %s: set CBP_GAME to the game folder that holds data/" % GAME)
    db = Pack(os.path.join(GAME, "data", "db.pack"))
    # Everything is written to a new folder first and swapped in only when every table decoded: a refresh that fails
    # half way (a table version the schema does not know yet) leaves vanilla_db and vanilla_db.prev exactly as they were.
    NEW = OUT + ".new"
    shutil.rmtree(NEW, ignore_errors=True)
    os.makedirs(NEW)
    want = tables_used()
    files = {}
    for name, _, _ in db.entries:
        parts = name.split("/")
        if len(parts) == 3 and parts[0] == "db" and parts[1][:-7] in want:
            files.setdefault(parts[1], []).append(name)
    missing = [t for t in want if t + "_tables" not in files]
    total = 0
    for table, names in sorted(files.items()):
        d = os.path.join(NEW, table)
        os.makedirs(d)
        for name in names:
            version, cols, rows = decode(db.get(name), table)
            fname = name.split("/")[-1]
            with open(os.path.join(d, fname + ".tsv"), "w", encoding="utf-8") as fh:
                fh.write("\t".join(cols) + "\n")
                fh.write("#%s;%d;%s" % (table, version, name) + "\t" * (len(cols) - 1) + "\n")
                for r in rows:
                    fh.write("\t".join(cell(r[c]) for c in cols) + "\n")
            total += len(rows)
    loc = Pack(os.path.join(GAME, "data", "local_en.pack"))
    locname = "text/db/land_units__.loc"
    rows = read_loc(loc.get(locname))
    os.makedirs(os.path.join(NEW, "text", "db"), exist_ok=True)
    with open(os.path.join(NEW, "text", "db", "land_units__.loc.tsv"), "w", encoding="utf-8") as fh:
        fh.write("key\ttext\ttooltip\n#Loc;1;%s\t\t\n" % locname)
        for k, t, tip in rows:
            fh.write("%s\t%s\t%s\n" % (k, t.replace("\t", " ").replace("\n", "\\n"), tip))
    for t in missing:                                     # not in db.pack: kept from the current export if it is there
        src = os.path.join(OUT, t + "_tables")
        if os.path.isdir(src):
            shutil.copytree(src, os.path.join(NEW, t + "_tables"))
    print("read %d tables (%d rows) and %d unit names from %s" % (len(files), total, len(rows), GAME))
    if missing:
        print("   not in db.pack (kept from the old export if there):", missing)
    had = os.path.isdir(OUT)
    diff = differences(read_export(OUT) if had else {}, read_export(NEW))
    old_names = open(os.path.join(OUT, "text", "db", "land_units__.loc.tsv"), encoding="utf-8").read() if had and os.path.exists(os.path.join(OUT, "text", "db", "land_units__.loc.tsv")) else None
    names_changed = old_names != open(os.path.join(NEW, "text", "db", "land_units__.loc.tsv"), encoding="utf-8").read()
    if had and not diff and not names_changed:
        shutil.rmtree(NEW)
        print("   nothing changed: the game's data is what vanilla_db already holds (vanilla_db.prev left as it was)")
        return
    for t, (v0, v1, added, removed, changed) in diff.items():
        what = []
        if v0 != v1:
            what.append("version %s -> %s" % (v0, v1))
        for label, keys in (("new", added), ("gone", removed), ("changed", changed)):
            if keys:
                what.append("%d %s (%s%s)" % (len(keys), label, ", ".join(keys[:6]), ", ..." if len(keys) > 6 else ""))
        print("   changed: %-52s %s" % (t, "; ".join(what)))
    if names_changed and had:
        print("   changed: unit names (text/db/land_units__.loc): community.py matches by name, run community.py to see what moved")
    if had:
        shutil.rmtree(OUT + ".prev", ignore_errors=True)
        os.rename(OUT, OUT + ".prev")
    os.rename(NEW, OUT)
    if had:
        listed_units_changed(diff)


def listed_units_changed(diff):
    """the community list's numbers are changes against vanilla: if CA has just changed a unit the list also changes,
    CA may have done what the list asked, and applying it again would do it twice. Name those units."""
    try:
        import vanilla as V
        import unit_model as UM
        import community as C
    except Exception as e:                                # the export is in place either way
        print("   (could not cross-check the community list: %s)" % e)
        return
    MU, LU, MIS = V.index("main_units", "unit"), V.index("land_units"), V.index("missile_weapons")
    moved = {t: set(v[4]) for t, v in diff.items()}
    hits = {}
    for line, pat, ch, keys in C.resolve(UM.recruitable(), UM.name, UM.faction):
        for k in keys:
            lu = LU.get(MU[k]["land_unit"], {})
            proj = MIS.get(lu.get("primary_missile_weapon", ""), {}).get("default_projectile", "")
            if (k in moved.get("main_units_tables", ()) or lu.get("key") in moved.get("land_units_tables", ())
                    or lu.get("primary_melee_weapon") in moved.get("melee_weapons_tables", ())
                    or proj in moved.get("projectiles_tables", ())):
                hits.setdefault(line, set()).add(UM.name(k))
    for line, names in sorted(hits.items()):
        print("   LOOK: CA changed %s, which community list entry %d also changes: has CA done it already?" % (", ".join(sorted(names)), line))


if __name__ == "__main__":
    main()
