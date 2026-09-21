-- LazyVim 自己的 autocmd 之后加载

local group = vim.api.nvim_create_augroup("LocalMisc", { clear = true })

-- >>> 进入终端 buffer 时直接进插入态 <<< --
vim.api.nvim_create_autocmd({ "TermOpen", "BufEnter" }, {
  group = group,
  pattern = "term://*",
  callback = function()
    vim.cmd("startinsert")
  end,
})
