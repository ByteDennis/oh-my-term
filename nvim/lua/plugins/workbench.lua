-- Wires the workbench layer into the LazyVim lifecycle.
--
-- It is a plugin spec only so that lazy.nvim runs it at the right time: after
-- snacks.nvim exists (the pickers need it) but early enough that the tabline and
-- session restore happen before the first screen is drawn.

return {
  {
    "folke/snacks.nvim",
    opts = {
      explorer = { enabled = true },
      picker = { enabled = true },
      terminal = { enabled = true },
      zen = { enabled = true },
    },
  },

  {
    "LazyVim/LazyVim",
    opts = function()
      -- Session restore has to be configured before VimEnter fires.
      require("workbench.session").setup({
        interval = 60 * 1000,
        debounce = 2 * 1000,
      })
    end,
  },

  {
    "folke/which-key.nvim",
    optional = true,
    opts = {
      spec = {
        -- Gives the C-a prefix a popup menu, which is the closest thing to
        -- herdr's own key hints.
        { "<C-a>", group = "workbench", mode = { "n", "t" } },
      },
    },
  },

  {
    "nvim-lua/plenary.nvim",
    lazy = false,
    priority = 100,
    config = function()
      require("workbench").setup()
    end,
  },
}
