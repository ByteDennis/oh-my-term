return {
  {
    "folke/tokyonight.nvim",
    opts = { style = "night" },
  },

  {
    "LazyVim/LazyVim",
    opts = { colorscheme = "tokyonight" },
  },

  {
    -- 保留 LazyVim 默认的 bufferline。
    -- Windows 分支把它禁掉是因为那边要用顶栏显示带名字的 tab（herdr 模拟层），
    -- 这边 tab 由真 herdr 管，顶栏还给 buffer 列表更有用。
    "akinsho/bufferline.nvim",
    opts = {
      options = {
        always_show_bufferline = true,
      },
    },
  },
}
