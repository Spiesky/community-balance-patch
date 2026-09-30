-- Community Balance Patch: Battle Logger, auto-resolve part
--
-- Fought battles are logged by the battle script. This logs the ones you auto-resolve: when you press the auto-resolve
-- button, it notes every unit on both sides and its strength before the battle, then after the battle how much of each
-- unit is left. Only battles you are part of, only single player, only when you choose auto-resolve. Same file, same
-- privacy: unit names and numbers, and mod pack names (never folder paths). Nothing leaves your PC.
--
-- It only reads. The button click just sets a flag; everything else happens at the game's own battle events, wrapped so
-- that a failure can never affect the campaign.

local LOG_FILE = "cbp_battle_log.txt"
local VERSION = "1"
local SHARE_PAGE = "https://spiesky.github.io/community-balance-patch/"

local autoresolve_clicked = false
local cache = nil

local function note(text)
	local file = io.open(LOG_FILE, "a")
	if file then
		file:write(text .. "\n")
		file:close()
	end
end

-- a failure is never allowed to touch the campaign, but it is written down instead of swallowed, so it can be fixed
local function guarded(where, f, ...)
	local ok, err = pcall(f, ...)
	if not ok then
		pcall(note, "#error;v" .. VERSION .. ";autoresolve " .. where .. ";" .. tostring(err))
	end
	return ok and err or nil
end

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

-- every unit of a character's army: cqi, key and strength in percent
local function read_force(character, side, is_player)
	local out = {}
	if not character or character:is_null_interface() or not character:has_military_force() then
		return out
	end
	local mf = character:military_force()
	local units = mf:unit_list()
	for i = 0, units:num_items() - 1 do
		local unit = units:item_at(i)
		table.insert(out, { cqi = unit:command_queue_index(), key = unit:unit_key(), side = side, player = is_player,
			before = unit:percentage_proportion_of_full_strength(), mf = mf:command_queue_index() })
	end
	return out
end

local function take_snapshot()
	local pb = cm:model():pending_battle()
	if not pb:is_active() then
		return nil
	end
	local units = {}
	local function add(character, side)
		local is_player = character and not character:is_null_interface() and character:faction():is_human()
		for _, u in ipairs(read_force(character, side, is_player)) do
			table.insert(units, u)
		end
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
	return units
end

-- is the player in this battle: as the main attacker or defender, or as a reinforcing army (cheap: runs for AI battles too)
local function player_involved()
	local pb = cm:model():pending_battle()
	local function human(c) return c and not c:is_null_interface() and c:faction():is_human() end
	if (pb:has_attacker() and human(pb:attacker())) or (pb:has_defender() and human(pb:defender())) then
		return true
	end
	for _, list in ipairs({ safe(function() return pb:secondary_attackers() end), safe(function() return pb:secondary_defenders() end) }) do
		for i = 0, list:num_items() - 1 do
			if human(list:item_at(i)) then
				return true
			end
		end
	end
	return false
end

local function write_result()
	local pb = cm:model():pending_battle()
	local result = "?"
	if safe(function() return pb:attacker_won() end) then
		result = "attacker"
	elseif safe(function() return pb:defender_won() end) then
		result = "defender"
	elseif safe(function() return pb:is_draw() end) then
		result = "draw"
	end
	-- strength after: look each army up again; a unit that is gone was destroyed
	local after = {}
	local forces = {}
	for _, u in ipairs(cache) do
		forces[u.mf] = true
	end
	for mf_cqi in pairs(forces) do
		local mf = cm:get_military_force_by_cqi(mf_cqi)
		if mf and not mf:is_null_interface() then
			local units = mf:unit_list()
			for i = 0, units:num_items() - 1 do
				local unit = units:item_at(i)
				after[unit:command_queue_index()] = unit:percentage_proportion_of_full_strength()
			end
		end
	end
	local lines = {}
	table.insert(lines, string.format("#autoresolve;v%s;%s;winner=%s;mods=%s", VERSION, safe(os.date, "%Y-%m-%d %H:%M") or "?", result, mod_packs()))
	for _, u in ipairs(cache) do
		table.insert(lines, string.format("a;%d;%s;%s;%s;%s", u.side, u.player and "1" or "0", tostring(u.key),
			tostring(u.before), tostring(after[u.cqi] or 0)))
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

function cbp_autoresolve_logger()
	if safe(function() return cm:is_multiplayer() end) ~= false then
		return
	end
	-- the click only sets a flag: no game reads inside a UI event
	core:add_listener("cbp_autoresolve_click", "ComponentLClickUp",
		function(context) return context and (context.string == "button_autoresolve" or context.string == "button_attack") end,
		function(context) autoresolve_clicked = (context.string == "button_autoresolve") end, true)
	-- before the battle: a snapshot of every army involved, but only for the player's own battles
	core:add_listener("cbp_autoresolve_pending", "PendingBattle",
		function()
			return safe(player_involved) == true
		end,
		function()
			autoresolve_clicked = false
			cache = guarded("snapshot", take_snapshot)
		end, true)
	-- a save made at the pre-battle screen: the game does not fire PendingBattle when it loads, so take the snapshot once
	-- the loading screen is gone (the same check CA's own battle cache makes)
	core:add_listener("cbp_autoresolve_loaded", "LoadingScreenDismissed", true,
		function()
			guarded("after load", function()
				local pb = cm:model():pending_battle()
				if pb:is_active() and not pb:has_been_fought() then
					if player_involved() then
						cache = take_snapshot()
					end
				end
			end)
		end, false)
	-- after the battle: log it if the player chose auto-resolve
	core:add_listener("cbp_autoresolve_completed", "BattleCompleted", true,
		function()
			if autoresolve_clicked and cache and #cache > 0 then
				guarded("write", write_result)
			elseif autoresolve_clicked then
				pcall(note, "#error;v" .. VERSION .. ";autoresolve;clicked but no snapshot from the PendingBattle event")
			end
			autoresolve_clicked = false
			cache = nil
		end, true)
end
