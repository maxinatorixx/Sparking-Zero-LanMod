-- Our diagnostics require an explicit per-launch opt-in; never replace global print.
local function Log(...)
    if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" then print(...) end
end
-- Local-player lookup deliberately does not require a possessed Pawn:
-- the main menu has a controller but no playable character.
local source = debug.getinfo(1, "S").source:gsub("^@", "")
local folder = assert(source:match("^(.*[/\\])"), "Cannot locate adapter scripts folder")
local instance = os.getenv("SZERO_LAN_INSTANCE")
-- The native search experiment owns the original Online operation path.
-- Do not also load the F5 panel or issue obsolete SpNet preset commands.
if os.getenv("SZERO_LAN_NATIVE_SEARCH") == "1" then
    local ok, err = pcall(function()
        return assert(loadfile(folder .. "native_search.lua"))()(folder, instance)
    end)
    if not ok then Log("[SzeroLAN] Native search startup failed: " .. tostring(err) .. "\n") end
    return
end
if instance and not instance:match("^[a-f0-9]+$") then instance = nil end
local stem = folder .. "lan_runtime" .. (instance and "_" .. instance or "")
local runtime_path, status_path = stem .. ".lua", stem .. ".status.json"
local applied_revision, scheduled, last_status = nil, false, nil

local function Safe(fn)
    local ok, result = pcall(fn)
    if ok then return result end
    return nil
end

local audit
if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" then
    audit = Safe(function() return assert(loadfile(folder .. "audit.lua"))()(folder, instance) end)
end
local audit_detail = ""
-- Optional read-only native-state evidence for the real Online menu path.
-- Independent of sidecar pairing; never initializes or redirects a session.
local session_trace
if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" and os.getenv("SZERO_LAN_NATIVE_TRACE") == "1" then
    session_trace = Safe(function()
        return assert(loadfile(folder .. "session_trace.lua"))()(folder, instance)
    end)
end
local function TraceSession()
    if session_trace then Safe(session_trace) end
end

local function Name(object)
    return Safe(function() return object:GetFullName() end) or "<unavailable>"
end

local function Live(object)
    if not object or not Safe(function() return object:IsValid() end) then return false end
    local name = Name(object)
    return not name:find("Default__", 1, true) and not name:find("Archetype__", 1, true)
end

local function Instances(class)
    return Safe(function() return FindAllOf(class) end) or {}
end

local function Member(object, key)
    return Safe(function() return object[key] end)
end

local controller_path, engine_path, next_discovery = nil, nil, 0
local function Path(object) return Name(object):gsub("^[^ ]+ ", "") end
local function Resolve(path)
    if not path then return nil end
    return Safe(function() return StaticFindObject(path) end)
end
local function ControllerContext(pc, route)
    if not Live(pc) then return end
    if Safe(function() return pc:IsLocalController() end) == false then return end
    local world = Safe(function() return pc:GetWorld() end)
    if not Live(world) or Member(world, "bIsTearingDown") == true then return end
    controller_path = Path(pc)
    return pc, pc, world, route
end
local function Context()
    -- Resolve paths afresh, never retain UObject wrappers across travel.
    local pc = Resolve(controller_path)
    if Live(pc) then
        local context, player, world, route = ControllerContext(pc, "cached local controller path")
        if context then return context, player, world, route end
    end
    controller_path = nil
    local fallback_world
    local engine = Resolve(engine_path)
    if Live(engine) then
        local viewport = Member(engine, "GameViewport")
        local world = Live(viewport) and Member(viewport, "World") or nil
        local gi = Member(engine, "GameInstance") or (Live(world) and Member(world, "OwningGameInstance"))
        local players = gi and Member(gi, "LocalPlayers")
        local player = players and Safe(function() return players[1] end)
        pc = player and Member(player, "PlayerController")
        local context, controller, owned_world, route = ControllerContext(pc, "GameInstance.LocalPlayers")
        if context then return context, controller, owned_world, route end
        if Live(world) then fallback_world = world end
    end
    if os.time() < next_discovery then
        if fallback_world then return fallback_world, nil, fallback_world, "GameViewport.World" end
        return nil, nil, nil, "Waiting for local context"
    end
    next_discovery = os.time() + 1
    if not Live(engine) and FindFirstOf then
        engine = Safe(function() return FindFirstOf("GameEngine") end)
        if Live(engine) then engine_path = Path(engine) end
    end
    -- Cold-start fallback only. No global object iteration once context exists.
    for _, player in pairs(Instances("LocalPlayer")) do
        if Live(player) then
            local pc = Member(player, "PlayerController")
            if Live(pc) then
                local context, controller, world, route = ControllerContext(pc, "LocalPlayer.PlayerController")
                if context then return context, controller, world, route end
            end
        end
    end
    for _, pc in pairs(Instances("PlayerController")) do
        if Live(pc) and Safe(function() return pc:IsLocalController() end) == true then
            local context, controller, world, route = ControllerContext(pc, "local PlayerController")
            if context then return context, controller, world, route end
        end
    end
    -- Transitional menus can expose their world through the viewport first.
    for _, engine in pairs(Instances("GameEngine")) do
        if Live(engine) then
            engine_path = Path(engine)
            local viewport = Member(engine, "GameViewport")
            local world = Live(viewport) and Member(viewport, "World") or nil
            if Live(world) then return world, nil, world, "GameViewport.World" end
        end
    end
    return nil, nil, nil, "No live local player/controller/viewport world"
end

local panel_ok, panel_error = pcall(function()
    local module = os.getenv("SZERO_LAN_NATIVE_MENU") == "1" and "native_menu.lua" or "panel.lua"
    local panel = assert(loadfile(folder .. module))()
    panel(stem, Context)
end)
if not panel_ok then Log("[SzeroLAN] Panel initialization failed: " .. tostring(panel_error) .. "\n") end

local function Json(value)
    return '"' .. tostring(value):gsub('[%z\1-\31\\"]', function(char)
        if char == "\\" then return "\\\\" end
        if char == '"' then return '\\"' end
        return string.format("\\u%04x", string.byte(char))
    end) .. '"'
end

-- Read-only getters: never initiate platform login, matchmaking or travel.
local function NativeState(world)
    local values = {}
    local instance = Member(world, "OwningGameInstance") or Member(Resolve(engine_path), "GameInstance")
    if Live(instance) then
        for _, method in ipairs({"GetTransitionMode", "GetBattleSetupStartMode",
            "GetBattleOnlineMode", "GetOnlineBattleMatchingState", "GetOnlineBattleFlg",
            "GetOnlineBattleSlaveFlg"}) do
            local value = Safe(function() return instance[method](instance) end)
            if type(value) == "number" or type(value) == "boolean" or type(value) == "string" then
                values[#values+1] = method .. "=" .. tostring(value)
            end
        end
    end
    return #values > 0 and (" | Native: " .. table.concat(values, "; ")) or ""
end

local function Status(cfg, stage, detail, world)
    local revision = cfg and cfg.revision or ""
    local match_id = cfg and cfg.match_id or ""
    local world_name = Live(world) and Name(world) or ""
    if world_name ~= "" then detail = detail .. NativeState(world) end
    if cfg and cfg.active then detail = detail .. audit_detail end
    local signature = revision .. stage .. detail .. world_name
    if signature == last_status then return end
    local report = '{"version":1,"revision":' .. Json(revision) ..
        ',"match_id":' .. Json(match_id) .. ',"stage":' .. Json(stage) ..
        ',"detail":' .. Json(detail) .. ',"world":' .. Json(world_name) .. '}'
    local written = Safe(function()
        local file = assert(io.open(status_path, "w"))
        file:write(report .. "\n")
        file:close()
        return true
    end)
    if written then last_status = signature end
    Log("[SzeroLAN] Stage=" .. stage .. " " .. detail ..
        (world_name ~= "" and " world=" .. world_name or "") .. "\n")
    if not written then Log("[SzeroLAN] Could not write status file: " .. status_path .. "\n") end
end

local function Monitor(cfg)
    local context, pc, world, route = Context()
    if not context then
        Status(cfg, "waiting_for_context", route)
        return
    end
    if audit then audit_detail = Safe(audit) or " | Console audit: Lua error" end
    Status(cfg, "commands_issued", "Networking commands issued; waiting for battle entry", world)
end

local function Poll()
    if scheduled then return false end
    local read = loadfile(runtime_path)
    if not read then return false end
    local ok, cfg = pcall(read)
    if not ok or type(cfg) ~= "table" or type(cfg.revision) ~= "string" then return false end
    if not cfg.active then
        applied_revision = cfg.revision
        scheduled = true
        ExecuteInGameThread(function()
            local success, err = pcall(function()
                TraceSession()
                local context, pc, world = Context()
                Status(cfg, "waiting_for_match", "Waiting for a server match assignment", world)
            end)
            if not success then Status(cfg, "adapter_error", tostring(err)) end
            scheduled = false
        end)
        return false
    end
    if cfg.join_order ~= 0 and cfg.join_order ~= 1 then return false end
    for _, port in ipairs({cfg.game_port or false, cfg.proxy_port or false}) do
        if type(port) ~= "number" or port % 1 ~= 0 or port < 1 or port > 65535 then return false end
    end
    if cfg.game_port == cfg.proxy_port then return false end

    scheduled = true
    ExecuteInGameThread(function()
        local success, err = pcall(function()
            TraceSession()
            if cfg.revision == applied_revision then Monitor(cfg); return end
            local context, pc, world, route = Context()
            if not context then Status(cfg, "waiting_for_context", route); return end
            local kismet = StaticFindObject("/Script/Engine.Default__KismetSystemLibrary")
            assert(kismet and kismet:IsValid(), "KismetSystemLibrary is unavailable")
            Status(cfg, "issuing_commands", "Using " .. route .. ": " .. Name(context), world)
            local commands = {
                "spn.multiplayerContext.contextMode PlainUdp",
                "spn.multiplayerContext.myDummyMatchingJoinOrder " .. cfg.join_order,
                "spn.multiplayerContext.myDummyP2pAddress 127.0.0.1:" .. cfg.game_port,
                "spn.multiplayerContext.dummyPeerP2pAddresses 127.0.0.1:" .. cfg.proxy_port,
                "spn.multiplayerContext.apply"
            }
            for _, command in ipairs(commands) do
                kismet:ExecuteConsoleCommand(context, command, pc)
                Log("[SzeroLAN] Issued: " .. command .. "\n")
            end
            applied_revision = cfg.revision
            Monitor(cfg)
        end)
        if not success then Status(cfg, "adapter_error", tostring(err)) end
        scheduled = false
    end)
    return false
end

LoopAsync(1000, Poll)
Log("[SzeroLAN] Menu-compatible adapter loaded. Runtime: " .. runtime_path .. "\n")
Status(nil, "adapter_loaded", "Waiting for launcher assignment")
