local original_getenv=os.getenv
os.getenv=function(key) if key=="SZERO_LAN_MOD_LOGGING" then return "1" end;return original_getenv(key) end
-- No native DLL or game memory is touched by this Lua contract test.
local factory=dofile("ue4ss/SzeroLAN/scripts/audit.lua")
local original_loadlib, original_open, original_remove=package.loadlib,io.open,os.remove
local calls, data, next_data=0,nil,nil
os.remove=function() data=nil; return true end
package.loadlib=function(path, entry)
    assert(path=="fixture/console_probe.dll" and entry=="szero_console_probe")
    return function() calls=calls+1; data=next_data end
end
io.open=function(path, mode)
    assert(path=="fixture/console_probe_ab12.json" and mode=="r")
    if not data then return nil end
    return {read=function(self, limit) assert(limit==16385); return data end,close=function() end}
end
local audit=factory("fixture/","ab12")
assert(calls==0,"creation must not run native helper")
assert(audit():find("pending",1,true) and calls==1)
next_data='{"version":1,"status":"snapshot","target_sha256":"wrong","registered":{}}'
assert(audit():find("pending",1,true),"reject unrelated image report")
next_data='{"version":1,"status":"snapshot","target_sha256":"e54e79e756f79719f09915078a37b6e87c23d32ecaaaa2f485d1a048ba198e55","complete_occupied_read":true,"registered":{"spn.multiplayerContext.contextMode":true,"spn.multiplayerContext.apply.exec":true}}'
assert(audit():find("1/5 base names registered",1,true))
local previous=calls
audit(); assert(calls==previous,"do not repeatedly audit registry")
next_data='{"version":1,"status":"unavailable","reason":"console_registry_bounds"}'
assert(factory("fixture/","ab12")():find("console_registry_bounds",1,true))
package.loadlib=function() return nil,"missing" end
assert(factory("fixture/","ab12")():find("helper unavailable",1,true))
package.loadlib=function() return function() end end
data=nil
audit=factory("fixture/","ab12")
for i=1,30 do audit() end
assert(audit():find("timed out",1,true))
data=next_data;os.remove=function() return nil,"locked" end
assert(factory("fixture/","ab12")():find("stale report",1,true))
package.loadlib,io.open,os.remove=original_loadlib,original_open,original_remove
os.getenv=original_getenv
print("Console audit contracts passed (mock native helper only)")
