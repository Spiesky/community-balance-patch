#!/usr/bin/env python3
"""Does the pack do exactly what the community list says, and nothing else?

Builds the beta twice, without and with the community list, reads both packs back, and compares every recruitable unit's
effective stats (the pack's row where there is one, else vanilla). Each difference must be one a community.py entry asks
for, and each entry's change must be there.

    python3 community_check.py
"""
import os
import subprocess
import sys

import vanilla as V
import unit_model as UM
import community as C
from packread import Pack
from rebalance_check import rows_of, norm

HERE = os.path.dirname(os.path.abspath(__file__))
TMP = os.path.join(os.path.dirname(HERE), "build", "check")
PROPOSALS = os.environ.get("CBP_PROPOSALS") or os.path.join(HERE, "_beta.json")


def build(out, community):
    env = dict(os.environ, CBP_PROPOSALS=PROPOSALS, CBP_OUT=out, CBP_COMMUNITY="1" if community else "0")
    subprocess.run([sys.executable, os.path.join(HERE, "build_rebalance.py")], env=env, check=True, stdout=subprocess.DEVNULL)
    return rows_of(Pack(out))


def stats(rows):
    idx = {t: {r.get("unit") if t == "main_units" else r.get("key"): r for r in rs} for t, rs in rows.items()}
    van = dict(land_units=V.index("land_units"), main_units=V.index("main_units", "unit"), melee_weapons=V.index("melee_weapons"),
               missile_weapons=V.index("missile_weapons"), projectiles=V.index("projectiles"), battle_entities=V.index("battle_entities"))
    AV = {r["key"]: float(r["armour_value"]) for r in V.table("unit_armour_types")}
    MO = V.index("mounts")

    def get(t, k):
        r = idx.get(t, {}).get(k) or van[t].get(k)
        return {c: norm(v) for c, v in r.items()} if r else {}

    out = {}
    for key in UM.recruitable():
        mu = get("main_units", key)
        lu = get("land_units", mu["land_unit"])
        w = get("melee_weapons", lu["primary_melee_weapon"])
        mw = get("missile_weapons", lu["primary_missile_weapon"])
        p = get("projectiles", mw.get("default_projectile", ""))
        e = get("battle_entities", lu["man_entity"])
        me = get("battle_entities", MO[lu["mount"]]["entity"]) if lu["mount"] in MO else {}
        s = dict(ma=lu["melee_attack"], md=lu["melee_defence"], cb=lu["charge_bonus"], ld=lu["morale"], hp=lu["bonus_hit_points"],
                 accuracy=lu["accuracy"], ammo=lu["primary_ammo"], missile_res=lu["damage_mod_missile"], armour=AV[lu["armour"]],
                 spacing=lu["spacing"], rank_depth=lu["rank_depth"], cost=mu["multiplayer_cost"], men=mu["num_men"],
                 ws_base=w.get("damage"), ws_ap=w.get("ap_damage"), bvi=w.get("bonus_v_infantry"), bvl=w.get("bonus_v_large"),
                 missile_base=p.get("damage"), missile_ap=p.get("ap_damage"), range=p.get("effective_range"),
                 reload=p.get("base_reload_time"), calibration_set=p.get("calibration_area"), shockwave=p.get("shockwave_radius"),
                 mass=e.get("mass"), speed=e.get("run_speed"), accel=e.get("acceleration"), decel=e.get("deceleration"),
                 turn=e.get("turn_speed"), mount_speed=me.get("run_speed"), mount_turn=me.get("turn_speed"))
        out[key] = s
    return out


def expected(entries_for_key, men):
    """(delta, set) per stat, from every entry naming this unit"""
    d, st = {}, {}
    for ch in entries_for_key:
        for k, v in ch.items():
            if k.startswith("_"):
                continue
            if k == "hp_total":
                d["hp"] = d.get("hp", 0) + round(v / men)
            elif k == "ws_swap":
                d["ws_base"] = d.get("ws_base", 0) - v
                d["ws_ap"] = d.get("ws_ap", 0) + v
            elif k in ("spacing", "rank_depth", "men", "calibration_set", "shockwave", "accel", "decel", "turn", "mount_turn"):
                st[k] = v
            elif k == "ammo_set":
                st["ammo"] = v
            elif k in ("ws_base_set", "ws_ap_set"):
                st[k[:-4]] = v
            elif k == "hp_set":
                st["hp_set"] = v
            elif k in ("speed", "mount_speed"):
                d[k] = d.get(k, 0) + v / 10.0
            else:
                d[k] = d.get(k, 0) + v
    return d, st


def main():
    os.makedirs(TMP, exist_ok=True)
    a = stats(build(os.path.join(TMP, "without.pack"), False))
    b = stats(build(os.path.join(TMP, "with.pack"), True))
    by_key = {}
    for line, pat, ch, keys in C.resolve(UM.recruitable(), UM.name, UM.faction):
        for k in keys:
            by_key.setdefault(k, []).append((line, ch))
    skip = {o["key"] for o in __import__("json").load(open(PROPOSALS))["units"] if o.get("elite")}
    # stats changed in place on shared entities (artillery engines, mounts) are checked on the entities, not here
    shared = {"mount_speed", "mount_turn"}
    fails, ok = [], 0
    for key in a:
        entries = [] if key in skip else [ch for _, ch in by_key.get(key, [])]
        d, st = expected(entries, int(a[key]["men"]))
        for s in a[key]:
            va, vb = a[key][s], b[key][s]
            if s == "hp" and "hp_set" in st:
                continue
            if s in st:
                good = vb == norm(st[s])
            elif s in d:
                if s == "cost":
                    good = abs(vb - va - d[s]) < 0.01
                else:
                    good = va != "" and abs(vb - va - d[s]) < 0.011
            elif s in shared:
                continue
            else:
                good = va == vb
            if not good:
                fails.append("%s (%s) %s: %s -> %s, expected %s" % (UM.name(key), key, s, va, vb, st.get(s, d.get(s, "no change"))))
            else:
                ok += 1
    print("%d unit stats as expected" % ok)
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else "%d problems" % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
