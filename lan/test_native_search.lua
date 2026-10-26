-- Standalone lifecycle contract: no game, DLL, network or real file accesses.
local factory = dofile("ue4ss/SzeroLAN/scripts/native_search.lua")
local real = {getenv=os.getenv, loadlib=package.loadlib, open=io.open, print=print,
    execute=ExecuteInGameThread, loop=LoopAsync, loadfile=loadfile}
local enabled, trace_enabled, instance = nil, nil, string.rep("a",32)
local backend_enabled
local logging_enabled="1"
local loads, calls, reads, output = 0, 0, 0, {}
local report, in_game, tick, queued = nil, false, nil, nil
os.getenv = function(key)
    if key=="SZERO_LAN_MOD_LOGGING" then return logging_enabled end
    if key=="SZERO_LAN_NATIVE_SEARCH" then return enabled end
    if key=="SZERO_LAN_INSTANCE" then return instance end
    if key=="SZERO_LAN_SERVICE_TRACE" then return trace_enabled end
    if key=="SZERO_LAN_NATIVE_SESSION3" then return backend_enabled end
end
print = function(message) output[#output+1] = message end
package.loadlib = function(path, entry)
    loads=loads+1
    assert(in_game and path=="fixture/native_search.dll" and entry=="szero_native_search")
    return function() assert(in_game); calls=calls+1 end
end
io.open = function(path, mode)
    assert(in_game and path=="fixture/native_search_"..instance..".json" and mode=="rb")
    reads=reads+1
    if not report then return nil end
    return {read=function(_,limit) assert(limit==2049);return report:sub(1,limit) end,
        close=function() end}
end
ExecuteInGameThread = function(fn)
    assert(not in_game and not queued)
    in_game=true;fn();in_game=false
end
LoopAsync = function(ms, fn) assert(ms==1000);tick=fn end
assert(factory("fixture/",instance)==nil and loads==0 and reads==0 and #output==0)
enabled="1"
for _, bad in ipairs({"", "ab12", "../bad",string.rep("a",33),string.rep("A",32)}) do
    assert(factory("fixture/",bad)==nil and loads==0)
end
output={}
factory("fixture/",instance)
assert(loads==1 and calls==1 and tick and #output==1)
report='{"version":1,"status":"installed","reason":"","searches":0,"cancels":0}'
tick();assert(calls==2 and #output==2 and output[2]:find('"status":"installed"',1,true))
tick();assert(calls==3 and #output==2, "unchanged status must not spam logs")
report=report:gsub('"searches":0','"searches":1')
tick();assert(#output==3, "changed counters should be reported")
report=string.rep("x",2049)
tick();assert(#output==3, "oversized report must not be read or printed unboundedly")
-- Queueing more polls while a game-thread callback is outstanding is forbidden.
ExecuteInGameThread=function(fn) assert(not queued);queued=fn end
tick();local before=calls;tick();assert(calls==before and queued)
in_game=true;queued();queued=nil;in_game=false
-- Restore the synchronous mock independently of UE4SS availability.
ExecuteInGameThread=function(fn) in_game=true;fn();in_game=false end
-- Optional service tracing is isolated: its failure never stops native polls.
trace_enabled="1"
local probe_loads,probe_calls=0,0
package.loadlib=function(path,entry)
    assert(in_game)
    if path=="fixture/service_trace.dll" then
        assert(entry=="szero_service_trace");probe_loads=probe_loads+1
        return function() probe_calls=probe_calls+1;error("optional fixture failure") end
    end
    assert(path=="fixture/native_search.dll")
    return function() calls=calls+1 end
end
local optional=factory("fixture/",instance)
local native_before=calls
assert(probe_loads==1 and probe_calls==1)
assert(optional()==false and calls==native_before+1 and probe_loads==1)
trace_enabled=nil
backend_enabled="1"
local backend_loads,backend_calls=0,0
package.loadlib=function(path,entry)
    assert(in_game)
    if path=="fixture/backend_adapter.dll" then
        assert(entry=="szero_backend_adapter");backend_loads=backend_loads+1
        return function() backend_calls=backend_calls+1;error("backend fixture failure") end
    end
    assert(path=="fixture/native_search.dll")
    return function() calls=calls+1 end
end
local backend=factory("fixture/",instance)
local backend_native_before=calls
assert(backend_loads==1 and backend_calls==1)
assert(backend()==false and calls==backend_native_before+1 and backend_loads==1)
-- Logging off must preserve native/backend operations without reports or probes.
for _,disabled in ipairs({"missing", "0"}) do
    if disabled=="missing" then logging_enabled=nil else logging_enabled="0" end
    trace_enabled,backend_enabled="1","1"
    local own_native,own_backend,own_probes=0,0,0
    local before_reads,before_output=reads,#output
    package.loadlib=function(path,entry)
        if path=="fixture/native_search.dll" then return function() own_native=own_native+1 end end
        if path=="fixture/backend_adapter.dll" then return function() own_backend=own_backend+1 end end
        own_probes=own_probes+1;error("diagnostic helper loaded while logging off")
    end
    local quiet=factory("fixture/",instance)
    quiet()
    assert(own_native==2 and own_backend==2 and own_probes==0)
    assert(reads==before_reads and #output==before_output,"logging off read/printed a report")
    assert(dofile("ue4ss/SzeroLAN/scripts/audit.lua")("fixture/",instance)==nil)
    assert(dofile("ue4ss/SzeroLAN/scripts/session_trace.lua")("fixture/",instance)==nil)
end
logging_enabled="1"
trace_enabled,backend_enabled=nil,nil
package.loadlib=function() loads=loads+1;return nil,"fixture missing" end
local before_loads=loads
local failed=factory("fixture/",instance)
assert(failed()==true and loads==before_loads+1)
assert(output[#output]:find("helper unavailable",1,true))
package.loadlib=function() return function() error("fixture call failure") end end
assert(factory("fixture/",instance)()==true)
assert(output[#output]:find("fixture call failure",1,true))
ExecuteInGameThread=function() error("fixture scheduling failure") end
assert(factory("fixture/",instance)()==true)
assert(output[#output]:find("scheduling failed",1,true))
-- Main's opt-in branch must return before audit, panel, UObject or console work.
local branch_calls=0
loadfile=function(path)
    assert(path:match("native_search%.lua$"), "native branch loaded legacy module: "..path)
    return function() return function(folder, ident)
        assert(ident==instance and folder:match("scripts[/\\]$"));branch_calls=branch_calls+1
    end end
end
LoopAsync=function() error("legacy poll must not be registered") end
dofile("ue4ss/SzeroLAN/scripts/main.lua")
assert(branch_calls==1)
os.getenv,package.loadlib,io.open,print=real.getenv,real.loadlib,real.open,real.print
ExecuteInGameThread,LoopAsync,loadfile=real.execute,real.loop,real.loadfile
print("Native search startup, game-thread, bounded reporting and legacy isolation contracts passed (mock only)")
