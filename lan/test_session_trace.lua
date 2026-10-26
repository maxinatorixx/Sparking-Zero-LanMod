-- Pure Lua contract; never reads a game process or loads a native DLL.
local factory=dofile("ue4ss/SzeroLAN/scripts/session_trace.lua")
local getenv,loadlib,oldprint=os.getenv,package.loadlib,print
local enabled,loads,calls,prints=nil,0,0,0
os.getenv=function(key) if key=="SZERO_LAN_MOD_LOGGING" then return "1" end;assert(key=="SZERO_LAN_NATIVE_TRACE");return enabled end
package.loadlib=function(path,entry)
    loads=loads+1;assert(path=="fixture/session_probe.dll" and entry=="szero_session_probe")
    return function() calls=calls+1 end
end
print=function() prints=prints+1 end
assert(factory("fixture/","ab12")==nil and loads==0 and calls==0)
enabled="1"
for _,bad in ipairs({"","default","../ab12",string.rep("a",65)}) do assert(factory("fixture/",bad)==nil) end
local trace=factory("fixture/","ab12");assert(loads==0)
assert(trace():find("diagnostic only",1,true));assert(loads==1 and calls==1 and prints==1)
for i=2,365 do trace() end
assert(calls==360 and loads==1 and prints==1 and trace():find("window ended",1,true))
package.loadlib=function() return nil,"missing" end
assert(factory("fixture/","ab12")():find("helper unavailable",1,true))
package.loadlib=function() return function() error("fixture failure") end end
assert(factory("fixture/","ab12")():find("call failed",1,true))
os.getenv,package.loadlib,print=getenv,loadlib,oldprint
print("Passive session trace contracts passed (mock helper only)")
