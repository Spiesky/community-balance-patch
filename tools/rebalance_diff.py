#!/usr/bin/env python3
"""What changed between two proposal files: the review loop's diff.

    cp _rebalance.json _rebalance.before.json      # before editing lore_ladder.py
    python3 rebalance_solve.py
    python3 rebalance_diff.py _rebalance.before.json _rebalance.json

Lists every unit whose action, stats, size or price differs between the two, and a count by faction.
"""
import json
import sys
from collections import Counter


def sig(o):
    a = o["after"]
    return (o["action"], round(a["ma"]), round(a["md"]), round(a["hp"]), round(a["base"]), round(a["ap"]), a["men"], o["new_cost"], o["new_campaign_cost"])


def main():
    if len(sys.argv) < 3:
        print(__doc__); return 1
    A = {o["key"]: o for o in json.load(open(sys.argv[1]))["units"]}
    B = {o["key"]: o for o in json.load(open(sys.argv[2]))["units"]}
    changed = [k for k in B if k in A and sig(A[k]) != sig(B[k])]
    added = [k for k in B if k not in A]
    removed = [k for k in A if k not in B]
    print("%d units differ, %d new, %d gone" % (len(changed), len(added), len(removed)))
    by = Counter(B[k]["faction"] for k in changed)
    if by:
        print("by faction:", ", ".join("%s %d" % kv for kv in by.most_common()))
    for k in sorted(changed, key=lambda k: (B[k]["faction"], B[k]["name"])):
        a, b = A[k], B[k]
        aa, bb = a["after"], b["after"]
        bits = []
        if a["action"] != b["action"]:
            bits.append("%s → %s" % (a["action"], b["action"]))
        if round(aa["ma"]) != round(bb["ma"]) or round(aa["md"]) != round(bb["md"]):
            bits.append("MA/MD %d/%d → %d/%d" % (aa["ma"], aa["md"], bb["ma"], bb["md"]))
        if round(aa["hp"]) != round(bb["hp"]):
            bits.append("HP %d → %d" % (aa["hp"], bb["hp"]))
        if round(aa["base"]) != round(bb["base"]) or round(aa["ap"]) != round(bb["ap"]):
            bits.append("dmg %d+%d → %d+%d" % (aa["base"], aa["ap"], bb["base"], bb["ap"]))
        if aa["men"] != bb["men"]:
            bits.append("men %d → %d" % (aa["men"], bb["men"]))
        if a["new_cost"] != b["new_cost"]:
            bits.append("price %d → %d" % (a["new_cost"], b["new_cost"]))
        print("  %-4s %-44s %s" % (b["faction"], b["name"][:44], "; ".join(bits)))
    for k in added:
        print("  new: %s" % k)
    for k in removed:
        print("  gone: %s" % k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
