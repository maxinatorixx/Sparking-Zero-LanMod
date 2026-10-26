-- Our diagnostics require an explicit per-launch opt-in; never replace global print.
local function Log(...)
    if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" then print(...) end
end
-- Optional passive session evidence, NOT a native LAN backend implementation.
-- The caller schedules this closure on the game thread at most once per second.
-- Inactive by default: no DLL loading, files, UObject lookups or added loops.
return function(folder, instance)
    if os.getenv("SZERO_LAN_MOD_LOGGING") ~= "1" or os.getenv("SZERO_LAN_NATIVE_TRACE") ~= "1" then return nil end
    if type(instance) ~= "string" or #instance == 0 or #instance > 64 or
        instance:find("[^a-f0-9]") then return nil end
    local call, initialized, done, tries = nil, false, false, 0
    local detail = " | Native session trace: enabled (diagnostic only)"
    return function()
        if os.getenv("SZERO_LAN_MOD_LOGGING") ~= "1" then return "" end
        if done then return detail end
        if not initialized then
            initialized = true
            local ok, value = pcall(package.loadlib, folder .. "session_probe.dll", "szero_session_probe")
            if not ok or type(value) ~= "function" then
                done, detail = true, " | Native session trace: helper unavailable"
                return detail
            end
            call = value
            Log("[SzeroLAN] Passive native session trace: " .. folder .. "session_trace_" .. instance ..
                ".jsonl (max 300 seconds after hash verification; no native session initialization)\n")
        end
        tries = tries + 1
        local ok = pcall(call)
        if not ok then done, detail = true, " | Native session trace: helper call failed" end
        -- Bounds calls while the C helper independently enforces time, rate and
        -- record limits. Hash verification usually consumes only a few polls.
        if tries >= 360 then done, detail = true, " | Native session trace: capture window ended" end
        return detail
    end
end
