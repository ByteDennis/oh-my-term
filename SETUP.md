# 安装

按这个顺序做，前两步零风险且立刻有收益。

## 1. 启用 herdr 的 zsh 插件（一行，收益最大）

`~/.zshrc` 的 `plugins=(...)` 里加 `herdr`。插件目录已经在
`~/.oh-my-zsh/plugins/herdr`，只是没被启用，所以 `hrdrs` / `hrdral` / `hrdrwt`
这些别名和补全现在全是失效的。

顺便 source 一下本仓库的补充：

```zsh
source ~/path/to/oh-my-term/zsh/herdr.zsh
```

## 2. 修掉销毁性键位冲突（15 分钟，防事故）

改动前 `prefix+w` 在 tmux 里是「选会话」、在 herdr 里是「**关 pane**」。
两个环境来回切迟早误删正在跑的 agent。原因和修法见
[`nvim/docs/keys.md`](nvim/docs/keys.md)。

```bash
cp ~/.config/herdr/config.toml ~/.config/herdr/config.toml.bak
ln -sf ~/path/to/oh-my-term/herdr/config.toml ~/.config/herdr/config.toml
herdr server reload-config
```

tmux 那边是一个小叠加文件，不替换你现有的 `~/.tmux.conf`：

```
# ~/.tmux.conf 末尾，TPM 那行之前
source-file ~/path/to/oh-my-term/tmux/herdr-align.conf
```

然后 `prefix + C-r` 重载。

## 3. 全局 justfile

```bash
mkdir -p ~/.config/just
ln -sf ~/path/to/oh-my-term/just/justfile ~/.config/just/justfile
```

（`just/` 目录还没建，见 `plans/cross-platform-workbench.md` §5。）

## 4. 先在沙箱里试 LazyVim

不碰现有的 `~/.config/nvim`：

```bash
ln -sfn ~/path/to/oh-my-term/nvim ~/.config/lazyvim
NVIM_APPNAME=lazyvim nvim
```

确认能开、`:checkhealth` 干净、在真实项目里 LSP 能跳定义之后再考虑切换。

## 5. 正式切换

```bash
mv ~/.config/nvim ~/.config/nvim.quick
ln -sfn ~/path/to/oh-my-term/nvim ~/.config/nvim
```

回滚就是把 `~/.config/nvim.quick` 挪回来。

> 注意 `~/.config/nvim.bak` 这个名字**已经被占用**了，里面是你上次装的 LazyVim，
> 别覆盖。
