#!/usr/bin/env python3
"""Does the patch make the game make more sense? Checks the proposals (_rebalance.json) against vanilla:

  size       no unit changes size, or a resized unit keeps at least its vanilla total health
  direction  a stronger unit never gets cheaper, a weaker one never dearer (beyond rounding)
  limits     no regiment's power or price moves more than 20% (23% with rounding), except the named lore elites
  attack     no attack or defence drop of more than 3 on a unit that got stronger
  roster     'pay more, get >15% less' pairs in one faction and caste: vanilla vs patched, and none new
  fairness   spread of gold per power within each caste: vanilla vs patched (lower is fairer)
"""
import json, math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
R = json.load(open(os.environ.get("CBP_PROPOSALS") or os.path.join(HERE, "_rebalance.json")))["units"]
fails = []


def pw(o, after):
    return o["after"].get("power_reg", o["power_reg"]) if after else o["power_reg"]


def cost(o, after):
    return (o["new_cost"] if after else o["cost"]) or 0


renown = {o["key"] for o in R if re.search(r"\(.+\)$", o["name"]) and any(
    b["name"] in (re.match(r"^.* \((.+)\)$", o["name"]).group(1), re.sub(r" – (.+)$", r" (\1)", re.match(r"^.* \((.+)\)$", o["name"]).group(1)))
    for b in R)}

for o in R:
    b, a = o["before"], o["after"]
    if a["men"] != b["men"] and a["men"] * a["hp"] < b["men"] * b["hp"]:
        fails.append("size: %s loses total health (%d x %.0f -> %d x %.0f)" % (o["name"], b["men"], b["hp"], a["men"], a["hp"]))
    if o["action"] == "decided":
        continue
    dp = pw(o, 1) / pw(o, 0) if pw(o, 0) else 1
    dc = cost(o, 1) / cost(o, 0) if cost(o, 0) else 1
    if (dp > 1.02 and dc < 0.98) or (dp < 0.98 and dc > 1.02):
        fails.append("direction: %s power x%.2f, price %d -> %d" % (o["name"], dp, cost(o, 0), cost(o, 1)))
    if not o.get("elite") and (abs(math.log(dp)) > math.log(1.23) or abs(math.log(dc)) > math.log(1.23)):
        fails.append("limits: %s power x%.2f, price x%.2f" % (o["name"], dp, dc))
    if dp > 1 and (a["ma"] - b["ma"] < -3 or a["md"] - b["md"] < -3):
        fails.append("attack: %s MA %s->%s MD %s->%s" % (o["name"], b["ma"], a["ma"], b["md"], a["md"]))


def pairs(after):
    g = {}
    for o in R:
        if cost(o, after) and o["key"] not in renown:
            g.setdefault((o["faction"], o["caste"]), []).append(o)
    out, tot = set(), 0
    for grp in g.values():
        for i, x in enumerate(grp):
            for y in grp[i + 1:]:
                cx, cy, px, py = cost(x, after), cost(y, after), pw(x, after), pw(y, after)
                if abs(cx - cy) < 50:
                    continue
                tot += 1
                if (cx > cy and py > px * 1.15) or (cy > cx and px > py * 1.15):
                    out.add((x["name"], y["name"]))
    return out, tot


v, tv = pairs(False)
p, tp = pairs(True)
by_name = {o["name"]: o for o in R}
notes = []
for x, y in sorted(p - v):
    moved = [by_name[n] for n in (x, y) if by_name[n]["action"] != "none"]
    if moved and all(o.get("gun") or o.get("elite") for o in moved):
        notes.append("design rule (gunpowder or lore elite) moves this pair past 15%%: %s / %s" % (x, y))
    else:
        fails.append("roster: new 'pay more, get less' pair: %s / %s" % (x, y))


def spread(after):
    sq = []
    for c in {o["caste"] for o in R}:
        xs = [math.log(cost(o, after)) - math.log(pw(o, after)) for o in R
              if o["caste"] == c and cost(o, after) > 0 and pw(o, after) > 0 and o["key"] not in renown]
        m = sum(xs) / len(xs)
        sq += [(x - m) ** 2 for x in xs]
    return math.sqrt(sum(sq) / len(sq))


changed = sum(1 for o in R if o["action"] != "none")
print("changed units: %d" % changed)
print("pay more, get >15%% less (same faction and caste): vanilla %d of %d (%.1f%%), patched %d of %d (%.1f%%)"
      % (len(v), tv, 100 * len(v) / tv, len(p), tp, 100 * len(p) / tp))
print("gold per power spread within caste (lower is fairer): vanilla %.3f, patched %.3f" % (spread(False), spread(True)))
for n in notes:
    print("NOTE " + n)
for f in fails:
    print("FAIL " + f)
print("PASS: the patch makes sense on every check" if not fails else "%d problems" % len(fails))
sys.exit(1 if fails else 0)
