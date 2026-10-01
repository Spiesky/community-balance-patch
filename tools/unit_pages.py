#!/usr/bin/env python3
"""Fill the generated blocks on the pages players read, from the pack's own data, so a page cannot quote numbers the
pack does not have.

    python3 unit_pages.py          rewrites the blocks in units/*.md and docs/AUTORESOLVE.md

A block is everything between two HTML comments (invisible on GitHub):

    <!-- BETA_NUMBERS:blood_knights -->   vanilla and patch, side by side, for the units of that page   <!-- /BETA_NUMBERS:blood_knights -->
    <!-- GRIND:blood_knights -->          the grind_check.py figures against Skavenslaves, in a sentence <!-- /GRIND:blood_knights -->
    <!-- AUTORESOLVE_LOOKUPS -->          the game's own auto-resolve rows the page argues from          <!-- /AUTORESOLVE_LOOKUPS -->

A bare {{BETA_NUMBERS:x}} / {{GRIND:x}} / {{AUTORESOLVE_LOOKUPS}} token on a line of its own becomes a block the first
time. Everything outside the blocks is written by hand and never touched. Reads _beta.json (CBP_PROPOSALS overrides).
"""
import glob
import json
import os
import re

import vanilla as V

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROPOSALS = os.environ.get("CBP_PROPOSALS") or os.path.join(HERE, "_beta.json")
PAGES = {                      # page name -> the units on it, by key pattern, in the order shown
    "blood_knights": [r"vmp_blood_knights_sword|vmp_blood_knights(?!.*lance)", r"vmp_cav_blood_knights"],
    "grail_knights": [r"brt_cav_grail_knights", r"brt_cav_grail_guardians"],
    "swords_of_chaos": [r"chs_cav_chaos_knights_ror_0"],
}


def units(page, R):
    out = []
    for rx in PAGES[page]:
        out += sorted((o for o in R if re.search(rx, o["key"]) and o.get("elite") and o not in out), key=lambda o: o["name"])
    return out


def numbers(page, R):
    lines = ["| | models | melee attack / defence | charge bonus | HP per model | total HP | weapon damage | price (custom battle) | campaign: recruit / upkeep |",
             "|---|---|---|---|---|---|---|---|---|"]
    for o in units(page, R):
        b, a = o["before"], o["after"]

        def weapon(s):
            t = "%.0f + %.0f AP" % (s["base"], s["ap"])
            if s["bvl"]:
                t += ", +%.0f vs large" % s["bvl"]
            if s["bvi"]:
                t += ", +%.0f vs infantry" % s["bvi"]
            return t
        lines.append("| %s, vanilla | %d | %.0f / %.0f | %.0f | %.0f | %.0f | %s | %d | %d / %d |" % (
            o["name"], b["men"], b["ma"], b["md"], b["cb"], b["hp"], b["men"] * b["hp"], weapon(b), o["cost"], o["campaign_cost"], o["upkeep"]))
        lines.append("| patch | **%d** | %.0f / %.0f | %.0f | **%.0f** | %.0f | %s | **%d** | %d / %d |" % (
            a["men"], a["ma"], a["md"], a["cb"], a["hp"], a["men"] * a["hp"], weapon(a), o["new_cost"], o["new_campaign_cost"], o["new_upkeep"]))
    lines.append("")
    lines.append("Attack, defence and charge are what the unit card shows with the unit's permanent passives on. Models are at "
                 "Ultra unit size; smaller settings scale both versions the same way.")
    return "\n".join(lines)


def grind(page, R):
    import unit_model as UM
    import grind_check as G
    import rebalance_verify as RV
    slaves = UM.card("wh2_main_skv_inf_skavenslaves_0")
    out = []
    for o in units(page, R):
        v = UM.card(o["key"])
        p, _ = RV.after(o["key"])
        (rv, mv), (rp, mp) = G.ratio(v, slaves), G.ratio(p, slaves)
        out.append("**%s**: about %d Skavenslaves killed for every rider lost (vanilla: about %d), and about %d a minute by the "
                   "whole unit (vanilla: about %d)." % (o["name"], round(rp, -1) if rp >= 100 else round(rp), round(rv), round(mp, -1), round(mv, -1)))
    out.append("")
    out.append("These are the combat model's estimates (`tools/grind_check.py`), not measurements: sustained melee, no charges, "
               "Skavenslaves that never rout, and one swing killing at most the models it can reach.")
    return "\n".join(out)


def lookups():
    L = V.table("autoresolver_modifier_group_lookups")
    M = V.table("autoresolver_modifier_group_to_modifiers")
    T = V.index("autoresolver_modifier_targets")
    if not L or not M:
        return "(the auto-resolve tables are not in `vanilla_db/`: run `tools/refresh_vanilla.py`)"

    def mods(group):
        rows = [r for r in M if r["group"] == group]
        return ", ".join("%s %+.3g against %s" % (r["modifier_bonus"].replace("unit_", "").replace("_kps_multiplier", " kill rate"),
                                                  float(r["value"]), r["modifier_target"]) for r in rows) or "none"

    def where(group):
        rows = [r for r in L if r["modifier_group_applied"] == group]
        by = {}
        for r in rows:
            by.setdefault(r["player_type"], []).append(r["battle_type"])
        return "; ".join("`%s` in %s" % (pt, ", ".join(sorted(bts))) for pt, bts in sorted(by.items())) or "nowhere"

    out = ["From the game's own tables (`autoresolver_modifier_group_to_modifiers`, `autoresolver_modifier_group_lookups`), as read "
           "by `tools/refresh_vanilla.py`:", "",
           "| group | modifiers | applied to (`player_type`) and where (`battle_type`) |", "|---|---|---|"]
    for g in ("wh_moderate_kps_multiplier_bonus", "wh_strong_kps_multiplier_bonus", "wh_strong_ranged_kps_multiplier_penalty",
              "wh_settlement_human_v_ai_bonus", "wh_settlement_human_v_ai_penalty"):
        out.append("| `%s` | %s | %s |" % (g, mods(g), where(g)))
    types = sorted({r["player_type"] for r in L})
    out += ["", "Every `player_type` the game uses: %s." % ", ".join("`%s`" % t for t in types), "",
            "What this shows. `wh_moderate_kps_multiplier_bonus` is used in one place, for the defender in a fortify battle, and "
            "its two rows are the same missile row twice; its stronger sibling `wh_strong_kps_multiplier_bonus` has one melee "
            "and one missile row. And the game has one-sided `player_type` values: CA's own handicap on AI missiles "
            "(`wh_strong_ranged_kps_multiplier_penalty`) is attached with `ai_vs_human`, which the test pack's rule copies, "
            "so that it lowers only the AI's kill rate against the player's back line."]
    return "\n".join(out)


def fill(text, R):
    def block(kind, page, body):
        tag = kind + (":" + page if page else "")
        return "<!-- %s -->\n%s\n<!-- /%s -->" % (tag, body, tag)

    def make(kind, page):
        if kind == "BETA_NUMBERS":
            return numbers(page, R)
        if kind == "GRIND":
            return grind(page, R)
        return lookups()
    n = 0
    for kind in ("BETA_NUMBERS", "GRIND", "AUTORESOLVE_LOOKUPS"):
        rx = re.compile(r"<!-- %s(?::(\w+))? -->.*?<!-- /%s(?::\w+)? -->|\{\{%s(?::(\w+))?\}\}" % (kind, kind, kind), re.S)

        def sub(m):
            nonlocal n
            page = m.group(1) or m.group(2)
            if kind != "AUTORESOLVE_LOOKUPS" and page not in PAGES:
                raise SystemExit("unit_pages: no units known for %s:%s (add it to PAGES)" % (kind, page))
            n += 1
            return block(kind, page, make(kind, page))
        text = rx.sub(sub, text)
    return text, n


def main():
    R = json.load(open(PROPOSALS))["units"]
    total = 0
    for path in sorted(glob.glob(os.path.join(ROOT, "units", "*.md"))) + [os.path.join(ROOT, "docs", "AUTORESOLVE.md")]:
        text = open(path, encoding="utf-8").read()
        new, n = fill(text, R)
        left = re.findall(r"\{\{[A-Z_:a-z]+\}\}", new)
        if left:
            raise SystemExit("%s: unfilled placeholders %s" % (os.path.relpath(path, ROOT), left))
        if new != text:
            open(path, "w", encoding="utf-8").write(new)
        total += n
    print("unit pages: %d generated blocks up to date" % total)


if __name__ == "__main__":
    main()
