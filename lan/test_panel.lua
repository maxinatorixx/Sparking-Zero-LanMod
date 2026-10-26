local original_getenv=os.getenv
os.getenv=function(key) if key=="SZERO_LAN_MOD_LOGGING" then return "1" end;return original_getenv(key) end
-- Mock only. Full-screen layout/focus, no F11, closed-menu/per-frame budgets.
local tick, keys, objects, command = nil, {}, {}, nil
local data = 'return {version=1,name="Tester",ready=false,lobbies={{id="abcdef123456",name="LAN",players=2}}}'
local world_name, count, final_text = "World Menu", 0, nil
local text_updates, contexts, focus, anchors, offsets = 0, 0, nil, nil, nil
local fail_input, fail_focus = false, false
local original_xpcall=xpcall
local messages, original_print = {}, print
print=function(value) messages[#messages+1]=tostring(value); original_print(value) end
-- Match the pinned loader's real names; the old fabricated UP/DOWN names
-- allowed the regression to pass this mock while failing in the game.
Key = {F5=5,UP_ARROW=38,DOWN_ARROW=40,LEFT_ARROW=37,RIGHT_ARROW=39,RETURN=13,ESCAPE=27,F11=122}
function RegisterKeyBind(key, fn) keys[key]=fn end
function IsKeyBindRegistered() return false end
function ExecuteInGameThread(fn) fn() end
function FName(value) return value end
function FText(value) return value end
function LoopAsync(ms, fn) assert(ms==500); tick=fn end
function StaticFindObject(path)
    if path=="/Script/UMG.Default__WidgetBlueprintLibrary" then
        return {IsValid=function() return true end,
            SetInputMode_UIOnlyEx=function(self, ...)
                assert(select("#", ...)==4); focus="ui"
                if fail_input then error(function() end) end
            end,
            SetInputMode_GameAndUIEx=function(self, ...)
                assert(select("#", ...)==5); focus="game_and_ui"
            end}
    end
    if path:find("WidgetBlueprintLibrary:",1,true) then
        error("UFunction property iteration is not available in pinned UE4SS")
    end
    if path:match("^/Script/UMG%.") then return {IsValid=function() return true end} end
    return objects[path]
end
function StaticConstructObject(class, outer, name)
    count=count+1
    local path="/Game/"..name
    local object={Font={}}
    object.IsValid=function() return true end
    object.GetFullName=function() return "Object "..path end
    object.IsInViewport=function() return true end
    for _, method in ipairs({"SetBrushColor","SetPadding","SetAutoWrapText","SetContent",
                             "SetPosition","SetSize","AddToViewport","SetUserFocus"}) do
        object[method]=function() end
    end
    object.SetAnchors=function(self, value) anchors=value end
    object.SetOffsets=function(self, value) offsets=value end
    object.AddChildToCanvas=function() return object end
    object.SetText=function(self, text) final_text=text; text_updates=text_updates+1 end
    object.SetUserFocus=function()
        if fail_focus then error(function() end) end
    end
    object.SetVisibility=function(self, value) self.visibility=value end
    objects[path]=object
    return object
end
local original_open=io.open
function io.open(path, mode)
    if mode=="r" then
        assert(path=="test.ui.lua")
        return {read=function() return data end, close=function() end}
    end
    assert(path=="test.command.json" and mode=="w")
    return {write=function(self, text) command=text end, close=function() end}
end
local world={IsValid=function() return true end, GetFullName=function() return world_name end}
local pc={GetFullName=function() return "PlayerController Current" end,
          IsValid=function() return true end,bShowMouseCursor=false}
local context=function() contexts=contexts+1; return pc, pc, world end
dofile("ue4ss/SzeroLAN/scripts/panel.lua")("test", context)
for index=1,20 do tick() end
assert(count==0 and contexts==0, "closed menu must not touch UObjects")
assert(not keys[Key.F11], "F11 remains entirely unbound by this mod")
keys[Key.F5](); tick()
assert(count==5 and focus=="ui")
assert(anchors.Maximum.X==1 and anchors.Maximum.Y==1)
assert(offsets.Left==0 and offsets.Right==0 and offsets.Bottom==0)
assert(final_text:find("Tester",1,true))
assert(final_text:find("not implemented",1,true))
local previous_updates=text_updates
for index=1,20 do tick() end
assert(text_updates==previous_updates, "unchanged text must not invalidate Slate layout")
keys[Key.RETURN](); assert(command=='{"serial":1,"op":"queue"}\n')
keys[Key.DOWN_ARROW](); keys[Key.DOWN_ARROW](); keys[Key.RETURN]()
assert(command:find('"lobby_id":"abcdef123456"',1,true))
keys[Key.DOWN_ARROW](); keys[Key.RETURN]()
assert(command:find('"value":true',1,true))
keys[Key.DOWN_ARROW](); keys[Key.RETURN](); assert(command:find('"op":"leave"',1,true))
local previous=command
keys[Key.ESCAPE](); tick()
assert(focus=="game_and_ui" and objects["/Game/SzeroLAN_1"].visibility==1)
local closed_contexts=contexts
for index=1,20 do tick() end
assert(contexts==closed_contexts, "no hidden-menu engine polling")
keys[Key.RETURN](); assert(command==previous)
keys[Key.F5](); tick(); assert(count==5)
objects={}
tick(); assert(count==10 and final_text:find("Tester",1,true), "rebuild lost menu in same world with text/focus")
objects={}; world_name="World Next"
tick(); assert(count==15, "rebuild after travel without cached wrappers")
data='os.execute("must not execute")'
tick(); assert(final_text:find("Tester",1,true))
-- A non-string error must identify the failing stage and not leave the menu
-- shown, trap input or auto-retry every frame. Include a resolvable PC path.
objects.Current=pc
keys[Key.ESCAPE]();tick()
fail_input=true
keys[Key.F5]();tick()
assert(objects["/Game/SzeroLAN_3"].visibility==1)
assert(table.concat(messages,"\n"):find("stage=input.SetInputMode_UIOnlyEx.invoke",1,true))
local failed_contexts=contexts
for _=1,20 do tick() end
assert(contexts==failed_contexts,"failed open must not keep polling UObjects")
fail_input=false;fail_focus=true
-- Emulate the supplied loader's observable behavior: an unformatted error
-- object reaches the caller instead of the xpcall handler's formatted result.
xpcall=function(fn)
    return pcall(fn)
end
keys[Key.F5]();tick()
assert(focus=="game_and_ui" and objects["/Game/SzeroLAN_3"].visibility==1,"partial focus change must roll back")
assert(table.concat(messages,"\n"):find("stage=input.SetUserFocus",1,true))
fail_focus=false
xpcall=original_xpcall
keys[Key.F5]();tick();assert(focus=="ui","explicit F5 retry works after failure")
io.open=original_open
print=original_print
os.getenv=original_getenv
print("Full-screen menu, focus, key-conflict and idle-work mock contracts passed")
