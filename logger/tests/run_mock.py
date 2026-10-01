#!/usr/bin/env python3
"""Runs the two Battle Logger scripts outside the game, against mock game objects, and checks what they write.

    python3 logger/tests/run_mock.py        (needs: pip install lupa)

The scripts run in a real Lua 5.1 (the version the game uses) through lupa. The mocks stand in for the game's
bm / cm / core / common objects and for io (files live in memory). Every scenario checks that the output follows
docs/LOG_FORMAT.md and that an error inside the game's functions never comes out of the script.
"""
import os
import re
import sys

try:
    from lupa import lua51
except ImportError:
    sys.exit("lupa with Lua 5.1 is needed: pip install lupa")

HERE = os.path.dirname(os.path.abspath(__file__))
BATTLE = os.path.join(HERE, "..", "cbp_battle_logger.lua")
CAMPAIGN = os.path.join(HERE, "..", "cbp_autoresolve_logger.lua")
LOG = "cbp_battle_log.txt"

checks = 0
failures = []


def check(ok, what):
    global checks
    checks += 1
    if not ok:
        failures.append(what)
        print("  FAIL: " + what)


# ---------------------------------------------------------------------------------------------------------------------
# the format, as docs/LOG_FORMAT.md describes it

BATTLE_KEYS = ["campaign", "type", "multiplayer", "siege", "player", "attacker", "winner", "secs", "cbp", "mods"]
RESULT_KEYS = ["mode", "winner", "turn", "difficulty", "type", "ambush", "night", "settlement", "quest", "campaign",
               "player_side", "cbp", "mods"]
NUM = re.compile(r"^(\?|-?\d+(\.\d+)?)$")
FLAG = re.compile(r"^[01?]$")


def parse(text, name):
    """Splits a log into blocks and checks every line against the format. Returns (blocks, error lines)."""
    blocks, errors, current = [], [], None
    lines = text.split("\n")
    check(text == "" or text.endswith("\n"), name + ": the file ends with a line break")
    for line in lines[:-1]:
        check("\r" not in line and line != "", name + ": no empty or broken line: %r" % line)
        if line.startswith("#error;") or line.startswith("#debug;"):
            check(current is None, name + ": a diagnostic line is never inside a block")
            check(not re.search(r"[/\\]", line), name + ": no path in a diagnostic line: " + line)
            check(".lua" not in line, name + ": no script name in a diagnostic line: " + line)
            errors.append(line)
        elif line.startswith("# "):
            check(current is None, name + ": comment outside a block")
        elif line == "#end":
            check(current is not None, name + ": #end closes a block")
            blocks.append(current)
            current = None
        elif line.startswith("#"):
            check(current is None, name + ": a header does not start inside a block")
            f = line.split(";")
            kind = f[0][1:]
            check(kind in ("battle", "result"), name + ": known block " + f[0])
            check(f[1] == "v2", name + ": version 2")
            check(re.match(r"^\d{4}-\d\d-\d\d \d\d:\d\d$", f[2]) is not None, name + ": date is the third field")
            keys = [x.split("=", 1)[0] for x in f[3:]]
            check(all("=" in x for x in f[3:]), name + ": header fields are key=value")
            check(keys == (BATTLE_KEYS if kind == "battle" else RESULT_KEYS), name + ": header keys %s" % keys)
            check(keys[-1] == "mods", name + ": mods is the last header field")
            head = dict(x.split("=", 1) for x in f[3:] if "=" in x)
            for pack in head.get("mods", "").split("|"):
                check(pack != "" and not re.search(r"[/\;]", pack), name + ": pack names only: %r" % pack)
            current = {"kind": kind, "head": head, "units": []}
        else:
            check(current is not None, name + ": a unit line is inside a block: " + line)
            f = line.split(";")
            check("|" not in line, name + ": no | in a unit line: " + line)
            if current and current["kind"] == "battle":
                check(f[0] == "u" and len(f) == 17, name + ": u line has 17 fields: " + line)
                if len(f) == 17:
                    for i in (1, 2, 5, 6, 7, 10, 11, 12, 15):
                        check(NUM.match(f[i]) is not None, name + ": u field %d is a number or ?: %s" % (i + 1, line))
                    for i in (3, 8, 9, 13, 14):
                        check(FLAG.match(f[i]) is not None, name + ": u field %d is 0, 1 or ?: %s" % (i + 1, line))
                    if f[10] != "?":
                        check(re.match(r"^[01]\.\d{3}$", f[10]) is not None, name + ": hp has three decimals: " + line)
                    check((f[14] == "1") == (f[15] != "?"), name + ": first_rout_s goes with ever_routed: " + line)
                    current["units"].append(f)
            elif current:
                check(f[0] == "r" and len(f) == 9, name + ": r line has 9 fields: " + line)
                if len(f) == 9:
                    check(f[1] in ("1", "2"), name + ": side is 1 or 2: " + line)
                    for i in (2, 5, 6, 7):
                        check(NUM.match(f[i]) is not None, name + ": r field %d is a number or ?: %s" % (i + 1, line))
                    check(FLAG.match(f[3]) is not None, name + ": r player flag: " + line)
                    current["units"].append(f)
    check(current is None, name + ": every block is closed")
    return blocks, errors


# ---------------------------------------------------------------------------------------------------------------------
# mocks (Lua). Loaded under a chunk name that is a Windows path with a user name in it, so that every injected error
# carries that path, as the worst case of what a real error message could contain.

MOCK_CHUNK = "@C:\\Users\\John Quincy Smith\\Steam\\script\\_lib\\mock.lua"

COMMON_MOCK = r"""
MOCK = { files = {}, raise = {}, svr = {}, cbp = "0.2.0", listeners = {} }
MOCK.files["used_mods.txt"] = 'add_working_directory "C:/Users/John Quincy Smith/Steam/content/1";\n'
	.. 'mod "community_balance_patch.pack";\nmod "odd;na|me.pack";\nmod "community_balance_patch_battle_logger.pack";\n'

function MOCK.maybe(name)
	if MOCK.raise[name] then
		error(MOCK.raise[name])
	end
end

io = {
	open = function(name, mode)
		MOCK.maybe("io.open")
		if mode == "r" then
			local text = MOCK.files[name]
			if not text then return nil end
			return {
				lines = function() return text:gmatch("([^\n]*)\n") end,
				close = function() end,
			}
		end
		MOCK.files[name] = MOCK.files[name] or ""
		return {
			write = function(_, s) MOCK.files[name] = MOCK.files[name] .. s end,
			close = function() end,
		}
	end
}

common = { get_localised_string = function(key)
	MOCK.maybe("common.get_localised_string")
	if key == "cbp_version" then return MOCK.cbp end
	return ""
end }

core = {}
function core:add_listener(name, event, condition, callback, persistent)
	MOCK.maybe("core.add_listener")
	table.insert(MOCK.listeners, { name = name, event = event, condition = condition, callback = callback, persistent = persistent })
end
function core:svr_save_string(name, value) MOCK.maybe("core.svr_save_string"); MOCK.svr[name] = value end
function core:svr_load_string(name) MOCK.maybe("core.svr_load_string"); return MOCK.svr[name] or "" end
function core:svr_save_bool(name, value) MOCK.svr[name] = value end
function core:svr_load_bool(name) return MOCK.svr[name] == true end

-- fires an event the way the game does: no pcall, so an error that leaves the script is seen by the test
function MOCK.fire(event, context)
	local keep, n = {}, 0
	for _, l in ipairs(MOCK.listeners) do
		local hit = l.event == event and (l.condition == true or (type(l.condition) == "function" and l.condition(context)))
		if hit then
			n = n + 1
			l.callback(context)
		end
		if not hit or l.persistent then table.insert(keep, l) end
	end
	MOCK.listeners = keep
	return n
end
"""

BATTLE_MOCK = r"""
MOCK.now_ms, MOCK.deployed_ms, MOCK.timers, MOCK.phases, MOCK.alliances = 0, 0, {}, {}, {}
MOCK.battle = { from_campaign = true, type = "land_normal", multiplayer = false, siege = false, player = 1, winner = 1 }

local function list(items, name)
	return {
		count = function() MOCK.maybe(name .. ".count"); return #items end,
		item = function(_, i) return items[i] end,
	}
end

function MOCK.unit(d)
	local function get(name, value)
		return function()
			MOCK.maybe("unit." .. name)
			if d.raise and d.raise[name] then error("unit call failed: " .. name) end
			return value
		end
	end
	return {
		type = get("type", d.key), initial_number_of_men = get("initial_number_of_men", d.men),
		number_of_men_alive = get("number_of_men_alive", d.alive), number_of_enemies_killed = get("number_of_enemies_killed", d.kills),
		is_shattered = get("is_shattered", d.shattered or false), unary_hitpoints = get("unary_hitpoints", d.hp),
		ammo_left = get("ammo_left", d.ammo or 0), starting_ammo = get("starting_ammo", d.ammo0 or 0),
		is_commanding_unit = get("is_commanding_unit", d.general or false), unique_ui_id = get("unique_ui_id", d.uid),
		is_routing = function()
			MOCK.maybe("unit.is_routing")
			local s = (MOCK.now_ms - MOCK.deployed_ms) / 1000
			return d.rout_from ~= nil and s >= d.rout_from and (d.rout_to == nil or s < d.rout_to)
		end,
	}
end

function MOCK.army(units, reinforcements)
	return {
		units = function() MOCK.maybe("army.units"); return list(units, "units") end,
		num_reinforcement_units = function() MOCK.maybe("army.num_reinforcement_units"); return #(reinforcements or {}) end,
		get_reinforcement_units = function(_, i) return list(reinforcements[i], "units") end,
	}
end

function MOCK.alliance(armies, attacker)
	return { armies = function() return list(armies, "armies") end, is_attacker = function() return attacker end }
end

bm = {}
function bm:alliances() MOCK.maybe("bm.alliances"); MOCK.unit_walks = (MOCK.unit_walks or 0) + 1; return list(MOCK.alliances, "alliances") end
function bm:is_from_campaign() MOCK.maybe("bm.is_from_campaign"); return MOCK.battle.from_campaign end
function bm:battle_type() MOCK.maybe("bm.battle_type"); return MOCK.battle.type end
function bm:is_multiplayer() MOCK.maybe("bm.is_multiplayer"); return MOCK.battle.multiplayer end
function bm:is_siege_battle() MOCK.maybe("bm.is_siege_battle"); return MOCK.battle.siege end
function bm:get_player_alliance_num() MOCK.maybe("bm.get_player_alliance_num"); return MOCK.battle.player end
function bm:player_is_attacker() MOCK.maybe("bm.player_is_attacker"); return MOCK.alliances[MOCK.battle.player]:is_attacker() end
function bm:victorious_alliance() MOCK.maybe("bm.victorious_alliance"); return MOCK.battle.winner end
function bm:time_elapsed_ms() MOCK.maybe("bm.time_elapsed_ms"); return MOCK.now_ms end
function bm:register_phase_change_callback(phase, callback)
	MOCK.maybe("bm.register_phase_change_callback")
	table.insert(MOCK.phases, { phase = phase, callback = callback })
end
-- timers as in CA's lib_timer_manager.lua (battle): a repeating callback re-registers itself, then calls
function bm:callback(callback, interval, name)
	table.insert(MOCK.timers, { time = MOCK.now_ms + interval, callback = callback, name = name })
	table.sort(MOCK.timers, function(a, b) return a.time < b.time end)
end
function bm:repeat_callback(callback, interval, name)
	MOCK.maybe("bm.repeat_callback")
	assert(type(callback) == "function" and type(interval) == "number" and interval > 0 and type(name) == "string")
	self:callback(function() self:repeat_callback(callback, interval, name); callback() end, interval, name)
end
function bm:remove_callback(name)
	MOCK.maybe("bm.remove_callback")
	local keep = {}
	for _, t in ipairs(MOCK.timers) do
		if t.name ~= name then table.insert(keep, t) end
	end
	MOCK.timers = keep
end

-- the game calls phase callbacks one after the other without pcall (lib_battle_manager.lua)
function MOCK.phase(name)
	if name == "Deployed" then MOCK.deployed_ms = MOCK.now_ms end
	for _, p in ipairs(MOCK.phases) do
		if p.phase == name then p.callback() end
	end
end
function MOCK.advance(to_ms)
	while #MOCK.timers > 0 and MOCK.timers[1].time <= to_ms do
		local t = table.remove(MOCK.timers, 1)
		MOCK.now_ms = t.time
		t.callback()
	end
	MOCK.now_ms = to_ms
end
"""

CAMPAIGN_MOCK = r"""
-- the world: factions, armies and units. MOCK.forces is what exists now; the pending battle points at characters.
MOCK.forces, MOCK.factions, MOCK.pb, MOCK.pbc = {}, {}, {}, { attackers = {}, defenders = {} }
MOCK.campaign = { multiplayer = false, turn = 37, difficulty = "hard", name = "main_warhammer" }

local function list(items)
	return { num_items = function() return #items end, item_at = function(_, i) return items[i + 1] end }
end

function MOCK.faction(name, human)
	local f = { name = function() return name end, is_human = function() MOCK.maybe("faction.is_human"); return human end }
	MOCK.factions[name] = f
	return f
end

function MOCK.unit(d)
	return {
		d = d,
		command_queue_index = function() return d.cqi end,
		unit_key = function() return d.key end,
		percentage_proportion_of_full_strength = function()
			MOCK.maybe("unit.percentage_proportion_of_full_strength")
			return d.strength
		end,
		experience_level = function() MOCK.maybe("unit.experience_level"); return d.xp end,
	}
end

-- a character with an army; the army is also entered in the world
function MOCK.character(faction, mf_cqi, units)
	local force = {
		units = units,
		is_null_interface = function() return false end,
		command_queue_index = function() return mf_cqi end,
		unit_list = function(self) MOCK.maybe("mf.unit_list"); return list(self.units) end,
	}
	MOCK.forces[mf_cqi] = force
	return {
		cqi = mf_cqi + 1000, force = force, faction_name = faction:name(),
		is_null_interface = function() MOCK.maybe("character.is_null_interface"); return false end,
		faction = function() MOCK.maybe("character.faction"); return faction end,
		has_military_force = function() return true end,
		military_force = function() MOCK.maybe("character.military_force"); return force end,
	}
end

local pb = {}
function pb:is_active() return MOCK.pb.active == true end
function pb:has_been_fought() MOCK.maybe("pb.has_been_fought"); return MOCK.pb.fought == true end
function pb:has_attacker() MOCK.maybe("pb.has_attacker"); return MOCK.pb.attacker ~= nil end
function pb:has_defender() MOCK.maybe("pb.has_defender"); return MOCK.pb.defender ~= nil end
function pb:attacker() MOCK.maybe("pb.attacker"); return MOCK.pb.attacker end
function pb:defender() MOCK.maybe("pb.defender"); return MOCK.pb.defender end
function pb:secondary_attackers() return list(MOCK.pb.secondary_attackers or {}) end
function pb:secondary_defenders() return list(MOCK.pb.secondary_defenders or {}) end
function pb:attacker_won() return MOCK.pb.winner == "attacker" end
function pb:defender_won() return MOCK.pb.winner == "defender" end
function pb:is_draw() return MOCK.pb.winner == "draw" end
function pb:battle_type() MOCK.maybe("pb.battle_type"); return MOCK.pb.type or "land_normal" end
function pb:ambush_battle() return MOCK.pb.ambush == true end
function pb:night_battle() return MOCK.pb.night == true end
function pb:has_contested_garrison() return MOCK.pb.settlement == true end
function pb:set_piece_battle_key() MOCK.maybe("pb.set_piece_battle_key"); return MOCK.pb.quest or "" end

local model = {}
function model:pending_battle() MOCK.maybe("model.pending_battle"); return pb end
function model:turn_number() return MOCK.campaign.turn end

cm = {}
function cm:model() return model end
function cm:is_multiplayer() MOCK.maybe("cm.is_multiplayer"); return MOCK.campaign.multiplayer end
function cm:get_difficulty(as_string) assert(as_string == true); return MOCK.campaign.difficulty end
function cm:get_campaign_name() return MOCK.campaign.name end
function cm:get_faction(name) return MOCK.factions[name] or false end
function cm:get_military_force_by_cqi(cqi)
	MOCK.maybe("cm.get_military_force_by_cqi")
	return MOCK.forces[cqi] or false
end
-- CA's pending battle cache: unit cqi and key per army, nothing else (lib_campaign_manager.lua, cache_pending_battle_character)
function MOCK.build_ca_cache()
	local function record(c)
		local r = { cqi = c.cqi, mf_cqi = c.force:command_queue_index(), faction_name = c.faction_name, units = {} }
		for _, u in ipairs(c.force.units) do
			table.insert(r.units, { unit_cqi = u.d.cqi, unit_key = u.d.key })
		end
		return r
	end
	local a, d = {}, {}
	if MOCK.pb.attacker then table.insert(a, record(MOCK.pb.attacker)) end
	for _, c in ipairs(MOCK.pb.secondary_attackers or {}) do table.insert(a, record(c)) end
	if MOCK.pb.defender then table.insert(d, record(MOCK.pb.defender)) end
	for _, c in ipairs(MOCK.pb.secondary_defenders or {}) do table.insert(d, record(c)) end
	MOCK.pbc = { attackers = a, defenders = d }
end
function cm:pending_battle_cache_num_attackers() MOCK.maybe("cm.pending_battle_cache"); return #MOCK.pbc.attackers end
function cm:pending_battle_cache_num_defenders() return #MOCK.pbc.defenders end
function cm:pending_battle_cache_get_attacker(i) local r = MOCK.pbc.attackers[i]; return r.cqi, r.mf_cqi, r.faction_name end
function cm:pending_battle_cache_get_defender(i) local r = MOCK.pbc.defenders[i]; return r.cqi, r.mf_cqi, r.faction_name end
function cm:pending_battle_cache_get_attacker_units(i) return MOCK.pbc.attackers[i].units end
function cm:pending_battle_cache_get_defender_units(i) return MOCK.pbc.defenders[i].units end
function cm:pending_battle_cache_human_is_involved()
	for _, side in ipairs({ MOCK.pbc.attackers, MOCK.pbc.defenders }) do
		for _, r in ipairs(side) do
			local f = MOCK.factions[r.faction_name]
			if f and f:is_human() then return true end
		end
	end
	return false
end

-- a standard battle: the player attacks with a main army and a reinforcing army, an AI army defends
function MOCK.standard_battle(player_attacks)
	MOCK.forces = {}
	local emp = MOCK.faction("wh_main_emp_empire", true)
	local grn = MOCK.faction("wh_main_grn_greenskins", false)
	local main = MOCK.character(emp, 11, {
		MOCK.unit({ cqi = 101, key = "wh_main_emp_cha_karl_franz", strength = 100, xp = 0 }),
		MOCK.unit({ cqi = 102, key = "wh_main_emp_inf_swordsmen", strength = 87.5, xp = 3 }),
		MOCK.unit({ cqi = 103, key = "wh_main_emp_inf_handgunners", strength = 62.123456, xp = 9 }) })
	local second = MOCK.character(emp, 12, { MOCK.unit({ cqi = 111, key = "wh_main_emp_cav_reiksguard", strength = 100, xp = 1 }) })
	local enemy = MOCK.character(grn, 21, {
		MOCK.unit({ cqi = 201, key = "wh_main_grn_inf_orc_boyz", strength = 100, xp = 2 }),
		MOCK.unit({ cqi = 202, key = "wh_main_grn_mon_giant", strength = 55, xp = 0 }) })
	if player_attacks then
		MOCK.pb = { active = true, fought = false, attacker = main, defender = enemy, secondary_attackers = { second } }
	else
		MOCK.pb = { active = true, fought = false, attacker = enemy, defender = main, secondary_defenders = { second } }
	end
	MOCK.build_ca_cache()
end

-- what the battle did: Karl Franz hurt, the swordsmen destroyed, the giant's army wiped out
function MOCK.resolve(winner)
	MOCK.pb.fought = true
	MOCK.pb.winner = winner
	MOCK.forces[11].units[1].d.strength = 64.5
	table.remove(MOCK.forces[11].units, 2)
	MOCK.forces[11].units[2].d.xp = 9
	MOCK.forces[21] = nil
end
"""


def compile_lua(lua, code, chunk):
    """Compiles a chunk under a given name (the name is what Lua puts in front of error messages)."""
    return lua.eval("function(code, name) return assert(loadstring(code, name)) end")(code, chunk)


def runtime(*mocks):
    lua = lua51.LuaRuntime(unpack_returned_tuples=True)
    for code in (COMMON_MOCK,) + mocks:
        compile_lua(lua, code, MOCK_CHUNK)()
    return lua


def load_script(lua, path):
    """Loads a script the way the game does: under its pack path, run once. Nothing may come out of it."""
    with open(path, encoding="utf-8") as f:
        code = f.read()
    chunk = "@script\\" + ("battle" if path == BATTLE else "campaign") + "\\mod\\" + os.path.basename(path)
    compile_lua(lua, code, chunk)()


def log_of(lua):
    return lua.eval("MOCK.files['%s'] or ''" % LOG)


def never_raises(what, f):
    try:
        f()
        check(True, what)
    except Exception as e:  # an error out of the script is exactly what must never happen
        check(False, "%s: an error came out of the script: %s" % (what, e))


# ---------------------------------------------------------------------------------------------------------------------
# battle scenarios

STANDARD_BATTLE = r"""
MOCK.alliances = {
	MOCK.alliance({ MOCK.army({
		MOCK.unit({ key = "wh_main_emp_cha_karl_franz", men = 1, alive = 1, kills = 41, hp = 0.4371, general = true, uid = 1 }),
		MOCK.unit({ key = "wh_main_emp_inf_swordsmen", men = 120, alive = 87, kills = 64, hp = 0.713, uid = 2, rout_from = 30, rout_to = 50 }),
		MOCK.unit({ key = "wh_main_emp_inf_handgunners", men = 90, alive = 90, kills = 112, hp = 1, ammo = 3, ammo0 = 14, uid = 3 }),
	}, { { MOCK.unit({ key = "wh_main_emp_cav_reiksguard", men = 60, alive = 51, kills = 30, hp = 0.85, uid = 9 }) } }) }, true),
	MOCK.alliance({ MOCK.army({
		MOCK.unit({ key = "wh_main_grn_inf_orc_boyz", men = 120, alive = 20, kills = 30, hp = 0.1666, uid = 4, rout_from = 205 }),
		MOCK.unit({ key = "wh_main_grn_mon_giant", men = 1, alive = 0, kills = 12, hp = 0, uid = 5, rout_from = 95, shattered = true }),
		MOCK.unit({ key = "odd;unit|key", men = 80, alive = 80, kills = 0, hp = 1, uid = 6, raise = { number_of_enemies_killed = true } }),
	}) }, false),
}
"""


def fight(lua, deploy_ms=45000, length_s=212, deployed=True):
    """Drives a battle: deployment, the fighting phase in one-second steps, then the end."""
    lua.execute("MOCK.advance(%d)" % deploy_ms)
    if deployed:
        never_raises("Deployed phase", lambda: lua.execute("MOCK.phase('Deployed')"))
    for s in range(1, length_s + 1):
        never_raises("battle second %d" % s, lambda: lua.execute("MOCK.advance(%d)" % (deploy_ms + s * 1000)))
    never_raises("VictoryCountdown phase", lambda: lua.execute("MOCK.phase('VictoryCountdown')"))
    never_raises("Complete phase", lambda: lua.execute("MOCK.phase('Complete')"))


def battle_run(setup="", **kw):
    lua = runtime(BATTLE_MOCK)
    lua.execute(STANDARD_BATTLE)
    lua.execute(setup)
    never_raises("battle script loads", lambda: load_script(lua, BATTLE))
    fight(lua, **kw)
    return lua, log_of(lua)


def units_by_key(block):
    return dict((u[4], u) for u in block["units"])


def test_battle():
    print("battle: a normal campaign battle")
    lua, text = battle_run()
    print(text)
    blocks, errors = parse(text, "normal")
    check(text.startswith("# Community Balance Patch Battle Logger. Share this file at https://"), "first line of a new file is the comment")
    check(len(blocks) == 1 and not errors, "one block, no error line")
    h = blocks[0]["head"]
    check(h["campaign"] == "1" and h["type"] == "land_normal" and h["multiplayer"] == "0" and h["siege"] == "0", "header: battle kind")
    check(h["player"] == "1" and h["attacker"] == "1" and h["winner"] == "1", "header: player, attacker, winner")
    check(h["secs"] == "212", "secs counts from the start of the fighting, not of the deployment: " + h["secs"])
    check(h["cbp"] == "0.2.0", "cbp version")
    check(h["mods"] == "community_balance_patch.pack|odd,na,me.pack|community_balance_patch_battle_logger.pack", "mods: " + h["mods"])
    u = units_by_key(blocks[0])
    check(len(blocks[0]["units"]) == 7, "seven units, the reinforcement included")
    check(u["wh_main_emp_inf_swordsmen"] == "u;1;1;1;wh_main_emp_inf_swordsmen;120;87;64;0;0;0.713;0;0;0;1;30;2".split(";"),
          "the unit that routed at second 30 and rallied: " + ";".join(u["wh_main_emp_inf_swordsmen"]))
    check(u["wh_main_emp_cha_karl_franz"] == "u;1;1;1;wh_main_emp_cha_karl_franz;1;1;41;0;0;0.437;0;0;1;0;?;1".split(";"),
          "single entity: hp is the loss measure: " + ";".join(u["wh_main_emp_cha_karl_franz"]))
    check(u["wh_main_emp_inf_handgunners"][11:13] == ["3", "14"], "ammunition left and at the start")
    check(u["wh_main_emp_cav_reiksguard"][1:4] == ["1", "1", "1"] and u["wh_main_emp_cav_reiksguard"][16] == "9", "reinforcement unit")
    check(u["wh_main_grn_mon_giant"][8:10] == ["1", "1"] and u["wh_main_grn_mon_giant"][14:16] == ["1", "100"],
          "rout at 95 is seen at the 100 second sample: " + ";".join(u["wh_main_grn_mon_giant"]))
    check(u["wh_main_grn_inf_orc_boyz"][14:16] == ["1", "210"], "rout at 205 is seen at 210: " + ";".join(u["wh_main_grn_inf_orc_boyz"]))
    check("odd,unit,key" in u and u["odd,unit,key"][7] == "?", "a ; or | in a value becomes a comma, a failed call becomes ?")
    check(u["odd,unit,key"][3] == "0", "enemy units are not the player's")
    check(lua.eval("#MOCK.timers") == 0, "the repeating callback is removed when the battle ends")

    print("battle: a second battle goes into the same file; custom battle without the patch")
    lua.execute("MOCK.phases = {}; MOCK.now_ms = 0; MOCK.cbp = ''; MOCK.battle.from_campaign = false; MOCK.battle.winner = 0; MOCK.svr = {}")
    never_raises("battle script loads again", lambda: load_script(lua, BATTLE))
    fight(lua, length_s=5)
    text2 = log_of(lua)
    blocks, errors = parse(text2, "second")
    check(len(blocks) == 2 and text2.count("# Community Balance Patch") == 1, "second block appended, comment written once")
    check(blocks[1]["head"]["cbp"] == "none" and blocks[1]["head"]["campaign"] == "0" and blocks[1]["head"]["winner"] == "0",
          "no patch: cbp=none, custom battle: campaign=0, no winner: 0")
    check(all(x[14] == "0" for x in blocks[1]["units"]), "a battle shorter than one sample: nobody routing at the end, ever_routed 0")
    check(lua.eval("MOCK.svr.cbp_logger_from_battle") is None, "custom battle: no note for the campaign script")

    print("battle: the patch version text is missing, or the call fails")
    _, text = battle_run("MOCK.cbp = nil", length_s=12)
    check(parse(text, "cbp nil")[0][0]["head"]["cbp"] == "none", "nil version text: cbp=none")
    _, text = battle_run("MOCK.raise['common.get_localised_string'] = 'no such thing'", length_s=12)
    check(parse(text, "cbp raise")[0][0]["head"]["cbp"] == "?", "failed call: cbp=?")
    _, text = battle_run("MOCK.cbp = '0.2;0|x'", length_s=12)
    check(parse(text, "cbp odd")[0][0]["head"]["cbp"] == "0.2,0,x", "version text is sanitised")

    print("battle: the player's alliance cannot be read")
    _, text = battle_run("MOCK.raise['bm.get_player_alliance_num'] = 'boom'", length_s=40)
    blocks, errors = parse(text, "no player")
    check(blocks[0]["head"]["player"] == "?", "player=?, not 0")
    check(all(x[3] == "?" for x in blocks[0]["units"]), "player flag is ? on every unit, not 0")

    print("battle: every header call fails")
    _, text = battle_run("for _, n in ipairs({'is_from_campaign','battle_type','is_multiplayer','is_siege_battle','victorious_alliance'}) do MOCK.raise['bm.' .. n] = 'boom' end", length_s=20)
    blocks, errors = parse(text, "header fails")
    h = blocks[0]["head"]
    check([h[k] for k in ("campaign", "type", "multiplayer", "siege", "winner")] == ["?"] * 5, "each failed header call is ?")

    print("battle: the unit lists fail when the battle ends")
    lua = runtime(BATTLE_MOCK)
    lua.execute(STANDARD_BATTLE)
    load_script(lua, BATTLE)
    lua.execute("MOCK.advance(45000); MOCK.phase('Deployed'); MOCK.advance(60000)")
    lua.execute("MOCK.raise['bm.alliances'] = 'cannot open D:\\\\Games\\\\Total War\\\\data.pack; really | truly'")
    never_raises("Complete with failing unit lists", lambda: lua.execute("MOCK.phase('Complete')"))
    text = log_of(lua)
    print(text)
    blocks, errors = parse(text, "lists fail")
    check(len(blocks) == 0 and len(errors) == 1, "no block, one #error line")
    check(errors[0] == "#error;v2;write_battle;cannot open <path> really , truly", "error text without paths or separators: " + errors[0])
    check("John" not in text and "Quincy" not in text and "Smith" not in text and "mock" not in text, "nothing of the script path or the user name is written")

    print("battle: the sampler fails once in the middle of the battle")
    lua = runtime(BATTLE_MOCK)
    lua.execute(STANDARD_BATTLE)
    load_script(lua, BATTLE)
    lua.execute("MOCK.advance(45000); MOCK.phase('Deployed'); MOCK.advance(45000 + 45000)")
    lua.execute("MOCK.raise['bm.alliances'] = 'boom'")
    never_raises("sample with failing unit lists", lambda: lua.execute("MOCK.advance(45000 + 55000)"))
    check(lua.eval("#MOCK.timers") == 0, "one error cancels the sampler for good")
    lua.execute("MOCK.raise['bm.alliances'] = nil; MOCK.advance(45000 + 212000)")
    never_raises("Complete", lambda: lua.execute("MOCK.phase('Complete')"))
    text = log_of(lua)
    blocks, errors = parse(text, "sampler fails")
    check(len(errors) == 1 and errors[0] == "#error;v2;sampler;boom", "one #error line for the sampler: %s" % errors)
    u = units_by_key(blocks[0])
    check(u["wh_main_emp_inf_swordsmen"][14:16] == ["1", "30"], "what was seen before the error is kept")
    check(u["wh_main_emp_inf_handgunners"][14:16] == ["?", "?"], "after the error a unit not seen routing is ?, not 0")
    check(u["wh_main_grn_inf_orc_boyz"][14:16] == ["1", "212"], "routing at the end still counts as routed")

    check(text.startswith("# Community Balance Patch Battle Logger. Share this file at https://") and text.count("# Community") == 1,
          "an #error line written first still leaves the comment as the first line of a new file, once")

    print("battle: error messages with folder and user names of several words")
    for message, expect in (
            ("cannot open C:\\\\Users\\\\Lucas Erik Hellgren\\\\AppData\\\\x.txt: Permission denied", "cannot open <path> Permission denied"),
            ("C:\\\\Program Files (x86)\\\\Steam\\\\steamapps\\\\common\\\\Total War WARHAMMER III\\\\used_mods.txt: No such file", "<path> No such file"),
            ("/home/a b c d/steam/file: gone", "<path> gone"),
            ("attempt to index a nil value", "attempt to index a nil value"),
            ("one\\\\two", "<path>")):
        lua = runtime(BATTLE_MOCK)
        lua.execute(STANDARD_BATTLE)
        load_script(lua, BATTLE)
        lua.execute("MOCK.advance(45000); MOCK.phase('Deployed'); MOCK.advance(60000)")
        lua.execute("MOCK.raise['bm.alliances'] = '%s'" % message)
        never_raises("Complete", lambda: lua.execute("MOCK.phase('Complete')"))
        blocks, errors = parse(log_of(lua), "long path")
        check(len(errors) == 1 and errors[0] == "#error;v2;write_battle;" + expect, "%s -> %s" % (message, errors))

    print("battle: the game cannot remove the sampler when the battle ends")
    lua = runtime(BATTLE_MOCK)
    lua.execute(STANDARD_BATTLE)
    load_script(lua, BATTLE)
    lua.execute("MOCK.advance(45000); MOCK.phase('Deployed'); MOCK.advance(45000 + 212000)")
    lua.execute("MOCK.raise['bm.remove_callback'] = 'boom'")
    never_raises("Complete", lambda: lua.execute("MOCK.phase('Complete')"))
    text = log_of(lua)
    blocks, errors = parse(text, "sampler not removed")
    check(len(blocks) == 1 and not errors, "the battle is written")
    check(units_by_key(blocks[0])["wh_main_emp_inf_handgunners"][14] == "0", "ever_routed is still 0 for a unit never seen routing")
    walks = lua.eval("MOCK.unit_walks")
    check(lua.eval("#MOCK.timers") == 1, "the timer is still there (this is the case being tested)")
    never_raises("time goes on after the battle", lambda: lua.execute("MOCK.advance(45000 + 300000)"))
    check(lua.eval("MOCK.unit_walks") == walks and log_of(lua) == text, "the sampler makes no game call and writes nothing after the battle")

    print("battle: the fighting phase is never announced, or the timer cannot be started")
    _, text = battle_run(deployed=False, length_s=60)
    blocks, errors = parse(text, "no Deployed")
    check(all(x[14] in ("?", "1") for x in blocks[0]["units"]) and not errors, "no sampling: ever_routed is ? or 1, never 0")
    _, text = battle_run("MOCK.raise['bm.repeat_callback'] = 'boom'", length_s=60)
    blocks, errors = parse(text, "no timer")
    check(len(errors) == 1 and errors[0].startswith("#error;v2;start sampler;"), "timer failure is an #error line")
    check(len(blocks) == 1 and all(x[14] in ("?", "1") for x in blocks[0]["units"]), "the battle is still written")
    check(text.startswith("# Community Balance Patch Battle Logger.") and text.count("# Community") == 1, "comment first, once")

    print("battle: the game gives no unit ids")
    _, text = battle_run("MOCK.raise['unit.unique_ui_id'] = 'boom'")
    blocks, errors = parse(text, "no uid")
    u = units_by_key(blocks[0])
    check(all(x[16] == "?" for x in blocks[0]["units"]), "uid is ?")
    check(u["wh_main_emp_inf_swordsmen"][14:16] == ["1", "30"], "routing is still tracked, by the unit's place in the lists")

    print("battle: every unit call fails")
    names = ["type", "initial_number_of_men", "number_of_men_alive", "number_of_enemies_killed", "is_shattered", "unary_hitpoints",
             "ammo_left", "starting_ammo", "is_commanding_unit", "unique_ui_id", "is_routing"]
    _, text = battle_run("".join("MOCK.raise['unit.%s'] = 'boom';" % n for n in names), length_s=30)
    blocks, errors = parse(text, "units fail")
    check(all(x[4:] == ["?"] * 13 for x in blocks[0]["units"]), "every field is ?: " + ";".join(blocks[0]["units"][0]))

    print("battle: no battle manager at all, and no file access")
    lua = runtime()
    never_raises("script loads without bm", lambda: load_script(lua, BATTLE))
    blocks, errors = parse(log_of(lua), "no bm")
    check(len(errors) == 1 and errors[0].startswith("#error;v2;register;"), "an #error line: %s" % errors)
    lua = runtime(BATTLE_MOCK)
    lua.execute(STANDARD_BATTLE)
    lua.execute("MOCK.raise['io.open'] = 'access denied'")
    never_raises("script loads without file access", lambda: load_script(lua, BATTLE))
    fight(lua, length_s=30)
    check(log_of(lua) == "", "nothing written, nothing raised")


# ---------------------------------------------------------------------------------------------------------------------
# campaign scenarios

def campaign_session(lua=None, first_tick=True):
    """A script session: the campaign scripts are loaded, and the mod function is called on the first tick."""
    if lua is None:
        lua = runtime(CAMPAIGN_MOCK)
    lua.execute("MOCK.listeners = {}")
    never_raises("campaign script loads", lambda: load_script(lua, CAMPAIGN))
    if first_tick:
        never_raises("campaign script starts", lambda: lua.execute("cbp_autoresolve_logger()"))
    return lua


def fire(lua, event, button=None):
    ctx = "{ string = '%s' }" % button if button else "{}"
    never_raises(event + (" " + button if button else ""), lambda: lua.execute("MOCK.fire('%s', %s)" % (event, ctx)))


def pending(lua, player_attacks=True, extra=""):
    lua.execute("MOCK.standard_battle(%s) %s" % ("true" if player_attacks else "false", extra))
    fire(lua, "PendingBattle")


def to_battle_and_back(lua):
    """The player fights: the campaign script session ends, the battle script runs, a new campaign session starts."""
    fire(lua, "ComponentLClickUp", "button_attack")
    lua.execute("MOCK.svr.cbp_logger_from_battle = true")      # what the battle script does when it loads
    lua.execute("MOCK.resolve('attacker')")
    campaign_session(lua)                                      # fresh script state, same world, same registry
    fire(lua, "LoadingScreenDismissed")


EXPECT_UNITS_AUTO = [
    "r;1;1;1;wh_main_emp_cha_karl_franz;100;64.5;0;wh_main_emp_empire",
    "r;1;1;1;wh_main_emp_inf_swordsmen;87.5;0;3;wh_main_emp_empire",
    "r;1;1;1;wh_main_emp_inf_handgunners;62.12;62.12;9;wh_main_emp_empire",
    "r;1;2;1;wh_main_emp_cav_reiksguard;100;100;1;wh_main_emp_empire",
    "r;2;1;0;wh_main_grn_inf_orc_boyz;100;0;2;wh_main_grn_greenskins",
    "r;2;1;0;wh_main_grn_mon_giant;55;0;0;wh_main_grn_greenskins",
]


def lines_of(block):
    return [";".join(u) for u in block["units"]]


def test_campaign():
    print("campaign: an auto-resolved battle")
    lua = campaign_session()
    pending(lua)
    fire(lua, "ComponentLClickUp", "button_autoresolve")
    lua.execute("MOCK.resolve('attacker')")
    fire(lua, "BattleCompleted")
    text = log_of(lua)
    print(text)
    blocks, errors = parse(text, "auto")
    check(text.startswith("# Community Balance Patch Battle Logger."), "first line of a new file is the comment")
    check(len(blocks) == 1 and not errors, "one block, no error line")
    h = blocks[0]["head"]
    check(h["mode"] == "auto" and h["winner"] == "attacker" and h["turn"] == "37" and h["difficulty"] == "hard", "header: mode, winner, turn, difficulty")
    check(h["type"] == "land_normal" and h["ambush"] == "0" and h["night"] == "0" and h["settlement"] == "0" and h["quest"] == "", "header: battle kind")
    check(h["campaign"] == "main_warhammer" and h["player_side"] == "1" and h["cbp"] == "0.2.0", "header: campaign, player side, patch")
    check(lines_of(blocks[0]) == EXPECT_UNITS_AUTO, "unit lines:\n    " + "\n    ".join(lines_of(blocks[0])))
    check(lua.eval("MOCK.svr.cbp_logger_snapshot") == "", "the stored snapshot is cleared after the battle")

    print("campaign: a fought battle (the script is started again while the battle is fought)")
    lua = campaign_session()
    pending(lua, extra="MOCK.pb.ambush = true; MOCK.pb.type = 'land_ambush'")
    check(log_of(lua) == "", "nothing is written before the battle")
    to_battle_and_back(lua)
    fire(lua, "BattleCompleted")
    text = log_of(lua)
    print(text)
    blocks, errors = parse(text, "fought")
    check(len(blocks) == 1 and not errors, "one block, no error line")
    h = blocks[0]["head"]
    check(h["mode"] == "fought" and h["winner"] == "attacker" and h["type"] == "land_ambush" and h["ambush"] == "1", "header: fought, ambush")
    check(lines_of(blocks[0]) == EXPECT_UNITS_AUTO, "same unit lines as the auto-resolved battle (experience from before the battle):\n    " + "\n    ".join(lines_of(blocks[0])))
    never_raises("a second BattleCompleted", lambda: lua.execute("MOCK.fire('BattleCompleted', {})"))
    check(log_of(lua) == text, "a second BattleCompleted event for the same battle writes nothing")

    print("campaign: a fought battle after the game was restarted in between (no stored snapshot)")
    lua = campaign_session()
    pending(lua, player_attacks=False)
    fire(lua, "ComponentLClickUp", "button_attack")
    lua.execute("MOCK.svr = {}; MOCK.resolve('defender')")
    campaign_session(lua)
    fire(lua, "LoadingScreenDismissed")
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "fought, no snapshot")
    h = blocks[0]["head"]
    check(h["mode"] == "fought" and h["winner"] == "defender" and h["player_side"] == "2", "fought, player defended")
    check(all(u[5] == "?" and u[7] == "?" for u in blocks[0]["units"]), "strength before and experience are ?, not guessed")
    check(";".join(blocks[0]["units"][0]) == "r;1;1;0;wh_main_grn_inf_orc_boyz;?;0;?;wh_main_grn_greenskins", "destroyed enemy: " + ";".join(blocks[0]["units"][0]))
    check("r;2;1;1;wh_main_emp_cha_karl_franz;?;64.5;?;wh_main_emp_empire" in lines_of(blocks[0]), "strength after is still read")

    print("campaign: a stored snapshot from another battle is not used")
    lua = campaign_session()
    pending(lua)
    lua.execute("MOCK.svr.cbp_logger_snapshot = '101,50,1 102,50,1 103,50,1 111,50,1 201,50,1 999,50,1'")
    to_battle_and_back(lua)
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "stale snapshot")
    check(all(u[5] == "?" for u in blocks[0]["units"]), "a snapshot that does not list exactly the same units is ignored")

    print("campaign: the player's army is destroyed in a fought battle")
    lua = campaign_session()
    pending(lua)
    fire(lua, "ComponentLClickUp", "button_attack")
    lua.execute("MOCK.svr.cbp_logger_from_battle = true; MOCK.pb.fought = true; MOCK.pb.winner = 'defender'; MOCK.forces[11] = nil; MOCK.forces[12] = nil")
    campaign_session(lua)
    fire(lua, "LoadingScreenDismissed")
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "army destroyed")
    mine = [u for u in blocks[0]["units"] if u[3] == "1"]
    check(len(mine) == 4 and all(u[6] == "0" for u in mine), "every unit of the destroyed armies has strength_after 0")
    check([u[5] for u in mine] == ["100", "87.5", "62.12", "100"], "strength before from the stored snapshot")
    check(blocks[0]["head"]["winner"] == "defender" and blocks[0]["head"]["mode"] == "fought", "fought and lost")

    print("campaign: retreat, a declined battle, maintain siege (the battle is not fought)")
    lua = campaign_session()
    pending(lua)
    fire(lua, "BattleCompleted")
    check(log_of(lua) == "", "nothing is written")
    print("campaign: then a battle between AI factions")
    lua.execute("MOCK.standard_battle(true); MOCK.factions = {}; MOCK.pb.attacker.faction = function() return MOCK.faction('wh_main_dwf_dwarfs', false) end; MOCK.pb.secondary_attackers = {}; MOCK.build_ca_cache()")
    fire(lua, "PendingBattle")
    fire(lua, "ComponentLClickUp", "button_autoresolve")       # a stray click must not matter
    lua.execute("MOCK.resolve('attacker')")
    fire(lua, "BattleCompleted")
    check(log_of(lua) == "", "nothing is written for AI against AI")
    print("campaign: AI against AI right after a load (the script never saw the battle start)")
    campaign_session(lua)
    fire(lua, "BattleCompleted")
    check(log_of(lua) == "", "nothing is written")

    print("campaign: a save loaded at the pre-battle screen, then auto-resolved")
    lua = runtime(CAMPAIGN_MOCK)
    lua.execute("MOCK.standard_battle(false); MOCK.pb.settlement = true; MOCK.pb.type = 'settlement_standard'")
    campaign_session(lua)
    fire(lua, "LoadingScreenDismissed")
    fire(lua, "ComponentLClickUp", "button_autoresolve")
    lua.execute("MOCK.resolve('defender')")
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "loaded at pre-battle")
    h = blocks[0]["head"]
    check(h["mode"] == "auto" and h["settlement"] == "1" and h["type"] == "settlement_standard" and h["player_side"] == "2", "auto, settlement, player defends")
    check("r;2;1;1;wh_main_emp_inf_swordsmen;87.5;0;3;wh_main_emp_empire" in lines_of(blocks[0]), "strength before from the snapshot taken after the load")

    print("campaign: a save loaded at the pre-battle screen, then fought")
    lua = runtime(CAMPAIGN_MOCK)
    lua.execute("MOCK.standard_battle(true)")
    campaign_session(lua)
    fire(lua, "LoadingScreenDismissed")
    to_battle_and_back(lua)
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "loaded, fought")
    check(blocks[0]["head"]["mode"] == "fought" and lines_of(blocks[0]) == EXPECT_UNITS_AUTO, "fought, with strengths before")

    print("campaign: two battles in a row, a quest battle with odd names")
    lua = campaign_session()
    pending(lua)
    fire(lua, "ComponentLClickUp", "button_autoresolve")
    lua.execute("MOCK.resolve('draw')")
    fire(lua, "BattleCompleted")
    pending(lua, extra="MOCK.pb.quest = 'wh_main_qb_emp;ghal|maraz'; MOCK.pb.night = true; MOCK.campaign.difficulty = 'very hard'; MOCK.forces[21].units[1].d.key = 'a;b|c'")
    fire(lua, "ComponentLClickUp", "button_autoresolve")
    lua.execute("MOCK.resolve('defender')")
    fire(lua, "BattleCompleted")
    text = log_of(lua)
    blocks, errors = parse(text, "two battles")
    check(len(blocks) == 2 and text.count("# Community Balance Patch") == 1, "two blocks, comment once")
    check(blocks[0]["head"]["winner"] == "draw", "draw")
    h = blocks[1]["head"]
    check(h["quest"] == "wh_main_qb_emp,ghal,maraz" and h["night"] == "1" and h["difficulty"] == "very hard", "quest key sanitised, night, difficulty with a space")
    check(any(u[4] == "a,b,c" for u in blocks[1]["units"]), "unit key sanitised")

    print("campaign: multiplayer")
    lua = runtime(CAMPAIGN_MOCK)
    lua.execute("MOCK.campaign.multiplayer = true; MOCK.svr.cbp_logger_from_battle = true")
    campaign_session(lua)
    check(lua.eval("MOCK.svr.cbp_logger_from_battle") is False, "the note from the battle script is cleared in multiplayer too")
    fire(lua, "LoadingScreenDismissed")
    pending(lua)
    fire(lua, "ComponentLClickUp", "button_autoresolve")
    lua.execute("MOCK.resolve('attacker')")
    fire(lua, "BattleCompleted")
    check(log_of(lua) == "" and lua.eval("MOCK.svr.cbp_logger_snapshot") is None, "nothing is written, nothing is stored")
    print("campaign: after a multiplayer battle, a single-player save loaded at the pre-battle screen")
    lua.execute("MOCK.campaign.multiplayer = false; MOCK.svr.cbp_logger_from_battle = true")   # the battle script ran in multiplayer
    lua.execute("MOCK.campaign.multiplayer = true")
    campaign_session(lua)                                      # back in the multiplayer campaign
    lua.execute("MOCK.campaign.multiplayer = false; MOCK.standard_battle(true)")
    campaign_session(lua)                                      # the single-player save
    fire(lua, "LoadingScreenDismissed")
    lua.execute("MOCK.resolve('attacker')")                    # auto-resolved without the button (hotkey)
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "after multiplayer")
    check(len(blocks) == 1 and blocks[0]["head"]["mode"] == "auto" and lines_of(blocks[0]) == EXPECT_UNITS_AUTO and not errors,
          "the snapshot is taken: mode=auto with strengths before")

    print("campaign: the game does not say whether the campaign is multiplayer")
    for setup in ("MOCK.raise['cm.is_multiplayer'] = 'boom in C:/Users/John Quincy Smith/x y/z.lua'", "MOCK.campaign.multiplayer = nil"):
        lua = runtime(CAMPAIGN_MOCK)
        lua.execute(setup)
        campaign_session(lua)
        fire(lua, "LoadingScreenDismissed")
        pending(lua)
        fire(lua, "ComponentLClickUp", "button_autoresolve")
        lua.execute("MOCK.resolve('attacker')")
        fire(lua, "BattleCompleted")
        pending(lua)
        fire(lua, "BattleCompleted")
        text = log_of(lua)
        blocks, errors = parse(text, "multiplayer unknown")
        check(not blocks and len(errors) == 1 and errors[0].startswith("#error;v2;result multiplayer;"), "no block, one #error line for the session: %s" % errors)
        check(text.startswith("# Community Balance Patch Battle Logger.") and "Quincy" not in text, "comment first, no path")

    print("campaign: the events come before the first tick")
    lua = campaign_session(first_tick=False)
    pending(lua)
    to_battle_and_back_before_tick = lambda: (fire(lua, "ComponentLClickUp", "button_attack"),
                                              lua.execute("MOCK.svr.cbp_logger_from_battle = true; MOCK.resolve('attacker')"),
                                              campaign_session(lua, first_tick=False))
    to_battle_and_back_before_tick()
    fire(lua, "BattleCompleted")
    never_raises("first tick", lambda: lua.execute("cbp_autoresolve_logger()"))
    blocks, errors = parse(log_of(lua), "before first tick")
    check(len(blocks) == 1 and blocks[0]["head"]["mode"] == "fought" and lines_of(blocks[0]) == EXPECT_UNITS_AUTO and not errors,
          "a fought battle that completes before the first tick is written")
    lua = runtime(CAMPAIGN_MOCK)
    lua.execute("MOCK.standard_battle(true)")
    campaign_session(lua, first_tick=False)
    fire(lua, "LoadingScreenDismissed")
    never_raises("first tick", lambda: lua.execute("cbp_autoresolve_logger()"))
    lua.execute("MOCK.resolve('attacker')")                    # auto-resolved without the button (hotkey)
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "load before first tick")
    check(len(blocks) == 1 and blocks[0]["head"]["mode"] == "auto" and lines_of(blocks[0]) == EXPECT_UNITS_AUTO,
          "a pre-battle save whose loading screen goes before the first tick: mode=auto with strengths before")
    check(lua.eval("#MOCK.listeners") == 3, "the first tick adds no listener a second time")

    print("campaign: the check 'is the player in this battle' fails")
    for name in ("character.faction", "character.is_null_interface", "pb.has_attacker", "pb.attacker", "pb.has_defender", "pb.defender"):
        for how in ("auto", "loaded"):
            lua = runtime(CAMPAIGN_MOCK)
            lua.execute("MOCK.raise['%s'] = 'boom'" % name)
            if how == "auto":
                campaign_session(lua)
                pending(lua)
                fire(lua, "ComponentLClickUp", "button_autoresolve")
            else:
                lua.execute("MOCK.standard_battle(true)")
                campaign_session(lua)
                fire(lua, "LoadingScreenDismissed")
            lua.execute("MOCK.resolve('attacker')")
            fire(lua, "BattleCompleted")
            text = log_of(lua)
            blocks, errors = parse(text, "involved " + name)
            check(len(blocks) == 1 and blocks[0]["head"]["mode"] == "auto" and len(blocks[0]["units"]) == 6,
                  "%s fails (%s): the battle is still written, from the game's cache\n%s" % (name, how, text))
            check(any(e.startswith("#error;v2;result involved;") for e in errors), "and the failure is an #error line: %s" % errors)
            check(text.startswith("# Community Balance Patch Battle Logger.") and text.count("# Community") == 1,
                  "an #error line written first still leaves the comment as the first line, once")
            if blocks:
                check(all(u[5] == "?" and u[7] == "?" for u in blocks[0]["units"]) and ";".join(blocks[0]["units"][0][:7]) == "r;1;1;1;wh_main_emp_cha_karl_franz;?;64.5",
                      "strength before is ?, strength after is read")
    print("campaign: the same failure during battles between AI factions")
    lua = campaign_session()
    lua.execute("MOCK.raise['pb.has_attacker'] = 'boom'")
    for _ in range(30):
        lua.execute("MOCK.standard_battle(true); MOCK.factions['wh_main_emp_empire'].is_human = function() return false end")
        fire(lua, "PendingBattle")
        lua.execute("MOCK.resolve('attacker')")
        fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "AI battles, check fails")
    check(not blocks and len(errors) == 20, "no block; the #error lines stop at 20 per script session: %d" % len(errors))

    print("campaign: the click handler only sets a flag")
    lua = campaign_session()
    lua.execute("cm = setmetatable({}, { __index = function() error('game read inside a click') end })")
    fire(lua, "ComponentLClickUp", "button_autoresolve")
    fire(lua, "ComponentLClickUp", "button_attack")
    fire(lua, "ComponentLClickUp", "something_else")
    check(log_of(lua) == "", "no game read, nothing written")

    print("campaign: injected errors")
    cases = [
        ("pb.battle_type", lambda b, e: b and b[0]["head"]["type"] == "?" and not e, "type=?"),
        ("pb.set_piece_battle_key", lambda b, e: b and b[0]["head"]["quest"] == "?" and not e, "quest=?"),
        ("unit.experience_level", lambda b, e: b and all(u[7] == "?" for u in b[0]["units"]), "xp=?"),
        ("unit.percentage_proportion_of_full_strength", lambda b, e: b and all(u[5] == "?" and u[6] in ("?", "0") for u in b[0]["units"]), "strengths are ?"),
        ("cm.get_military_force_by_cqi", lambda b, e: b and all(u[6] == "?" for u in b[0]["units"]), "strength after is ?, not 0, when the armies cannot be looked up"),
        ("mf.unit_list", lambda b, e: len(b) == 1 and len(e) == 4 and all(u[5] == "?" and u[6] in ("?", "0") for u in b[0]["units"]),
         "no army readable: #error lines, the units come from the game's cache, strengths are ?"),
        ("character.military_force", lambda b, e: len(b) == 1 and len(e) == 4 and all(u[5] == "?" for u in b[0]["units"]),
         "no snapshot: #error lines, the units come from the game's cache, strength before is ?"),
        ("pb.has_been_fought", lambda b, e: not b and len(e) == 1, "one #error line, no block"),
        ("model.pending_battle", lambda b, e: not b and len(e) >= 1, "#error lines, no block"),
        ("faction.is_human", lambda b, e: not b and len(e) == 2 and e[0].startswith("#error;v2;result involved;") and e[1].startswith("#error;v2;result write;"),
         "nobody can say whether the player is in it: no block, two #error lines"),
        ("core.svr_save_string", lambda b, e: len(b) == 1 and len(e) == 2, "the block is written, the registry failure is two #error lines"),
        ("io.open", lambda b, e: not b and not e, "nothing can be written, nothing raised"),
    ]
    for name, expect, what in cases:
        for mode in ("auto", "fought"):
            lua = campaign_session()
            lua.execute("MOCK.raise['%s'] = 'boom in C:/Users/John Quincy Smith/x.lua'" % name)
            pending(lua)
            if mode == "auto":
                fire(lua, "ComponentLClickUp", "button_autoresolve")
                lua.execute("MOCK.resolve('attacker')")
            else:
                to_battle_and_back(lua)
            fire(lua, "BattleCompleted")
            text = log_of(lua)
            blocks, errors = parse(text, "inject " + name + " " + mode)
            if mode == "auto":
                check(expect(blocks, errors), "%s fails (%s): %s\n%s" % (name, mode, what, text))
            check("John" not in text and "Quincy" not in text and "Smith" not in text, "no path in the log")
    lua = campaign_session()
    pending(lua)
    lua.execute("MOCK.raise['cm.pending_battle_cache'] = 'boom'")
    to_battle_and_back(lua)
    fire(lua, "BattleCompleted")
    blocks, errors = parse(log_of(lua), "cache fails")
    check(not blocks and len(errors) == 1 and errors[0] == "#error;v2;result write;boom", "the game's cache fails after a fought battle: %s" % errors)

    print("campaign: no game objects at all")
    lua = runtime()
    never_raises("script loads without cm", lambda: load_script(lua, CAMPAIGN))
    never_raises("script starts without cm", lambda: lua.execute("cbp_autoresolve_logger()"))
    for event in ("LoadingScreenDismissed", "PendingBattle", "BattleCompleted", "PendingBattle", "BattleCompleted"):
        fire(lua, event)
    blocks, errors = parse(log_of(lua), "no cm")
    check(not blocks and len(errors) == 1 and errors[0].startswith("#error;v2;result multiplayer;"), "no block, one #error line: %s" % errors)
    lua = runtime()
    lua.execute("MOCK.raise['core.add_listener'] = 'boom'")
    never_raises("script loads when listeners cannot be added", lambda: load_script(lua, CAMPAIGN))
    never_raises("script starts", lambda: lua.execute("cbp_autoresolve_logger()"))
    text = log_of(lua)
    blocks, errors = parse(text, "no listeners")
    check(lua.eval("#MOCK.listeners") == 0 and len(errors) == 1 and errors[0] == "#error;v2;result register;boom", "one #error line: %s" % errors)
    check(text.startswith("# Community Balance Patch Battle Logger."), "comment first")


# ---------------------------------------------------------------------------------------------------------------------
# the game runs Lua 5.1

def test_lua51():
    print("Lua 5.1: both scripts compile, and use nothing newer")
    lua = lua51.LuaRuntime()
    check(lua.eval("_VERSION") == "Lua 5.1", "the test runtime is " + lua.eval("_VERSION"))
    for path in (BATTLE, CAMPAIGN):
        with open(path, encoding="utf-8") as f:
            code = f.read()
        try:
            compile_lua(lua, code, "@" + os.path.basename(path))
            check(True, os.path.basename(path) + " compiles as Lua 5.1")
        except Exception as e:
            check(False, "%s compiles as Lua 5.1: %s" % (os.path.basename(path), e))
        bare = re.sub(r"--[^\n]*", "", code)
        bare = re.sub(r'"(\\.|[^"\\\n])*"|\'(\\.|[^\'\\\n])*\'', '""', bare)
        for bad, what in ((r"\bgoto\b", "goto"), (r"//", "integer division"), (r"<<|>>|[^~]~[^=]|&", "bit operators"),
                          (r"\butf8\.", "utf8 library"), (r"\btable\.(un)?pack\b", "table.pack/unpack"),
                          (r"\bmath\.(tointeger|type)\b", "math.tointeger/type"), (r"<(const|close)>", "attributes")):
            check(re.search(bad, bare) is None, "%s: no %s" % (os.path.basename(path), what))
        check(all(ord(c) < 128 for c in code), os.path.basename(path) + ": plain ASCII")
        globals_set = re.findall(r"^function\s+([A-Za-z_][\w.:]*)", code, re.M)
        check(globals_set == (["cbp_autoresolve_logger"] if path == CAMPAIGN else []),
              "%s: the only global it defines is the function the game calls: %s" % (os.path.basename(path), globals_set))


if __name__ == "__main__":
    test_lua51()
    test_battle()
    test_campaign()
    print()
    if failures:
        print("%d of %d checks FAILED" % (len(failures), checks))
        for f in failures:
            print("  " + f)
        sys.exit(1)
    print("all %d checks passed" % checks)
