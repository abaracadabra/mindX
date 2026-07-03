--[[
  dato.lua — a DAIO-owned data-DAO as an AO process.

  Modeled on the AO DAO cookbook (https://cookbook_ao.arweave.net/tutorials/begin/dao.html):
  message-driven Handlers.add over persistent state tables. Unlike the cookbook's
  peer stake-to-vote DAO, a dato is OWNED by the DAIO — the DAIO is the authority;
  participants request to JOIN (with a fee tag) and the owner/govern admits.

  State:
    Owner      = "<DAIO address/id>"           -- set at spawn from the spawning message
    Deployer   = "<participant wallet>"        -- the client that spawned this dato
    Settings   = { default_tier, join_fee, open_join, max_members }
    Members    = { [wallet] = { joined_at, fee_paid, settings } }
    Names      = { [<handle>.<tier>.<root>] = { controller, proof } }
    Records    = { [name] = { sha256, tier, proof, content_type, version } }

  Permanence tiers (the name declares the tier): immortal | immutable | mutable.
  IMMORTAL commits carry an Arweave tx id in `proof` (the fulfillment desk uploads
  the bytes off-process; this process records the permanence proof).

  Load:  aos dato --load dato.lua    (then send Spawn/Configure/Join/Govern/Commit)
]]--

Owner    = Owner    or nil
Deployer = Deployer or nil
Settings = Settings or { default_tier = "immutable", join_fee = 0, open_join = true, max_members = 0 }
Members  = Members  or {}
Names    = Names    or {}
Records  = Records  or {}

local TIERS = { immortal = true, immutable = true, mutable = true }

local function reply(msg, action, data)
  ao.send({ Target = msg.From, Action = action, Data = (data or "ok") })
end

local function is_owner(addr) return Owner ~= nil and addr == Owner end

-- Spawn: the first message binds Owner (DAIO) + Deployer (participant) + name.
Handlers.add("Spawn",
  Handlers.utils.hasMatchingTag("Action", "Spawn"),
  function(msg)
    if Owner ~= nil then return reply(msg, "Spawn-Error", "already spawned") end
    Owner    = msg.Tags["Owner-DAIO"] or msg.From
    Deployer = msg.Tags["Deployer"] or msg.From
    Settings.default_tier = msg.Tags["Default-Tier"] or Settings.default_tier
    Settings.join_fee     = tonumber(msg.Tags["Join-Fee"] or "0") or 0
    Settings.open_join    = (msg.Tags["Open-Join"] ~= "false")
    if msg.Tags["Name"] then Names[msg.Tags["Name"]] = { controller = Owner, proof = nil } end
    Members[Deployer] = { joined_at = msg.Timestamp, fee_paid = 0, settings = {} }
    reply(msg, "Spawned", "dato owned by " .. tostring(Owner))
  end)

-- Configure: owner-only settings update.
Handlers.add("Configure",
  Handlers.utils.hasMatchingTag("Action", "Configure"),
  function(msg)
    if not is_owner(msg.From) then return reply(msg, "Configure-Error", "owner only") end
    if msg.Tags["Default-Tier"] and TIERS[msg.Tags["Default-Tier"]] then Settings.default_tier = msg.Tags["Default-Tier"] end
    if msg.Tags["Join-Fee"]    then Settings.join_fee   = tonumber(msg.Tags["Join-Fee"]) or Settings.join_fee end
    if msg.Tags["Open-Join"]   then Settings.open_join  = (msg.Tags["Open-Join"] ~= "false") end
    if msg.Tags["Max-Members"] then Settings.max_members = tonumber(msg.Tags["Max-Members"]) or 0 end
    reply(msg, "Configured")
  end)

-- Join: a participant requests to join. Paid datos require a Fee-Tx tag whose
-- amount (Fee-Paid) covers Settings.join_fee; closed datos require owner approval.
Handlers.add("Join",
  Handlers.utils.hasMatchingTag("Action", "Join"),
  function(msg)
    local wallet = msg.From
    if Members[wallet] then return reply(msg, "Joined", "already a member") end
    if (not Settings.open_join) and (not is_owner(msg.Tags["Approved-By"] or "")) then
      return reply(msg, "Join-Error", "closed-join: owner approval required")
    end
    if Settings.max_members > 0 then
      local n = 0; for _ in pairs(Members) do n = n + 1 end
      if n >= Settings.max_members then return reply(msg, "Join-Error", "at capacity") end
    end
    local fee_paid = tonumber(msg.Tags["Fee-Paid"] or "0") or 0
    if Settings.join_fee > 0 and (fee_paid < Settings.join_fee or not msg.Tags["Fee-Tx"]) then
      return reply(msg, "Join-Fee-Required", tostring(Settings.join_fee))
    end
    Members[wallet] = { joined_at = msg.Timestamp, fee_paid = fee_paid,
                        fee_tx = msg.Tags["Fee-Tx"], settings = {} }
    reply(msg, "Joined", "welcome")
  end)

-- Govern: owner or member action over the dato (extensible).
Handlers.add("Govern",
  Handlers.utils.hasMatchingTag("Action", "Govern"),
  function(msg)
    if not (is_owner(msg.From) or Members[msg.From]) then
      return reply(msg, "Govern-Error", "not a member or owner")
    end
    local act = msg.Tags["Govern-Action"]
    if act == "set_open_join" and is_owner(msg.From) then
      Settings.open_join = (msg.Tags["Value"] ~= "false")
    elseif act == "remove_member" and is_owner(msg.From) then
      Members[msg.Tags["Wallet"] or ""] = nil
    else
      return reply(msg, "Govern-Error", "unknown or unauthorized action")
    end
    reply(msg, "Governed", act)
  end)

-- Commit: record data at a permanence tier. The name declares the tier; IMMUTABLE
-- is hash-locked (re-commit with a different sha256 is rejected); IMMORTAL carries
-- the Arweave tx id (Proof); MUTABLE bumps a version.
Handlers.add("Commit",
  Handlers.utils.hasMatchingTag("Action", "Commit"),
  function(msg)
    if not (is_owner(msg.From) or Members[msg.From]) then
      return reply(msg, "Commit-Error", "not a member or owner")
    end
    local name = msg.Tags["Name"]
    local tier = msg.Tags["Tier"] or Settings.default_tier
    local sha  = msg.Tags["Sha256"]
    if not name or not sha or not TIERS[tier] then return reply(msg, "Commit-Error", "need Name, Sha256, valid Tier") end
    local prev = Records[name]
    if tier == "immutable" and prev and prev.tier == "immutable" and prev.sha256 ~= sha then
      return reply(msg, "Commit-Error", "immutable lock: sha256 mismatch")
    end
    local version = (prev and prev.tier == "mutable") and (prev.version + 1) or 1
    Records[name] = {
      sha256 = sha, tier = tier, proof = msg.Tags["Proof"],
      content_type = msg.Tags["Content-Type"] or "application/octet-stream", version = version,
    }
    Names[name] = { controller = msg.From, proof = msg.Tags["Proof"] }
    reply(msg, "Committed", name .. " v" .. tostring(version))
  end)

-- Info: read-only snapshot.
Handlers.add("Info",
  Handlers.utils.hasMatchingTag("Action", "Info"),
  function(msg)
    local n = 0; for _ in pairs(Members) do n = n + 1 end
    ao.send({ Target = msg.From, Action = "Info-Response",
      Data = require("json").encode({ owner = Owner, deployer = Deployer,
        settings = Settings, members = n, records = (function() local c=0; for _ in pairs(Records) do c=c+1 end; return c end)() }) })
  end)
