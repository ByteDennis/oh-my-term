-- Loaded by LazyVim after its own autocmds.

local group = vim.api.nvim_create_augroup("WorkbenchMisc", { clear = true })

-- >>> drop into insert mode when entering a terminal buffer <<< --
vim.api.nvim_create_autocmd({ "TermOpen", "BufEnter" }, {
  group = group,
  pattern = "term://*",
  callback = function()
    vim.cmd("startinsert")
  end,
})
