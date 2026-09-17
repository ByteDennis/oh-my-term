-- Loaded by LazyVim before plugins start.
-- Only options that differ from the LazyVim defaults belong here.

local opt = vim.opt

opt.colorcolumn = "80"  -- carried over from the previous config
opt.scrolloff = 3       -- LazyVim defaults to 4
opt.showtabline = 2     -- always visible; the workbench tabline lives here
opt.swapfile = false
opt.hlsearch = false
opt.mouse = "a"         -- required for the clickable tabline

-- LazyVim already sets relativenumber, shiftwidth=2, splitbelow, splitright,
-- termguicolors and expandtab the way this config wants them.

if vim.fn.has("win32") == 1 then
  -- Without this, :terminal and every :! call open cmd.exe. Point them at Git
  -- Bash so that shell behaviour matches the Linux branch.
  --
  -- If Git is installed elsewhere, change this one path.
  local bash = "C:/Program Files/Git/bin/bash.exe"
  if vim.fn.executable(bash) == 1 then
    opt.shell = bash
    opt.shellcmdflag = "-c"
    opt.shellredir = ">%s 2>&1"
    opt.shellpipe = "2>&1| tee"
    opt.shellquote = ""
    opt.shellxquote = ""
  end
end
