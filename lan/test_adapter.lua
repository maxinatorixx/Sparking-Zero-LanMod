local base_getenv=os.getenv
os.getenv=function(key) if key=="SZERO_LAN_MOD_LOGGING" then return "1" end;return base_getenv(key) end
-- Standalone contract test; no game, UE4SS or actual status-file writes.
local commands, tick = {}, nil
local trace_calls, in_game_thread = 0, false
local assignment = {active=false, revision="waiting"}
local available = true
local expected_runtime = "lan_runtime.lua"
local report = ""
local clock, scans = 0, 0
local original_time = os.time
os.time = function() return clock end
local function object(name, fields)
    fields = fields or {}
    fields.IsValid = function() return true end
    fields.GetFullName = function() return name end
    return fields
end
local world = object('World /Game/Menu.\"Menu\"')
local pc = object("PlayerController /Game/Menu.Controller", {
    GetWorld=function() return world end,
    IsLocalController=function() return true end,
    Pawn={IsValid=function() return false end}, -- Main-menu regression.
})
local player = object("LocalPlayer /Engine.LocalPlayer", {PlayerController=pc})
local classes = {LocalPlayer={player}}
function FindAllOf(class) scans=scans+1; if available then return classes[class] end end
function LoopAsync(interval, fn)
    assert(interval==1000)
    tick=function() clock=clock+2; return fn() end
end
function ExecuteInGameThread(fn)
    assert(not in_game_thread)
    in_game_thread=true
    fn()
    in_game_thread=false
end
function StaticFindObject(path)
    if path~="/Script/Engine.Default__KismetSystemLibrary" then
        if not available then return nil end
        for class, list in pairs(classes) do
            for _, obj in pairs(list) do
                if obj:GetFullName():gsub("^[^ ]+ ", "")==path then return obj end
                if class=="LocalPlayer" and not obj:GetFullName():find("Default__",1,true) then
                    local controller=obj.PlayerController
                    if controller and controller:GetFullName():gsub("^[^ ]+ ", "")==path then return controller end
                end
            end
        end
        return nil
    end
    return {IsValid=function() return true end,
        ExecuteConsoleCommand=function(self, context, command, controller)
            assert(context==pc and controller==pc or context==world and controller==nil)
            commands[#commands+1]=command
        end}
end
local original_loadfile = loadfile
local original_open = io.open
function io.open(path, mode)
    assert(mode=="w")
    local suffix=expected_runtime:gsub("%.lua$", ".status.json")
    assert(path:sub(-#suffix)==suffix)
    return {write=function(self, value) report=value end, close=function() end}
end
local function stage(value) assert(report:find('"stage":"'..value..'"',1,true),report) end
function loadfile(path)
    if path:match("session_trace%.lua$") then
        return function() return function()
            return function()
                assert(in_game_thread, "native trace must run on the game thread")
                trace_calls=trace_calls+1
            end
        end end
    end
    if path:match("audit%.lua$") then return function() return function() return function() return "" end end end end
    if path:match("panel%.lua$") then return function() return function() end end end
    assert(path:sub(-#expected_runtime) == expected_runtime)
    return function() return assignment end
end
dofile("ue4ss/SzeroLAN/scripts/main.lua")
stage("adapter_loaded")
assert(#commands==0)
tick()
stage("waiting_for_match")
assert(#commands==0)
assignment={active=true,revision="match-a",join_order=1,game_port=32001,proxy_port=32002}
available=false
tick()
stage("waiting_for_context")
assert(#commands==0, "retry until controller exists")
available=true
tick()
stage("commands_issued")
assert(#commands==5)
assert(report:find('\\"Menu\\"',1,true), "status must escape JSON quotes")
assert(commands[1]=="spn.multiplayerContext.contextMode PlainUdp")
assert(commands[2]=="spn.multiplayerContext.myDummyMatchingJoinOrder 1")
assert(commands[3]=="spn.multiplayerContext.myDummyP2pAddress 127.0.0.1:32001")
assert(commands[4]=="spn.multiplayerContext.dummyPeerP2pAddresses 127.0.0.1:32002")
assert(commands[5]=="spn.multiplayerContext.apply")
classes.SSGameInstance={object("SSGameInstance Current", {
    GetTransitionMode=function() return 2 end,
    GetOnlineBattleFlg=function() return false end,
})}
world.OwningGameInstance=classes.SSGameInstance[1]
tick()
assert(report:find("GetTransitionMode=2",1,true), "read-only native diagnostics")
assert(report:find("GetOnlineBattleFlg=false",1,true))
classes.SSGameInstance=nil
world.OwningGameInstance=nil
tick()
assert(#commands==5, "same assignment must not be re-applied")
local hot_scans=scans
for index=1,100 do tick() end
assert(scans==hot_scans, "stable controller must not scan global UObjects")
local another_world=object("World Other")
classes.SSBattleGameStateBase={object("Battle Other", {GetWorld=function() return another_world end})}
tick(); stage("commands_issued")
classes.SSBattleGameStateBase={object("Battle Current", {GetWorld=function() return world end})}
tick(); stage("commands_issued"); assert(#commands==5)
classes.SSBattleGameStateBase=nil
assignment={active=false,revision="finished"}
tick()
assert(#commands==5)
assignment={active=true,revision="match-b",join_order=0,game_port=32001,proxy_port=32002}
classes.LocalPlayer={object("LocalPlayer Default__LocalPlayer", {PlayerController=pc})}
classes.PlayerController={object("PlayerController Remote", {IsLocalController=function() return false end})}
tick(); stage("waiting_for_context"); assert(#commands==5)
classes.PlayerController[2]=pc
tick()
assert(#commands==10, "new match must apply automatically")
classes.LocalPlayer=nil; classes.PlayerController=nil
classes.GameEngine={object("GameEngine Engine", {GameViewport=object("Viewport", {World=world})})}
assignment.revision="viewport-match"
tick(); assert(#commands==15, "viewport fallback")
assignment={active=true,revision="invalid",join_order=0,game_port=0,proxy_port=32002}
tick()
assert(#commands==15, "invalid runtime config rejected")
local original_getenv = os.getenv
os.getenv = function(name)
    if name == "SZERO_LAN_INSTANCE" then return "ab12" end
    return original_getenv(name)
end
expected_runtime = "lan_runtime_ab12.lua"
dofile("ue4ss/SzeroLAN/scripts/main.lua")
assignment={active=true,revision="instance-match",join_order=0,game_port=32001,proxy_port=32002}
tick()
assert(#commands==20, "separate game instance runtime path must be used")
assert(trace_calls==0, "normal launch must not load or call the session helper")
os.getenv = function(name)
    if name == "SZERO_LAN_NATIVE_TRACE" then return "1" end
    if name == "SZERO_LAN_INSTANCE" then return "ab12" end
    return original_getenv(name)
end
dofile("ue4ss/SzeroLAN/scripts/main.lua")
assignment={active=false,revision="native-online-menu-no-sidecar-match"}
tick()
assert(trace_calls==1 and #commands==20, "trace native menu without queueing or issuing commands")
assignment={active=true,revision="trace-assigned",join_order=0,game_port=32001,proxy_port=32002}
tick()
assert(trace_calls==2, "at most one trace per assigned poll")
-- Legacy mode still writes operational status but must not load diagnostics off.
local mock_loadfile=loadfile
os.getenv=function(name)
    if name=="SZERO_LAN_MOD_LOGGING" then return nil end
    if name=="SZERO_LAN_NATIVE_TRACE" then return "1" end
    if name=="SZERO_LAN_INSTANCE" then return "ab12" end
    return base_getenv(name)
end
loadfile=function(path)
    assert(not path:match("audit%.lua$") and not path:match("session_trace%.lua$"),"loaded diagnostics while logging off")
    return mock_loadfile(path)
end
local previous_trace_calls=trace_calls
dofile("ue4ss/SzeroLAN/scripts/main.lua")
assignment={active=false,revision="quiet-status"};tick()
assert(trace_calls==previous_trace_calls)
os.getenv = base_getenv
loadfile=original_loadfile
io.open=original_open
os.time=original_time
print("Menu controller and adapter status contracts passed (mock UE4SS only)")
