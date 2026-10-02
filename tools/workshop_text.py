#!/usr/bin/env python3
"""The Workshop texts, from the pack's own numbers, so the page cannot describe a different pack from the one uploaded.

    python3 workshop_text.py           -> ../workshop/patch_description.txt, logger_description.txt, change_note.txt,
                                          logger_change_note.txt

The templates are workshop/*.tmpl (Steam BBCode). {VERSION} is the VERSION file, {UNITS} {ELITES} {GUNS} {THEME}
{LISTED} {BK_MORE} are counted from _beta.json and build/beta/community_log.json, {GAME} is GAME below. The change notes are
CHANGELOG.md's entry for VERSION and the newest Battle Logger entry. Steam's editor refuses a description with umlauts, or longer than about 7,570 characters
(found by testing; the documented limit is 8,000): both fail here instead.
"""
import json
import os
import re
import sys

import community as C

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WS = os.path.join(ROOT, "workshop")
GAME = "9.0"                # the game version the data was read from; change it with the first build after a CA patch
LIMIT = 7500


def counts():
    R = json.load(open(os.path.join(HERE, "_beta.json")))["units"]
    log_path = os.path.join(ROOT, "build", "beta", "community_log.json")
    if not os.path.exists(log_path):
        raise SystemExit("no build/beta/community_log.json: run tools/patch_day.sh first")
    engines = {ln for ln, what, ents, sets in C.ARTILLERY + C.ENTITIES} | {C.MOUNT_ACCEL[0]}
    listed = {k for ln, k, ch in json.load(open(log_path)) if not isinstance(ch, str) and ln not in engines}
    changed = {o["key"] for o in R if o["action"] != "none" and not o.get("held")}
    bk = next(o for o in R if o["key"] == "wh3_main_vmp_blood_knights_sword_shield")
    return dict(UNITS=len(changed | listed), ELITES=sum(1 for o in R if o.get("elite")), GUNS=sum(1 for o in R if o.get("gun")),
                THEME=sum(1 for o in R if o.get("theme") and o["action"] != "none"), LISTED=len(listed),
                BK_MORE=int(round((bk["new_campaign_cost"] / bk["campaign_cost"] - 1) * 20.0) * 5))


def entry(heading_rx, bullet=False):
    """one CHANGELOG.md entry as (label, a single paragraph of plain text, whether its bracket still says it is not
    uploaded). heading_rx picks the "## ..." section; with bullet, the entry is the first "- **N** (...): ..." bullet
    in that section and the label is N."""
    text = open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8").read()
    m = re.search(r"^## (%s)(?: \(([^)\n]*)\))?[ \t]*\n(.*?)(?=^## |\Z)" % heading_rx, text, re.M | re.S)
    if not m:
        raise SystemExit("CHANGELOG.md has no '## %s' entry (write it before building, docs/RELEASING.md)" % heading_rx.replace("\\", ""))
    label, bracket, body = m.group(1), m.group(2) or "", m.group(3)
    if bullet:
        b = re.search(r"^- \*\*(\d+)\*\*(?: \(([^)\n]*)\))?:?[ \t]*(.*?)(?=^- \*\*\d+\*\*|\Z)", body, re.M | re.S)
        if not b:
            raise SystemExit("CHANGELOG.md: no numbered entry under '## %s'" % label)
        label, bracket, body = b.group(1), b.group(2) or "", b.group(3)
    plain = re.sub(r"\s+", " ", re.sub(r"[`*]", "", body)).strip(" -")
    return label, plain, "not uploaded" in bracket


ASCII = {"\u2013": "-", "\u2014": "-", "\u2018": "'", "\u2019": "'", "\u201c": '"', "\u201d": '"', "\u2192": "to", "\u00d7": "x"}


def check(name, text, limit=LIMIT):
    bad = sorted({ch for ch in text if ord(ch) > 126})
    if bad:
        raise SystemExit("%s: characters Steam's editor refuses: %s" % (name, " ".join(bad)))
    if len(text) > limit:
        raise SystemExit("%s: %d characters, over the %d the Workshop takes" % (name, len(text), limit))
    left = re.findall(r"\{[^{}\n]{1,30}\}", text)
    if left:
        raise SystemExit("%s: placeholders left unfilled: %s" % (name, left))
    tags = set(re.findall(r"\[/?([a-z0-9*]+)[=\]]", text))
    unknown = tags - {"b", "h1", "h2", "list", "url", "*"}
    if unknown:
        raise SystemExit("%s: BBCode tags the pages do not use: %s" % (name, sorted(unknown)))
    for tag in tags - {"*"}:
        if len(re.findall(r"\[%s[=\]]" % tag, text)) != text.count("[/%s]" % tag):
            raise SystemExit("%s: unbalanced [%s] tags" % (name, tag))


def main():
    version = open(os.path.join(ROOT, "VERSION")).read().strip()
    values = dict(counts(), VERSION=version, GAME=GAME)
    for tmpl, out in (("patch_description.tmpl", "patch_description.txt"), ("logger_description.tmpl", "logger_description.txt")):
        text = open(os.path.join(WS, tmpl), encoding="utf-8").read()
        for k, v in values.items():
            text = text.replace("{%s}" % k, str(v))
        check(out, text)
        open(os.path.join(WS, out), "w", encoding="utf-8").write(text)
        print("wrote workshop/%s  %d characters" % (out, len(text)))
    _, body, undated = entry(re.escape(version))
    notes = [("change_note.txt", "Alpha %s. %s" % (version, body), undated)]
    number, body, undated_logger = entry("Battle Logger", bullet=True)
    notes.append(("logger_change_note.txt", "Battle Logger %s: %s" % (number, body), undated_logger))
    for name, text, und in notes:
        for ch, plain in ASCII.items():
            text = text.replace(ch, plain)
        check(name, text)
        open(os.path.join(WS, name), "w", encoding="utf-8").write(text + "\n")
        print("wrote workshop/%s  %d characters%s" % (name, len(text), "   (its CHANGELOG.md entry is not dated yet: tools/upload.sh will refuse until it is)" if und else ""))


if __name__ == "__main__":
    sys.exit(main())
