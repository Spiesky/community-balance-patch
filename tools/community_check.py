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
import gunpowder as GP
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


def entity_problems(path):
    """every battle_entities row the pack overrides in place (an engine, a mount, a hitbox) differs from vanilla in
    exactly the columns a list line sets for it, with the values it sets"""
    rows = {r["key"]: r for r in rows_of(Pack(path)).get("battle_entities", [])}
    BE, MO = V.index("battle_entities"), V.index("mounts")
    want = {}
    for line, what, ents, sets in C.ARTILLERY + C.ENTITIES:
        for e in ents:
            want.setdefault(e, {}).update(sets)
    from decided import ELITE_BODIES                      # the patch's own lore-elite bodies, not the list's
    for e, sets in ELITE_BODIES.items():
        if e in rows:
            want.setdefault(e, {}).update(sets)
    line, what, rx, accel = C.MOUNT_ACCEL
    for m in MO:
        if rx.search(m) and MO[m]["entity"] in BE:
            want.setdefault(MO[m]["entity"], {})["acceleration"] = accel
    mounts = {}                                           # mount speed and turn, changed in place for every rider
    for line, pat, ch, keys in C.resolve(UM.recruitable(), UM.name, UM.faction):
        for k in keys:
            lu = V.index("land_units")[V.index("main_units", "unit")[k]["land_unit"]]
            if lu["mount"] in MO and ("mount_speed" in ch or "mount_turn" in ch):
                mounts.setdefault(MO[lu["mount"]]["entity"], set()).update({"run_speed"} if "mount_speed" in ch else set(), {"turn_speed"} if "mount_turn" in ch else set())
    out = []
    for key, r in rows.items():
        if key not in BE:
            continue                                      # a per-unit clone (cbp_..._man): checked through the unit's stats
        sets, changed = want.get(key, {}), {c for c in r if norm(r[c]) != norm(BE[key].get(c, ""))}
        allowed = set(sets) | mounts.get(key, set()) | ({"run_speed"} if "walk_speed" in sets else set())
        if changed - allowed:
            out.append("entity %s: columns changed that no list line sets: %s" % (key, sorted(changed - allowed)))
        for c, v in sets.items():
            if norm(r[c]) != norm(v):
                out.append("entity %s: %s is %s, the list says %s" % (key, c, r[c], v))
    for key, sets in want.items():                      # not in the pack is right only if vanilla already has the values
        if key not in rows and any(norm(BE[key].get(c, "")) != norm(v) for c, v in sets.items()):
            out.append("entity %s: the list changes it but it is not in the pack" % key)
    return out


def alternate_problems(path, guns):
    """a list entry that changes a unit's shot changes its alternate ammunition the same way"""
    T = rows_of(Pack(path))
    junctions = {str(r["id"]): r for r in T.get("unit_missile_weapon_junctions", [])}
    missiles = {r["key"]: r for r in T.get("missile_weapons", [])}
    projectiles = {r["key"]: r for r in T.get("projectiles", [])}
    MIS, PJ = V.index("missile_weapons"), V.index("projectiles")
    out = []
    for line, pat, ch, keys in C.resolve(UM.recruitable(), UM.name, UM.faction):
        moves = {k: v for k, v in ch.items() if k in ("missile_base", "missile_ap", "range", "reload")}
        if not moves:
            continue
        for key in keys:
            gd, gr = guns.get(key, (1.0, 1.0))
            for j in V.where("unit_missile_weapon_junctions", unit=key):
                if j["missile_weapon"] not in MIS:
                    continue
                jj = junctions.get(str(j["id"]))
                p = jj and projectiles.get(missiles.get(jj["missile_weapon"], {}).get("default_projectile", ""))
                if not p:
                    out.append("%s: alternate ammunition %s is not changed with the unit's shot (entry %d)" % (UM.name(key), j["missile_weapon"], line))
                    continue
                vp = PJ[MIS[j["missile_weapon"]]["default_projectile"]]
                for k, col, f in (("missile_base", "damage", gd), ("missile_ap", "ap_damage", gd), ("range", "effective_range", 1.0), ("reload", "base_reload_time", gr)):
                    if k in moves:
                        base = float(vp[col] or 0) * (gd if col in ("damage", "ap_damage") and key in guns else gr if col == "base_reload_time" and key in guns else 1.0)
                        if abs(float(p[col]) - (base + moves[k] * f)) > 1.01:
                            out.append("%s: alternate %s %s is %s, expected about %s (entry %d)" % (UM.name(key), j["missile_weapon"], col, p[col], base + moves[k] * f, line))
    return out


def main():
    os.makedirs(TMP, exist_ok=True)
    a = stats(build(os.path.join(TMP, "without.pack"), False))
    b = stats(build(os.path.join(TMP, "with.pack"), True))
    by_key = {}
    for line, pat, ch, keys in C.resolve(UM.recruitable(), UM.name, UM.faction):
        for k in keys:
            by_key.setdefault(k, []).append((line, ch))
    props = __import__("json").load(open(PROPOSALS))["units"]
    skip = {o["key"] for o in props if o.get("elite")}
    # on a gun the list's missile numbers go through the gunpowder rule (community.apply): damage x, reload x, and the
    # ammunition change is made to the vanilla count before the rule cuts it
    guns = {o["key"]: tuple(o["gun"]) for o in props if o.get("gun")}
    LUV, MUV = V.index("land_units"), V.index("main_units", "unit")
    unresolved = [(line, pat) for line, pat, ch, keys in C.resolve(UM.recruitable(), UM.name, UM.faction) if not keys]
    # stats changed in place on shared entities (artillery engines, mounts) are checked on the entities, not here
    shared = {"mount_speed", "mount_turn"}
    fails, ok = [], 0
    for key in a:
        entries = [] if key in skip else [ch for _, ch in by_key.get(key, [])]
        d, st = expected(entries, int(a[key]["men"]))
        if key in guns:
            gd, gr = guns[key]
            for s_, f_ in (("missile_base", gd), ("missile_ap", gd), ("reload", gr)):
                if s_ in d:
                    d[s_] = round(d[s_] * f_) if s_ != "reload" else d[s_] * f_
            if "ammo" in d or "ammo" in st:
                v0 = int(float(LUV[MUV[key]["land_unit"]]["primary_ammo"]))
                st["ammo"] = GP.ammo(st["ammo"] if "ammo" in st else v0 + d.pop("ammo"))
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
    fails += entity_problems(os.path.join(TMP, "with.pack"))
    fails += alternate_problems(os.path.join(TMP, "with.pack"), guns)
    print("%d unit stats as expected" % ok)
    for line, pat in unresolved:                      # an entry naming no unit: CA renamed it, or the pattern is wrong
        fails.append("entry %d (%s) names no unit in the game" % (line, pat))
    fails += C.check_resolution(UM.recruitable(), UM.name, UM.faction)
    for f in fails:
        print("FAIL", f)
    print("PASS" if not fails else "%d problems" % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
