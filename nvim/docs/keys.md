# 键位

三层，互不重叠：

| 层 | 触发 | 归谁 |
|---|---|---|
| 工作台 | `C-a` + 键 | **herdr**。nvim 根本收不到这些键 |
| 导航 | 裸 `Ctrl` | 编辑器 |
| 功能 | `<Space>` | 编辑器 |

这是和 Windows 分支最大的结构差异：那边没有 herdr，所以 nvim 要自己实现一个
`C-a` 前缀层；这边真 herdr 在外层把 `C-a` 全吃掉了，nvim 里一条 `C-a` 映射都
不该有。

## 工作台层（herdr）

配置在 `herdr/config.toml`。

| 键 | 动作 |
|---|---|
| `C-a \|` / `C-a -` | 竖 / 横分屏 |
| `C-a h/j/k/l` | 移动焦点 |
| `M-h/j/k/l` | 移动焦点，无前缀（见下方说明） |
| `C-a c` | 新建 tab |
| `C-a r` | 重命名 tab |
| `C-a C-h` / `C-a C-l` | 上 / 下一个 tab |
| `C-a 1..9` | 按序号跳 tab |
| `C-a w` | workspace 选择器 |
| `C-a x` | 关 pane |
| `C-a X` | 关 tab |
| `C-a D` | 关 workspace |
| `C-a z` | zoom |
| `C-a [` | copy mode |
| `C-a d` | detach |
| `C-a C-r` | 重载配置 |
| `C-a C-p` / `C-a C-f` / `C-a C-g` | 命令面板 / 文件查看器 / agent 时间线 |

## 销毁性键位为什么改了

改动前 `close_pane = "prefix+w"`，而 tmux 的 `prefix+w` 是「打开会话选择器」。
同一个键，一边无害、一边直接删掉正在跑的 agent。

关键在于：**herdr 的默认值本来就和 tmux 对得上**（`workspace_picker` 默认就是
`prefix+w`）。冲突是自定义配置把 `workspace_picker` 挪到 `s`、把销毁性的
`close_pane` 放到 `w` 造成的。所以修法是把这几个改回 herdr 默认，而不是去改
tmux。

对齐后：

| 键 | herdr | tmux（叠加 `tmux/herdr-align.conf` 后） |
|---|---|---|
| `prefix+w` | workspace 选择器 | choose-session |
| `prefix+x` | 关 pane | kill-pane |
| `prefix+X` | 关 tab | kill-window（带确认） |
| `prefix+D` | 关 workspace | kill-session（带确认） |

## 无前缀切 pane

herdr 的 `focus_pane_*` 只接受一个绑定值，给不了「`prefix+h` 和 `alt+h` 都行」。
所以 `alt+hjkl` 是用自定义 shell 命令补的：

```toml
[[keys.command]]
key = "alt+h"
type = "shell"
command = "herdr pane focus --direction left --current"
```

代价是每次按键 fork 一个进程走 socket API，比内建绑定慢。pane 切换是最高频的
操作，**先用一周，觉得迟滞就把这四条删掉**，只留 `prefix+h`。

不能用 `ctrl+hjkl` 做无前缀绑定——nvim 要用它们切窗口，herdr 抢走了 nvim 就
收不到了。herdr 自己的文档也提醒 `alt+...` 的可靠性取决于终端。

## 数字自增没了

herdr **没有** tmux 那种 `send-prefix`（查过 `herdr --default-config`，
没有对应动作）。所以 `prefix = ctrl+a` 时，vim 原生的 `<C-a>` 数字加一在 herdr
里彻底拿不到。

替代键：`<leader>=`。`<C-x>` 减一不受影响，原样能用。

想把 `<C-a>` 要回来只有一个办法：把 herdr 的 prefix 换成别的键（默认是
`ctrl+b`）。但那样整套 `C-a` 肌肉记忆就都要重建，不划算。

## 编辑器层

`C-p` 文件 · `C-f` 全局搜索 · `C-b` buffer · `C-n` 文件树 · `C-s` 替换

`<leader>t` 终端 · `<leader>rn` 重命名 · `<leader>.` code action ·
`<leader>f` 格式化 · `<leader>=` 数字加一
