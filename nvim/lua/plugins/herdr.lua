-- herdr 相关的接线。
--
-- 和 Windows 分支最大的不同：那边 nvim 要自己模拟一个 herdr（C-a 前缀层、
-- 带名字的 tabline）；这边真 herdr 就在外面，C-a 根本到不了 nvim，
-- 所以这里只做两件事：会话持久化，以及让 nvim 知道自己跑在 herdr 里。

return {
  {
    "folke/snacks.nvim",
    opts = function(_, opts)
      opts.explorer = { enabled = true }
      opts.picker = { enabled = true }
      opts.terminal = opts.terminal or {}

      if vim.env.HERDR_ENV then
        -- 在 herdr 里时把 nvim 自己的终端调弱一点：开 shell、跑 agent 都该用
        -- herdr 的 pane（真 PTY，关掉终端还活着），nvim 内的 :terminal 只留给
        -- 一次性短命令。
        opts.terminal.win = { position = "bottom", height = 0.25 }
      end

      return opts
    end,
  },

  {
    "LazyVim/LazyVim",
    opts = function()
      -- 必须在 VimEnter 之前配置好，否则首次恢复赶不上
      require("workbench.session").setup({
        -- herdr 会把 pane 挂着，进程被杀不是常态，间隔放宽到 3 分钟
        interval = 180 * 1000,
      })
    end,
  },
}
