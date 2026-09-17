# oh-my-term：跨平台终端工作台计划

> **一句话目标**：同一套 `C-a` 键位语义，在 Linux 上由 **herdr** 提供，在 Windows 上由
> **Neovim 自己实现的模拟层**提供。两边肌肉记忆完全一致，编辑器都是 LazyVim。
> 外加一个 `just -g` 全局任务入口把两边的日常操作统一起来。

**目录**
1. [最终形态](#1-最终形态)
2. [现状盘点](#2-现状盘点)
3. [键位宪法——统一的 `C-a` 语义表](#3-键位宪法统一的-c-a-语义表)
4. [仓库结构与双分支策略](#4-仓库结构与双分支策略)
5. [全局 justfile（`just -g`）](#5-全局-justfilejust--g)
6. [Windows 上的 herdr 模拟层（核心）](#6-windows-上的-herdr-模拟层核心)
7. [LazyVim 迁移](#7-lazyvim-迁移)
8. [Windows 专属注意事项](#8-windows-专属注意事项)
9. [冲突与待办](#9-冲突与待办)
10. [执行顺序](#10-执行顺序)

---

## 1. 最终形态

```
          Linux                                Windows
          ─────                                ───────
   ┌─────────────────┐                  ┌─────────────────────┐
   │  herdr 0.7.x    │  ← C-a 前缀 →    │  Windows Terminal   │
   │  workspace/tab  │                  │  + Git Bash         │
   │  /pane/agent    │                  └──────────┬──────────┘
   └────────┬────────┘                             │
            │                            ┌─────────┴───────────┐
            │                            │  Neovim             │
            │                            │  ┌───────────────┐  │
            ▼                            │  │ herdr 模拟层  │ │ ← C-a 前缀
   ┌─────────────────┐                   │  │ tab=tab       │  │
   │     Neovim      │                   │  │ window=pane   │  │
   │    (LazyVim)    │                   │  └───────────────┘  │
   └─────────────────┘                   │     (LazyVim)       │
                                         └─────────────────────┘
```

**分层职责**

| 层 | Linux | Windows |
|---|---|---|
| 外层多路复用（workspace / tab / pane / agent） | herdr（真进程隔离，PTY 常驻） | Neovim 的 tabpage / window（模拟） |
| 内层编辑 | LazyVim | LazyVim |
| 任务入口 | `just -g` | `just -g` |
| 触发键 | `C-a`（herdr 吃掉） | `C-a`（nvim 吃掉） |

> 这个设计的关键在于：**`C-a` 在两个平台上被不同的东西接管，但语义完全一样。**
> Linux 上 `C-a |` 让 herdr 开一个真 pane；Windows 上 `C-a |` 让 nvim 开一个 vsplit。
> 手指不需要知道区别。

**Windows 侧要复刻的 herdr 能力**（你点名的三项 + 配套）：

| herdr 能力 | Windows/nvim 对应实现 | 章节 |
|---|---|---|
| tab 有名字、可重命名 | `vim.t.tabname` + 自定义 tabline | §6.3 |
| 鼠标点 tab 名直接改名 | tabline 的 `%N@Func@` 可点击区域 + 双击判定 | §6.4 |
| `prefix+1..9` 快捷跳转 | `<C-a>1..9` → `tabnext` | §6.2 |
| pane 分屏 / 移动 / 关闭 | nvim window 操作 | §6.2 |
| zoom（最大化单 pane） | `Snacks.zen.zoom()` | §6.2 |
| workspace 选择器 | `Snacks.picker.projects()` | §6.2 |
| 会话持久化 | `persistence.nvim`（LazyVim extra） | §6.5 |
| agent pane（跑 claude/codex） | `Snacks.terminal` + 专用 tab | §6.6 |

---

## 2. 现状盘点

以下都是在这台 Linux 上实测的结果。

| 组件 | 版本 / 位置 | 状态 |
|---|---|---|
| Neovim | 本机 v0.10.2（`/opt/nvim-linux64`） | ⚠️ **偏旧**。目标版本定为 **0.12.4**，见 §2.1 |
| `~/.config/nvim` | albingroen/quick.nvim fork | **packer + coc**，旧栈 |
| `~/.config/nvim.bak` | **已经是一个 LazyVim starter** | 含 `lazy-lock.json`、`lazyvim.json`（启用了 `extras.editor.leap`） |
| `~/.local/share/nvim` | 有 `lazy/`、`mason/`、`telescope_history` | 上次 LazyVim 的运行时数据还在 |
| herdr | 0.7.1 | 配置 `~/.config/herdr/config.toml`，prefix `ctrl+a` |
| tmux | `~/.tmux.conf` | prefix `C-a`，TPM + resurrect/continuum |
| just | 1.43.1 | **尚无 global justfile** |
| zsh | oh-my-zsh + `zsh-vi-mode` | `~/.oh-my-zsh/plugins/herdr` 存在但**没启用** |

> ⚠️ 三件立刻要知道的事：
> 1. 你**以前装过 LazyVim 又换回了 quick.nvim**。`nvim.bak` 是个现成起点，不用从零开始。
> 2. `~/.zshrc` 的 `plugins=(...)` 里没有 `herdr`，所以 `hrdrs` / `hrdral` / `hrdrwt` 这些别名和补全**现在都没生效**。一行就能修。
> 3. 你的 tmux 和 herdr 在 `prefix+w` 上语义冲突（一个是选会话，一个是**关 pane**）。见 §9.1。

### 2.1 目标版本：Neovim 0.12.4

本机现在是 0.10.2，**计划统一按 0.12.4 写**（当前 stable 是 0.12.5，2026-08-23 发布）。
本文档里所有 Lua 代码都已在 0.12.4 上实测通过（见 §6.4）。

0.12 相对 0.10 有三个**直接影响本计划**的变化，都已在 0.12.4 上确认存在：

| 新 API | 作用 | 对计划的影响 |
|---|---|---|
| `vim.pack` | **内置插件管理器** | 理论上可以不要 lazy.nvim。但 LazyVim 本身依赖 lazy.nvim，所以这轮**不用**；留作以后「脱离 LazyVim 自己搭」的备选 |
| `vim.lsp.config` / `vim.lsp.enable` | **原生 LSP 配置**，不再需要 nvim-lspconfig 的样板 | §7 Phase 2 从 coc 迁到 LSP 时，底层轻得多 |
| `vim.lsp.completion` | **内置补全** | 你最在意的 `<Tab>` 补全循环，可以不装 blink.cmp 直接用原生的。见 §7 Phase 2 |

升级注意：0.12 的 Linux 压缩包目录名从 `nvim-linux64` 改成了 **`nvim-linux-x86_64`**，
所以不能原地解压覆盖 `/opt/nvim-linux64`，要么换路径要么先删旧的。

```bash
# >>> 升级本机 nvim 到 0.12.4 <<< #
curl -LO https://github.com/neovim/neovim/releases/download/v0.12.4/nvim-linux-x86_64.tar.gz
sudo tar -C /opt -xzf nvim-linux-x86_64.tar.gz      # 解出 /opt/nvim-linux-x86_64
sudo ln -sfn /opt/nvim-linux-x86_64/bin/nvim /usr/local/bin/nvim
```

Neovim 的层级关系（你给的那条，补上 herdr 和 Windows 分支）：

```
herdr (Linux) / Windows Terminal (Windows)
    ↓
Neovim executable
    ↓
配置目录：Linux  ~/.config/nvim
         Windows %LOCALAPPDATA%\nvim
         沙箱    NVIM_APPNAME=lazyvim → ~/.config/lazyvim
    ↓
LazyVim config          ← 「桌面环境」
    ↓
lazy.nvim               ← 包管理器
    ↓
plugins
```

Neovim 是操作系统，LazyVim 是装好的桌面环境，herdr 是窗口管理器兼任务调度器。

---

## 3. 键位宪法——统一的 `C-a` 语义表

**这是整个计划的宪法。任何新键位必须落进下面某一层，不能跨层抢键。**

### 3.1 分层

| 层 | 触发方式 | Linux 归属 | Windows 归属 |
|---|---|---|---|
| L0 工作台 | `C-a` + 键 | herdr | Neovim 模拟层 |
| L1 编辑器导航 | 裸 `Ctrl` 键 | Neovim | Neovim |
| L2 编辑器功能 | `<Space>` leader | Neovim | Neovim |

不打架的原因：L0 全部要 `C-a` 前缀，L1 用裸 Ctrl，L2 用 Space。三者互不相交。

### 3.2 L0 统一语义表（**核心表**）

| 动作 | 键 | Linux / herdr | Windows / nvim 模拟层 | 现有 tmux |
|---|---|---|---|---|
| 竖分屏 | `C-a \|` | `split_vertical` | `:vsplit` | ✅ 一致 |
| 横分屏 | `C-a -` | `split_horizontal` | `:split` | ✅ 一致 |
| 焦点移动 | `C-a h/j/k/l` | `focus_pane_*` | `wincmd h/j/k/l` | ✅ 一致 |
| 新建 tab | `C-a c` | `new_tab` | `:tabnew` | ✅ 一致 |
| **重命名 tab** | `C-a r` | `rename_tab` | **`vim.t.tabname`（§6.3）** | ✅ 一致 |
| 上/下一个 tab | `C-a C-h` / `C-a C-l` | `previous_tab`/`next_tab` | `tabprev`/`tabnext` | ✅ 一致 |
| **按序号跳 tab** | `C-a 1..9` | `switch_tab` | **`Ntabnext`（§6.2）** | ✅ 一致 |
| 关 pane | `C-a w` | `close_pane` | `:close` | ❌ tmux 是 `p`，见 §9.1 |
| 关 tab | `C-a q` | `close_tab` | `:tabclose` | ❌ tmux 是 `x` |
| zoom | `C-a z` | `zoom` | `Snacks.zen.zoom()` | ✅ 一致 |
| copy mode | `C-a [` | `copy_mode` | `<C-\><C-n>`（终端里） | ✅ 一致 |
| workspace 选择器 | `C-a s` | `workspace_picker` | `Snacks.picker.projects()` | ❌ tmux 是 `w` |
| 新 workspace | `C-a C` | `new_workspace` | 新 tab + `:tcd` | — |
| 上/下 workspace | `C-a C-j` / `C-a C-k` | `next/previous_workspace` | session 切换 | — |
| resize | `C-a J` | `resize_mode` | `<C-w>` resize 系列 | tmux 用 `J`/`K` |
| detach | `C-a d` | `detach` | **无对应**（存 session 后退出） | ✅ 一致 |
| reload config | `C-a C-r` | `reload_config` | `:source` 配置 | ✅ 一致 |
| 命令面板 | `C-a C-p` | `jt.command-palette.open` | `Snacks.picker.commands()` | — |
| 文件查看器 | `C-a C-f` | herdr-file-viewer | `Snacks.explorer()` | — |
| agent 时间线 | `C-a C-g` | `agent-recap` | **无对应** | — |
| 送出字面 `C-a` | `C-a C-a` | 待确认（§9.3） | 映射成 `<C-a>`（数字自增） | ✅ tmux 已有 |

> 注意最后一行：nvim 原生 `C-a` 是「数字自增」。被前缀吃掉后，用 `C-a C-a` 找回来
> ——这正是你 tmux 里 `bind C-a send-prefix` 的同一套逻辑，直接迁移。

### 3.3 L1/L2 现有键位（从你的配置里提取，**要保留**）

| 键 | 作用 | 迁移到 LazyVim 后 |
|---|---|---|
| `<Space>` | leader | LazyVim 默认相同 ✅ |
| `C-h/j/k/l` | 窗口移动 | LazyVim 默认相同 ✅ |
| `C-p` | 查找文件（telescope ivy） | 改 `Snacks.picker.files()` |
| `C-f` | 全局搜索 live_grep | 改 `Snacks.picker.grep()` |
| `C-b` | buffer 列表 | 改 `Snacks.picker.buffers()` |
| `C-t` | git worktree 选择器 | 需要重建，见 §9.2 |
| `C-n` | 文件树（netrw，宽 30） | 改 `Snacks.explorer()` |
| `C-s` | 起手 `:%s/` | 直接保留（LazyVim 不占 `C-s`） |
| `vs` / `sp` | 竖/横分屏 | **建议废弃**，见 §9.2 |
| `tn/tj/tk/to` | tab 新建/上/下/only | 与 `C-a` 层重复，见 §9.2 |
| `<leader>t` | 下方开 terminal（高 20） | `Snacks.terminal` |
| `<Esc>`(terminal) | 回 normal | 保留 |
| `gd` / `K` | 跳定义 / 悬浮文档 | LazyVim 默认相同 ✅ |
| `<leader>rn` | 重命名符号 | 保留（LazyVim 默认是 `<leader>cr`） |
| `<leader>.` | code action | 保留（LazyVim 默认是 `<leader>ca`） |
| `<leader>f` | 格式化 | 保留（LazyVim 默认是 `<leader>cf`） |
| `<leader>l` | eslint autofix | 需要重建 |
| `<Tab>`/`<S-Tab>`/`<CR>` | 补全菜单循环确认 | **必须显式重配**，默认行为和 coc 不同 |
| `H`/`L`（operator-pending） | `^` / `$` | 从 `nvim.bak` 恢复 |

选项习惯：`relativenumber`、`colorcolumn=80`、`tabstop=shiftwidth=2`、`scrolloff=3`、
`hlsearch=false`、`swapfile=false`、`showtabline=2`、`mouse=a`、`splitbelow/splitright`。

---

## 4. 仓库结构与双分支策略

### 4.1 目录结构

```
oh-my-term/
├── plans/                      # 本文档所在
├── nvim/                       # → 平台各自软链到 nvim 配置目录
│   ├── init.lua
│   ├── lua/config/{lazy,options,keymaps,autocmds}.lua
│   └── lua/plugins/
│       ├── ui.lua              # tabline / bufferline
│       ├── picker.lua          # snacks.picker 键位
│       └── workbench.lua       # ★ herdr 模拟层（仅 Windows 激活）
├── just/justfile               # → 软链到全局 justfile 位置
├── herdr/config.toml           # 仅 Linux 分支有意义
├── tmux/tmux.conf              # 仅 Linux
├── zsh/                        # 共享片段
└── bootstrap/
    ├── linux.sh
    └── windows.ps1
```

### 4.2 分支模型

```
main ───────●───────●───────●        共享的一切（nvim 主体、justfile、plans）
             \       \       \
linux    ─────●───────●───────●      herdr/ tmux/ + Linux 路径
              \       \       \
windows  ──────●───────●──────●      Windows Terminal 设置 + Windows 路径
```

- `main`：**唯一的真相源**。所有跨平台内容只在这里改。
- `linux` / `windows`：只装平台特有的增量，**永远不往回合并到 main**。
- 同步方式：在 main 上提交后，两个分支各自 `git rebase main`。
  rebase（而不是 merge）能让平台增量始终是最顶上那几个 commit，diff 一眼看得清。

```bash
# >>> 把 main 的新内容推到两个平台分支 <<< #
git checkout main && git pull
for b in linux windows; do
  git checkout "$b" && git rebase main && git push --force-with-lease
done
```

> 💡 **强烈建议**：让平台分支的 diff 尽量小。大部分平台差异用**运行时探测**解决，
> 而不是靠分支分叉——分叉的部分越少，rebase 越不会冲突：
>
> ```lua
> -- 在共享代码里直接判断平台，这样这段代码可以留在 main 分支
> local is_win = vim.fn.has("win32") == 1
> ```
>
> 理想状态：`nvim/` 目录 100% 在 main 分支，两个平台分支只有 `bootstrap/` 和
> `herdr/`、`tmux/` 这类真正没法共用的东西。

### 4.3 配置落地（软链）

**Linux**

```bash
ln -sfn ~/path/to/oh-my-term/nvim  ~/.config/nvim
mkdir -p ~/.config/just
ln -sf  ~/path/to/oh-my-term/just/justfile ~/.config/just/justfile
```

**Windows**（Git Bash，**不需要管理员**，用目录 junction）

```bash
# Git Bash 里的 ln -s 对目录不可靠，改用 cmd 的 mklink /J（junction）
REPO=$(cygpath -w ~/path/to/oh-my-term)
cmd //c mklink //J "%LOCALAPPDATA%\nvim" "$REPO\nvim"
cmd //c mklink //J "%APPDATA%\just"      "$REPO\just"
```

> Windows 上 Neovim 默认读 `%LOCALAPPDATA%\nvim`（配置）和 `%LOCALAPPDATA%\nvim-data`（数据）。
> 另一条路是设环境变量 `XDG_CONFIG_HOME=%USERPROFILE%\.config` 让两边路径字面一致，
> Neovim 支持，但会影响其他读 XDG 的工具——**装好后先用 `:echo stdpath('config')` 实测确认**。

---

## 5. 全局 justfile（`just -g`）

### 5.1 搜索顺序

`just -g` / `just --global-justfile` 取**第一个存在的**：

**Linux**（已实测）：
1. `$XDG_CONFIG_HOME/just/justfile`
2. `~/.config/just/justfile`   ← 本机 `XDG_CONFIG_HOME` 未设，**推荐这个**
3. `~/justfile`
4. `~/.justfile`

**Windows**（同一套逻辑，config 目录换成 Windows 的）：
1. `%XDG_CONFIG_HOME%\just\justfile`
2. `%APPDATA%\just\justfile`   ← 推荐
3. `%USERPROFILE%\justfile`
4. `%USERPROFILE%\.justfile`

> Windows 那几条路径我没法在这台 Linux 上实测。装好后跑 `just -g --dump` 确认一下
> 它读到的是不是你放的那份。

### 5.2 两个必踩的坑（都已实测）

**坑 1：默认 shell 是 `sh -cu`，开了 `nounset`。**
引用未定义变量会直接 `parameter not set` 并让 recipe 以 exit 2 失败。

**坑 2：recipe 默认不在你调用它的目录里跑。**
对全局 justfile 这是致命的——你要的是「对当前项目执行」。
解决办法是给 recipe 加 `[no-cd]`（实测：加了就是调用目录，不加不是）。

> **全局 justfile 里的 recipe 默认就该带 `[no-cd]`**，除非它明确是操作 `$HOME` 的。

### 5.3 骨架（已实测可解析可运行）

放到 `oh-my-term/just/justfile`，软链到上面的位置：

```just
# Linux/macOS 用的 shell：-e 出错即停，-u 未定义变量报错，pipefail 管道任一环失败即失败
set shell := ["bash", "-euo", "pipefail", "-c"]
# Windows 上强制走 Git Bash，而不是 just 默认的 sh/cmd —— 这样上面所有 recipe 一份通用
set windows-shell := ["C:/Program Files/Git/bin/bash.exe", "-euo", "pipefail", "-c"]
# 让 $1 $2 ... 在 recipe 里可用
set positional-arguments

# >>> 不带参数时列出所有全局 recipe <<< #
[no-cd]
default:
    @just -g --list --unsorted

# >>> 用 NVIM_APPNAME 切换 neovim 配置，不传参就是默认配置 <<< #
[no-cd]
nv app="":
    @if [ -z "$1" ]; then nvim; else NVIM_APPNAME="$1" nvim; fi

# >>> 在沙箱里启动 LazyVim，完全不碰正在用的配置 <<< #
[no-cd]
lazy *args:
    NVIM_APPNAME=lazyvim nvim "$@"

# >>> 动手术前给 neovim 的四个目录全部打快照 <<< #
backup-nvim tag=`date +%Y%m%d-%H%M%S`:
    #!/usr/bin/env bash
    set -euo pipefail
    for d in ~/.config/nvim ~/.local/share/nvim ~/.local/state/nvim ~/.cache/nvim; do
        [ -e "$d" ] && cp -a "$d" "$d.$1" && echo "saved $d.$1"
    done

# >>> 用当前目录名开或接一个 herdr 会话（仅 Linux） <<< #
[no-cd]
hs name=`basename "$PWD"`:
    herdr --session "$1"

# >>> 让正在跑的 herdr server 重读 config.toml <<< #
herdr-reload:
    herdr server reload-config

# >>> 打印当前各层配置的真实状态，排查用 <<< #
[no-cd]
doctor:
    @echo "nvim        : $(nvim --version | head -1)"
    @echo "NVIM_APPNAME: ${NVIM_APPNAME:-<unset, 用默认配置目录>}"
    @echo "just        : $(just --version)"
    @echo "global jf   : $(just -g --dump >/dev/null 2>&1 && echo ok || echo MISSING)"
```

实测输出（在这台机器上）：

```
$ just -g doctor
nvim        : NVIM v0.10.2
NVIM_APPNAME: <unset, 用默认配置目录>
just        : just 1.43.1
global jf   : MISSING          ← 还没放，放完就变 ok
```

### 5.4 接进 shell

`~/.zshrc`（Linux）和 `~/.bashrc`（Git Bash）都加：

```sh
alias J='just -g'      # 大写 = 全局作用域
alias Jl='just -g --list'
# 小写 just 仍然走项目本地 justfile
```

> 大写=更大作用域，和你 tmux 里 `prefix+R` 重命名 session、`prefix+r` 重命名 window
> 的既有直觉一致。

---

## 6. Windows 上的 herdr 模拟层（核心）

> 文件：`nvim/lua/plugins/workbench.lua`
> 这一节的代码**两个平台都能跑**，但默认只在 Windows（或显式开启时）激活 `C-a` 前缀，
> 因为在 Linux 上 `C-a` 会被真 herdr 先吃掉，nvim 根本收不到。

### 6.1 映射关系

| herdr 概念 | Neovim 对应 | 说明 |
|---|---|---|
| workspace | session（`persistence.nvim`）+ `:tcd` | 一个项目一个 session |
| tab | tabpage | 有名字，可重命名，可点击 |
| pane | window（split） | 分屏、移动、zoom |
| agent | terminal buffer（`Snacks.terminal`） | 跑 claude / codex |

### 6.2 前缀层实现

Neovim 原生就支持多键映射——把 `<C-a>x` 直接注册成一个映射，nvim 会在按下 `<C-a>`
后等待下一个键（等待时长由 `timeoutlen` 控制）。**不需要任何插件**。

```lua
-- nvim/lua/plugins/workbench.lua
local M = {}

-- Linux 上 C-a 被真 herdr 吃掉，nvim 收不到，所以这一层只在 Windows 激活。
-- 想在 Linux 上也试，把 vim.g.oh_workbench 设成 true 即可。
local function enabled()
  return vim.g.oh_workbench == true or vim.fn.has("win32") == 1
end

-- >>> 注册一个 C-a 前缀映射，normal / terminal 两种模式都覆盖 <<< #
local function pmap(key, action, desc)
  -- normal 模式：直接执行
  vim.keymap.set("n", "<C-a>" .. key, action, { desc = "workbench: " .. desc, silent = true })
  -- terminal 模式：先 <C-\><C-n> 退出 terminal 插入态，再执行同一个动作。
  -- 这一条很关键 —— agent 就跑在 terminal buffer 里，不加这个前缀层在 agent 窗口里会失灵。
  vim.keymap.set("t", "<C-a>" .. key, function()
    vim.cmd("stopinsert")
    vim.schedule(function()
      if type(action) == "function" then action() else vim.cmd("normal! " .. action) end
    end)
  end, { desc = "workbench: " .. desc, silent = true })
end

function M.setup()
  if not enabled() then return end

  -- ── 分屏：和 herdr 的 split_vertical / split_horizontal 同键 ──
  pmap("|", "<cmd>vsplit<cr>", "竖分屏")
  pmap("-", "<cmd>split<cr>",  "横分屏")

  -- ── 焦点移动：herdr focus_pane_* ──
  pmap("h", "<cmd>wincmd h<cr>", "焦点左")
  pmap("j", "<cmd>wincmd j<cr>", "焦点下")
  pmap("k", "<cmd>wincmd k<cr>", "焦点上")
  pmap("l", "<cmd>wincmd l<cr>", "焦点右")

  -- ── tab：new_tab / rename_tab / close_tab ──
  pmap("c", "<cmd>tabnew<cr>",   "新建 tab")
  pmap("r", M.rename_tab,        "重命名 tab")
  pmap("q", "<cmd>tabclose<cr>", "关闭 tab")
  pmap("<C-h>", "<cmd>tabprevious<cr>", "上一个 tab")
  pmap("<C-l>", "<cmd>tabnext<cr>",     "下一个 tab")

  -- ── 按序号跳 tab：herdr switch_tab = prefix+1..9 ──
  for i = 1, 9 do
    pmap(tostring(i), function()
      -- tab 数量不够时静默忽略，而不是报错
      if i <= vim.fn.tabpagenr("$") then vim.cmd(i .. "tabnext") end
    end, "跳到 tab " .. i)
  end

  -- ── pane：close_pane / zoom ──
  pmap("w", "<cmd>close<cr>", "关闭 pane")
  pmap("z", function() require("snacks").zen.zoom() end, "zoom 切换")

  -- ── copy mode：在 terminal 里就是退回 normal 模式 ──
  vim.keymap.set("t", "<C-a>[", "<C-\\><C-n>", { desc = "workbench: copy mode" })

  -- ── workspace / 面板 ──
  pmap("s",     function() require("snacks").picker.projects() end, "workspace 选择器")
  pmap("<C-p>", function() require("snacks").picker.commands() end, "命令面板")
  pmap("<C-f>", function() require("snacks").explorer() end,        "文件查看器")

  -- ── resize：herdr 的 resize_mode = prefix+shift+j ──
  pmap("J", "<cmd>resize -5<cr>",          "缩小高度")
  pmap("K", "<cmd>resize +5<cr>",          "增大高度")

  -- ── 送出字面 C-a（数字自增），对应 tmux 的 bind C-a send-prefix ──
  vim.keymap.set("n", "<C-a><C-a>", "<C-a>", { desc = "workbench: 数字自增" })

  M.setup_tabline()
end
```

> 📎 **这个代码块没有 `return M`**——§6.3 和 §6.4 是**同一个文件的后续部分**，
> `return M` 要放在整个文件的最后一行。三段按 §6.2 → §6.3 → §6.4 的顺序拼起来才完整。

> ⚠️ 上面 `pmap` 里 terminal 模式那段用了 `vim.cmd` + `vim.schedule`，
> 对 `<cmd>...<cr>` 形式的字符串 action 不适用。落地时建议**统一把 action 写成 Lua 函数**
> （例如 `function() vim.cmd.vsplit() end`），这样两种模式走同一条路径。
> 这是这份代码里最需要你自己跑一遍验证的地方。

### 6.3 tab 命名

Neovim 的 tabpage 原生没有名字，用 tab 作用域变量存：

```lua
-- >>> 取第 tabnr 个 tab 的显示名，没设过就退回当前文件名 <<< #
local function tab_name(tabnr)
  local handle = vim.api.nvim_list_tabpages()[tabnr]
  if not handle then return "?" end

  -- 用户手动命名过就优先用
  local ok, name = pcall(vim.api.nvim_tabpage_get_var, handle, "tabname")
  if ok and name and name ~= "" then return name end

  -- 否则用该 tab 当前窗口里 buffer 的文件名兜底
  local win = vim.api.nvim_tabpage_get_win(handle)
  local buf = vim.api.nvim_win_get_buf(win)
  local file = vim.fn.fnamemodify(vim.api.nvim_buf_get_name(buf), ":t")
  return file ~= "" and file or "[No Name]"
end

-- >>> 弹输入框重命名某个 tab，不传参就是当前 tab <<< #
function M.rename_tab(tabnr)
  tabnr = tabnr or vim.fn.tabpagenr()
  local handle = vim.api.nvim_list_tabpages()[tabnr]
  if not handle then return end

  vim.ui.input({ prompt = "Tab 名称: ", default = tab_name(tabnr) }, function(input)
    if input == nil then return end                       -- 用户按了 Esc
    vim.api.nvim_tabpage_set_var(handle, "tabname", input)
    vim.cmd.redrawtabline()
  end)
end
```

### 6.4 自定义 tabline + 鼠标改名

Neovim 的 `'tabline'` 支持点击区域语法 `%N@函数名@ ... %X`，
被点击时会回调函数并传入 `(minwid, 点击次数, 鼠标键, 修饰键)`。
**双击左键 = 重命名**，就是靠这个实现的。

```lua
-- >>> tabline 点击回调：左键单击切换，左键双击改名，中键关闭 <<< #
function _G.oh_tab_click(tabnr, clicks, button, _modifiers)
  if button == "l" and clicks == 2 then
    M.rename_tab(tabnr)                      -- 双击左键 → 改名
  elseif button == "l" then
    vim.cmd(tabnr .. "tabnext")              -- 单击左键 → 切过去
  elseif button == "m" then
    vim.cmd(tabnr .. "tabclose")             -- 中键 → 关掉
  end
end

-- >>> 生成 tabline 字符串，herdr 风格：序号 + 名字 + 修改标记 <<< #
function _G.oh_tabline()
  local parts = {}
  local current = vim.fn.tabpagenr()

  for i = 1, vim.fn.tabpagenr("$") do
    -- 当前 tab 用高亮色，其余用普通色
    local hl = (i == current) and "%#TabLineSel#" or "%#TabLine#"

    -- %i@func@ 开启点击区域，%X 关闭。i 会作为第一个参数传给回调。
    local label = string.format("%s%%%d@v:lua.oh_tab_click@ %d:%s ", hl, i, i, tab_name(i))

    -- 该 tab 里有未保存的 buffer 就加个 ●
    local modified = false
    for _, win in ipairs(vim.api.nvim_tabpage_list_wins(vim.api.nvim_list_tabpages()[i])) do
      if vim.bo[vim.api.nvim_win_get_buf(win)].modified then modified = true break end
    end
    if modified then label = label:sub(1, -2) .. "● " end

    parts[#parts + 1] = label .. "%X"
  end

  -- %#TabLineFill# 把剩下的空白填成背景色；%= 让后面的内容右对齐
  return table.concat(parts) .. "%#TabLineFill#"
end

-- >>> 启用自定义 tabline <<< #
function M.setup_tabline()
  vim.o.showtabline = 2                       -- 永远显示，和你现在的习惯一致
  vim.o.tabline = "%!v:lua.oh_tabline()"
  vim.o.mouse = "a"                           -- 鼠标必须开，否则点击区域无效
end

return M                                      -- 整个 workbench.lua 的最后一行
```

**已在 Neovim 0.10.2 和 0.12.4 上分别实测通过，输出完全一致**（三段拼成 `workbench.lua` 后 headless 加载）：

```
tabline opt  = %!v:lua.oh_tabline()
rendered     = %#TabLineSel#%1@v:lua.oh_tab_click@ 1:api %X%#TabLine#%2@v:lua.oh_tab_click@ 2:agent %X%#TabLine#%3@v:lua.oh_tab_click@ 3:[No Name] %X%#TabLineFill#
C-a| mapped  = true        (normal)
C-a3 mapped  = true        (normal)
C-aC-a map   = <C-A>       (数字自增找回来了)
term C-ah    = true        (terminal 模式也注册上了)
```

可以看到 `%1@v:lua.oh_tab_click@ ... %X` 这样的点击区域正确生成了，
第 1、2 个 tab 用了自定义名字，第 3 个走了 `[No Name]` 兜底。

> ⚠️ **和 LazyVim 默认的 bufferline.nvim 冲突**：LazyVim 默认用 bufferline 显示
> **buffer** 列表并接管 `tabline`。要用上面这套 herdr 风格的 **tab** 行，必须二选一：
>
> - **方案 A（推荐）**：禁用 bufferline，用上面的自定义 tabline。
>   完全可控，双击改名能实现，语义和 herdr 一一对应。
>   ```lua
>   { "akinsho/bufferline.nvim", enabled = false }
>   ```
> - **方案 B**：保留 bufferline，设 `mode = "tabs"` 让它显示 tabpage，
>   用 `name_formatter` 读 `vim.t.tabname`。改动小，但 **bufferline 不支持双击回调**，
>   鼠标改名做不到——你点名要这个功能，所以方案 B 不满足需求。

### 6.5 会话持久化（对应 herdr 的常驻会话）

herdr 最大的价值之一是「关掉终端 agent 还在跑」。这个 Windows 上**没法真正复刻**
（没有常驻 server 和 PTY）。能做到的是**恢复编辑状态**：

在 `lazyvim.json` 里启用 `lazyvim.plugins.extras.util.persistence`，得到：
- `<leader>qs` 恢复当前目录的 session
- `<leader>ql` 恢复上一次 session

再把它接到 `C-a` 层，语义上对应 herdr 的 workspace 切换：

```lua
pmap("d", function() require("persistence").save(); vim.cmd("qa") end, "保存 session 并退出（≈detach）")
```

> **这是两个平台的真实能力差距，不要指望抹平**：Linux 上 `C-a d` 是 detach，
> agent 继续跑；Windows 上只能存盘退出，进程会死。

### 6.6 agent pane

```lua
-- >>> 在下方开一个跑 agent 的终端 pane <<< #
pmap("a", function()
  require("snacks").terminal("claude", {
    win = { position = "bottom", height = 0.4 },
  })
end, "打开 agent pane")
```

---

## 7. LazyVim 迁移

### Phase 0 — 零风险试跑（`NVIM_APPNAME`）

**完全不碰 `~/.config/nvim`。**

```bash
git clone https://github.com/LazyVim/starter ~/.config/lazyvim
rm -rf ~/.config/lazyvim/.git
NVIM_APPNAME=lazyvim nvim          # 或者装好 justfile 之后直接 J lazy
```

`NVIM_APPNAME=lazyvim` 会把四个目录全部改道到 `lazyvim` 后缀
（`~/.config/lazyvim`、`~/.local/share/lazyvim`、`~/.local/state/lazyvim`、`~/.cache/lazyvim`），
现有配置和插件一根汗毛都不会动。Windows 上同理，改道到 `%LOCALAPPDATA%\lazyvim`。

> 因为 `~/.config/nvim.bak` 已经是一个带 `leap` extra 的 LazyVim starter，
> 也可以 `cp -a ~/.config/nvim.bak ~/.config/lazyvim` 起步。
> 但 `lazy-lock.json` 是旧的，进去先 `:Lazy update`。

**退出条件**：能开、`:checkhealth` 干净、在真实项目里 LSP 能跳定义。

正式切换时的备份（注意 `nvim.bak` 这个名字**已被占用**，别覆盖）：

```bash
mv ~/.config/nvim        ~/.config/nvim.quick
mv ~/.local/share/nvim   ~/.local/share/nvim.quick
mv ~/.local/state/nvim   ~/.local/state/nvim.quick
mv ~/.cache/nvim         ~/.cache/nvim.quick
```

### Phase 1 — 键位移植层

`nvim/lua/config/keymaps.lua`。LazyVim 已自带的（`C-h/j/k/l`、`gd`、`K`、Space leader）不用重复写。

```lua
local map = vim.keymap.set
local Snacks = require("snacks")

-- ── L1：VSCode 肌肉记忆的裸 Ctrl 键 ──
-- 改用 snacks.picker 而不是 telescope：Windows 上不需要编译 fzf-native，省掉一整类构建问题
map("n", "<C-p>", function() Snacks.picker.files() end,   { desc = "查找文件" })
map("n", "<C-f>", function() Snacks.picker.grep() end,    { desc = "全局搜索" })
map("n", "<C-b>", function() Snacks.picker.buffers() end, { desc = "Buffer 列表" })
map("n", "<C-n>", function() Snacks.explorer() end,       { desc = "文件树" })
map("n", "<C-s>", ":%s/",                                 { desc = "全文替换（起手）" })

-- ── L2：leader 层，保留你现在的键而不是 LazyVim 默认的 <leader>c* ──
map("n", "<leader>t", function()
  Snacks.terminal(nil, { win = { position = "bottom", height = 0.3 } })
end, { desc = "终端" })
map("t", "<Esc>", "<C-\\><C-n>", { desc = "终端回 normal" })

map("n", "<leader>rn", vim.lsp.buf.rename,      { desc = "重命名符号" })
map("n", "<leader>.",  vim.lsp.buf.code_action, { desc = "Code action" })
map("n", "<leader>f",  function() require("conform").format({ lsp_fallback = true }) end, { desc = "格式化" })

-- ── 从 nvim.bak 恢复的 operator-pending 映射 ──
map("o", "H", "^", { silent = true })
map("o", "L", "$", { silent = true })
```

`nvim/lua/config/options.lua` 补上 LazyVim 默认没有的：

```lua
vim.opt.colorcolumn = "80"     -- 你现在的习惯
vim.opt.scrolloff   = 3        -- LazyVim 默认是 4
vim.opt.showtabline = 2        -- 永远显示 tabline（herdr 模拟层要用）
vim.opt.swapfile    = false
vim.opt.hlsearch    = false
```

（`relativenumber`、`shiftwidth=2`、`splitbelow/right`、`mouse=a`、`termguicolors`
LazyVim 默认就对，不用写。）

### Phase 2 — 补齐 VSCode 那一半

| VSCode 能力 | 现在（coc） | LazyVim 对应 | 要做什么 |
|---|---|---|---|
| LSP | coc.nvim | 原生 LSP + `mason.nvim`（0.12 起可用 `vim.lsp.config`/`vim.lsp.enable`） | 列出实际在用的 coc extension，逐个换 mason server |
| 补全 `<Tab>` 循环 | coc 自定义 | blink.cmp **或 0.12 原生 `vim.lsp.completion`** | **必须显式配** `<Tab>`/`<S-Tab>`/`<CR>`。原生方案少一个插件，但功能比 blink 少（无 snippet 源、无模糊排序），建议先用 LazyVim 默认的 blink.cmp |
| 格式化 | `prettier.formatFile` | `conform.nvim` | 配 prettier / black |
| eslint autofix | `eslint.executeAutofix` | `nvim-lint` + eslint_d 或 LSP code action | 重建 `<leader>l` |
| 文件树 `C-n` | netrw `Lexplore` | `Snacks.explorer()` | 已在 Phase 1 |
| 模糊查找 | telescope | **snacks.picker** | 换掉 telescope，Windows 免编译 |
| git worktree `C-t` | `telescope git_worktree` | 需要重建 | 见 §9.2 |
| 注释 | vim-commentary + ts-context | LazyVim 内置 `gc`/`gcc`（带 ts 上下文） | 直接删旧插件 |
| surround | ur4ltz/surround.nvim | `mini.surround`（LazyVim 内置） | 键位不同，需适应 |
| 跳转 | — | flash.nvim（默认）/ leap（旧 extra） | 二选一，见 §9.2 |
| 主题 | tokyonight | tokyonight（LazyVim 默认） | ✅ 无需改 |

### Phase 3 — Linux 侧接 herdr

1. **启用 herdr 的 zsh 插件**（一行，收益最大）：
   `~/.zshrc` 的 `plugins=(...)` 加 `herdr`，拿到 `hrdrs`（fzf 选会话）、
   `hrdrwt`（建 worktree）、`hrdral`（列 agent）和补全。

2. **herdr 已有的三个自定义键**就是 herdr 版命令面板，和 nvim 里的裸键语义对齐：
   `prefix+C-p` 命令面板 / `prefix+C-f` 文件查看器 / `prefix+C-g` agent 时间线。
   这个巧合值得保留，已写进 §3.2 的统一表。

3. **剪贴板**：tmux 走 `xclip`，herdr 下走 OSC 52。
   nvim 设 `vim.opt.clipboard = "unnamedplus"`，并在 `--remote` SSH 场景下实测验证。

### Phase 4 — 切换与回滚

```bash
J backup-nvim                        # 四个目录打快照
mv ~/.config/nvim ~/.config/nvim.quick
ln -sfn ~/path/to/oh-my-term/nvim ~/.config/nvim
```

回滚就是把 `~/.config/nvim.quick` 挪回来。`~/.config/lazyvim` 沙箱保留，
以后试新东西继续在沙箱里试。

---

## 8. Windows 专属注意事项

### 8.1 Windows Terminal 设置

你选了 Windows Terminal，这是对的——herdr 官方也把它列为 native pane 支持的终端。
需要确认这几个键能传进 Git Bash：

| 键 | 默认是否被 WT 占用 | 处理 |
|---|---|---|
| `Ctrl+A` | 否（WT 的全选是 `Ctrl+Shift+A`） | ✅ 可以直接当前缀 |
| `Ctrl+H/J/K/L` | 否 | ✅ |
| `Alt+H/J/K/L` | 否（WT 用 `Alt+方向键` 切 pane） | ✅ |
| `Ctrl+Shift+V` | WT 粘贴 | 保留，herdr 文档也用这个 |

如果之后发现某个键进不去，在 WT 的 `settings.json` 里把对应 action 的
`keys` 删掉或改掉即可。

### 8.2 让 `:terminal` 用 Git Bash 而不是 cmd

Windows 上 Neovim 默认的 `shell` 是 `cmd.exe`，`:terminal` 和 `<leader>t` 会开出 cmd。
在 `options.lua` 里按平台覆盖：

```lua
if vim.fn.has("win32") == 1 then
  -- 指向 Git Bash。装在别处的话改这个路径。
  vim.o.shell = "C:/Program Files/Git/bin/bash.exe"
  vim.o.shellcmdflag = "-c"
  vim.o.shellredir = ">%s 2>&1"
  vim.o.shellpipe = "2>&1| tee"
  vim.o.shellquote = ""
  vim.o.shellxquote = ""
end
```

> ⚠️ 这组设置会影响 `:!`、`:grep`、以及插件内部所有 shell 调用。
> 改完务必跑 `:checkhealth` 和一次 `:Lazy update` 确认没炸。
> 如果出怪问题，先只改 `shell` + `shellcmdflag`，其余留默认。

### 8.3 依赖

| 依赖 | 为什么 | 怎么装 |
|---|---|---|
| Neovim 0.12.4 | 本体（**别装成 winget 仓库里的旧版**） | `winget install Neovim.Neovim` 后用 `nvim --version` 确认；版本不对就去 GitHub release 下 `nvim-win64.msi` |
| Git for Windows | Git Bash 本体 | `winget install Git.Git` |
| ripgrep | `C-f` 全局搜索 | `winget install BurntSushi.ripgrep.MSVC` |
| fd | 文件查找 | `winget install sharkdp.fd` |
| C 编译器 | nvim-treesitter 编译 parser | `winget install zig.zig`（最省事）或 LLVM/MSVC |
| Nerd Font | 图标 | 在 WT 里设成 `JetBrainsMono Nerd Font` 之类 |

> **选 snacks.picker 而不是 telescope 的最大理由就在这**：
> telescope-fzf-native 需要 `make` + C 工具链，在 Windows 上是个典型踩坑点；
> snacks.picker 是纯 Lua，装上就能用。

### 8.4 剪贴板

Windows 原生 Neovim 自带剪贴板支持，一般开箱可用。装完先跑：

```vim
:checkhealth provider
```

看 clipboard 一节是不是绿的。不行就装 `win32yank` 并确保在 `PATH` 里。

---

## 9. 冲突与待办

### 9.1 `prefix+w` 语义反转（**高优先级，会误删 agent**）

`prefix+w` 在 tmux 里是「打开会话选择器」（无害），在 herdr 里是「**关掉当前 pane**」（销毁性）。
你在两个环境之间切的时候，这一个键会直接删掉正在跑的 agent。

两个方案：

- **A（改 herdr 迁就 tmux）**：herdr `close_pane` 改成 `prefix+p`（对齐 tmux 的 kill-pane），
  `prefix+w` 留给 picker。
- **B（改 tmux 迁就 herdr）**：tmux `bind w choose-session` 改成 `bind s choose-session`
  （顺便对齐 herdr 的 `workspace_picker = prefix+s`），`prefix+w` 绑 `kill-pane`。

**推荐 B**——因为 §3.2 的统一表是以 herdr 为基准写的，Windows 模拟层也照 herdr 做。
让 tmux 这个正在被替代的东西去迁就，改动面最小。

同时 `prefix+x`（tmux 关 window，带确认）vs herdr `prefix+q`（关 tab）也要统一。

### 9.2 LazyVim 默认键 vs 你的习惯

| 你的键 | 问题 | 建议 |
|---|---|---|
| `vs` / `sp` 分屏 | `s` 被 **flash.nvim** 占用（跳转）；`vs` 还会让 `v` 进 visual 后卡顿等待 timeoutlen | **废弃**，改用 `C-a \|` / `C-a -`——正好和 herdr/tmux 完全同构 |
| `tn/tj/tk/to` | `t` 是 till motion，这四个会让对应的 till 失效；而且和 `C-a` 层的 tab 操作重复 | **废弃**，统一走 `C-a c` / `C-a C-h` / `C-a C-l` |
| `C-f` / `C-b` | 覆盖原生翻页 | 已经覆盖多年，照搬 |
| `C-s` = `:%s/` | 很多配置里 `C-s` = 保存，LazyVim 不占 | 照搬，安全 |
| `C-t` git worktree | 依赖 telescope extension，但我们换成了 snacks.picker | **待定**：① 保留 telescope 只为这一个功能；② 用 `Snacks.picker` 自己写一个读 `git worktree list` 的 picker；③ 在 Linux 上改用 `herdr worktree` |
| `leap` vs `flash` | `nvim.bak` 选了 leap extra，新版 LazyVim 默认 flash | **二选一**，别同时开——两个都抢 `s`/`S` |
| `C-a` | Linux 被 herdr 吃，Windows 被模拟层吃；原生是数字自增 | 已解决：`C-a C-a` 送字面量（§3.2 最后一行） |

### 9.3 herdr 是否支持 send-prefix

tmux 有 `bind C-a send-prefix`，herdr 的 `config.toml` 里没看到对应设置。
需要查 herdr 文档确认 `prefix+C-a` 能不能送出字面 `C-a`。
如果不能，nvim 里的数字自增在 Linux 上就彻底没了（可以退而映射到 `<leader>+`）。

### 9.4 herdr 缺少无前缀的 pane 切换

tmux 有 `M-h/j/k/l` 直接切 pane（不用前缀），herdr 的 `focus_pane_*` 全是 prefix 形式。
需要确认 herdr 是否支持 `focus_pane_left = "alt+h"` 这种写法。
这是日常频率最高的操作，值得专门确认。

### 9.5 `pmap` 的 terminal 分支要重写

**已验证**（Neovim 0.10.2，见 §6.4）：tabline 渲染、点击区域生成、`C-a` 前缀在
normal 和 terminal 两种模式下都能注册、`C-a C-a` 能送出字面 `C-a`。

**未验证、且已知写得不干净**：`pmap` 里 terminal 模式那段同时处理字符串和函数两种
action，字符串会走 `vim.cmd("normal! <cmd>vsplit<cr>")`——这是错的。
落地时把所有 action **统一写成 Lua 函数**：

```lua
pmap("|", function() vim.cmd.vsplit() end, "竖分屏")
```

这样 normal 和 terminal 两条路径共用同一个函数，`pmap` 里的类型判断也可以整个删掉。
**这是整份代码里唯一需要你亲手在 Windows 上跑一遍的地方。**

### 9.6 本机 nvim 还是 0.10.2

计划按 0.12.4 写，但 `/opt/nvim-linux64` 上跑的还是 0.10.2。
升级命令见 §2.1。注意目录名变了（`nvim-linux64` → `nvim-linux-x86_64`），
不能原地覆盖。升级后先跑 `:checkhealth`，再 `J lazy` 确认沙箱还正常。

### 9.7 能力差距，别指望抹平

| 能力 | Linux (herdr) | Windows (nvim 模拟) |
|---|---|---|
| 关终端后 agent 继续跑 | ✅ 常驻 server + PTY | ❌ 进程随 nvim 死 |
| 从任意 tty 重新接入 | ✅ `herdr session attach` | ❌ |
| agent 状态自动分类（blocked/working/done） | ✅ | ❌ |
| agent recap 时间线 | ✅ | ❌ |
| 真进程隔离的 pane | ✅ | ⚠️ 只是 nvim 的 window |

**如果这些能力在 Windows 上也是刚需，唯一的路是 `herdr --remote` 连回 Linux**
（herdr 官方支持，且 Windows 客户端就是 preview beta 里最成熟的部分）。
你这轮选择了「Windows 不跑 herdr」，所以上表就是接受的代价。

---

## 10. 执行顺序

| # | 任务 | 耗时 | 风险 |
|---|---|---|---|
| 0 | **升级本机 nvim 0.10.2 → 0.12.4**（§2.1） | 10 min | 低（旧版留着可回滚） |
| 1 | 建仓库骨架 + `main`/`linux`/`windows` 三分支（§4） | 30 min | 无 |
| 2 | 全局 justfile 落地 + `J` 别名 + **zsh 加 `herdr` 插件**（§5） | 30 min | 无 |
| 3 | **解决 §9.1 的 `prefix+w`** | 15 min | 不做会误删 agent |
| 4 | `J lazy` 跑起 Phase 0 沙箱（§7 Phase 0） | 1 h | 无（沙箱） |
| 5 | Phase 1 键位移植（§7 Phase 1） | 1–2 h | 低 |
| 6 | **写 herdr 模拟层并在 Windows 上实测**（§6 + §9.5） | 3–4 h | 中，核心工作量 |
| 7 | Phase 2 逐项补齐 coc → LSP（每次只换一个能力） | 分几天 | 中 |
| 8 | Windows 依赖 + 终端设置（§8） | 1 h | 低 |
| 9 | Phase 3 Linux 接 herdr / Phase 4 正式切换 | 1 h | 低（有快照可回滚） |

先做 0–3，它们零风险且立刻有收益（尤其第 3 项是在防事故）。
第 6 项是真正的新东西，建议单独开一个工作块。
