-- UI overrides.

return {
  {
    -- LazyVim ships bufferline to show BUFFERS across the top. The workbench
    -- layer needs that row for TABS instead, with names and double-click rename,
    -- which bufferline cannot do. One of the two has to go.
    "akinsho/bufferline.nvim",
    enabled = false,
  },

  {
    "folke/tokyonight.nvim",
    opts = { style = "night" },
  },

  {
    "LazyVim/LazyVim",
    opts = {
      colorscheme = "tokyonight",
    },
  },
}
