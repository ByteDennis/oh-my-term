-- 会话持久化。
--
-- 和 Windows 分支的区别：这台机器上 herdr 会把 pane 一直挂着，所以「进程被杀」
-- 不是常态，定时保存的间隔可以放宽。但 nvim 自己的窗口布局、打开的 buffer、
-- tab 名字仍然只存在于 nvim 进程里，herdr 救不了，所以这一层还是要有。
--
-- 一个坑：`:mksession` 不保存 tab 作用域变量，所以 vim.t.tabname 会丢。
-- 解决办法是写一个 sidecar JSON 放在 session 文件旁边，source 完再贴回去。

local M = {}

local uv = vim.uv or vim.loop

M.config = {
  dir = vim.fs.normalize(vim.fn.stdpath("state") .. "/sessions"),
  interval = 180 * 1000,
  debounce = 2 * 1000,
}

-- 首次恢复尝试结束前不允许自动保存，否则启动画面会把好好的 session 覆盖掉
local armed = false
local timer = nil
local debounce_timer = nil

-- >>> 把当前工作目录压成一个合法文件名 <<< --
local function key()
  return (vim.fs.normalize(vim.fn.getcwd()):gsub("[:/\\]", "%%"))
end

local function session_path()
  return M.config.dir .. "/" .. key() .. ".vim"
end

local function meta_path()
  return M.config.dir .. "/" .. key() .. ".json"
end

-- >>> 当前 buffer 里有没有值得保存的东西 <<< --
local function worth_saving()
  for _, buf in ipairs(vim.api.nvim_list_bufs()) do
    if vim.api.nvim_buf_is_loaded(buf) and vim.bo[buf].buflisted then
      if vim.api.nvim_buf_get_name(buf) ~= "" and vim.bo[buf].buftype == "" then
        return true
      end
    end
  end
  return false
end

-- >>> 把 tab 名字写进 sidecar <<< --
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

-- >>> 读回 tab 名字并贴到恢复出来的 tabpage 上 <<< --
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

-- >>> 写 session 文件和 sidecar <<< --
function M.save(opts)
  opts = opts or {}

  -- 手动保存随时允许；自动保存要等首次恢复结束
  if not opts.force and (not armed or not worth_saving()) then
    return false
  end

  vim.fn.mkdir(M.config.dir, "p")

  local ok, err = pcall(vim.cmd, "mksession! " .. vim.fn.fnameescape(session_path()))
  if not ok then
    vim.notify("session 保存失败: " .. tostring(err), vim.log.levels.WARN)
    return false
  end

  save_meta()

  if opts.notify then
    vim.notify("session 已保存", vim.log.levels.INFO)
  end
  return true
end

-- >>> 恢复当前目录对应的 session <<< --
function M.restore()
  if vim.fn.filereadable(session_path()) == 0 then
    return false
  end

  if not pcall(vim.cmd, "silent! source " .. vim.fn.fnameescape(session_path())) then
    return false
  end

  load_meta()
  vim.cmd.redrawtabline()
  return true
end

-- >>> 布局变化后延迟保存，把连续的变化合并成一次 <<< --
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

function M.clear()
  os.remove(session_path())
  os.remove(meta_path())
  vim.notify("session 已清除", vim.log.levels.INFO)
end

function M.setup(opts)
  M.config = vim.tbl_extend("force", M.config, opts or {})

  -- tabpages 是让布局能整体回来的关键。
  -- terminal 故意不存：herdr 下 agent 跑在 herdr 的 pane 里，nvim 里恢复一个
  -- 死掉的 shell 比不恢复更糟。
  vim.o.sessionoptions = "buffers,curdir,folds,help,tabpages,winsize,winpos"

  local group = vim.api.nvim_create_augroup("WorkbenchSession", { clear = true })

  vim.api.nvim_create_autocmd("VimEnter", {
    group = group,
    nested = true,
    callback = function()
      -- 只有裸 `nvim` 才自动恢复。指名打开某个文件时显然不是这个意图。
      if vim.fn.argc() == 0 and vim.g.workbench_restore ~= false then
        M.restore()
      end
      armed = true
      if not timer then
        timer = uv.new_timer()
        timer:start(M.config.interval, M.config.interval, vim.schedule_wrap(function()
          M.save()
        end))
      end
    end,
  })

  vim.api.nvim_create_autocmd("VimLeavePre", {
    group = group,
    callback = function()
      M.save()
    end,
  })

  vim.api.nvim_create_autocmd({ "TabNew", "TabClosed", "BufWritePost" }, {
    group = group,
    callback = save_soon,
  })

  vim.api.nvim_create_user_command("SessionSave", function()
    M.save({ notify = true, force = true })
  end, { desc = "立即保存 session" })

  vim.api.nvim_create_user_command("SessionRestore", function()
    if not M.restore() then
      vim.notify("这个目录没有 session", vim.log.levels.WARN)
    end
  end, { desc = "恢复 session" })

  vim.api.nvim_create_user_command("SessionClear", function()
    M.clear()
  end, { desc = "删除当前目录的 session" })
end

return M
