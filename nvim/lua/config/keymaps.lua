-- LazyVim 在 VeryLazy 时加载这个文件。
--
-- 三层，互不重叠：
--   C-a + 键   herdr 接管，nvim 根本收不到（所以这里一条都不能写）
--   裸 Ctrl    编辑器导航
--   <Space>    编辑器功能
--
-- LazyVim 自带的 C-h/j/k/l 窗口移动、gd、K、Space leader 不重复写。

local map = vim.keymap.set

-- >>> 调 snacks.nvim 的 picker，缺失时给警告而不是报错 <<< --
local function picker(fn)
  return function()
    local ok, S = pcall(require, "snacks")
    if not ok then
      vim.notify("snacks.nvim 不可用", vim.log.levels.WARN)
      return
    end
    fn(S)
  end
end

-- 裸 Ctrl 层，沿用你原来的键。这几个故意盖掉了原生翻页，已经用了很多年。
map("n", "<C-p>", picker(function(S) S.picker.files() end), { desc = "查找文件" })
map("n", "<C-f>", picker(function(S) S.picker.grep() end), { desc = "全局搜索" })
map("n", "<C-b>", picker(function(S) S.picker.buffers() end), { desc = "Buffer 列表" })
map("n", "<C-n>", picker(function(S) S.explorer() end), { desc = "文件树" })
map("n", "<C-s>", ":%s/", { desc = "全文替换（起手）" })

-- leader 层，保留你原来的键而不是 LazyVim 默认的 <leader>c*
map("n", "<leader>t", picker(function(S)
  S.terminal(nil, { win = { position = "bottom", height = 0.3 } })
end), { desc = "终端" })

map("t", "<Esc>", "<C-\\><C-n>", { desc = "终端回 normal" })

map("n", "<leader>rn", vim.lsp.buf.rename, { desc = "重命名符号" })
map("n", "<leader>.", vim.lsp.buf.code_action, { desc = "Code action" })
map("n", "<leader>f", function()
  require("conform").format({ lsp_fallback = true })
end, { desc = "格式化" })

-- 数字自增的替代键。
-- herdr 没有 tmux 那种 send-prefix，所以 prefix=ctrl+a 时原生 <C-a> 在 herdr
-- 里彻底拿不到了。<C-x> 减一不受影响，只有加一需要换个键。
map({ "n", "v" }, "<leader>=", "<C-a>", { desc = "数字加一" })

-- 行首行尾的 operator-pending 映射
map("o", "H", "^", { silent = true })
map("o", "L", "$", { silent = true })
