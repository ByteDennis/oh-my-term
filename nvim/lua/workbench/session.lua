-- Crash-safe session persistence.
--
-- Why this is not just persistence.nvim:
--
-- Every save-on-exit scheme hangs off VimLeavePre. A Windows forced restart never
-- gives Neovim a chance to run it, so the session file is whatever it was when you
-- last quit cleanly, which may be days old. Two changes fix that:
--
--   1. Autosave on a timer, so an unexpected death costs at most `interval` seconds.
--   2. Autosave on layout changes (new tab, closed tab, written buffer), so the
--      expensive-to-rebuild parts are captured the moment they change.
--
-- Tab names need separate handling: `:mksession` does not persist tab-scoped
-- variables, so vim.t.tabname is written to a sidecar JSON file next to the
-- session and re-applied after the session is sourced.

local M = {}

local uv = vim.uv or vim.loop

M.config = {
  dir = vim.fs.normalize(vim.fn.stdpath("state") .. "/sessions"),
  interval = 60 * 1000, -- autosave period in milliseconds
  debounce = 2 * 1000,  -- wait this long after a layout change before saving
}

-- Set once the initial restore attempt is finished. Nothing is allowed to
-- autosave before then, otherwise an empty startup screen would overwrite a
-- perfectly good session.
local armed = false
local timer = nil
local debounce_timer = nil

-- >>> turn the current working directory into a safe file name <<< --
local function key()
  local cwd = vim.fs.normalize(vim.fn.getcwd())
  -- Windows paths contain a drive colon and backslashes; none of them are legal
  -- in a file name, so flatten every separator to a single character.
  return (cwd:gsub("[:/\\]", "%%"))
end

local function session_path()
  return M.config.dir .. "/" .. key() .. ".vim"
end

local function meta_path()
  return M.config.dir .. "/" .. key() .. ".json"
end

-- >>> true when the current buffers are worth saving <<< --
local function worth_saving()
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(buf) and vim.bo[buf].buflisted then
      local name = vim.api.nvim_buf_get_name(buf)
      if name ~= "" and vim.bo[buf].buftype == "" then
        return true
      end
    end
  end
  return false
end

-- >>> write tab names to the sidecar file <<< --
local function save_meta()
  local names = {}
  for i, handle in ipairs(vim.api.nvim_list_tabpages()) do
    local ok, name = pcall(vim.api.nvim_tabpage_get_var, handle, "tabname")
    if ok and type(name) == "string" and name ~= "" then
      names[tostring(i)] = name
    end
  end

  local fd = io.open(meta_path(), "w")
  if not fd then
    return
  end
  fd:write(vim.json.encode({ tabnames = names, saved_at = os.time() }))
  fd:close()
end

-- >>> read tab names back and re-apply them to the restored tabpages <<< --
local function load_meta()
  if vim.fn.filereadable(meta_path()) == 0 then
    return
  end

  local ok, decoded = pcall(vim.json.decode, table.concat(vim.fn.readfile(meta_path()), "\n"))
  if not ok or type(decoded) ~= "table" or type(decoded.tabnames) ~= "table" then
    return
  end

  for i, handle in ipairs(vim.api.nvim_list_tabpages()) do
    local name = decoded.tabnames[tostring(i)]
    if name then
      pcall(vim.api.nvim_tabpage_set_var, handle, "tabname", name)
    end
  end
end

-- >>> write the session file and its sidecar <<< --
function M.save(opts)
  opts = opts or {}

  -- Manual saves are always allowed; automatic ones wait until restore finished.
  if not opts.force and not armed then
    return false
  end
  if not opts.force and not worth_saving() then
    return false
  end

  vim.fn.mkdir(M.config.dir, "p")

  local ok, err = pcall(vim.cmd, "mksession! " .. vim.fn.fnameescape(session_path()))
  if not ok then
    vim.notify("workbench: session save failed: " .. tostring(err), vim.log.levels.WARN)
    return false
  end

  save_meta()

  if opts.notify then
    vim.notify("workbench: session saved", vim.log.levels.INFO)
  end
  return true
end

-- >>> restore the session for the current directory <<< --
function M.restore()
  if vim.fn.filereadable(session_path()) == 0 then
    return false
  end

  -- Suppress the noise a session source normally produces.
  local ok = pcall(vim.cmd, "silent! source " .. vim.fn.fnameescape(session_path()))
  if not ok then
    return false
  end

  load_meta()
  vim.cmd.redrawtabline()
  return true
end

-- >>> queue a save shortly after a layout change, coalescing rapid changes <<< --
local function save_soon()
  if not armed then
    return
  end
  if debounce_timer then
    debounce_timer:stop()
    debounce_timer:close()
  end
  debounce_timer = uv.new_timer()
  debounce_timer:start(M.config.debounce, 0, vim.schedule_wrap(function()
    M.save()
  end))
end

-- >>> start the periodic autosave timer <<< --
local function start_timer()
  if timer then
    return
  end
  timer = uv.new_timer()
  timer:start(M.config.interval, M.config.interval, vim.schedule_wrap(function()
    M.save()
  end))
end

-- >>> delete the session for the current directory <<< --
function M.clear()
  os.remove(session_path())
  os.remove(meta_path())
  vim.notify("workbench: session cleared", vim.log.levels.INFO)
end

function M.setup(opts)
  M.config = vim.tbl_extend("force", M.config, opts or {})

  -- `tabpages` is what makes the herdr-style tab layout come back at all.
  -- `terminal` is deliberately absent: restoring dead shells is worse than useless.
  vim.o.sessionoptions = "buffers,curdir,folds,help,tabpages,winsize,winpos"

  local group = vim.api.nvim_create_augroup("WorkbenchSession", { clear = true })

  vim.api.nvim_create_autocmd("VimEnter", {
    group = group,
    nested = true,
    callback = function()
      -- Only auto-restore a bare `nvim`. If the user asked for a specific file,
      -- that is what they want to see.
      local started_bare = vim.fn.argc() == 0 and vim.g.workbench_restore ~= false
      if started_bare then
        M.restore()
      end
      armed = true
      start_timer()
    end,
  })

  -- Cheap insurance for the ordinary clean exit.
  vim.api.nvim_create_autocmd("VimLeavePre", {
    group = group,
    callback = function()
      M.save()
    end,
  })

  -- Layout changes are the expensive things to lose, so capture them promptly
  -- rather than waiting for the next timer tick.
  vim.api.nvim_create_autocmd({ "TabNew", "TabClosed", "BufWritePost" }, {
    group = group,
    callback = save_soon,
  })

  vim.api.nvim_create_user_command("SessionSave", function()
    M.save({ notify = true, force = true })
  end, { desc = "Save the workbench session now" })

  vim.api.nvim_create_user_command("SessionRestore", function()
    if not M.restore() then
      vim.notify("workbench: no session for this directory", vim.log.levels.WARN)
    end
  end, { desc = "Restore the workbench session" })

  vim.api.nvim_create_user_command("SessionClear", function()
    M.clear()
  end, { desc = "Delete the workbench session for this directory" })
end

return M
