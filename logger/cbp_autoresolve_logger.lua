-- Community Balance Patch: Battle Logger, campaign part
--
-- The battle script logs what happens inside a battle you fight. This logs the campaign's view of every battle you
-- take part in, fought or auto-resolved: before the battle it notes every unit on both sides with its strength and
-- experience, and after the battle how much of each unit is left, who won, and what kind of battle it was (turn,
-- difficulty, ambush, settlement, quest battle). Only battles you are part of, only single player. Same file, same
-- privacy: unit names and numbers, and mod pack names (never folder paths). Nothing leaves your PC. The format is
-- described in docs/LOG_FORMAT.md.
--
-- It only reads the campaign. The button click just sets a flag; everything else happens at the game's own battle
-- events, wrapped so that a failure can never affect the campaign. The logger keeps two notes of its own in the game's
-- script memory between campaign and battle (unit ids with their strength and experience level, and one flag); they
-- are gone when the game closes and are never saved.

local LOG_FILE = "cbp_battle_log.txt"
local VERSION = "2"
local SHARE_PAGE = "https://spiesky.github.io/community-balance-patch/"
local SVR_SNAPSHOT = "cbp_logger_snapshot"        -- the snapshot, kept in the game's script registry while a battle is fought
local SVR_FROM_BATTLE = "cbp_logger_from_battle"  -- set by the battle script when a battle was loaded

local DEBUG = false          -- test builds: trace every step as '#debug' lines (the analysis tools ignore them)
local autoresolve_clicked = false
local pending = nil          -- the battle seen starting in this script session: { involved = true, false or nil (not known), units = list or nil }
local from_battle = false    -- this script session began by coming back from a fought battle
local completed = false      -- a BattleCompleted event was already handled in this script session
local errors_noted = 0       -- '#error' lines written in this script session
local MAX_ERRORS = 20        -- no more than this many per script session, so a repeating failure cannot fill the file
local multiplayer_noted = false

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

-- a number as text: whole numbers without a decimal point, others with two decimals, anything else as "?"
local function num(v)
	if type(v) ~= "number" or v ~= v or v == math.huge or v == -math.huge then
		return "?"
	end
	if v == math.floor(v) then
		return string.format("%d", v)
	end
	local s = string.format("%.2f", v):gsub("0+$", ""):gsub("%.$", "")
	return s
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

local function note_error(where, err)
	if errors_noted >= MAX_ERRORS then
		return
	end
	errors_noted = errors_noted + 1
	pcall(note, "#error;v" .. VERSION .. ";result " .. where .. ";" .. clean_error(err))
end

-- a failure is never allowed to touch the campaign, but it is written down instead of swallowed, so it can be fixed
local function guarded(where, f, ...)
	local ok, result = pcall(f, ...)
	if not ok then
		note_error(where, result)
		return nil
	end
	return result
end

local function trace(text)
	if DEBUG then
		pcall(note, "#debug;result;" .. (safe(os.date, "%H:%M:%S") or "?") .. ";" .. clean(text))
	end
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

local function is_human(character)
	return character and not character:is_null_interface() and character:faction():is_human()
end

-- the armies of the pending battle in the game's order: the main attacker, the main defender, then the reinforcements
local function each_commander(pb, visit)
	local armies = { 0, 0 }
	local function add(character, side)
		armies[side] = armies[side] + 1
		visit(character, side, armies[side])
	end
	if pb:has_attacker() then add(pb:attacker(), 1) end
	if pb:has_defender() then add(pb:defender(), 2) end
	safe(function()
		local list = pb:secondary_attackers()
		for i = 0, list:num_items() - 1 do add(list:item_at(i), 1) end
	end)
	safe(function()
		local list = pb:secondary_defenders()
		for i = 0, list:num_items() - 1 do add(list:item_at(i), 2) end
	end)
end

-- is the player in this battle: as the main attacker or defender, or as a reinforcing army (cheap: runs for AI battles too)
local function player_involved()
	local involved = false
	each_commander(cm:model():pending_battle(), function(character)
		if is_human(character) then
			involved = true
		end
	end)
	return involved
end

-- before the battle: every unit of every army involved, with its strength in percent and its experience level
local function take_snapshot()
	local pb = cm:model():pending_battle()
	if not pb:is_active() then
		return nil
	end
	local units = {}
	each_commander(pb, function(character, side, army)
		-- one army that cannot be read costs that army, not the whole battle
		guarded("snapshot army", function()
			if not character or character:is_null_interface() or not character:has_military_force() then
				return
			end
			local player = safe(is_human, character)
			local faction = safe(function() return character:faction():name() end)
			local mf = character:military_force()
			local mf_cqi = mf:command_queue_index()
			local list = mf:unit_list()
			for i = 0, list:num_items() - 1 do
				local unit = list:item_at(i)
				table.insert(units, { side = side, army = army, player = player, faction = faction, mf = mf_cqi,
					cqi = safe(function() return unit:command_queue_index() end),
					key = safe(function() return unit:unit_key() end),
					before = safe(function() return unit:percentage_proportion_of_full_strength() end),
					xp = safe(function() return unit:experience_level() end) })
			end
		end)
	end)
	return units
end

-- The script is started again when the game comes back from a fought battle, so what it remembered is gone. The game's
-- script registry survives that, so the strengths and experience levels wait there: "cqi,strength,xp" for each unit.
local function store_snapshot(units)
	local parts = {}
	for _, u in ipairs(units or {}) do
		if u.cqi ~= nil then
			table.insert(parts, num(u.cqi) .. "," .. num(u.before) .. "," .. num(u.xp))
		end
	end
	core:svr_save_string(SVR_SNAPSHOT, table.concat(parts, " "))
end

local function load_stored_snapshot()
	local text = core:svr_load_string(SVR_SNAPSHOT)
	local stored = { units = {}, count = 0 }
	if type(text) ~= "string" then
		return stored
	end
	for cqi, before, xp in text:gmatch("([^, ]+),([^, ]+),([^, ]+)") do
		stored.units[cqi] = { before = tonumber(before), xp = tonumber(xp) }
		stored.count = stored.count + 1
	end
	return stored
end

-- The same battle as the game itself remembers it. The game saves this list with the campaign, so it is still there
-- after a fought battle, but it only holds each unit's id and key. Strength and experience before the battle come
-- from our own stored snapshot, and only if it lists exactly the same units; otherwise they are written as "?".
local function units_from_game_cache()
	local units = {}
	local function add(side, count, get_army, get_units)
		for army = 1, count do
			guarded("cache army", function()
				local _, mf_cqi, faction = get_army(army)
				local player = safe(function() return cm:get_faction(faction):is_human() end)
				for _, record in ipairs(get_units(army) or {}) do
					table.insert(units, { side = side, army = army, player = player, faction = faction, mf = mf_cqi,
						cqi = record.unit_cqi, key = record.unit_key })
				end
			end)
		end
	end
	add(1, cm:pending_battle_cache_num_attackers(),
		function(i) return cm:pending_battle_cache_get_attacker(i) end,
		function(i) return cm:pending_battle_cache_get_attacker_units(i) end)
	add(2, cm:pending_battle_cache_num_defenders(),
		function(i) return cm:pending_battle_cache_get_defender(i) end,
		function(i) return cm:pending_battle_cache_get_defender_units(i) end)
	local stored = safe(load_stored_snapshot)
	local same = stored ~= nil and stored.count == #units and stored.count > 0
	if same then
		for _, u in ipairs(units) do
			if stored.units[num(u.cqi)] == nil then
				same = false
			end
		end
	end
	if same then
		for _, u in ipairs(units) do
			u.before = stored.units[num(u.cqi)].before
			u.xp = stored.units[num(u.cqi)].xp
		end
	end
	return units
end

local function write_result(units, mode)
	local pb = cm:model():pending_battle()
	local winner = "?"
	if safe(function() return pb:attacker_won() end) then
		winner = "attacker"
	elseif safe(function() return pb:defender_won() end) then
		winner = "defender"
	elseif safe(function() return pb:is_draw() end) then
		winner = "draw"
	end
	-- strength after: look each army up again; a unit that is gone was destroyed
	local after = {}
	local forces = {}
	for _, u in ipairs(units) do
		if u.mf ~= nil then
			forces[u.mf] = "unread"
		end
	end
	for mf_cqi in pairs(forces) do
		forces[mf_cqi] = safe(function()
			local mf = cm:get_military_force_by_cqi(mf_cqi)
			if mf and not mf:is_null_interface() then
				local list = mf:unit_list()
				for i = 0, list:num_items() - 1 do
					local unit = list:item_at(i)
					after[unit:command_queue_index()] = unit:percentage_proportion_of_full_strength()
				end
			end
			return "read"
		end) or "failed"
	end
	-- attackers first, then defenders, each side's main army before its reinforcements
	local ordered = {}
	for side = 1, 2 do
		-- up to the largest army index on that side: an army that could not be read leaves a gap, not an end
		local last = 0
		for _, u in ipairs(units) do
			if u.side == side and type(u.army) == "number" and u.army > last then
				last = u.army
			end
		end
		for army = 1, last do
			for _, u in ipairs(units) do
				if u.side == side and u.army == army then
					table.insert(ordered, u)
				end
			end
		end
	end
	units = ordered
	local player_side = "?"
	for _, u in ipairs(units) do
		if u.player and (player_side == "?" or u.side < player_side) then
			player_side = u.side
		end
	end
	local lines = {}
	table.insert(lines, string.format(
		"#result;v%s;%s;mode=%s;winner=%s;turn=%s;difficulty=%s;type=%s;ambush=%s;night=%s;settlement=%s;quest=%s;campaign=%s;player_side=%s;cbp=%s;mods=%s",
		VERSION, clean(safe(os.date, "%Y-%m-%d %H:%M") or "?"), mode, winner,
		num(safe(function() return cm:model():turn_number() end)),
		clean(safe(function() return cm:get_difficulty(true) end) or "?"),
		clean(safe(function() return pb:battle_type() end) or "?"),
		flag(safe(function() return pb:ambush_battle() end)),
		flag(safe(function() return pb:night_battle() end)),
		flag(safe(function() return pb:has_contested_garrison() end)),
		clean(safe(function() return pb:set_piece_battle_key() end) or "?"),
		clean(safe(function() return cm:get_campaign_name() end) or "?"),
		tostring(player_side), patch_version(), safe(mod_packs) or "unknown"))
	for _, u in ipairs(units) do
		-- "0" needs the unit's army to have been looked up without a failure; otherwise it is not known
		local left = "?"
		if u.cqi ~= nil and after[u.cqi] ~= nil then
			left = num(after[u.cqi])
		elseif u.cqi ~= nil and forces[u.mf] == "read" then
			left = "0"
		end
		table.insert(lines, table.concat({ "r", u.side, u.army, flag(u.player), clean(u.key or "?"), num(u.before), left,
			num(u.xp), clean(u.faction or "?") }, ";"))
	end
	table.insert(lines, "#end")
	note(table.concat(lines, "\n"))
end

-- a battle is starting (or a save was loaded at the pre-battle screen): remember it, with a snapshot if the player is in it
local function battle_pending()
	autoresolve_clicked = false
	-- if the check itself fails it is written down, and the question is put to the game's own cache after the battle
	local ok, involved = pcall(player_involved)
	if not ok then
		note_error("involved", involved)
		involved = nil
	end
	pending = { involved = involved }
	if involved then
		pending.units = guarded("snapshot", take_snapshot)
		guarded("store snapshot", store_snapshot, pending.units)
	end
	trace("pending, involved=" .. tostring(pending.involved) .. " units=" .. tostring(pending.units and #pending.units or "nil"))
end

-- a battle sequence is over. The game sends this for every battle, also for one that was not fought (retreat, maintain
-- siege, a battle the player declined) and for battles between AI factions.
local function battle_completed()
	local seen, clicked, first = pending, autoresolve_clicked, not completed
	pending = nil
	autoresolve_clicked = false
	from_battle = false
	completed = true
	local fought = cm:model():pending_battle():has_been_fought()
	trace("BattleCompleted fought=" .. tostring(fought) .. " seen=" .. tostring(seen ~= nil) .. " clicked=" .. tostring(clicked))
	local units, mode = nil, nil
	if not fought then
		-- nothing happened: nothing is written
	elseif seen then
		-- This script saw the battle start and is still running, so the game never loaded a battle: it was auto-resolved.
		local involved = seen.involved
		if involved == nil then
			involved = cm:pending_battle_cache_human_is_involved()
		end
		if involved then
			mode = "auto"
			units = seen.units
			if not units or #units == 0 then
				if seen.involved ~= nil then
					note_error("snapshot", "no snapshot from before the battle, strengths before are unknown")
				end
				units = units_from_game_cache()
			end
		end
	elseif first and cm:pending_battle_cache_human_is_involved() then
		-- This script did not see the battle start: it was started again while the battle was fought. If the auto-resolve
		-- button was clicked since, the battle cannot have been loaded after that click. Only the first battle to end
		-- in a script session can be one that started before it.
		mode = clicked and "auto" or "fought"
		units = units_from_game_cache()
	end
	if units and #units > 0 then
		write_result(units, mode)
	end
	guarded("clear snapshot", function() core:svr_save_string(SVR_SNAPSHOT, "") end)
end

-- Single player only. Asked at each event and not once at the start: the game only knows the answer once the campaign
-- world exists. If the game gives no answer nothing is logged, and that is written down once.
local function single_player()
	local ok, multiplayer = pcall(function() return cm:is_multiplayer() end)
	if ok and multiplayer == false then
		return true
	end
	if not (ok and multiplayer == true) and not multiplayer_noted then
		multiplayer_noted = true
		note_error("multiplayer", ok and "the game did not say whether this is a multiplayer campaign" or multiplayer)
	end
	return false
end

-- did the battle script run just before this script started? Read the note and clear it (in multiplayer too, so that
-- it cannot be left behind for a later single-player campaign).
from_battle = safe(function() return core:svr_load_bool(SVR_FROM_BATTLE) end) == true
safe(function() core:svr_save_bool(SVR_FROM_BATTLE, false) end)

-- The listeners are added now, while the script is loaded, and not on the first tick: the game can send these events
-- before the first tick (CA's own battle listeners start this early for the same reason).
local register_noted = false
local function listen(name, event, condition, callback, persistent)
	local ok, err = pcall(function() core:add_listener(name, event, condition, callback, persistent) end)
	if not ok and not register_noted then
		register_noted = true
		note_error("register", err)
	end
end

-- the click only sets a flag: no game reads inside a UI event
listen("cbp_autoresolve_click", "ComponentLClickUp",
	function(context) return context and (context.string == "button_autoresolve" or context.string == "button_attack") end,
	function(context)
		autoresolve_clicked = (context.string == "button_autoresolve")
		trace("click " .. tostring(context.string))
	end, true)
-- before the battle: note it, and take a snapshot of every army involved if it is one of the player's own battles
listen("cbp_autoresolve_pending", "PendingBattle", true,
	function()
		from_battle = false
		if single_player() then
			guarded("pending", battle_pending)
		end
	end, true)
-- a save made at the pre-battle screen: the game does not fire PendingBattle when it loads, so take the snapshot once
-- the loading screen is gone (the same check CA's own battle cache makes). Not when coming back from a fought battle.
listen("cbp_autoresolve_loaded", "LoadingScreenDismissed", true,
	function()
		guarded("after load", function()
			if from_battle or pending ~= nil or not single_player() then
				return
			end
			local pb = cm:model():pending_battle()
			if pb:is_active() and not pb:has_been_fought() then
				battle_pending()
			end
		end)
	end, false)
-- after the battle: one #result block for every battle the player took part in
listen("cbp_autoresolve_completed", "BattleCompleted", true,
	function()
		if single_player() then
			guarded("write", battle_completed)
		end
	end, true)

-- The game calls this on the first tick. Everything is already set up above.
function cbp_autoresolve_logger()
	trace("started")
end
