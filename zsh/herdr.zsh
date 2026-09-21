# herdr 的 shell 接线。
#
# 在 ~/.zshrc 里做一件事就够了：把 herdr 加进 oh-my-zsh 的 plugins 列表。
#
#     plugins=(
#       git
#       herdr          # <- 加这一行
#       zsh-autosuggestions
#       ...
#     )
#
# 插件目录 ~/.oh-my-zsh/plugins/herdr 已经存在，但没被启用，
# 所以 hrdrs / hrdral / hrdrwt 这些别名和补全现在都是失效的。
#
# 下面这些是插件之外的补充，source 这个文件即可。

# >>> 全局 justfile 的入口，大写 = 更大作用域 <<< #
alias J='just -g'
alias Jl='just -g --list'

# >>> 用当前目录名开或接一个 herdr 会话 <<< #
hs() {
  herdr --session "${1:-$(basename "$PWD")}"
}

# >>> 在 herdr pane 里时给提示符加个标记，避免搞不清身在何处 <<< #
if [[ -n "$HERDR_ENV" ]]; then
  export HERDR_IN_SESSION=1
fi
