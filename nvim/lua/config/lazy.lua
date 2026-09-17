-- Bootstrap lazy.nvim, then LazyVim, then this repo's own plugin specs.

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"

if not (vim.uv or vim.loop).fs_stat(lazypath) then
  local out = vim.fn.system({
    "git", "clone", "--filter=blob:none",
    "https://github.com/folke/lazy.nvim.git", "--branch=stable", lazypath,
  })
  if vim.v.shell_error ~= 0 then
    vim.api.nvim_echo({
      { "Failed to clone lazy.nvim:\n", "ErrorMsg" },
      { out, "WarningMsg" },
    }, true, {})
    vim.fn.getchar()
    os.exit(1)
  end
end

vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
  spec = {
    { "LazyVim/LazyVim", import = "lazyvim.plugins" },
    { import = "plugins" },
  },
  defaults = { lazy = true, version = false },
  install = { colorscheme = { "tokyonight" } },
  checker = {
    -- Do not check for updates in the background. On a 16 GB machine there is no
    -- reason to spend memory and network on this; run :Lazy update by hand.
    enabled = false,
  },
  change_detection = { notify = false },
  performance = {
    rtp = {
      -- Disabling unused runtime plugins measurably shortens startup.
      disabled_plugins = {
        "gzip", "tarPlugin", "tohtml", "tutor", "zipPlugin",
        "netrwPlugin", "matchit", "matchparen",
      },
    },
  },
})
