-- Mock contracts only: no actual native widget, focus, navigation or game test.
local tick,keys,objects,post=nil,{},{},nil
local view='return {version=1,name="Tester",connected=true,lobbies={{id="abcdef123456",name="LAN"}}}'
local report='{}'
local request,command,constructed,contexts,updates=nil,nil,0,0,0
local bridge_calls,phase,clock=0,"hashing",0
local original_open,original_getenv,original_loadlib,original_time=io.open,os.getenv,package.loadlib,os.time
os.getenv=function(key) if key=="SZERO_LAN_MOD_LOGGING" then return "1" end;if key=="SZERO_LAN_INSTANCE" then return "deadbeef" end end
os.time=function() return clock end
Key={F5=5,ESCAPE=27,UP=38,DOWN=40,RETURN=13,F11=122}
function RegisterKeyBind(key,fn) keys[key]=fn end
function IsKeyBindRegistered() return false end
function RegisterHook(name,pre,callback)
    assert(name=="/Script/SS.SSMenuManager:CallbackDecidedButton")
    assert(type(pre)=="function");post=callback
end
function ExecuteInGameThread(fn) fn() end
function LoopAsync(ms,fn) assert(ms==500);tick=fn end
function FName(value) return value end
function FText(value) return value end
local focused,activated,deactivated,anchors=false,0,0,nil
function StaticFindObject(name)
    if name=="/Script/UMG.Default__WidgetBlueprintLibrary" then return {
        IsValid=function() return true end,
        SetInputMode_UIOnlyEx=function() focused=true end,
        SetInputMode_GameAndUIEx=function() focused=false end} end
    if name:find("WidgetBlueprintLibrary:",1,true) then
        error("UFunction property iteration is not available in pinned UE4SS")
    end
    if name:match("^/Script/") then return {IsValid=function() return true end,class=name} end
    return objects[name]
end
function StaticConstructObject(class,outer,name)
    constructed=constructed+1
    local object={class=class.class,outer=outer,address=0x10000+constructed*0x100,visibility=1}
    local pathname="/Game/"..name
    object.IsValid=function() return true end
    object.GetFullName=function() return "Object "..pathname end
    object.GetAddress=function(self) return self.address end
    object.IsInViewport=function(self) return self.in_viewport end
    object.AddToViewport=function(self) self.in_viewport=true end
    object.RemoveFromParent=function(self) self.in_viewport=false end
    object.SetVisibility=function(self,value) self.visibility=value end
    object.SetText=function(self,value) self.value=value;updates=updates+1 end
    object.SetAnchors=function(self,value) anchors=value end
    object.SetOffsets=function(self,value) assert(value.Left==0 and value.Right==0) end
    object.AddChildToCanvas=function(self) return self end
    object.ActivateWithAllChildWidget=function() activated=activated+1 end
    object.DeactivateWithAllChildWidget=function() deactivated=deactivated+1 end
    object.SetKeyboardFocusOnPossible=function(self) self.native_focus_requested=true end
    for _,method in ipairs({"SetBrushColor","SetPadding","SetContent","AddChildToVerticalBox","SetAutoWrapText"}) do
        object[method]=function() end
    end
    objects[pathname]=object;return object
end
package.loadlib=function(path,name)
    assert(path:match("menu_bridge%.dll$") and name=="szero_menu_bridge")
    return function()
        bridge_calls=bridge_calls+1
        if request then
            local pid,serial,root,tree,count,addresses=request:match("^SZERO_MENU_V1 (%d+) (%d+) (%x+) (%x+) (%d+)\n(.-)\n$")
            assert(pid=="42" and tonumber(count)==8 and tonumber(root,16) and tonumber(tree,16))
            local n=0;for _ in addresses:gmatch("%x+") do n=n+1 end;assert(n==8)
            report='{"version":1,"status":"bound","pid":42,"serial":'..serial..'}';request=nil
        else report='{"version":1,"status":"'..phase..'","pid":42,"serial":0}' end
    end
end
io.open=function(path,mode)
    if mode=="r" then
        local value=path=="test.ui.lua" and view or path:match("menu_bridge_deadbeef%.json$") and report
        assert(value,"Unexpected read "..path)
        return {read=function() return value end,close=function() end}
    end
    assert(mode=="w")
    return {write=function(self,...)
        local parts={...};for i,v in ipairs(parts) do parts[i]=tostring(v) end
        local value=table.concat(parts)
        if path:match("%.request$") then request=(request or "")..value
        else assert(path=="test.command.json");command=value end
    end,close=function() end}
end
local world_name="World Menu"
local world={IsValid=function() return true end,GetFullName=function() return world_name end}
local pc={GetFullName=function() return "PlayerController Current" end,bShowMouseCursor=false}
local context=function() contexts=contexts+1;return pc,pc,world end
dofile("ue4ss/SzeroLAN/scripts/native_menu.lua")("test",context)
local function step() clock=clock+1;tick() end
for _=1,20 do step() end
assert(constructed==0 and contexts==0 and bridge_calls==0,"closed native menu is idle")
assert(not keys[Key.UP] and not keys[Key.DOWN] and not keys[Key.RETURN] and not keys[Key.F11],"native input is not simulated")
keys[Key.F5]();step();assert(constructed==0,"no widgets before exact-build verification")
phase="ready";step()
local root=objects["/Game/SzeroLAN_Native_1"]
assert(root and root.class=="/Script/SS.SSMenuManager" and root.native_focus_requested)
assert(focused and activated==1 and anchors.Maximum.X==1 and anchors.Maximum.Y==1)
assert(objects["/Game/SzeroLAN_Native_1_Action1"].class=="/Script/SS.SSMenuButton")
local function press(index,owner)
    local button=objects["/Game/SzeroLAN_Native_1_Action"..index]
    post({get=function() return owner or root end},{get=function() return button end})
end
press(1,{IsValid=function() return true end,GetFullName=function() return "Object /Game/ProductionMenu" end})
assert(not command,"production menu callback must not enqueue LAN")
press(1);assert(command:find('"op":"queue"',1,true))
press(3);assert(command:find('"lobby_id":"abcdef123456"',1,true))
press(4);assert(command:find('"value":true',1,true))
local old=updates;for _=1,20 do step() end;assert(updates==old,"unchanged native labels/status do not redraw")
press(8);step();assert(not focused and deactivated==1 and root.visibility==1)
local before=contexts;for _=1,20 do step() end;assert(contexts==before)
local previous=command;press(1);assert(command==previous,"closed menu ignores callbacks")
keys[Key.F5]();step();assert(activated==2)
objects={};world_name="World Next";step()
assert(objects["/Game/SzeroLAN_Native_2"],"fresh paths after travel; no cached UObject handles")
view='os.execute("not permitted")';step()
local original_find=StaticFindObject
StaticFindObject=function(name)
    local value=original_find(name)
    if name=="/Script/UMG.Default__WidgetBlueprintLibrary" then
        value.SetInputMode_UIOnlyEx=function() focused=true;error("fixture input failure") end
    end
    return value
end
objects={};world_name="World InputFailure";step()
assert(not focused and objects["/Game/SzeroLAN_Native_3"].visibility==1,"failed opening must restore input and hide root")
local failed_contexts=contexts
keys[Key.F5]();for _=1,5 do step() end
assert(contexts==failed_contexts,"failed native menu must remain disabled until restart")
StaticFindObject=original_find
local old_count=constructed
phase="unavailable";objects={}
dofile("ue4ss/SzeroLAN/scripts/native_menu.lua")("test",context)
keys[Key.F5]();step()
assert(constructed==old_count,"unsupported executable must never construct or bind native widgets")
io.open,os.getenv,package.loadlib,os.time=original_open,original_getenv,original_loadlib,original_time
print("Native widget ownership/callback/focus-request/idle mock contracts passed (not a native game test)")
