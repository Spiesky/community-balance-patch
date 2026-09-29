-- Community Balance Patch: Battle Logger
--
-- At the end of every battle this writes one line per unit to cbp_battle_log.txt in the game folder: the unit, how
-- many models it started and ended with, how many it killed, and whether it was routing. It also notes the names of the
-- mod packs in use (names only, never folder paths). Nothing leaves your PC: the game's scripts cannot go online. If you
-- want to help, attach the file to a test report on the Community Balance Patch GitHub page. Thank you!
--
-- It only reads. Everything is wrapped so that a failure here can never affect the battle.

local LOG_FILE = "cbp_battle_log.txt"
local VERSION = "1"

local function safe(f, ...)
	local ok, result = pcall(f, ...)
	if ok then
		return result
	end
	return nil
end

local function mod_packs()
	local names = {}
	local file = io.open("used_mods.txt", "r")
	if not file then
		return "unknown"
	end
	for line in file:lines() do
		local pack = line:match('^%s*mod%s+"([^"/\\]+%.pack)"')
		if pack then
			table.insert(names, pack)
		end
	end
	file:close()
	return #names > 0 and table.concat(names, "|") or "none"
end

local function flag(v)
	if v == nil then
		return "?"
	end
	return v and "1" or "0"
end

local function write_battle()
	local lines = {}
	local when = safe(os.date, "%Y-%m-%d %H:%M") or "?"
	table.insert(lines, string.format("#battle;v%s;%s;multiplayer=%s;siege=%s;mods=%s",
		VERSION, when, flag(safe(function() return bm:is_multiplayer() end)),
		flag(safe(function() return bm:is_siege_battle() end)), mod_packs()))
	local player = safe(function() return bm:get_player_alliance_num() end) or 0
	local alliances = bm:alliances()
	for a = 1, alliances:count() do
		local armies = alliances:item(a):armies()
		for b = 1, armies:count() do
			local units = armies:item(b):units()
			for u = 1, units:count() do
				local unit = units:item(u)
				table.insert(lines, string.format("u;%d;%d;%s;%s;%s;%s;%s;%s;%s",
					a, b, flag(a == player),
					tostring(safe(function() return unit:type() end) or "?"),
					tostring(safe(function() return unit:initial_number_of_men() end) or "?"),
					tostring(safe(function() return unit:number_of_men_alive() end) or "?"),
					tostring(safe(function() return unit:number_of_enemies_killed() end) or "?"),
					flag(safe(function() return unit:is_routing() end)),
					flag(safe(function() return unit:is_shattered() end))))
			end
		end
	end
	table.insert(lines, "#end")
	local file = io.open(LOG_FILE, "a")
	if file then
		file:write(table.concat(lines, "\n") .. "\n")
		file:close()
	end
end

local written = false
local function on_complete()
	if written then
		return
	end
	written = true
	safe(write_battle)
end

safe(function()
	bm:register_phase_change_callback("Complete", on_complete)
end)
