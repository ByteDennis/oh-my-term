-- Workbench: a herdr-compatible control layer for Neovim.
--
-- On Linux the real herdr owns the C-a prefix and Neovim never sees those keys.
-- On Windows there is no herdr, so this module reproduces the same key semantics
-- on top of Neovim's own primitives:
--
--     herdr tab   -> Neovim tabpage
--     herdr pane  -> Neovim window
--     herdr agent -> terminal buffer
--
-- The point is that your fingers do not need to know which platform they are on.

local M = {}

M.prefix = "<C-a>"

-- >>> true when this layer should own the prefix key <<< --
function M.enabled()
  -- vim.g.workbench is an explicit override, useful for testing on Linux.
  if vim.g.workbench ~= nil then
    return vim.g.workbench == true
  end
  return vim.fn.has("win32") == 1
end

-- >>> register one prefixed key in both normal and terminal mode <<< --
local function pmap(key, fn, desc)
  local opts = { desc = "workbench: " .. desc, silent = true }
  vim.keymap.set("n", M.prefix .. key, fn, opts)
  -- Agents and shells live in terminal buffers, so the prefix has to work from
  -- terminal-insert mode too. Leave insert first, then run the same function.
  -- Both modes call the identical Lua function, so behaviour cannot drift.
  vim.keymap.set("t", M.prefix .. key, function()
    vim.cmd("stopinsert")
    vim.schedule(fn)
  end, opts)
end

-- >>> call into snacks.nvim, warning instead of erroring when it is missing <<< --
local function snacks(fn)
  return function()
    local ok, S = pcall(require, "snacks")
    if not ok then
      vim.notify("workbench: snacks.nvim is not available", vim.log.levels.WARN)
      return
    end
    fn(S)
  end
end

-- >>> install every prefixed binding <<< --
function M.setup()
  if not M.enabled() then
    return
  end

  local tabline = require("workbench.tabline")
  local session = require("workbench.session")

  -- Splits. Same keys as herdr split_vertical / split_horizontal.
  pmap("|", function() vim.cmd.vsplit() end, "split vertical")
  pmap("-", function() vim.cmd.split() end, "split horizontal")

  -- Pane focus. Same keys as herdr focus_pane_*.
  pmap("h", function() vim.cmd.wincmd("h") end, "focus left")
  pmap("j", function() vim.cmd.wincmd("j") end, "focus down")
  pmap("k", function() vim.cmd.wincmd("k") end, "focus up")
  pmap("l", function() vim.cmd.wincmd("l") end, "focus right")

  -- Tabs. Same keys as herdr new_tab / rename_tab / close_tab.
  pmap("c", function() vim.cmd.tabnew() end, "new tab")
  pmap("r", function() tabline.rename() end, "rename tab")
  pmap("q", function() vim.cmd.tabclose() end, "close tab")
  pmap("<C-h>", function() vim.cmd.tabprevious() end, "previous tab")
  pmap("<C-l>", function() vim.cmd.tabnext() end, "next tab")

  -- Jump to tab by number, like herdr switch_tab (prefix+1..9).
  for i = 1, 9 do
    pmap(tostring(i), function()
      -- Silently ignore when that tab does not exist, instead of erroring.
      if i <= vim.fn.tabpagenr("$") then
        vim.cmd(i .. "tabnext")
      end
    end, "go to tab " .. i)
  end

  -- Panes. herdr close_pane / zoom.
  pmap("w", function() vim.cmd.close() end, "close pane")
  pmap("z", snacks(function(S) S.zen.zoom() end), "toggle zoom")

  -- Pane resize. herdr resize_mode.
  pmap("J", function() vim.cmd("resize -5") end, "shrink height")
  pmap("K", function() vim.cmd("resize +5") end, "grow height")

  -- Pickers. Mirrors the three custom herdr commands in config.toml, which use
  -- the same letters: C-p command palette, C-f file viewer, s workspace picker.
  pmap("s", snacks(function(S) S.picker.projects() end), "workspace picker")
  pmap("<C-p>", snacks(function(S) S.picker.commands() end), "command palette")
  pmap("<C-f>", snacks(function(S) S.explorer() end), "file viewer")

  -- Open an agent in a bottom pane.
  pmap("a", snacks(function(S)
    S.terminal(nil, { win = { position = "bottom", height = 0.4 } })
  end), "agent pane")

  -- Session control. See workbench.session for why this matters on Windows.
  pmap("d", function() session.save({ notify = true }) end, "save session now")

  -- Copy mode. In a terminal buffer this is just leaving terminal-insert mode.
  vim.keymap.set("t", M.prefix .. "[", "<C-\\><C-n>", { desc = "workbench: copy mode" })

  -- Neovim's native C-a increments a number. The prefix swallows it, so press it
  -- twice to get it back. This is the same trick as tmux's `bind C-a send-prefix`.
  vim.keymap.set("n", M.prefix .. M.prefix, "<C-a>", { desc = "workbench: increment number" })

  tabline.setup()
end

return M
