#!/usr/bin/env python3
"""Sum up battle logs from the Battle Logger add-on (cbp_battle_log.txt files players share).

    python3 battle_logs.py logs/*.txt                      the per-unit tables
    python3 battle_logs.py --unit blood_knights logs/*.txt only units whose key contains the text
    python3 battle_logs.py --csv units.csv logs/*.txt      also write the tables as one CSV file

The format is docs/LOG_FORMAT.md (versions 1 and 2). This file is also the parser the other tools import:
load(paths) gives the blocks and the read counts, read(paths) just the blocks.

What is kept apart, always: the patch version (vanilla / patched <version>), fought and auto-resolved battles, the
player's units and the other side's, battles with no other mods and battles with other mods loaded (or a mod
list that could not be read: "mods ?"), and the two log versions (version 1 counts models, version 2 counts hit points: the two are never mixed).

What the columns mean:
  HP lost    mean fraction of its hit points a unit lost in a battle (version 2). Works for single entities too.
  kills      mean kills per unit per battle. Kills count entities: a Giant is one kill, so is a Skavenslave.
  k/100%HP   kills per 100% of its own hit points lost, over the units that lost any. "-" when none did.
  rout W/L   share of units seen routing at any time (ever_routed), for units on the winning side and on the losing
             side. Version 1 logs only say who was routing when the battle ended, which is the losing side, so
             routing is not reported for them.
  battles    distinct battles behind the row; files: distinct log files. Files written by fetch_logs.py
             (issue_<number>_<author>.txt) count one per author. Any other file counts one per file, whatever its
             name: the tool cannot tell whether two hand-saved files came from the same player.
  side       in fought battles "player side" is the player's alliance: the logger flags every unit of it, so an AI
             ally reinforcing the player is in these rows too. In auto-resolved battles "player" is a human faction.
"Kills per model lost" is not printed. It is biased by unit size: a change that halves a unit's models while keeping
its strength doubles the ratio without the unit fighting any better.

The same file is often shared more than once: a block is counted once (identity: hash of its header and unit lines).
"""
import collections, csv, datetime, hashlib, os, re, statistics, sys

PATCH = "community_balance_patch.pack"
LOGGER = "community_balance_patch_battle_logger.pack"
AR_TEST = "cbp_autoresolve"             # cbp_autoresolve_test.pack: the packs that carry the auto-resolve rules
SIZES = (0.25, 0.5, 0.75, 1.0)          # small, medium, large, ultra
MIN_MEN = 20                            # single entities and small units do not scale cleanly with unit size
PAIR_MINUTES = 30                       # a fought #result is written this soon after its #battle, or it is another battle


def num(text, kind=float):
    """A number, or None for '?', an empty field or anything that is not a number"""
    try:
        v = kind(text)
    except (TypeError, ValueError):
        return None
    return v if v == v and v not in (float("inf"), float("-inf")) else None


def flag(text):
    """True for '1', False for '0', None for '?' or anything else"""
    return True if text == "1" else False if text == "0" else None


def classify(head):
    """The mods of a battle, from its header fields, per the table at the end of docs/LOG_FORMAT.md"""
    raw = head.get("mods")
    known = raw not in (None, "", "unknown", "?")
    packs = [p.strip().lower() for p in raw.split("|") if p.strip() and p.strip().lower() != "none"] if known else []
    cbp = head.get("cbp")
    if cbp not in (None, "", "?", "none"):
        patched, version = True, cbp
    else:                               # logger 1, or a patch build from before it carried its version
        patched, version = PATCH in packs, None
    others = [p for p in packs if p != PATCH and p != LOGGER and not p.startswith(AR_TEST)]
    return dict(packs=packs, mods_known=known, patched=patched, cbp=version,
                ar_rules=any(p.startswith(AR_TEST) for p in packs), others=others,
                clean=known and not others,
                patch="patched " + (version or "(no version)") if patched else "vanilla" if known or cbp == "none" else "patch ?")


def source(path):
    """Who a log file came from: fetch_logs.py names files issue_<number>_<author>.txt, so the author. Any other
    file is its own source, by its full path: every player's file is called cbp_battle_log.txt, so the name alone
    would merge them."""
    m = re.match(r"issue_\d+_(.+)\.txt$", os.path.basename(path))
    return "author:" + m.group(1) if m else "file:" + os.path.abspath(path)


def when(date):
    """The time of a header date ('YYYY-MM-DD HH:MM'), or None for '?' or anything else"""
    try:
        return datetime.datetime.strptime(date.strip(), "%Y-%m-%d %H:%M")
    except (AttributeError, ValueError):
        return None


def decode(data):
    """The text of a log file. The logger writes UTF-8; an editor may have re-saved it with a byte-order mark or as UTF-16."""
    if data[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return data.decode("utf-16", errors="replace")
    return data.decode("utf-8-sig", errors="replace")


def parse(text, path="", info=None):
    """The blocks of one log, in file order, fought results paired with their battles. Never raises on bad input."""
    info = info if info is not None else collections.Counter()
    blocks, cur = [], None
    for line in text.replace("\r", "\n").split("\n"):
        line = line.strip().strip("\ufeff")
        if not line:
            continue
        f = line.split(";")
        if line.startswith("#error;") or line.startswith("#debug;"):
            info["diagnostic lines"] += 1
        elif line == "#end":
            if cur is not None:
                blocks.append(cur)
            cur = None
        elif line.startswith("#") and len(f) >= 3 and re.match(r"v\d+$", f[1]):
            if cur is not None:
                info["truncated blocks"] += 1           # a header before the #end of the block above
            head = dict(p.split("=", 1) for p in f[3:] if "=" in p)
            cur = dict(name=f[0][1:], version=int(f[1][1:]), date=f[2], head=head, units=[], lines=[line], file=path)
            cur["kind"] = {"battle": "battle", "result": "result", "autoresolve": "result"}.get(cur["name"])
            if cur["kind"] == "result":
                cur["mode"] = "auto" if cur["name"] == "autoresolve" else head.get("mode", "?")
            cur.update(classify(head))
        elif cur is None:
            continue                                    # the comment line at the top, or the tail of a cut block
        elif f[0] == "u" and cur["kind"] == "battle" and len(f) >= 10:
            g = f + ["?"] * (17 - len(f))
            cur["units"].append(dict(
                alliance=num(g[1], int), army=num(g[2], int), player=flag(g[3]), key=g[4], men=num(g[5], int),
                alive=num(g[6], int), kills=num(g[7], int), routing=flag(g[8]), shattered=flag(g[9]), hp=num(g[10]),
                ammo=num(g[11]), ammo_start=num(g[12]), general=flag(g[13]), ever_routed=flag(g[14]),
                first_rout_s=num(g[15]), uid=g[16]))
            cur["lines"].append(line)
        elif f[0] == "r" and cur["kind"] == "result" and len(f) >= 7:
            g = f + ["?"] * (9 - len(f))
            cur["units"].append(dict(side=num(g[1], int), army=num(g[2], int), player=flag(g[3]), key=g[4],
                                     before=num(g[5]), after=num(g[6]), xp=num(g[7], int), faction=g[8]))
            cur["lines"].append(line)
        elif f[0] == "a" and cur["kind"] == "result" and len(f) >= 6:
            cur["units"].append(dict(side=num(f[1], int), army=None, player=flag(f[2]), key=f[3],
                                     before=num(f[4]), after=num(f[5]), xp=None, faction="?"))
            cur["lines"].append(line)
        # any other line type inside a block is one this parser does not know: skipped
    if cur is not None:
        info["truncated blocks"] += 1                   # the file ends inside a block
    info["unknown blocks"] += sum(1 for b in blocks if not b["kind"])       # a block type from a later version
    blocks = [b for b in blocks if b["kind"]]
    for b in blocks:
        b["id"] = hashlib.sha1("\n".join(b["lines"]).encode("utf-8")).hexdigest()
        b["source"] = source(path)
    pair(blocks)
    return blocks


def pair(blocks):
    """A fought #result describes the campaign #battle written just before it in the same file. Only the nearest
    one is tried, and only if the two list the same kind of units and the result is dated at or up to PAIR_MINUTES
    after the battle: if the battle script failed to write its block, an older battle must not be taken for this one
    (two battles of the same army list the same units). No pair when either date cannot be read."""
    last = None                                         # the nearest preceding campaign battle
    for b in blocks:
        if b["kind"] == "battle" and b["head"].get("campaign") == "1":
            last = b
        elif b["kind"] == "result" and b["mode"] == "fought" and last is not None and "result_id" not in last:
            mine = set(u["key"] for u in b["units"])
            theirs = set(u["key"] for u in last["units"])
            t0, t1 = when(last["date"]), when(b["date"])
            close = t0 is not None and t1 is not None and 0 <= (t1 - t0).total_seconds() <= PAIR_MINUTES * 60
            if close and mine and len(mine & theirs) * 2 >= len(mine):
                last["result_id"], b["battle_id"] = b["id"], last["id"]


def load(paths):
    """(blocks, info): every distinct block of every file, and the counts of what was read"""
    info = collections.Counter()
    seen, out = {}, []
    for path in paths:
        try:
            with open(path, "rb") as fh:
                text = decode(fh.read())
        except OSError as e:
            info["unreadable files"] += 1
            print("cannot read %s: %s" % (path, e), file=sys.stderr)
            continue
        info["files"] += 1
        found = parse(text, path, info)
        if not found:
            info["files without blocks"] += 1
            print("%s: no log blocks found" % path, file=sys.stderr)
        for b in found:
            info["blocks"] += 1
            if b["id"] in seen:
                info["duplicates"] += 1
                first = seen[b["id"]]                   # a later copy may have the pair the first copy was cut from
                for k in ("result_id", "battle_id"):
                    if k in b and k not in first:
                        first[k] = b[k]
                continue
            seen[b["id"]] = b
            out.append(b)
    for b in out:                                       # link the pairs, both ways, among the blocks that were kept
        other = seen.get(b.get("result_id"))
        if other is not None and other.get("battle_id") == b["id"]:
            b["result"], other["battle"] = other, b
    info["distinct files"] = len(set(b["source"] for b in out))
    return out, info


def read(paths):
    """The distinct blocks of the given log files (see load for the counts as well)"""
    for b in load(paths)[0]:
        yield b


def vanilla_men():
    """unit key -> vanilla models at ultra size; empty when vanilla_db is not there (the size is then unknown)"""
    try:
        import vanilla as V
        return {k: int(r["num_men"]) for k, r in V.index("main_units", "unit").items() if r.get("num_men", "").isdigit()}
    except Exception:
        return {}


def unit_size(battle, men):
    """The unit-size setting of a #battle block (0.25, 0.5, 0.75 or 1), or None if it cannot be told.
    As docs/LOG_FORMAT.md says: units with fewer than 20 models in vanilla are left out (a lord is 1 model at every
    size), and the middle ratio is used, not the largest (a patched unit with more models than vanilla would
    otherwise raise the size)."""
    result = battle.get("result")
    if battle["head"].get("campaign") == "1" and result is None:
        return None                                     # strength before the battle unknown: units may be depleted
    before = collections.defaultdict(float)
    for u in (result["units"] if result else []):
        if u["before"]:
            before[(u["key"], u["player"])] = max(before[(u["key"], u["player"])], u["before"])
    most = collections.defaultdict(int)
    for u in battle["units"]:
        if u["men"]:
            most[(u["key"], u["player"])] = max(most[(u["key"], u["player"])], u["men"])
    ratios = []
    for k, m in most.items():
        full = men.get(k[0], 0)
        strength = before.get(k) if result else 100.0
        if full >= MIN_MEN and strength:
            ratios.append(m / (full * strength / 100.0))
    if not ratios:
        return None
    r = statistics.median(ratios)
    size = min(SIZES, key=lambda s: abs(s - r))
    return size if abs(size - r) <= 0.125 else None


def who(battle, unit):
    if unit["player"] is None:
        return "?"
    if unit["player"]:
        # in a #battle the flag is the player's alliance (allied AI armies too), in a result a human faction
        return "player side" if battle["kind"] == "battle" else "player"
    return "human" if battle["head"].get("multiplayer") == "1" else "AI"


def tables(blocks, only=None):
    """section -> {(unit, patch, mode, who, mods): totals}. Sections: 'v2' fought (hit points), 'v1' fought
    (models), 'auto' auto-resolved (strength)."""
    men = vanilla_men()
    out = {"v2": {}, "v1": {}, "auto": {}}

    def row(section, b, u, mode):
        mods = "clean" if b["clean"] else "other mods" if b["mods_known"] else "mods ?"
        key = (u["key"], b["patch"], mode, who(b, u), mods)
        s = out[section].setdefault(key, dict(battles=set(), files=set(), sizes=set(), c=collections.Counter()))
        s["battles"].add(b["id"])
        s["files"].add(b["source"])
        return s

    for b in blocks:
        if b["kind"] == "battle" and b["version"] >= 2:
            size = unit_size(b, men)
            winner = num(b["head"].get("winner"), int)
            for u in b["units"]:
                if (only and only not in u["key"]) or u["hp"] is None:
                    continue                            # no hit points read: nothing to measure the unit by
                s = row("v2", b, u, "fought")
                c = s["c"]
                s["sizes"].add(size)
                lost = min(1.0, max(0.0, 1.0 - u["hp"]))
                c["units"] += 1
                c["hp_lost"] += lost
                c["campaign"] += b["head"].get("campaign") == "1"
                if u["kills"] is not None:
                    c["kill_units"] += 1
                    c["kills"] += u["kills"]
                    if lost > 0:
                        c["kills_hurt"] += u["kills"]
                        c["hp_lost_hurt"] += lost
                if u["ever_routed"] is not None and winner in (1, 2) and u["alliance"] in (1, 2):
                    side = "won" if u["alliance"] == winner else "lost"
                    c[side] += 1
                    c[side + "_routed"] += u["ever_routed"]
        elif b["kind"] == "battle":
            for u in b["units"]:
                if (only and only not in u["key"]) or u["men"] is None or u["alive"] is None or u["men"] <= 0:
                    continue
                c = row("v1", b, u, "fought")["c"]
                c["units"] += 1
                c["men"] += u["men"]
                c["men_lost"] += max(0, u["men"] - u["alive"])
                if u["kills"] is not None:
                    c["kill_units"] += 1
                    c["kills"] += u["kills"]
        elif b["mode"] == "auto":
            for u in b["units"]:
                if (only and only not in u["key"]) or not u["before"] or u["after"] is None:
                    continue
                c = row("auto", b, u, "auto+rules" if b["ar_rules"] else "auto")["c"]
                c["units"] += 1
                c["strength_lost"] += min(1.0, max(0.0, (u["before"] - u["after"]) / u["before"]))
    return out


def ratio(a, b, fmt="%.0f%%", scale=100.0):
    return fmt % (scale * a / b) if b else "-"


def cells(section, s):
    """The printed cells of one row, after the five key columns"""
    c = s["c"]
    base = [str(len(s["battles"])), str(len(s["files"]))]
    if section == "v2":
        sizes = ",".join("?" if z is None else "%g" % z for z in sorted(s["sizes"], key=lambda z: z or 0))
        return base + [str(c["campaign"]), sizes, ratio(c["hp_lost"], c["units"]),
                       ratio(c["kills"], c["kill_units"], "%.1f", 1), ratio(c["kills_hurt"], c["hp_lost_hurt"], "%.1f", 1),
                       ratio(c["won_routed"], c["won"]), ratio(c["lost_routed"], c["lost"])]
    if section == "v1":
        return base + [ratio(c["men_lost"], c["men"]), ratio(c["kills"], c["kill_units"], "%.1f", 1)]
    return base + [ratio(c["strength_lost"], c["units"])]


KEYS = ["unit", "patch", "mode", "side", "mods"]
SECTIONS = [
    ("v2", "Fought battles, log version 2 (hit points)",
     ["battles", "files", "campaign", "size", "HP lost", "kills", "k/100%HP", "rout W", "rout L"]),
    ("v1", "Fought battles, log version 1 (models lost: not comparable with the hit points above; no routing)",
     ["battles", "files", "models lost", "kills"]),
    ("auto", "Auto-resolved battles (percent of the unit's strength lost; auto+rules: the auto-resolve test pack was loaded)",
     ["battles", "files", "strength lost"]),
]


def main():
    args = sys.argv[1:]
    only = out_csv = None
    for opt in ("--unit", "--csv"):
        if opt in args:
            i = args.index(opt)
            if i + 1 >= len(args):
                sys.exit(opt + " needs a value")
            if opt == "--unit":
                only = args[i + 1]
            else:
                out_csv = args[i + 1]
            del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    blocks, info = load(args)
    print("read %d blocks from %d files: %d duplicates left out, %d distinct blocks from %d distinct log files"
          % (info["blocks"], info["files"], info["duplicates"], len(blocks), info["distinct files"]))
    extra = ["%d %s" % (info[k], k) for k in ("truncated blocks", "unknown blocks", "diagnostic lines", "unreadable files", "files without blocks") if info[k]]
    if extra:
        print("skipped: " + ", ".join(extra))
    fought = [b for b in blocks if b["kind"] == "battle"]
    print("files: fetch_logs.py files count one per issue author, any other file one per file")
    print("%d fought (%d version 1, %d paired with a campaign result), %d auto-resolved, %d campaign results of fought battles"
          % (len(fought), sum(b["version"] < 2 for b in fought), sum("result" in b for b in fought),
             sum(b["kind"] == "result" and b["mode"] == "auto" for b in blocks),
             sum(b["kind"] == "result" and b["mode"] == "fought" for b in blocks)))
    if not vanilla_men():
        print("vanilla_db not found: unit size shown as ?")
    rows, all_tables = [], tables(blocks, only)
    for section, title, cols in SECTIONS:
        table = all_tables[section]
        if not table:
            continue
        print("\n" + title)
        print("%-46s %-22s %-10s %-11s %-10s " % tuple(KEYS) + " ".join("%*s" % (max(8, len(c)), c) for c in cols))
        for key in sorted(table):
            vals = cells(section, table[key])
            print("%-46s %-22s %-10s %-11s %-10s " % ((key[0][:46],) + key[1:]) + " ".join("%*s" % (max(8, len(c)), v) for c, v in zip(cols, vals)))
            rows.append(dict(zip(["section"] + KEYS + cols, [section] + list(key) + vals)))
    if not rows:
        print("\nno units to report")
    if out_csv:
        names = ["section"] + KEYS
        for _, _, cols in SECTIONS:
            names += [c for c in cols if c not in names]
        with open(out_csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, names, restval="")
            w.writeheader()
            w.writerows(rows)
        print("\nwrote %s (%d rows)" % (out_csv, len(rows)))


if __name__ == "__main__":
    main()
