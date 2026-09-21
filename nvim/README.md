# nvim — Linux 分支

LazyVim。外层的 tab / pane / agent 由真 **herdr** 管，所以这份配置里
**没有** `C-a` 前缀层——那是 Windows 分支才需要的模拟层。

```
Linux（本分支）                    Windows
  C-a  ->  herdr                     C-a  ->  nvim 自己的模拟层
           tab / pane / agent                 tabpage / window / terminal
```

```
init.lua            入口
lua/config/         LazyVim 引导、选项、键位
lua/plugins/        插件声明，含 herdr 接线和内存预算
lua/workbench/      会话持久化
docs/               键位、会话
```

配套的三份配置在仓库同级目录：`herdr/`、`tmux/`、`zsh/`。

- [`docs/keys.md`](docs/keys.md) — 三层键位，以及销毁性键位为什么要改
- [`docs/sessions.md`](docs/sessions.md) — 状态怎么留下来
- [`plans/cross-platform-workbench.md`](../plans/cross-platform-workbench.md) — 设计，在 `main` 上
