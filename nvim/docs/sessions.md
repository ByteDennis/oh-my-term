# 会话恢复

herdr 会把 pane 一直挂着，进程被杀不是常态，所以这一层没有 Windows 分支那么
紧要。但 nvim 自己的窗口布局、打开的 buffer、tab 名字只活在 nvim 进程里，
herdr 救不了，所以还是要有。

| 触发 | 时机 |
|---|---|
| 定时器 | 每 180 秒（Windows 分支是 60 秒） |
| 布局变化 | `TabNew` / `TabClosed` / `BufWritePost` 之后 2 秒，去抖 |
| 正常退出 | `VimLeavePre` |

裸 `nvim` 会自动恢复当前目录的 session；`nvim foo.lua` 不会，因为那显然不是
你的意图。

## tab 名字

`:mksession` **不保存 tab 作用域变量**，所以 `vim.t.tabname` 默认会丢。解决办法
是写一个 sidecar JSON 放在 session 文件旁边，source 完 session 再贴回去。

```
~/.local/state/nvim/sessions/
  %home%you%code%myproject.vim     :mksession 的输出
  %home%you%code%myproject.json    tab 名字
```

## 命令

`:SessionSave` · `:SessionRestore` · `:SessionClear`

## terminal 故意不存

`sessionoptions` 里没有 `terminal`。herdr 下 agent 和 shell 都应该跑在 herdr 的
pane 里（真 PTY，关掉终端还活着），nvim 里恢复一个已经死掉的 shell 比不恢复更糟。
