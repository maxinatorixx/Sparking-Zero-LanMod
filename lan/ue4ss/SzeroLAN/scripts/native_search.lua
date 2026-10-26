-- Our diagnostics require an explicit per-launch opt-in; never replace global print.
local function Log(...)
    if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" then print(...) end
end
-- Explicit opt-in native adapter; session-v3 is a separate launcher selection.
-- The DLL owns native ABI, hash checks, service lifetime and network handoff.
-- Lua performs no network I/O or UObject discovery. Reports are not match proof.
return function(folder, instance)
    if os.getenv("SZERO_LAN_NATIVE_SEARCH") ~= "1" then return nil end
    if type(instance) ~= "string" or #instance ~= 32 or instance:find("[^a-f0-9]") then
        Log("[SzeroLAN] Native search disabled: invalid launch instance\n")
        return nil
    end
    local report_path = folder .. "native_search_" .. instance .. ".json"
    local call, initialized, stopped, scheduled, previous = nil, false, false, false, nil
    local trace_requested = os.getenv("SZERO_LAN_SERVICE_TRACE") == "1"
    local trace_call, trace_initialized, trace_failed
    local backend_requested = os.getenv("SZERO_LAN_NATIVE_SESSION3") == "1"
    local backend_call, backend_initialized, backend_failed
    local function Backend()
        if not backend_requested or backend_failed then return end
        local ok, err = pcall(function()
            if not backend_initialized then
                backend_initialized = true
                backend_call = assert(package.loadlib(folder .. "backend_adapter.dll", "szero_backend_adapter"))
                Log("[SzeroLAN] LAN backend adapter requested; report: " .. folder ..
                    "native_backend_adapter_" .. instance .. ".jsonl\n")
            end
            backend_call()
        end)
        if not ok then
            backend_failed = true
            Log("[SzeroLAN] LAN backend adapter unavailable: " .. tostring(err) .. "\n")
        end
    end
    local function Trace()
        if os.getenv("SZERO_LAN_MOD_LOGGING") ~= "1" or not trace_requested or trace_failed then return end
        local ok, err = pcall(function()
            if not trace_initialized then
                trace_initialized = true
                trace_call = assert(package.loadlib(folder .. "service_trace.dll", "szero_service_trace"))
                Log("[SzeroLAN] Optional online-service diagnostic: " .. folder ..
                    "native_service_trace_" .. instance .. ".jsonl (bounded, game-thread coverage only)\n")
            end
            trace_call()
        end)
        if not ok then
            trace_failed = true
            Log("[SzeroLAN] Optional service diagnostic unavailable: " .. tostring(err) .. "\n")
        end
    end
    local function Report()
        if os.getenv("SZERO_LAN_MOD_LOGGING") ~= "1" then return end
        local file = io.open(report_path, "rb")
        if not file then return end
        local contents = file:read(2049)
        file:close()
        if not contents or #contents > 2048 or contents == previous then return end
        previous = contents
        Log("[SzeroLAN] Native search report: " .. contents:gsub("[%c]", " ") .. "\n")
    end
    local function Tick()
        if stopped then return true end
        if scheduled then return false end
        scheduled = true
        local queued, err = pcall(ExecuteInGameThread, function()
            local ok, failure = pcall(function()
                if not initialized then
                    initialized = true
                    local fn, why = package.loadlib(folder .. "native_search.dll", "szero_native_search")
                    if type(fn) ~= "function" then error("helper unavailable: " .. tostring(why)) end
                    call = fn
                end
                call()
                Backend() -- A backend failure must not disable working LAN sessions.
                Trace() -- Failure here must never stop the multiplayer helper.
                Report()
            end)
            scheduled = false
            if not ok then
                stopped = true
                Log("[SzeroLAN] Native search stopped: " .. tostring(failure) .. "\n")
            end
        end)
        if not queued then
            scheduled, stopped = false, true
            Log("[SzeroLAN] Native search scheduling failed: " .. tostring(err) .. "\n")
        end
        return stopped
    end
    local mode = os.getenv("SZERO_LAN_NATIVE_SESSION3") == "1" and
        "Native LAN session integration requested; gameplay is unverified. " or
        "Native search/cancel experiment requested; joining/battle entry unavailable. "
    Log("[SzeroLAN] " .. mode .. "Helper report determines installation. " ..
        "Use original Online menu. Report: " .. report_path .. "\n")
    Tick()
    if not stopped then LoopAsync(1000, Tick) end
    return Tick
end
