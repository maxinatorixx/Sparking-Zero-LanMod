-- Our diagnostics require an explicit per-launch opt-in; never replace global print.
local function Log(...)
    if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" then print(...) end
end
-- Runtime UMG panel. Store only object paths across frames, never UObject handles.
-- Construction pattern corroborated by public ue4ss-ModMenu; no source bundled.
return function(stem, context_provider)
    local view, visible, selected, serial = {}, false, 1, 0
    local action, shown, last_text, previous_cursor = 1, false, nil, nil
    local ui_path, command_path = stem .. ".ui.lua", stem .. ".command.json"
    local root_path, text_path, current_world, creating = nil, nil, nil, false
    local generation, retry_after, last_error = 0, 0, nil
    local stage, input_touched, attempted_pc_path = "idle", false, nil
    local trace_budget = 0
    local function step(name)
        stage = name
        -- Emit BEFORE crossing into the loader. In the supplied runtime,
        -- xpcall's formatted handler result did not reach the error logger.
        if trace_budget > 0 then
            trace_budget = trace_budget - 1
            Log("[SzeroLAN] Panel step=" .. name .. "\n")
        end
    end
    Log("[SzeroLAN] Panel revision=f5-open-v4 (UMG prototype, verified input parameter counts)\n")
    local function warn(message)
        if message ~= last_error then
            last_error = message
            Log("[SzeroLAN] Panel: " .. message .. "\n")
        end
    end
    local function send(op, extra)
        if not visible or not shown then return end
        serial = serial + 1
        local file = assert(io.open(command_path, "w"))
        file:write('{"serial":' .. serial .. ',"op":"' .. op .. '"' .. (extra or "") .. '}\n')
        file:close()
    end
    local function bind(key, fn)
        if not RegisterKeyBind or not Key or not Key[key] then
            warn("Key binding API unavailable: " .. key); return
        end
        if IsKeyBindRegistered and IsKeyBindRegistered(Key[key]) then
            warn(key .. " already bound; existing binding preserved"); return
        end
        RegisterKeyBind(Key[key], function()
            local ok, err = pcall(fn)
            if not ok then warn(tostring(err)) end
        end)
    end
    bind("F5", function()
        visible = not visible
        trace_budget = visible and 32 or 0
        Log("[SzeroLAN] Panel: F5 requested " .. (visible and "open" or "close") .. "\n")
    end)
    bind("ESCAPE", function() visible = false end)
    bind("UP_ARROW", function() if visible then action = (action - 2) % 6 + 1 end end)
    bind("DOWN_ARROW", function() if visible then action = action % 6 + 1 end end)
    local function next_lobby()
        if visible then selected = selected % math.max(1, #(view.lobbies or {})) + 1 end
    end
    bind("RIGHT_ARROW", next_lobby)
    bind("LEFT_ARROW", function()
        if visible then selected = (selected - 2) % math.max(1, #(view.lobbies or {})) + 1 end
    end)
    bind("RETURN", function()
        if action == 1 then send("queue")
        elseif action == 2 then send("create")
        elseif action == 3 then
            local lobby = (view.lobbies or {})[selected]
            if lobby and type(lobby.id) == "string" and #lobby.id == 12 and lobby.id:match("^[a-f0-9]+$") then
                send("join", ',"lobby_id":"' .. lobby.id .. '"')
            end
        elseif action == 4 then send("ready", ',"value":' .. (view.ready and "false" or "true"))
        elseif action == 5 then send("leave")
        elseif action == 6 then send("finish") end
    end)
    local function input_mode(pc, root, opened)
        step("input.library_lookup")
        local library = StaticFindObject("/Script/UMG.Default__WidgetBlueprintLibrary")
        assert(library and library:IsValid(), "WidgetBlueprintLibrary unavailable")
        local method = opened and "SetInputMode_UIOnlyEx" or "SetInputMode_GameAndUIEx"
        -- Exact supported build: runtime metadata verifies NumParms=4/5 and
        -- ParmsSize=18/19. Pinned UE4SS UFunction wrappers do NOT expose
        -- ForEachProperty; the previous attempted capability probe threw.
        if opened then
            step("input.cursor_snapshot")
            previous_cursor = pc.bShowMouseCursor
            step("input.focusable_property")
            root.bIsFocusable = true
            input_touched = true
            step("input." .. method .. ".invoke")
            library:SetInputMode_UIOnlyEx(pc, root, 0, false)
            step("input.SetUserFocus")
            root:SetUserFocus(pc)
        else
            step("input." .. method .. ".invoke")
            library:SetInputMode_GameAndUIEx(pc, nil, 0, false, false)
            if previous_cursor ~= nil then pc.bShowMouseCursor = previous_cursor end
            previous_cursor = nil
            input_touched = false
        end
    end
    local function path(object) return object:GetFullName():gsub("^[^ ]+ ", "") end
    local function find(name)
        if not name then return nil end
        local object = StaticFindObject(name)
        if object and object:IsValid() then return object end
    end
    local function construct(class, outer, name)
        local result = StaticConstructObject(assert(find("/Script/UMG." .. class)), outer, FName(name))
        assert(result and result:IsValid(), "Cannot construct " .. class)
        return result
    end
    local function lines()
        local result = {
            "Sparking ZERO LAN (experimental)",
            tostring(view.name or "Waiting for background client"),
            tostring(view.message or "Start using setup/launch window"),
            "Up/Down: action | Left/Right: lobby | Enter: select | Esc/F5: close",
            "Server: " .. (view.connected and "connected" or "disconnected") ..
                " | UDP: " .. (view.udp_ready and "ready" or "waiting") ..
                " | Queue: " .. (view.queued and "yes" or "no"),
            "Game: " .. tostring(view.adapter_stage or "waiting") ..
                " | Packets " .. tostring(view.sent or 0) .. "/" .. tostring(view.received or 0),
            "Character/stage selection entry is not implemented yet.",
        }
        for index, label in ipairs({"Quick match", "Create lobby", "Join selected lobby",
            view.ready and "Not ready" or "Ready", "Leave / cancel", "End assignment"}) do
            result[#result+1] = (index == action and "> " or "  ") .. label
        end
        local lobbies = view.lobbies or {}
        local first = math.floor((selected - 1) / 6) * 6 + 1
        for index = first, math.min(#lobbies, first + 5) do
            local lobby = lobbies[index]
            result[#result+1] = (index == selected and "> " or "  ") ..
                tostring(lobby.name) .. " | " .. tostring(lobby.players) .. " players" ..
                (lobby.in_match and " (paired)" or "")
        end
        if #lobbies == 0 then result[#result+1] = "No lobbies yet" end
        return table.concat(result, "\n")
    end
    local function update()
        step("context")
        local context, pc, world = context_provider()
        if not pc or not world or not world:IsValid() then return end
        attempted_pc_path = path(pc)
        local world_name = world:GetFullName() .. "|" .. pc:GetFullName()
        if world_name ~= current_world then
            -- Never touch old widget references during travel. Viewport owns lifetime.
            root_path, text_path, current_world = nil, nil, world_name
            shown, last_text, previous_cursor = false, nil, nil
            input_touched = false
            retry_after = 0
        end
        local root = find(root_path)
        local text = find(text_path)
        if not visible then
            if shown then
                step("close.collapse")
                if root then root:SetVisibility(1) end
                input_mode(pc, nil, false)
                shown = false
            end
            return
        end
        if root and not root:IsInViewport() then root, text = nil, nil end
        if not root or not text then
            if os.time() < retry_after then return end
            retry_after = os.time() + 5
            generation = generation + 1
            local tag = "SzeroLAN_" .. tostring(generation)
            step("build.UserWidget")
            root = construct("UserWidget", pc, tag)
            root_path = path(root)
            step("build.WidgetTree")
            local tree = construct("WidgetTree", root, tag .. "_Tree")
            root.WidgetTree = tree
            local canvas = construct("CanvasPanel", tree, tag .. "_Canvas")
            tree.RootWidget = canvas
            local border = construct("Border", tree, tag .. "_Border")
            border:SetBrushColor({R=0.02,G=0.02,B=0.04,A=1})
            border:SetPadding({Left=40,Top=30,Right=40,Bottom=30})
            text = construct("TextBlock", tree, tag .. "_Text")
            text:SetAutoWrapText(true)
            pcall(function() text.Font.Size = 18 end)
            border:SetContent(text)
            local slot = canvas:AddChildToCanvas(border)
            slot:SetAnchors({Minimum={X=0,Y=0},Maximum={X=1,Y=1}})
            slot:SetOffsets({Left=0,Top=0,Right=0,Bottom=0})
            step("build.AddToViewport")
            root:AddToViewport(9000)
            step("build.collapse")
            root:SetVisibility(1)
            root_path, text_path = path(root), path(text)
            retry_after = 0
            shown, last_text = false, nil
            Log("[SzeroLAN] In-game UMG LAN panel added to viewport (needs visual verification)\n")
        end
        if visible then
            step("open.text_data")
            local content = lines()
            if content ~= last_text then
                step("open.FText")
                local rendered = FText(content)
                step("open.SetText")
                text:SetText(rendered)
                last_text = content
            end
        end
        if visible ~= shown then
            -- Populate before showing; Slate needs a visible widget for focus.
            -- Any later failure collapses it and restores input below.
            step("open.visibility")
            root:SetVisibility(visible and 0 or 1)
            input_mode(pc, root, visible)
            shown = visible
            Log("[SzeroLAN] Panel: open sequence completed (rendering not verified)\n")
        end
        step("idle")
        trace_budget = 0
    end
    LoopAsync(500, function()
        local file = io.open(ui_path, "r")
        if file then
            local data = file:read(524289)
            file:close()
            if data and #data <= 524288 then
                local read = load(data, "SzeroLAN panel data", "t", {})
                if read then
                    local ok, updated = pcall(read)
                    if ok and type(updated) == "table" and updated.version == 1 then
                        view = updated
                        selected = math.min(selected, math.max(1, #(view.lobbies or {})))
                    end
                end
            end
        end
        if not creating and (visible or shown) then
            creating = true
            ExecuteInGameThread(function()
                local ok, err = xpcall(update, function(failure)
                    return "stage=" .. stage .. " " .. debug.traceback(tostring(failure), 2)
                end)
                if not ok then
                    -- Stage must be composed OUTSIDE the error handler too:
                    -- the live loader returned only a function error object.
                    warn("UMG update failed: stage=" .. stage .. " " .. tostring(err))
                    trace_budget = 0
                    visible, shown = false, false
                    -- Rollback is independent of the failed open step. F5 may
                    -- retry, but the asynchronous loop must not retry/spam.
                    local hidden, hide_error = pcall(function()
                        local root = find(root_path)
                        if root then root:SetVisibility(1) end
                    end)
                    if not hidden then warn("Rollback collapse failed: " .. tostring(hide_error)) end
                    if input_touched then
                        local restored, restore_error = pcall(function()
                            local pc = find(attempted_pc_path)
                            assert(pc, "Local controller unavailable for input rollback")
                            input_mode(pc, nil, false)
                        end)
                        if not restored then warn("Input rollback failed: " .. tostring(restore_error)) end
                    end
                end
                creating = false
            end)
        end
        return false
    end)
end
