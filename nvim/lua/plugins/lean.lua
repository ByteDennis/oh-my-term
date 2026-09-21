-- 内存与启动预算。
--
-- nvim 本身很便宜，贵的是 language server：每个都是独立进程，
-- typescript-language-server、rust-analyzer 在大工程上动辄几百 MB 到 1 GB 以上。
-- 这里控制的是「同时跑着几个 server」，不是 nvim 自己的堆。

return {
  {
    "williamboman/mason.nvim",
    opts = {
      -- 留空，用 :Mason 按需手装。
      -- 也完全可以不用 mason，自己用 npm/pip 把 server 装到 PATH 上，
      -- nvim-lspconfig 一样找得到。见 docs/herdr.md。
      ensure_installed = {},
    },
  },

  {
    "nvim-treesitter/nvim-treesitter",
    opts = {
      ensure_installed = {
        "bash", "c", "diff", "json", "lua", "luadoc", "markdown",
        "markdown_inline", "python", "query", "toml", "vim", "vimdoc", "yaml",
      },
    },
  },

  {
    "folke/snacks.nvim",
    opts = {
      bigfile = {
        -- 大文件里关掉 treesitter / LSP / 折叠，
        -- 否则内存占用会跟文件大小成正比
        enabled = true,
        size = 1024 * 1024,
      },
    },
  },
}
