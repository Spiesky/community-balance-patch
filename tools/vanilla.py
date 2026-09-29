#!/usr/bin/env python3
"""Read the vanilla WH3 database from vanilla_db/ (TSV exported from the installed game's db.pack with RPFM:
header row, then a #table;version;path line, then rows). CBP_DB points elsewhere."""
import csv, os, functools

DUMP = os.environ.get("CBP_DB", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vanilla_db"))


@functools.lru_cache(maxsize=None)
def table(name):
    d = os.path.join(DUMP, name + "_tables")
    if not os.path.isdir(d):
        return []
    out = []
    for f in sorted(os.listdir(d)):
        if not f.endswith(".tsv"):
            continue
        with open(os.path.join(d, f), newline="", encoding="utf-8", errors="replace") as fh:
            r = csv.reader(fh, delimiter="\t", quoting=csv.QUOTE_NONE)
            cols = next(r)
            next(r, None)                      # the #table;version;path line
            for row in r:
                if len(row) < len(cols):
                    row = row + [""] * (len(cols) - len(row))
                out.append(dict(zip(cols, row)))
    return out


def index(name, key="key"):
    return {r[key]: r for r in table(name) if key in r}


def where(name, **kw):
    return [r for r in table(name) if all(r.get(k) == v for k, v in kw.items())]
