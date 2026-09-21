-- LazyVim 在插件启动前加载这个文件。
-- 只放和 LazyVim 默认值不同的选项。

local opt = vim.opt

opt.colorcolumn = "80"
opt.scrolloff = 3   -- LazyVim 默认是 4
opt.showtabline = 2
opt.swapfile = false
opt.hlsearch = false
opt.mouse = "a"

-- relativenumber / shiftwidth=2 / splitbelow / splitright / termguicolors
-- LazyVim 默认就是想要的值，不用重复写。

-- herdr 和现代终端都支持 OSC 52，所以不需要 xclip 也能把 yank 送到系统剪贴板。
-- 这一条在 `herdr --remote` 走 SSH 的场景下尤其重要：远端机器上根本没有 X。
opt.clipboard = "unnamedplus"

if vim.env.SSH_TTY or vim.env.HERDR_ENV then
  vim.g.clipboard = {
    name = "OSC52",
    copy = {
      ["+"] = require("vim.ui.clipboard.osc52").copy("+"),
      ["*"] = require("vim.ui.clipboard.osc52").copy("*"),
    },
    paste = {
      -- OSC 52 的读取在多数终端里被禁用（安全考虑），所以粘贴回落到寄存器本身
      ["+"] = function() return vim.split(vim.fn.getreg('"'), "\n") end,
      ["*"] = function() return vim.split(vim.fn.getreg('"'), "\n") end,
    },
  }
end
