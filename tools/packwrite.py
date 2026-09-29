#!/usr/bin/env python3
"""Write Total War .pack files (PFH5) and encode db/loc payloads.

Companion to packread.py / dbread.py. Round-trip verified against
graetor's shipped pack.
"""
import struct, uuid, os
from dbread import load_defs
import gamever

# ---------------------------------------------------------------- pack

def build_pack(entries, pfh_type=3):
    """entries: list of (path, bytes). Returns the complete .pack bytes."""
    index = bytearray()
    data = bytearray()
    for path, payload in entries:
        index += struct.pack("<I", len(payload))
        index += b"\x00"                      # per-entry flag byte
        index += path.replace("/", "\\").encode("utf-8") + b"\x00"
        data += payload
    head = bytearray()
    head += b"PFH5"
    head += struct.pack("<I", pfh_type)       # bitmask: low nibble = pack type
    head += struct.pack("<I", 0)              # dependency count
    head += struct.pack("<I", 0)              # dependency block size
    head += struct.pack("<I", len(entries))
    head += struct.pack("<I", len(index))
    head += struct.pack("<I", 0)              # timestamp
    return bytes(head + index + data)


# ------------------------------------------------------------- db rows

def _w_field(val, ftype):
    if ftype == "Boolean":
        return b"\x01" if val else b"\x00"
    if ftype == "I16":
        return struct.pack("<h", int(val))
    if ftype in ("I32", "ColourRGB"):
        return struct.pack("<i", int(val))
    if ftype == "I64":
        return struct.pack("<q", int(val))
    if ftype == "F32":
        return struct.pack("<f", float(val))
    if ftype == "F64":
        return struct.pack("<d", float(val))
    if ftype == "StringU8":
        b = str(val).encode("utf-8")
        return struct.pack("<H", len(b)) + b
    if ftype == "StringU16":
        s = str(val)
        return struct.pack("<H", len(s)) + s.encode("utf-16-le")
    if ftype == "OptionalStringU8":
        if val is None or val == "":
            return b"\x00"
        b = str(val).encode("utf-8")
        return b"\x01" + struct.pack("<H", len(b)) + b
    if ftype == "OptionalStringU16":
        if val is None or val == "":
            return b"\x00"
        s = str(val)
        return b"\x01" + struct.pack("<H", len(s)) + s.encode("utf-16-le")
    raise ValueError("unhandled field type: %s" % ftype)


def _default_for(ftype):
    if ftype == "Boolean":
        return False
    if ftype in ("I16", "I32", "I64", "ColourRGB"):
        return 0
    if ftype in ("F32", "F64"):
        return 0.0
    return ""


def build_db(table, version, rows, guid=None):
    """rows: list of dicts keyed by field name. Missing fields take a default.

    The version is not a free choice. The game decodes our rows with its own
    layout for whatever number we stamp in the header, so it has to be the number
    the shipped game data uses. Writing names at version 1 when the game is on 0
    turns every row into nonsense and crashes the campaign on load, which is
    exactly what happened. Refuse it here rather than find out in a crash report.
    """
    defs = load_defs(table)
    if version not in defs:
        raise ValueError("no schema for %s v%d (have %s)" % (table, version, sorted(defs)))
    g_ver = gamever.ver(table)
    if g_ver is not None and g_ver != version:
        raise ValueError(
            "%s: refusing to write version %d, the game is on version %d. "
            "A higher version number is a DIFFERENT layout, not a newer one."
            % (table, version, g_ver))
    fields = defs[version]
    out = bytearray()
    g = guid or str(uuid.uuid4())
    out += b"\xfd\xfe\xfc\xff"
    out += struct.pack("<H", len(g)) + g.encode("utf-16-le")
    if version != 0:
        out += b"\xfc\xfd\xfe\xff" + struct.pack("<i", version)
    out += b"\x01"                            # mysterious byte
    out += struct.pack("<I", len(rows))
    for r in rows:
        for name, ftype in fields:
            out += _w_field(r.get(name, _default_for(ftype)), ftype)
    return bytes(out)


# ------------------------------------------------------------ loc rows

def build_loc(pairs, version=1):
    """pairs: list of (key, text)."""
    out = bytearray()
    out += b"\xff\xfe" + b"LOC" + b"\x00"
    out += struct.pack("<I", version)
    out += struct.pack("<I", len(pairs))
    for row in pairs:
        k, v = row[0], row[1]
        tip = row[2] if len(row) > 2 else 0
        out += struct.pack("<H", len(k)) + k.encode("utf-16-le")
        out += struct.pack("<H", len(v)) + v.encode("utf-16-le")
        out += bytes([tip])                   # tooltip flag
    return bytes(out)
