-- Community Balance Patch: Battle Logger
--
-- At the end of every battle this writes one line per unit to cbp_battle_log.txt in the game folder: the unit, how
-- many models it started and ended with, how many it killed, how much of its hit points and ammunition is left, and
-- whether it routed during the battle. The first line of each battle says what kind of battle it was, who won, how
-- long it lasted, and the names of the mod packs in use (names only, never folder paths). Nothing leaves your PC: the
-- game's scripts cannot go online. If you want to help, share it at https://spiesky.github.io/community-balance-patch/ .
-- Thank you! The format is described in docs/LOG_FORMAT.md.
--
-- It only reads the battle. Everything is wrapped so that a failure here can never affect the battle. The one thing it
-- sets is a note of its own in the game's script memory ("a battle was loaded"), for the campaign part of the logger.
-- That note is gone when the game closes and is never saved.

local LOG_FILE = "cbp_battle_log.txt"
local VERSION = "2"
local SHARE_PAGE = "https://spiesky.github.io/community-balance-patch/"
local SAMPLE_MS = 10000                       -- how often units are checked for routing during the battle
local SAMPLER = "cbp_battle_logger_sampler"   -- name of the repeating callback, so that it can be stopped

local function safe(f, ...)
	local ok, result = pcall(f, ...)
	if ok then
		return result
	end
	return nil
end

-- a recorded value never contains the separators or a line break
local function clean(v)
	local s = tostring(v)
	s = s:gsub("[;|]", ","):gsub("[%c]", " ")
	return s
end

-- an error message without the script name in front of it and without anything that looks like a folder path. A path
-- can have spaces in it, so everything from the first piece with a slash to the last one goes.
local function clean_error(err)
	local s = tostring(err)
	s = s:gsub('^.-%.lua"?%]?:%d+:%s*', "")
	s = s:gsub("%S*[/\\].*[/\\]%S*", "<path>")
	s = s:gsub("%S*[/\\]%S*", "<path>")
	return clean(s):sub(1, 200)
end

local function flag(v)
	if v == nil then
		return "?"
	end
	return v and "1" or "0"
end

-- a number as text: whole numbers without a decimal point, anything that is not a number as "?"
local function num(v, decimals)
	if type(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then
		return "?"
	end
	if decimals then
		return string.format("%." .. decimals .. "f", v)
	end
	if v == math.floor(v) then
		return string.format("%d", v)
	end
	return clean(v)
end

-- adds text to the log. The first line of a new file is the comment with the share link, whatever is written first.
local function note(text)
	local existing = io.open(LOG_FILE, "r")
	if existing then
		existing:close()
	else
		text = "# Community Balance Patch Battle Logger. Share this file at " .. SHARE_PAGE .. " - thank you!\n" .. text
	end
	local file = io.open(LOG_FILE, "a")
	if file then
		file:write(text .. "\n")
		file:close()
	end
end

-- a failure is never allowed to touch the battle, but it is written down instead of swallowed, so it can be fixed
local function note_error(where, err)
	pcall(note, "#error;v" .. VERSION .. ";" .. where .. ";" .. clean_error(err))
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
			table.insert(names, clean(pack))
		end
	end
	file:close()
	return #names > 0 and table.concat(names, "|") or "none"
end

-- which Community Balance Patch is loaded: the patch pack carries its version as a text entry
local function patch_version()
	local ok, text = pcall(function() return common.get_localised_string("cbp_version") end)
	if not ok then
		return "?"
	end
	if text == nil or text == "" then
		return "none"
	end
	return clean(text)
end

-- calls visit(unit, alliance, army, id) for every unit in the battle: each army's own units, then any reinforcement
-- groups that arrived during the battle. The id is the game's own unit id, or the unit's place in the lists if the
-- game does not give one. Nothing is kept: the lists are read again on every call.
local function each_unit(visit)
	local alliances = bm:alliances()
	for a = 1, alliances:count() do
		local armies = alliances:item(a):armies()
		for b = 1, armies:count() do
			local army = armies:item(b)
			local groups = { { 0, army:units() } }
			for r = 1, safe(function() return army:num_reinforcement_units() end) or 0 do
				local extra = safe(function() return army:get_reinforcement_units(r) end)
				if extra then
					table.insert(groups, { r, extra })
				end
			end
			for _, group in ipairs(groups) do
				local units = group[2]
				for u = 1, units:count() do
					local unit = units:item(u)
					local uid = safe(function() return unit:unique_ui_id() end)
					local id = uid ~= nil and ("u" .. tostring(uid)) or (a .. "/" .. b .. "/" .. group[1] .. "/" .. u)
					visit(unit, a, b, id, uid)
				end
			end
		end
	end
end

-- routing during the battle: every 10 seconds, note the first time each unit is seen routing. Only the unit id and
-- the second are kept, never a unit or army object.
local first_rout = {}
local sampling = "no"      -- "no": never started, "yes": running, "failed": stopped after an error, "done": battle over
local samples = 0
local fight_started_ms = 0

local function battle_secs()
	return math.floor((bm:time_elapsed_ms() - fight_started_ms) / 1000)
end

local function stop_sampler()
	pcall(function() bm:remove_callback(SAMPLER) end)
end

local function sample()
	local now = battle_secs()
	each_unit(function(unit, _, _, id)
		if first_rout[id] == nil and safe(function() return unit:is_routing() end) == true then
			first_rout[id] = now
		end
	end)
	samples = samples + 1
end

-- one error stops the sampling for good
local function on_sample()
	if sampling ~= "yes" then
		return
	end
	local ok, err = pcall(sample)
	if not ok then
		sampling = "failed"
		stop_sampler()
		note_error("sampler", err)
	end
end

local function on_deployed()
	local ok, err = pcall(function()
		if sampling ~= "no" then
			return
		end
		fight_started_ms = bm:time_elapsed_ms()
		bm:repeat_callback(on_sample, SAMPLE_MS, SAMPLER)
		sampling = "yes"
	end)
	if not ok then
		note_error("start sampler", err)
	end
end

local function write_battle(sampler_ran)
	local lines = {}
	local when = safe(os.date, "%Y-%m-%d %H:%M") or "?"
	local player = safe(function() return bm:get_player_alliance_num() end)
	local secs = safe(battle_secs)
	local winner = safe(function() return bm:victorious_alliance() end)
	if type(winner) == "number" and winner ~= 1 and winner ~= 2 then
		winner = 0
	end
	table.insert(lines, string.format(
		"#battle;v%s;%s;campaign=%s;type=%s;multiplayer=%s;siege=%s;player=%s;attacker=%s;winner=%s;secs=%s;cbp=%s;mods=%s",
		VERSION, clean(when),
		flag(safe(function() return bm:is_from_campaign() end)),
		clean(safe(function() return bm:battle_type() end) or "?"),
		flag(safe(function() return bm:is_multiplayer() end)),
		flag(safe(function() return bm:is_siege_battle() end)),
		num(player), flag(safe(function() return bm:player_is_attacker() end)), num(winner), num(secs),
		patch_version(), safe(mod_packs) or "unknown"))
	-- a unit never seen routing counts as "0" only if the sampling ran for the whole battle
	local sampled = sampler_ran and (samples > 0 or (secs or SAMPLE_MS) < SAMPLE_MS / 1000)
	each_unit(function(unit, a, b, id, uid)
		local routing = safe(function() return unit:is_routing() end)
		if routing == true and first_rout[id] == nil and secs then
			first_rout[id] = secs
		end
		local ever, first = "?", "?"
		if first_rout[id] ~= nil then
			ever, first = "1", num(first_rout[id])
		elseif sampled and routing == false then
			ever = "0"
		end
		table.insert(lines, table.concat({ "u", a, b, player ~= nil and flag(a == player) or "?",
			clean(safe(function() return unit:type() end) or "?"),
			num(safe(function() return unit:initial_number_of_men() end)),
			num(safe(function() return unit:number_of_men_alive() end)),
			num(safe(function() return unit:number_of_enemies_killed() end)),
			flag(routing),
			flag(safe(function() return unit:is_shattered() end)),
			num(safe(function() return unit:unary_hitpoints() end), 3),
			num(safe(function() return unit:ammo_left() end)),
			num(safe(function() return unit:starting_ammo() end)),
			flag(safe(function() return unit:is_commanding_unit() end)),
			ever, first,
			uid ~= nil and clean(uid) or "?" }, ";"))
	end)
	table.insert(lines, "#end")
	note(table.concat(lines, "\n"))
end

local written = false

local function on_complete()
	if written then
		return
	end
	written = true
	-- the sampler is switched off first, so that it does nothing more even if the game could not remove it
	local sampler_ran = sampling == "yes"
	if sampler_ran then
		sampling = "done"
		stop_sampler()
	end
	local ok, err = pcall(write_battle, sampler_ran)
	if not ok then
		note_error("write_battle", err)
	end
end

local ok, err = pcall(function()
	bm:register_phase_change_callback("Deployed", on_deployed)
	bm:register_phase_change_callback("Complete", on_complete)
end)
if not ok then
	note_error("register", err)
end

-- tell the campaign part of the logger that a battle was loaded, so that it knows the battle was fought and not
-- auto-resolved. This is a note in the game's script memory under our own name; nothing else reads it, it is never
-- saved, and the campaign part clears it.
pcall(function()
	if bm:is_from_campaign() then
		core:svr_save_bool("cbp_logger_from_battle", true)
	end
end)
