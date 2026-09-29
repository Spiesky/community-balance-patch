#!/usr/bin/env python3
"""Check every foreign key in the built pack actually points at something.

A pack whose tables all decode can still kill the campaign. The database loads
at the main menu, but picking a campaign is when the campaign tables get
resolved against each other, and a row pointing at a key that does not exist
takes the game down there rather than at load.

The schema already knows where every column points: each field carries
is_reference: Some(("table", "column")). So rather than guess which of our rows
is wrong, take every string field we write, look up what it is supposed to
reference, and check the value exists either in the vanilla dump or somewhere
in the pack itself.

    python3 refcheck.py [pack]
"""
import os, sys
from packread import Pack
from dbread import decode, load_refs
import vanilla

PACK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "build", "community_balance_patch.pack")
# required mods whose keys count as valid targets: python3 refcheck.py <pack> <required pack> ...
REQUIRED = sys.argv[2:]

# Columns the game treats as free text or as an id space of its own, where a
# "missing" reference means nothing.
SKIP = {
    ("loc", ""),
}


def pack_rows(pack):
    """{table_without_suffix: [rows]} for everything in the pack."""
    out, vers = {}, {}
    for n, _, _ in pack.entries:
        if not n.startswith("db/"):
            continue
        t = n.split("/")[1]
        try:
            v, cols, rows = decode(pack.get(n), t)
        except Exception:
            continue
        out.setdefault(t[:-7], []).extend(rows)
        vers[t[:-7]] = v
    return out, vers


def main():
    pack = Pack(PACK)
    rows, vers = pack_rows(pack)
    print("%s: %d tables" % (os.path.basename(PACK), len(rows)))
    required = {}
    for rp in REQUIRED:
        for t, rr in pack_rows(Pack(rp))[0].items():
            required.setdefault(t, []).extend(rr)

    # Which (table, column) pairs does anything we ship point at?
    wanted = set()
    for t in rows:
        for f, (rt, rc) in load_refs(t + "_tables").get(vers[t], {}).items():
            wanted.add((rt, rc))

    # Build the universe of valid keys for each of those: vanilla plus the pack.
    universe, missing_tables = {}, set()
    for rt, rc in sorted(wanted):
        vals = set()
        vrows = vanilla.table(rt)
        if vrows:
            if rc in vrows[0]:
                vals |= {r[rc] for r in vrows}
            else:
                missing_tables.add("%s.%s (column not in the dump)" % (rt, rc))
        for r in rows.get(rt, []) + required.get(rt, []):
            if rc in r:
                vals.add(str(r[rc]))
        if not vals and not vrows and rt not in rows:
            missing_tables.add("%s (table not in the dump or the pack)" % rt)
        universe[(rt, rc)] = vals

    dangling, checked = {}, 0
    for t in sorted(rows):
        refs = load_refs(t + "_tables").get(vers[t], {})
        if not refs:
            continue
        for r in rows[t]:
            for f, (rt, rc) in refs.items():
                val = r.get(f, "")
                if val in ("", None):
                    continue              # empty means "no requirement"
                val = str(val)
                checked += 1
                pool = universe.get((rt, rc), set())
                if not pool:
                    continue              # nothing to check against, not a finding
                if val not in pool:
                    key = (t, f, rt, rc)
                    dangling.setdefault(key, []).append(
                        (r.get("key") or r.get(list(r)[0]), val))

    print("%d foreign key values checked against %d key pools\n" % (checked, len(universe)))

    if missing_tables:
        print("reference targets that could not be resolved at all:")
        for m in sorted(missing_tables):
            print("    %s" % m)
        print()

    if not dangling:
        print("PASS: no dangling references")
        return 0

    total = sum(len(v) for v in dangling.values())
    print("DANGLING REFERENCES: %d values across %d columns\n" % (total, len(dangling)))
    for (t, f, rt, rc), hits in sorted(dangling.items(), key=lambda kv: -len(kv[1])):
        print("  %s.%s -> %s.%s   (%d bad)" % (t, f, rt, rc, len(hits)))
        for owner, val in hits[:6]:
            print("      %-50s = %s" % (owner, val))
        if len(hits) > 6:
            print("      ... and %d more" % (len(hits) - 6))
        print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
