-- herdr-style tabline: numbered, named, clickable tabs.
--
-- Neovim tabpages have no name of their own, so the display name is kept in a
-- tab-scoped variable (vim.t.tabname) and persisted by workbench.session.
--
-- The clickable regions use the `%N@Func@ ... %X` tabline syntax. Neovim calls
-- the function with (minwid, clicks, button, modifiers), which is what makes
-- double-click-to-rename possible.

local M = {}

-- >>> display name for tab number `tabnr` <<< --
function M.name(tabnr)
  local handle = vim.api.nvim_list_tabpages()[tabnr]
  if not handle then
    return "?"
  end

  local ok, name = pcall(vim.api.nvim_tabpage_get_var, handle, "tabname")
  if ok and type(name) == "string" and name ~= "" then
    return name
  end

  -- Fall back to the file shown in that tab's active window.
  local win = vim.api.nvim_tabpage_get_win(handle)
  local buf = vim.api.nvim_win_get_buf(win)
  local file = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(buf), ":t")
  return file ~= "" and file or "[No Name]"
end

-- >>> true when any buffer in this tab has unsaved changes <<< --
local function modified(tabnr)
  local handle = vim.api.nvim_list_tabpages()[tabnr]
  if not handle then
    return false
  end
  for _, win in ipairs(vim.api.nvim_tabpage_list_wins(handle)) do
    if vim.bo[vim.api.nvim_win_get_buf(win)].modified then
      return true
    end
  end
  return false
end

-- >>> prompt for a new name for tab `tabnr`, defaulting to the current one <<< --
function M.rename(tabnr)
  tabnr = tabnr or vim.fn.tabpagenr()
  local handle = vim.api.nvim_list_tabpages()[tabnr]
  if not handle then
    return
  end

  vim.ui.input({ prompt = "Tab name: ", default = M.name(tabnr) }, function(input)
    if input == nil then
      return -- cancelled
    end
    pcall(vim.api.nvim_tabpage_set_var, handle, "tabname", input)
    vim.cmd.redrawtabline()

    -- Names are part of the layout, so persist them straight away rather than
    -- waiting for the autosave timer.
    pcall(function()
      require("workbench.session").save()
    end)
  end)
end

-- >>> tabline mouse handler: click to switch, double-click to rename <<< --
function _G.workbench_tab_click(tabnr, clicks, button, _modifiers)
  if button == "l" and clicks == 2 then
    M.rename(tabnr)
  elseif button == "l" then
    vim.cmd(tabnr .. "tabnext")
  elseif button == "m" then
    vim.cmd(tabnr .. "tabclose")
  end
end

-- >>> build the tabline string <<< --
function _G.workbench_tabline()
  local parts = {}
  local current = vim.fn.tabpagenr()

  for i = 1, vim.fn.tabpagenr("$") do
    local hl = (i == current) and "%#TabLineSel#" or "%#TabLine#"
    local label = string.format("%s%%%d@v:lua.workbench_tab_click@ %d:%s", hl, i, i, M.name(i))
    label = label .. (modified(i) and " ● " or " ")
    parts[#parts + 1] = label .. "%X"
  end

  return table.concat(parts) .. "%#TabLineFill#"
end

function M.setup()
  vim.o.showtabline = 2
  vim.o.tabline = "%!v:lua.workbench_tabline()"
  vim.o.mouse = "a" -- required, otherwise the click regions do nothing
end

return M
