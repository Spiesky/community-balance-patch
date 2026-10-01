#!/usr/bin/env python3
"""Check the log readers against the hand-written logs in testdata/ (docs/LOG_FORMAT.md, versions 1 and 2).

    python3 test_logs.py        prints one line per check, exits 1 if any fails

Covers the parser (both versions, Windows line endings, ? values, added fields, unknown lines and blocks, #error
lines, blocks cut short), duplicates, the mod classification, pairing results with battles, the unit size, the
per-unit tables, the auto-resolve calibration and fetch_logs.py (log extraction, and a rerun against a stubbed
GitHub: no network is used).
"""
import contextlib, csv, io, json, os, subprocess, sys, tempfile, urllib.error
import battle_logs as BL

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "testdata")
FILES = [os.path.join(DATA, f) for f in ("v1_logger1.txt", "v2_logger2.txt", "v2_shared_again.txt")]
P, L = "community_balance_patch.pack", "community_balance_patch_battle_logger.pack"
failed = []


def check(name, got, want):
    ok = got == want
    print("%-4s %s" % ("ok" if ok else "FAIL", name) + ("" if ok else "\n       got  %r\n       want %r" % (got, want)))
    if not ok:
        failed.append(name)


def near(name, got, want):
    check(name, None if got is None else round(got, 3), want)


# ---- parser, duplicates
blocks, info = BL.load(FILES)
by_date = {b["date"]: b for b in blocks}
check("blocks read", info["blocks"], 14)
check("duplicates", info["duplicates"], 2)
check("distinct blocks", len(blocks), 12)
check("files", (info["files"], info["distinct files"]), (3, 3))
check("truncated blocks", info["truncated blocks"], 2)
check("unknown blocks", info["unknown blocks"], 1)
check("diagnostic lines", info["diagnostic lines"], 2)
check("read() yields the same blocks", [b["id"] for b in BL.read(FILES)], [b["id"] for b in blocks])
check("kinds", sorted((b["kind"], b["version"], b.get("mode")) for b in blocks), sorted([
    ("battle", 1, None), ("result", 1, "auto"), ("battle", 2, None), ("result", 2, "fought"), ("result", 2, "auto"),
    ("battle", 2, None), ("result", 2, "auto"), ("result", 2, "auto"), ("result", 2, "fought"), ("result", 2, "auto"),
    ("battle", 2, None), ("result", 2, "fought")], key=str))

v1 = by_date["2026-09-30 20:01"]
check("v1 battle: Windows line endings, 4 units", len(v1["units"]), 4)
check("v1 unit fields", [v1["units"][0][k] for k in ("alliance", "player", "key", "men", "alive", "kills", "hp", "ever_routed")],
      [1, True, "wh_main_emp_inf_swordsmen", 120, 90, 40, None, None])
check("v1 '?' kills is missing, not a number", v1["units"][3]["kills"], None)
ar1 = by_date["2026-09-30 20:10"]
check("v1 autoresolve unit", [ar1["units"][1][k] for k in ("side", "player", "key", "before", "after")],
      [1, True, "wh_main_emp_inf_handgunners", 100.0, 50.0])

A = by_date["2026-10-02 21:14"]
check("v2 battle header", [A["head"].get(k) for k in ("campaign", "player", "winner", "secs", "cbp")], ["1", "1", "1", "612", "0.2.0"])
check("v2 battle: unknown line skipped, 5 units", len(A["units"]), 5)
check("v2 unit fields", [A["units"][1][k] for k in ("hp", "ammo", "general", "ever_routed", "first_rout_s", "uid")],
      [0.65, None, False, True, 300.0, "2"])
check("v2 unit with a field added later", (A["units"][4]["key"], A["units"][4]["uid"]), ("wh_main_grn_mon_giant", "5"))
B = by_date["2026-10-02 21:40"]
check("result: unknown header key kept, mods still read", (B["head"].get("new_key"), B["packs"]), ("5", [P, L]))
check("result: '?' strength is missing", (B["units"][2]["before"], B["units"][2]["after"]), (None, None))
bom = "\ufeff#battle;v1;2026-09-30 20:01;multiplayer=0;siege=0;mods=none\nu;1;1;1;wh_main_emp_inf_swordsmen;120;90;40;0;0\n#end\n"
with tempfile.TemporaryDirectory() as tmp:
    for name, data in (("bom.txt", bom.encode("utf-8")), ("utf16.txt", bom.encode("utf-16")), ("empty.txt", b"not a log\n")):
        open(os.path.join(tmp, name), "wb").write(data)
    check("a file starting with a byte-order mark keeps its first block", len(BL.load([os.path.join(tmp, "bom.txt")])[0]), 1)
    check("a UTF-16 file is read", len(BL.load([os.path.join(tmp, "utf16.txt")])[0]), 1)
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        got = BL.load([os.path.join(tmp, "empty.txt")])
    check("a file with no blocks is named", (len(got[0]), got[1]["files without blocks"], "empty.txt: no log blocks found" in err.getvalue()), (0, 1, True))
    for who in ("alice", "bob"):
        os.mkdir(os.path.join(tmp, who))
        open(os.path.join(tmp, who, "cbp_battle_log.txt"), "w").write(bom.replace("20:01", "20:0%d" % len(who)))
    check("two players' files with the default name are two files",
          BL.load([os.path.join(tmp, w, "cbp_battle_log.txt") for w in ("alice", "bob")])[1]["distinct files"], 2)
check("parse() drops a byte-order mark too", len(BL.parse(bom)), 1)
check("empty input", BL.parse(""), [])
check("garbage input", BL.parse("hello\nu;1;2\n#end\n#battle\n;;;\n#battle;v2\n"), [])

# ---- classification
def cls(b):
    return (b["patch"], b["ar_rules"], b["clean"])


check("logger 1 with the patch", cls(v1), ("patched (no version)", False, True))
check("patched 0.2.0, clean", cls(A), ("patched 0.2.0", False, True))
check("another mod loaded", cls(by_date["2026-10-03 18:30"]) + (by_date["2026-10-03 18:30"]["others"],),
      ("patched 0.2.0", False, False, ["some_other_mod.pack"]))
check("auto-resolve test pack loaded", cls(by_date["2026-10-03 19:00"]), ("patched 0.2.0", True, True))
check("vanilla, no mods", cls(by_date["2026-10-03 19:20"]), ("vanilla", False, True))
check("logger 2, patch build without a version", cls(by_date["2026-10-03 20:00"]), ("patched (no version)", False, True))
check("mod list unknown is not clean", cls(by_date["2026-10-03 20:30"]), ("patch ?", False, False))
check("a cbp_ pack that is not ours is another mod", BL.classify({"mods": "cbp_something_else.pack"})["clean"], False)
check("logger pack alone is vanilla and clean", cls(BL.parse("#battle;v1;d;multiplayer=0;siege=0;mods=%s\n#end\n" % L)[0]),
      ("vanilla", False, True))

# ---- pairing
RA = by_date["2026-10-02 21:15"]
check("fought result paired with the battle before it", (A.get("result") is RA, RA.get("battle") is A), (True, True))
check("a result whose battle is missing does not take an older battle", "battle" in by_date["2026-10-03 20:00"], False)
check("a result with other units is not paired", ("result" in by_date["2026-10-04 19:00"], "battle" in by_date["2026-10-04 19:30"]), (False, False))
check("custom battles are never paired", "result" in by_date["2026-10-03 18:30"], False)


def camp(kind, date, strength="100", men="60"):
    if kind == "battle":
        return ("#battle;v2;%s;campaign=1;type=land_normal;multiplayer=0;siege=0;player=1;attacker=1;winner=1;secs=300;cbp=0.2.0;mods=none\n"
                "u;1;1;1;wh_main_emp_inf_swordsmen;%s;50;10;0;0;0.800;?;?;0;0;?;1\n#end\n" % (date, men))
    return ("#result;v2;%s;mode=fought;winner=attacker;turn=2;difficulty=hard;type=land_normal;ambush=0;night=0;settlement=0;quest=;"
            "campaign=main_warhammer;player_side=1;cbp=0.2.0;mods=none\nr;1;1;1;wh_main_emp_inf_swordsmen;%s;40;0;wh_main_emp_empire\n#end\n" % (date, strength))


D = "2026-10-06 "
late = {b["date"]: b for b in BL.parse(camp("battle", D + "14:00") + camp("battle", D + "14:30") + camp("result", D + "14:01")
                                       + camp("result", D + "14:31", "50"))}
check("a result dated before the battle is not paired with it", ("result_id" in late[D + "14:30"], "battle_id" in late[D + "14:01"]), (True, False))
check("  the battle takes the result written after it", late[D + "14:30"]["result_id"], late[D + "14:31"]["id"])
old = BL.parse(camp("battle", D + "10:05") + camp("result", D + "13:00"))
check("a result three hours after the battle is not paired", "result_id" in old[0], False)
check("a result 30 minutes after the battle is paired", "result_id" in BL.parse(camp("battle", D + "10:05") + camp("result", D + "10:35"))[0], True)
check("no pair when a date is ?", "result_id" in BL.parse(camp("battle", "?") + camp("result", D + "10:06"))[0], False)
check("a result just after midnight is paired", "result_id" in BL.parse(camp("battle", "2026-10-06 23:59") + camp("result", "2026-10-07 00:01"))[0], True)

# ---- unit size (needs vanilla_db)
men = BL.vanilla_men()
if men:
    check("size: campaign battle at large, depleted unit, lord ignored", BL.unit_size(A, men), 0.75)
    check("size: custom battle at ultra", BL.unit_size(by_date["2026-10-03 18:30"], men), 1.0)
    check("size: campaign battle without its result is unknown", BL.unit_size(by_date["2026-10-04 19:00"], men), None)
else:
    print("skip unit size checks: vanilla_db not found")
if men:
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "late.txt")
        open(path, "w").write(camp("battle", D + "14:00") + camp("battle", D + "14:30") + camp("result", D + "14:01") + camp("result", D + "14:31", "50"))
        got = {b["date"]: b for b in BL.load([path])[0]}
        check("size: 60 men at 50% strength is ultra, from the battle's own result", BL.unit_size(got[D + "14:30"], men), 1.0)
check("size without vanilla_db is unknown", BL.unit_size(A, {}), None)

# ---- per-unit tables
T = BL.tables(blocks)
sw = ("wh_main_emp_inf_swordsmen", "patched 0.2.0", "fought", "player side", "clean")
check("v2 player swordsmen, clean: two battles, two files", (len(T["v2"][sw]["battles"]), len(T["v2"][sw]["files"])), (2, 2))
c = T["v2"][sw]["c"]
near("  mean HP lost (0.35 and 0.10)", c["hp_lost"] / c["units"], 0.225)
near("  kills per battle (40 and 90)", c["kills"] / c["kill_units"], 65.0)
near("  kills per 100% HP lost", c["kills_hurt"] / c["hp_lost_hurt"], 288.889)
check("  routed: both on the winning side, one routed", (c["won"], c["won_routed"], c["lost"]), (2, 1, 0))
check("  printed cells", BL.cells("v2", T["v2"][sw])[4:], ["22%", "65.0", "288.9", "50%", "-"])
hg = ("wh_main_emp_inf_handgunners", "patched 0.2.0", "fought", "player side", "clean")
check("no HP lost: ratio printed as -", BL.cells("v2", T["v2"][hg])[4:], ["0%", "80.0", "-", "0%", "-"])
check("AI rows are separate from player rows",
      BL.cells("v2", T["v2"][("wh_main_grn_inf_orc_boyz", "patched 0.2.0", "fought", "AI", "clean")])[4:],
      ["95%", "20.0", "21.1", "-", "100%"])
swm = ("wh_main_emp_inf_swordsmen", "patched 0.2.0", "fought", "player side", "other mods")
check("other mods kept apart; lost side routed", BL.cells("v2", T["v2"][swm])[4:], ["100%", "55.0", "55.0", "-", "100%"])
hgm = ("wh_main_emp_inf_handgunners", "patched 0.2.0", "fought", "player side", "other mods")
check("kills '?' prints -, HP still counted", BL.cells("v2", T["v2"][hgm])[4:], ["50%", "-", "-", "-", "100%"])
check("unit without hit points is left out of the v2 table",
      ("wh_main_grn_inf_orc_boyz", "patched 0.2.0", "fought", "AI", "other mods") in T["v2"], False)
check("version 1 battles are not in the hit point table", any(k[1] == "patched (no version)" for k in T["v2"]), False)
check("v1 table: models lost, no routing", BL.cells("v1", T["v1"][("wh_main_emp_inf_swordsmen", "patched (no version)", "fought", "player side", "clean")]),
      ["1", "1", "25%", "40.0"])
check("v1 table: '?' kills", BL.cells("v1", T["v1"][("wh_main_grn_mon_giant", "patched (no version)", "fought", "AI", "clean")]),
      ["1", "1", "100%", "-"])
check("auto table, v1 and v2 pooled by patch label only",
      sorted((k[1], k[2], k[4], BL.cells("auto", s)[2]) for k, s in T["auto"].items() if k[0] == "wh_main_emp_inf_swordsmen"),
      [("patch ?", "auto", "mods ?", "6%"), ("patched (no version)", "auto", "clean", "20%"), ("patched 0.2.0", "auto", "clean", "8%"),
       ("patched 0.2.0", "auto+rules", "clean", "30%"), ("vanilla", "auto", "clean", "60%")])
check("fought results are not in the auto table", any("empire_knights" in k[0] for k in T["auto"]), False)
ally = BL.parse(camp("battle", D + "09:00").replace("#end", "u;1;2;1;wh_main_brt_inf_men_at_arms;120;100;5;0;0;0.900;?;?;0;0;?;2\n#end"))
check("fought rows are the player's side (an allied army is flagged too), auto rows the player",
      (sorted(set(k[3] for k in BL.tables(ally)["v2"])), sorted(set(k[3] for k in T["auto"]))), (["player side"], ["AI", "player"]))
check("--unit filter", sorted(set(k[0] for t in BL.tables(blocks, "giant").values() for k in t)), ["wh_main_grn_mon_giant"])

# ---- the command line, with --csv
with tempfile.TemporaryDirectory() as tmp:
    out = os.path.join(tmp, "units.csv")
    run = subprocess.run([sys.executable, os.path.join(HERE, "battle_logs.py"), "--csv", out] + FILES, capture_output=True, text=True)
    check("battle_logs.py runs", run.returncode, 0)
    check("first line of the output", run.stdout.splitlines()[0] if run.stdout else run.stderr,
          "read 14 blocks from 3 files: 2 duplicates left out, 12 distinct blocks from 3 distinct log files")
    rows = list(csv.DictReader(open(out, encoding="utf-8")))
    check("csv rows = table rows", len(rows), sum(len(t) for t in T.values()))
    check("csv has no nan", any("nan" in v.lower() for r in rows for v in r.values() if r["unit"] != v), False)
    print("\n".join("     | " + l for l in run.stdout.splitlines()))

    # ---- calibration: 6 players, 4 fought and 4 auto-resolved battles each, made up so the answer is known
    try:
        import autoresolve_calibrate as AC
        classes = AC.unit_class()
    except Exception as e:
        classes = {}
        print("skip calibration checks: %s" % e)
    if classes:
        def result(n, mode, sword, gun, mods=P):
            return ["#result;v2;2026-10-05 %02d:%02d;mode=%s;winner=attacker;turn=%d;difficulty=hard;type=land_normal;ambush=0;"
                    "night=0;settlement=0;quest=;campaign=main_warhammer;player_side=1;cbp=0.2.0;mods=%s" % (n // 60, n % 60, mode, n, mods),
                    "r;1;1;1;wh_main_emp_inf_swordsmen;100;%d;0;wh_main_emp_empire" % sword,
                    "r;1;1;1;wh_main_emp_inf_handgunners;100;%d;0;wh_main_emp_empire" % gun,
                    "r;2;1;0;wh_main_grn_inf_orc_boyz;100;0;0;wh_main_grn_greenskins", "#end"]

        def write(players, per, auto_mods=P, name="issue_%d_player%d.txt"):
            paths, n = [], 0
            for p in range(players):
                lines = []
                for _ in range(per):
                    n += 1
                    lines += result(n, "fought", 60, 90) + result(n, "auto", 80, 60, auto_mods)
                paths.append(os.path.join(tmp, name % (p + 1, p)))
                open(paths[-1], "w").write("\n".join(lines) + "\n")
            return paths

        rows, rules, skipped, counts = AC.calibrate(BL.load(write(6, 4))[0], classes)
        r = {x["cls"]: x for x in rows}
        check("calibrate: battles used", counts, {"fought": 24, "auto": 24, "v1": 0})
        near("calibrate: handgunners take 20% of the losses with 50% of the strength when fought", r["inf_mis"]["fi"], 0.4)
        near("calibrate: and 67% when auto-resolved", r["inf_mis"]["ai"], 1.333)
        check("calibrate: rules (missile -0.70, melee held at the +0.5 limit)", rules, {"inf_mis": -0.7, "inf_mel": 0.5})
        check("calibrate: battles and files per class", (r["inf_mis"]["fought"]["n"], r["inf_mis"]["fought"]["files"]), (24, 6))
        rows, rules, skipped, counts = AC.calibrate(BL.load(write(4, 6))[0], classes)
        check("calibrate: 24 battles from 4 files is not enough", (rules, [x["rule"] for x in rows]), ({}, ["not enough data"] * 2))
        rows, rules, skipped, counts = AC.calibrate(BL.load(write(6, 3))[0], classes)
        check("calibrate: 18 battles from 6 files is not enough", (rules, [x["rule"] for x in rows]), ({}, ["not enough data"] * 2))
        rows, rules, skipped, counts = AC.calibrate(BL.load(write(6, 4, P + "|cbp_autoresolve_test.pack"))[0], classes)
        check("calibrate: auto battles with the test pack are not a baseline", (counts["auto"], rules), (0, {}))
        rows, rules, skipped, counts = AC.calibrate(BL.load(write(6, 4) + write(6, 4))[0], classes)
        check("calibrate: the same logs twice count once", counts["fought"], 24)
        hand = write(5, 5, name="log_%d_%d.txt")
        rows, rules, skipped, counts = AC.calibrate(BL.load(hand)[0], classes)
        r = {x["cls"]: x for x in rows}
        check("calibrate: hand-saved files are not counted as players, so no rule",
              (rules, r["inf_mis"]["fought"]["n"], r["inf_mis"]["fought"]["files"], r["inf_mis"]["rule"]), ({}, 25, 0, "not enough data"))
        check("calibrate: --trust-files counts them", AC.calibrate(BL.load(hand)[0], classes, trust=True)[1], {"inf_mis": -0.7, "inf_mel": 0.5})
        one = os.path.join(tmp, "issue_9_solo.txt")
        open(one, "w").write("".join(open(h).read() for h in hand))
        rows, rules, skipped, counts = AC.calibrate(BL.load([one])[0], classes)
        check("calibrate: 25 battles from one player: no rule and no interval", (rules, [x["ci"] for x in rows]), ({}, [None, None]))
        nomods = os.path.join(tmp, "issue_10_nomods.txt")
        open(nomods, "w").write("\n".join(result(900, "auto", 80, 60, "unknown") + [l.replace(";mods=x", "") for l in result(901, "auto", 80, 60, "x")]
                                          + result(902, "fought", 60, 90, "unknown")) + "\n")
        rows, rules, skipped, counts = AC.calibrate(BL.load([nomods])[0], classes, with_mods=True)
        check("calibrate: --include-modded never takes an auto battle with an unreadable mod list", counts, {"fought": 1, "auto": 0, "v1": 0})
        content, front = AC.to_write({"inf_mis": -0.7, "inf_mel": 0.5}, {"art_fld": -0.7, "inf_mis": -0.35, "cav_mis": -0.25})
        check("write: calibrated back-line classes over the rules in use, front line left out",
              (content["rules"], content["calibrated"], content["kept_from_before"], front),
              ({"art_fld": -0.7, "inf_mis": -0.7, "cav_mis": -0.25}, ["inf_mis"], ["art_fld", "cav_mis"], {"inf_mel": 0.5}))
        check("write: nothing calibrated when only a front-line class passes", AC.to_write({"inf_mel": 0.5}, dict(AC.BACK_LINE))[0]["calibrated"], [])
        # players who differ: the interval is taken over players, so it has width although every player's battles agree
        paths = []
        for p in range(6):
            lines = []
            for n in range(4):
                lines += result(p * 10 + n, "fought", 60, 90 if p % 2 else 40) + result(p * 10 + n, "auto", 80, 60)
            paths.append(os.path.join(tmp, "issue_%d_split%d.txt" % (p + 70, p)))
            open(paths[-1], "w").write("\n".join(lines) + "\n")
        r = {x["cls"]: x for x in AC.calibrate(BL.load(paths)[0], classes)[0]}
        check("calibrate: players who disagree give an interval with width", r["inf_mis"]["ci"][1] - r["inf_mis"]["ci"][0] > 0.2, True)
        rows, rules, skipped, counts = AC.calibrate(blocks, classes)
        check("calibrate on testdata: no rule from a handful of battles, v1 kept apart", (rules, counts), ({}, {"fought": 3, "auto": 3, "v1": 1}))
        # noisy data where fought and auto do not differ: the interval must contain zero
        import random
        rnd, paths = random.Random(3), []
        for p in range(8):
            lines = []
            for n in range(5):
                lines += result(p * 10 + n, "fought", rnd.randint(20, 100), rnd.randint(20, 100))
                lines += result(p * 10 + n, "auto", rnd.randint(20, 100), rnd.randint(20, 100))
            paths.append(os.path.join(tmp, "issue_%d_noisy%d.txt" % (p + 50, p)))
            open(paths[-1], "w").write("\n".join(lines) + "\n")
        rows, rules, skipped, counts = AC.calibrate(BL.load(paths)[0], classes)
        check("calibrate: no difference in the data, no rule", (rules, [x["rule"] for x in rows]), ({}, ["not clear"] * 2))
        again = AC.calibrate(BL.load(paths)[0], classes)[0]
        check("calibrate: the bootstrap is seeded", [x["ci"] for x in again], [x["ci"] for x in rows])

# ---- fetch_logs.py: pulling the log out of an issue body (no network)
import fetch_logs as FL
body = ("### Mod version\n\n0.2.0\n\n### Battle log (optional)\n\n```text\n# Community Balance Patch Battle Logger.\r\n"
        "#battle;v1;2026-09-30 20:01;multiplayer=0;siege=0;mods=none\r\nu;1;1;1;wh_main_emp_inf_swordsmen;120;90;40;0;0\r\n#end\r\n"
        "#error;v1;write_battle;C:\\Users\\someone\\x.lua:3: oops\n```\n\n### Notes, replays, screenshots\n\nu; this is my note\n"
        "```\n#autoresolve;v1;2026-09-30 20:10;winner=attacker;mods=none\na;1;1;wh_main_emp_inf_swordsmen;100;80\n#end\n```\n")
check("fetch_logs: log lines out of an issue body", FL.log_lines(body), [
    "#battle;v1;2026-09-30 20:01;multiplayer=0;siege=0;mods=none", "u;1;1;1;wh_main_emp_inf_swordsmen;120;90;40;0;0", "#end",
    "#autoresolve;v1;2026-09-30 20:10;winner=attacker;mods=none", "a;1;1;wh_main_emp_inf_swordsmen;100;80", "#end"])
check("fetch_logs: an issue with no log", (FL.log_lines("### Battle log (optional)\n\n_No response_\n"), FL.log_lines(None)), ([], []))
check("fetch_logs: files of one author are one source", (BL.source("logs/issue_12_Some-One.txt"), BL.source("logs/issue_30_Some-One.txt"), BL.source("my.txt")),
      ("author:Some-One", "author:Some-One", "file:" + os.path.abspath("my.txt")))
check("fetch_logs: a sentence inside a block is not kept",
      FL.log_lines("#battle;v1;d;multiplayer=0;siege=0;mods=none\ni; think this unit is bad\nu;1;1;1;k;120;90;40;0;0\nu;?;?;?;k;?;?;?;?;?\n#end\n"),
      ["#battle;v1;d;multiplayer=0;siege=0;mods=none", "u;1;1;1;k;120;90;40;0;0", "u;?;?;?;k;?;?;?;?;?", "#end"])

# a stubbed GitHub: issue 7 has its log in the body and one more block in a comment on the second page of comments
BLOCK = "#autoresolve;v1;2026-09-30 20:%02d;winner=attacker;mods=none\na;1;1;wh_main_emp_inf_swordsmen;100;80\n#end\n"
state = dict(fail=None)


def fake_get(url, raw=False):
    if "/comments" in url:
        if state["fail"]:
            raise urllib.error.HTTPError(url, state["fail"], "no", None, None)
        if url.endswith("&page=1"):
            return [dict(user=dict(login="someone"), body="thanks")] * 100
        return [dict(user=dict(login="tester"), body=BLOCK % 2)]
    return [dict(number=7, user=dict(login="tester"), comments=101, body=BLOCK % 1), dict(number=8, user=dict(login="other"), comments=0, body="no log")]


def fetch():
    out = io.StringIO()
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
            FL.main()
        code = 0
    except SystemExit as e:
        code = e.code
    return code, out.getvalue()


with tempfile.TemporaryDirectory() as tmp:
    FL.get, FL.OUT, argv, sys.argv = fake_get, tmp, sys.argv, ["fetch_logs.py"]
    path = os.path.join(tmp, "issue_7_tester.txt")
    code, _ = fetch()
    check("fetch_logs: body and second page of comments, an issue with no log is skipped",
          (code, sorted(f for f in os.listdir(tmp) if f.endswith(".txt")), open(path).read().count("#end")), (0, ["issue_7_tester.txt"], 2))
    for status in (403, 500):
        state["fail"] = status
        code, text = fetch()
        check("fetch_logs: comments answer %d: the complete file is not overwritten, exit is not 0" % status,
              (open(path).read().count("#end"), code not in (0, None), "Rate limit" in str(code)), (2, True, status == 403))
    os.remove(path)
    code, text = fetch()
    check("fetch_logs: comments answer 500 and no file yet: written from the body, exit is not 0",
          (open(path).read().count("#end"), code not in (0, None), "incomplete" in text), (1, True, True))
    sys.argv = argv

print("\n%d checks failed: %s" % (len(failed), ", ".join(failed)) if failed else "\nall checks passed")
sys.exit(1 if failed else 0)
