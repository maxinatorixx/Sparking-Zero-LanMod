-- Our diagnostics require an explicit per-launch opt-in; never replace global print.
local function Log(...)
    if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" then print(...) end
end
-- Optional native read-only registry snapshot, called on the game thread only.
-- Registration is NOT proof of command acceptance, socket binding or a session.
return function(folder, instance)
    if os.getenv("SZERO_LAN_MOD_LOGGING") ~= "1" then return nil end
    local call, initialized, done, tries = nil, false, false, 0
    local detail = " | Console audit: pending"
    local report = folder .. "console_probe_" .. (instance or "default") .. ".json"
    local expected = {"contextMode", "myDummyMatchingJoinOrder", "myDummyP2pAddress",
        "dummyPeerP2pAddresses", "apply"}
    return function()
        if os.getenv("SZERO_LAN_MOD_LOGGING") ~= "1" then return "" end
        if done then return detail end
        if not initialized then
            initialized = true
            -- Only our generated report. Never accept an older launch/reload
            -- while asynchronous hash verification is still pending.
            os.remove(report)
            local stale = io.open(report, "r")
            if stale then
                stale:close()
                done, detail = true, " | Console audit: stale report could not be cleared"
                return detail
            end
            local ok, value = pcall(function()
                return package.loadlib(folder .. "console_probe.dll", "szero_console_probe")
            end)
            if not ok or type(value) ~= "function" then
                done, detail = true, " | Console audit: native helper unavailable"
                return detail
            end
            call = value
        end
        tries = tries + 1
        local ok, err = pcall(call)
        if not ok then
            done, detail = true, " | Console audit: helper call failed"
            Log("[SzeroLAN] Console audit call failed: " .. tostring(err) .. "\n")
            return detail
        end
        local file = io.open(report, "r")
        if file then
            local data = file:read(16385); file:close()
            if data and #data <= 16384 and data:find('"version":1',1,true) then
                if data:find('"status":"unavailable"',1,true) then
                    done, detail = true, " | Console audit: " .. (data:match('"reason":"([a-z_]+)"') or "unavailable")
                elseif data:find('"status":"snapshot"',1,true) and
                    data:find('"validation":"native_layout"',1,true) then
                    local found = 0
                    for _, name in ipairs(expected) do
                        if data:find('"spn.multiplayerContext.' .. name .. '":true',1,true) then found = found + 1 end
                    end
                    done = true
                    local complete = data:find('"complete_occupied_read":true',1,true) and "complete occupied read" or "partial read"
                    detail = " | Console audit: " .. found .. "/5 base names registered (" .. complete .. "; not acceptance)"
                end
                if done then Log("[SzeroLAN] Console registry report: " .. data .. "\n") end
            end
        end
        if not done and tries >= 30 then done, detail = true, " | Console audit: timed out" end
        return detail
    end
end
