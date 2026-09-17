-- Loaded by LazyVim on VeryLazy.
--
-- Three layers, and they must not overlap:
--   C-a + key   workbench layer (see lua/workbench/) -- herdr semantics
--   bare Ctrl   editor navigation
--   <Space>     editor features
--
-- LazyVim already provides C-h/j/k/l window movement, gd, K and the Space leader,
-- so those are not repeated here.

local map = vim.keymap.set

-- >>> run a snacks.nvim picker, warning instead of erroring if it is missing <<< --
local function picker(fn)
  return function()
    local ok, S = pcall(require, "snacks")
    if not ok then
      vim.notify("snacks.nvim is not available", vim.log.levels.WARN)
      return
    end
    fn(S)
  end
end

-- Bare Ctrl keys, carried over from the previous config. These deliberately
-- shadow the native paging commands, which is how they have been used for years.
map("n", "<C-p>", picker(function(S) S.picker.files() end), { desc = "Find files" })
map("n", "<C-f>", picker(function(S) S.picker.grep() end), { desc = "Grep" })
map("n", "<C-b>", picker(function(S) S.picker.buffers() end), { desc = "Buffers" })
map("n", "<C-n>", picker(function(S) S.explorer() end), { desc = "File tree" })
map("n", "<C-s>", ":%s/", { desc = "Substitute" })

-- Leader layer. These keep the old bindings rather than the LazyVim <leader>c*
-- equivalents, because the muscle memory is already there.
map("n", "<leader>t", picker(function(S)
  S.terminal(nil, { win = { position = "bottom", height = 0.3 } })
end), { desc = "Terminal" })

map("t", "<Esc>", "<C-\\><C-n>", { desc = "Terminal normal mode" })

map("n", "<leader>rn", vim.lsp.buf.rename, { desc = "Rename symbol" })
map("n", "<leader>.", vim.lsp.buf.code_action, { desc = "Code action" })
map("n", "<leader>f", function()
  require("conform").format({ lsp_fallback = true })
end, { desc = "Format" })

-- Operator-pending shortcuts for start and end of line.
map("o", "H", "^", { silent = true })
map("o", "L", "$", { silent = true })
