#!/usr/bin/env python3
"""Decode Total War db tables out of a .pack using schema_wh3.ron."""
import struct, sys, re, os
from packread import Pack

# RPFM's WH3 schema (RPFM keeps it current: Settings > Update Schemas). CBP_SCHEMA points elsewhere.
SCHEMA = os.environ.get("CBP_SCHEMA") or next(
    (p for p in (os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_wh3.ron"),
                 os.path.expanduser("~/.config/rpfm/schemas/schema_wh3.ron"),
                 os.path.join(os.environ.get("APPDATA", ""), "FrodoWazEre", "rpfm", "config", "schemas", "schema_wh3.ron"))
     if os.path.exists(p)), "schema_wh3.ron")
_cache = {}


def load_defs(table):
    """Return {version: [(fieldname, type), ...]} for a table."""
    if table in _cache:
        return _cache[table]
    txt = open(SCHEMA, "r", encoding="utf-8").read()
    m = re.search(r'\n        "%s": \[\n' % re.escape(table), txt)
    if not m:
        _cache[table] = {}
        return {}
    start = m.end()
    # the table block ends at the next `\n        ],\n`
    end = txt.index("\n        ],\n", start)
    block = txt[start:end]
    defs = {}
    # split into versioned definitions
    for vm in re.finditer(r"version:\s*(-?\d+),\s*\n\s*fields:\s*\[", block):
        ver = int(vm.group(1))
        fstart = vm.end()
        depth = 1
        i = fstart
        while depth:
            if block[i] == "[":
                depth += 1
            elif block[i] == "]":
                depth -= 1
            i += 1
        fblock = block[fstart:i - 1]
        fields = []
        for fm in re.finditer(r'name:\s*"([^"]+)",\s*\n\s*field_type:\s*([A-Za-z0-9_]+)', fblock):
            fields.append((fm.group(1), fm.group(2)))
        defs[ver] = fields
    # local layouts the RPFM schema does not know yet (schema_patch.json, keyed by table then version)
    patch_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema_patch.json")
    if os.path.exists(patch_path):
        import json as _json
        patch = _json.load(open(patch_path))
        for pv, pf in patch.get(table, {}).items():
            defs[int(pv)] = [tuple(f) for f in pf]
        # "_fallback": used only where the schema has no layout for that version at all (an older schema file)
        for pv, pf in patch.get("_fallback", {}).get(table, {}).items():
            defs.setdefault(int(pv), [tuple(f) for f in pf])
    _cache[table] = defs
    return defs


_refcache = {}


def load_refs(table):
    """{version: {field: (referenced_table, referenced_column)}}.

    The schema declares the game's own foreign keys. A row pointing at a key
    that does not exist is the classic cause of a campaign that loads its
    database fine and then dies the moment you pick a campaign, because that is
    when the campaign tables get resolved against each other.
    """
    if table in _refcache:
        return _refcache[table]
    txt = open(SCHEMA, "r", encoding="utf-8").read()
    m = re.search(r'\n        "%s": \[\n' % re.escape(table), txt)
    if not m:
        _refcache[table] = {}
        return {}
    start = m.end()
    end = txt.index("\n        ],\n", start)
    block = txt[start:end]
    out = {}
    for vm in re.finditer(r"version:\s*(-?\d+),\s*\n\s*fields:\s*\[", block):
        ver = int(vm.group(1))
        i, depth = vm.end(), 1
        while depth:
            if block[i] == "[":
                depth += 1
            elif block[i] == "]":
                depth -= 1
            i += 1
        refs = {}
        for chunk in block[vm.end():i - 1].split('name: "')[1:]:
            fname = chunk.split('"', 1)[0]
            rm = re.search(r'is_reference:\s*Some\(\("([^"]+)",\s*"([^"]+)"\)\)', chunk)
            if rm:
                refs[fname] = (rm.group(1), rm.group(2))
        out[ver] = refs
    _refcache[table] = out
    return out


def read_field(d, pos, ftype):
    if ftype == "Boolean":
        return bool(d[pos]), pos + 1
    if ftype in ("I16",):
        return struct.unpack_from("<h", d, pos)[0], pos + 2
    if ftype in ("I32", "ColourRGB"):
        return struct.unpack_from("<i", d, pos)[0], pos + 4
    if ftype == "I64":
        return struct.unpack_from("<q", d, pos)[0], pos + 8
    if ftype == "F32":
        return struct.unpack_from("<f", d, pos)[0], pos + 4
    if ftype == "F64":
        return struct.unpack_from("<d", d, pos)[0], pos + 8
    if ftype == "StringU8":
        n = struct.unpack_from("<H", d, pos)[0]
        pos += 2
        return d[pos:pos + n].decode("utf-8", "replace"), pos + n
    if ftype == "StringU16":
        n = struct.unpack_from("<H", d, pos)[0]
        pos += 2
        return d[pos:pos + n * 2].decode("utf-16-le", "replace"), pos + n * 2
    if ftype == "OptionalStringU8":
        has = d[pos]
        pos += 1
        if not has:
            return "", pos
        n = struct.unpack_from("<H", d, pos)[0]
        pos += 2
        return d[pos:pos + n].decode("utf-8", "replace"), pos + n
    if ftype == "OptionalStringU16":
        has = d[pos]
        pos += 1
        if not has:
            return "", pos
        n = struct.unpack_from("<H", d, pos)[0]
        pos += 2
        return d[pos:pos + n * 2].decode("utf-16-le", "replace"), pos + n * 2
    raise ValueError("unhandled field type: %s" % ftype)


def decode(data, table):
    pos = 0
    guid = None
    version = 0
    if data[0:4] == b"\xfd\xfe\xfc\xff":
        pos = 4
        n = struct.unpack_from("<H", data, pos)[0]
        pos += 2
        guid = data[pos:pos + n * 2].decode("utf-16-le")
        pos += n * 2
    if data[pos:pos + 4] == b"\xfc\xfd\xfe\xff":
        pos += 4
        version = struct.unpack_from("<i", data, pos)[0]
        pos += 4
    pos += 1  # mysterious byte
    count = struct.unpack_from("<I", data, pos)[0]
    pos += 4

    defs = load_defs(table)
    if version not in defs:
        raise ValueError("no schema for %s v%d (have %s)" % (table, version, sorted(defs)))
    fields = defs[version]
    rows = []
    for _ in range(count):
        row = {}
        for name, ftype in fields:
            row[name], pos = read_field(data, pos, ftype)
        rows.append(row)
    return version, [f[0] for f in fields], rows


def dump(packpath, needle, maxrows=None):
    p = Pack(packpath)
    for n, _, _ in p.entries:
        if not n.startswith("db/"):
            continue
        table = n.split("/")[1]
        if needle not in n:
            continue
        data = p.get(n)
        try:
            ver, cols, rows = decode(data, table)
        except Exception as e:
            print("## %s  -> ERROR %s" % (n, e))
            continue
        print("## %s  (v%d, %d rows)" % (n, ver, len(rows)))
        print("   " + " | ".join(cols))
        for r in (rows if maxrows is None else rows[:maxrows]):
            print("   " + " | ".join(str(r[c]) for c in cols))
        print()


if __name__ == "__main__":
    mx = int(sys.argv[3]) if len(sys.argv) > 3 else None
    dump(sys.argv[1], sys.argv[2], mx)
