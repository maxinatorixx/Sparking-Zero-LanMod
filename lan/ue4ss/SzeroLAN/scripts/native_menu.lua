-- Our diagnostics require an explicit per-launch opt-in; never replace global print.
local function Log(...)
    if os.getenv("SZERO_LAN_MOD_LOGGING") == "1" then print(...) end
end
-- Opt-in native-widget controls, NOT the main-menu controller/scene stack.
-- Uses only fresh LAN-owned SSMenuManager/SSMenuButton objects. The UI bridge
-- binds their dynamic native button callbacks after exact-build/ownership checks.
-- No production menu, online API, session flag or level transition is changed.
-- Bare native widget PreConstruct/Construct and actual navigation have NOT
-- been exercised in the game; an opt-in real-game test may crash. pcall does
-- not protect against native lifecycle faults. Never enable by default.
return function(stem, context_provider)
    local folder=assert(debug.getinfo(1,"S").source:gsub("^@",""):match("^(.*[/\\])"))
    local instance=os.getenv("SZERO_LAN_INSTANCE") or "default"
    assert(instance=="default" or (#instance<=64 and instance:match("^[a-f0-9]+$")),"Invalid instance")
    local bridge_path=folder.."menu_bridge_"..instance
    local bridge, load_error=package.loadlib(folder.."menu_bridge.dll","szero_menu_bridge")
    local view,visible,shown,creating={},false,false,false
    local root_path,text_path,world_name,button_paths=nil,nil,nil,{}
    local serial,generation,retry_after=0,0,0
    local selected,last_text,last_error,previous_cursor=1,nil,nil,nil
    local verified,pid,button_texts=false,nil,{}
    local last_labels,build_failed={},false
    local function warn(message)
        if message~=last_error then Log("[SzeroLAN] Native menu: "..message.."\n");last_error=message end
    end
    if not bridge then warn("UI bridge unavailable: "..tostring(load_error));return end
    local function path(object) return object:GetFullName():gsub("^[^ ]+ ","") end
    local function find(name)
        if not name then return nil end
        local value=StaticFindObject(name)
        if value and value:IsValid() then return value end
    end
    local function unwrap(value)
        if value==nil then return nil end
        local ok,result=pcall(function() return value:get() end)
        return ok and result or value
    end
    local function send(op,extra)
        if not visible or not shown then return end
        serial=serial+1
        local file=assert(io.open(stem..".command.json","w"))
        file:write('{"serial":'..serial..',"op":"'..op..'"'..(extra or "")..'}\n');file:close()
    end
    local function act(index)
        if index==1 then send("queue")
        elseif index==2 then send("create")
        elseif index==3 then
            local lobby=(view.lobbies or {})[selected]
            if lobby and type(lobby.id)=="string" and #lobby.id==12 and lobby.id:match("^[a-f0-9]+$") then
                send("join",',"lobby_id":"'..lobby.id..'"')
            end
        elseif index==4 then send("ready",',"value":'..(view.ready and "false" or "true"))
        elseif index==5 then send("leave")
        elseif index==6 then send("finish")
        elseif index==7 then selected=selected%math.max(1,#(view.lobbies or {}))+1
        elseif index==8 then visible=false end
    end
    -- Registration happens outside ExecuteInGameThread, as required by UE4SS3.
    local hooked,hook_error=pcall(function()
        assert(RegisterHook,"RegisterHook unavailable")
        RegisterHook("/Script/SS.SSMenuManager:CallbackDecidedButton",function() end,function(context,button)
            local ok,err=pcall(function()
                if not visible or not shown or not root_path then return end
                local owner,pressed=unwrap(context),unwrap(button)
                if not owner or not pressed or not owner:IsValid() or not pressed:IsValid() then return end
                if path(owner)~=root_path then return end
                local pressed_path=path(pressed)
                for index,name in ipairs(button_paths) do if name==pressed_path then act(index);return end end
            end)
            if not ok then warn("Button callback: "..tostring(err)) end
        end)
    end)
    if not hooked then warn("Native button hook unavailable: "..tostring(hook_error));return end
    local function bind(key,callback)
        if not RegisterKeyBind or not Key or not Key[key] then return end
        if IsKeyBindRegistered and IsKeyBindRegistered(Key[key]) then warn(key.." already bound; preserved");return end
        RegisterKeyBind(Key[key],callback)
    end
    bind("F5",function()
        if not build_failed then visible=not visible
        else warn("Native UI disabled after an error; restart with native_menu=false") end
    end)
    bind("ESCAPE",function() visible=false end)
    -- No arrow/Enter/gamepad simulation: actual native widget navigation must work.
    local function report()
        local file=io.open(bridge_path..".json","r");if not file then return nil end
        local data=file:read(2049);file:close()
        if not data or #data>2048 then return nil end
        local status=data:match('"status"%s*:%s*"([a-z_]+)"')
        local process=data:match('"pid"%s*:%s*(%d+)')
        return status,process,data:match('"serial"%s*:%s*(%d+)'),data
    end
    local function ready()
        if verified then return true end
        bridge()
        local status,process,ack,data=report()
        if status=="ready" and process then
            generation=math.max(generation,tonumber(ack) or 0)
            verified,pid=true,process;return true
        end
        if status=="unavailable" or status=="rejected" then warn(data or "Verification failed") end
        return false
    end
    local function construct(class,outer,name)
        local object=StaticConstructObject(assert(find(class),"Missing class "..class),outer,FName(name))
        assert(object and object:IsValid(),"Cannot construct "..class);return object
    end
    local function text(tree,name,label)
        local object=construct("/Script/UMG.TextBlock",tree,name)
        object:SetAutoWrapText(true);object:SetText(FText(label));return object
    end
    local labels={"Quick match","Create lobby","Join selected lobby","Ready / not ready",
        "Leave / cancel","End assignment","Next lobby","Close LAN menu"}
    local function build(pc)
        generation=generation+1
        local tag="SzeroLAN_Native_"..generation
        Log("[SzeroLAN] Native-widget experiment: bare-class lifecycle/input unverified, may crash; native main-menu stack NOT integrated\n")
        local root=construct("/Script/SS.SSMenuManager",pc,tag)
        local tree=construct("/Script/UMG.WidgetTree",root,tag.."_Tree");root.WidgetTree=tree
        local canvas=construct("/Script/UMG.CanvasPanel",tree,tag.."_Canvas");tree.RootWidget=canvas
        local border=construct("/Script/UMG.Border",tree,tag.."_Background")
        border:SetBrushColor({R=0.02,G=0.02,B=0.04,A=1});border:SetPadding({Left=40,Top=24,Right=40,Bottom=24})
        local box=construct("/Script/UMG.VerticalBox",tree,tag.."_Layout");border:SetContent(box)
        local info=text(tree,tag.."_Status","LAN native controls: waiting");box:AddChildToVerticalBox(info)
        local buttons,addresses={},{}
        local paths,text_paths={},{}
        for index,label in ipairs(labels) do
            local button=construct("/Script/SS.SSMenuButton",tree,tag.."_Action"..index)
            local sub=construct("/Script/UMG.WidgetTree",button,tag.."_ActionTree"..index)
            local caption=text(sub,tag.."_Caption"..index,label);sub.RootWidget=caption
            -- Render our own caption tree; do not assign native protected caption
            -- or remote-button fields / rely on a cooked Blueprint's named children.
            button.WidgetTree=sub;button.bIsFocusable=true
            box:AddChildToVerticalBox(button)
            buttons[index]=button;paths[index]=path(button);text_paths[index]=path(caption)
            addresses[index]=string.format("%x",button:GetAddress())
        end
        local slot=canvas:AddChildToCanvas(border)
        slot:SetAnchors({Minimum={X=0,Y=0},Maximum={X=1,Y=1}})
        slot:SetOffsets({Left=0,Top=0,Right=0,Bottom=0})
        root.bIsFocusable=true;root:AddToViewport(9000);root:SetVisibility(1)
        local ok,err=pcall(function()
            local request=assert(io.open(bridge_path..".request","w"))
            request:write("SZERO_MENU_V1 ",pid," ",generation," ",string.format("%x",root:GetAddress())," ",
                string.format("%x",tree:GetAddress())," ",#buttons,"\n",table.concat(addresses," "),"\n")
            request:close();bridge()
            local status,process,ack,detail=report()
            assert(status=="bound" and process==pid and tonumber(ack)==generation,
                "Native button binding rejected: "..tostring(detail))
        end)
        if not ok then
            build_failed=true;root:RemoveFromParent();error(tostring(err).."; native UI disabled until restart")
        end
        root_path,text_path,button_paths,button_texts=path(root),path(info),paths,text_paths
        last_labels={}
        Log("[SzeroLAN] Experimental native SSMenuManager/button controls created; main-menu stack NOT integrated\n")
        return root,info
    end
    local function input_mode(pc,root,opened)
        local library=assert(find("/Script/UMG.Default__WidgetBlueprintLibrary"))
        local method=opened and "SetInputMode_UIOnlyEx" or "SetInputMode_GameAndUIEx"
        -- Supported build metadata verifies 4/5 parameters. UE4SS3 UFunction
        -- wrappers have no ForEachProperty; do not probe that unsupported API.
        if opened then
            previous_cursor=pc.bShowMouseCursor
            library:SetInputMode_UIOnlyEx(pc,root,0,false)
            root:ActivateWithAllChildWidget();root:SetKeyboardFocusOnPossible()
        else
            if root then pcall(function() root:DeactivateWithAllChildWidget() end) end
            library:SetInputMode_GameAndUIEx(pc,nil,0,false,false)
            if previous_cursor~=nil then pc.bShowMouseCursor=previous_cursor end
            previous_cursor=nil
        end
    end
    local function lines()
        local lobby=(view.lobbies or {})[selected]
        return table.concat({"Sparking ZERO LAN — experimental native widget controls",
            "Not integrated into the native main-menu scene stack; battle entry remains unresolved.",
            tostring(view.name or ""),tostring(view.message or ""),
            "Server: "..(view.connected and "connected" or "disconnected")..
                " | Game packets: "..tostring(view.sent or 0).."/"..tostring(view.received or 0),
            "Selected lobby: "..(lobby and tostring(lobby.name) or "none"),
            "Use native focus/navigation and confirm. F5 / Escape closes."},"\n")
    end
    local function update()
        local _,pc,world=context_provider()
        if not pc or not world or not world:IsValid() then return end
        local identity=world:GetFullName().."|"..pc:GetFullName()
        if identity~=world_name then
            root_path,text_path,button_paths,button_texts=nil,nil,{},{}
            world_name,shown,last_text,previous_cursor=identity,false,nil,nil;retry_after=0;last_labels={}
        end
        local root,info=find(root_path),find(text_path)
        if not visible then
            if shown then if root then root:SetVisibility(1) end;input_mode(pc,root,false);shown=false end
            return
        end
        if root and not root:IsInViewport() then root,info=nil,nil end
        if not root or not info then
            if build_failed or os.time()<retry_after or not ready() then return end
            retry_after=os.time()+5;root,info=build(pc);shown,last_text=false,nil;retry_after=0
        end
        if not shown then root:SetVisibility(0);input_mode(pc,root,true);shown=true end
        local value=lines();if value~=last_text then info:SetText(FText(value));last_text=value end
        -- Native LastFocusedWidget is a reflected field. Never retain its wrapper.
        local focused
        pcall(function() if root.LastFocusedWidget and root.LastFocusedWidget:IsValid() then focused=path(root.LastFocusedWidget) end end)
        for index,name in ipairs(button_texts) do
            local caption=find(name)
            if caption then
                local highlighted=focused==button_paths[index]
                local label=(highlighted and "> " or "   ")..labels[index]
                if last_labels[index]~=label then caption:SetText(FText(label));last_labels[index]=label end
            end
        end
    end
    LoopAsync(500,function()
        local file=io.open(stem..".ui.lua","r")
        if file then
            local data=file:read(524289);file:close()
            if data and #data<=524288 then
                local read=load(data,"SzeroLAN native menu data","t",{})
                if read then local ok,new=pcall(read)
                    if ok and type(new)=="table" and new.version==1 then
                        view=new
                        selected=math.min(selected,math.max(1,#(view.lobbies or {})))
                    end
                end
            end
        end
        if not creating and (visible or shown) then
            creating=true;ExecuteInGameThread(function()
                local ok,err=pcall(update)
                if not ok then
                    warn(tostring(err))
                    visible,build_failed=false,true
                    -- Best-effort input rollback even when opening failed after
                    -- switching to UIOnly; a failed experiment must not trap input.
                    pcall(function()
                        local root=find(root_path)
                        if root then root:SetVisibility(1) end
                        local _,pc=context_provider()
                        if pc then input_mode(pc,root,false) end
                    end)
                    shown=false
                end
                creating=false
            end)
        end
        return false
    end)
end
