-- Community Balance Patch: Battle Logger
--
-- At the end of every battle this writes one line per unit to cbp_battle_log.txt in the game folder: the unit, how
-- many models it started and ended with, how many it killed, and whether it was routing. It also notes the names of the
-- mod packs in use (names only, never folder paths). Nothing leaves your PC: the game's scripts cannot go online. If you
-- want to help, share it at https://spiesky.github.io/community-balance-patch/ . Thank you!
--
-- It only reads. Everything is wrapped so that a failure here can never affect the battle.

local LOG_FILE = "cbp_battle_log.txt"
local VERSION = "1"
local SHARE_PAGE = "https://spiesky.github.io/community-balance-patch/"

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
			local army = armies:item(b)
			-- the army's own units, then any reinforcement groups that arrived during the battle
			local groups = { army:units() }
			for r = 1, safe(function() return army:num_reinforcement_units() end) or 0 do
				local extra = safe(function() return army:get_reinforcement_units(r) end)
				if extra then
					table.insert(groups, extra)
				end
			end
			for _, units in ipairs(groups) do
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
	end
	table.insert(lines, "#end")
	local existing = io.open(LOG_FILE, "r")
	if existing then
		existing:close()
	else
		table.insert(lines, 1, "# Community Balance Patch Battle Logger. Share this file at " .. SHARE_PAGE .. " - thank you!")
	end
	local file = io.open(LOG_FILE, "a")
	if file then
		file:write(table.concat(lines, "\n") .. "\n")
		file:close()
	end
end

local written = false
-- a failure is never allowed to touch the battle, but it is written down instead of swallowed, so it can be fixed
local function note(text)
	local file = io.open(LOG_FILE, "a")
	if file then
		file:write(text .. "\n")
		file:close()
	end
end

local function on_complete()
	if written then
		return
	end
	written = true
	local ok, err = pcall(write_battle)
	if not ok then
		pcall(note, "#error;v" .. VERSION .. ";write_battle;" .. tostring(err))
	end
end

local ok, err = pcall(function()
	bm:register_phase_change_callback("Complete", on_complete)
end)
if not ok then
	pcall(note, "#error;v" .. VERSION .. ";register;" .. tostring(err))
end
