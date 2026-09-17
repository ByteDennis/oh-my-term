-- Memory and startup budget for a 16 GB machine.
--
-- Neovim itself is cheap. Language servers are not: each one is a separate
-- process, and a few of them (typescript, rust-analyzer, gopls on a big module)
-- routinely take 500 MB to 1.5 GB on their own. The rules here are about keeping
-- the number of concurrently running servers small, not about Neovim's own heap.

return {
  {
    "williamboman/mason.nvim",
    opts = {
      -- Install servers explicitly with :Mason instead of letting an import pull
      -- in a long list. Every extra server is another resident process.
      ensure_installed = {},
    },
  },

  {
    "nvim-treesitter/nvim-treesitter",
    opts = {
      -- Parsers are compiled per language and loaded per buffer. Keeping the list
      -- short also avoids needing a C toolchain for languages you never open.
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
        -- Turn off treesitter, LSP and folds in large files rather than letting
        -- them consume memory proportional to file size.
        enabled = true,
        size = 1024 * 1024, -- 1 MB
      },
    },
  },
}
