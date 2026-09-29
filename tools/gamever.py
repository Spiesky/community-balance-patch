#!/usr/bin/env python3
"""The one place that knows which schema version the game is actually on.

Every db file in a pack carries a version number, and the game decodes the rows
with ITS layout for that number. The RPFM schema often knows several versions of
a table, and a higher number is not a newer or better layout, it is just a
different one: resource_costs version 0 has six fields and version 2 has four,
names version 0 starts with an I64 id and version 1 starts with four I32s. Write
the wrong number and every row after the header is garbage, which is what the
game means by "the first invalid database record is N in table X".

The dump tells us the answer for free. Each extracted TSV carries a line

    #<table>_tables;<version>;db/<table>_tables/data__

which is the version the shipped game data is on. That is the number to write.

This module is the authority; packwrite.build_db refuses anything that
contradicts it.
"""
import json, os, glob

from vanilla import DUMP

_v = None


def _scan_dump():
    out = {}
    for path in glob.glob(os.path.join(DUMP, "*_tables", "*.tsv")):
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                fh.readline()                     # header row
                marker = fh.readline()
        except OSError:
            continue
        if marker.startswith("#"):
            bits = marker[1:].split(";")
            if len(bits) >= 2 and bits[1].strip().isdigit():
                out[bits[0].strip()] = int(bits[1])
    return out


def versions():
    """{table_name_with_tables_suffix: version the game is on}, read from vanilla_db/."""
    global _v
    if _v is None:
        _v = _scan_dump()
    return _v


def ver(table, default=None):
    """Version for a table, named with or without the _tables suffix."""
    v = versions()
    if table in v:
        return v[table]
    if table + "_tables" in v:
        return v[table + "_tables"]
    return default


def known():
    return bool(versions())


if __name__ == "__main__":
    v = versions()
    print("%d tables known" % len(v))
    for t in ("names_tables", "character_skill_node_sets_tables",
              "resource_costs_tables", "land_units_tables",
              "unit_upgrade_to_unit_groups_tables"):
        print("  %-45s %s" % (t, v.get(t)))
