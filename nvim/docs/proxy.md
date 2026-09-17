# Working behind a proxy

Neovim itself needs no proxy configuration. It has no HTTP client. Three
independent child processes do the downloading, and they read different settings.

| What | Downloader | Reads `*_PROXY` env vars |
|---|---|---|
| lazy.nvim (plugins) | `git` subprocess | yes |
| nvim-treesitter (parsers) | `git` / `curl` | yes |
| Mason (LSP servers) | `curl`, else `wget`, else PowerShell | yes, in practice |

## `HTTP_PROXY` is not enough

Plugin URLs are `https://`, and `HTTP_PROXY` only covers `http://`. Tested against
the same repository with a deliberately dead proxy:

```
HTTP_PROXY=http://127.0.0.1:9   ->  clone succeeds     (variable ignored)
HTTPS_PROXY=http://127.0.0.1:9  ->  connection refused (variable honoured)
https_proxy=http://127.0.0.1:9  ->  connection refused (variable honoured)
```

Set `HTTPS_PROXY`. Set both cases if you want to be safe: curl reads `http_proxy`
in lowercase only, but accepts either case for the rest.

lazy.nvim passes the whole environment through to `git` (`uv.os_environ()` in
`lua/lazy/manage/process.lua`), overriding only `GIT_DIR`, `GIT_WORK_TREE`,
`GIT_INDEX_FILE` and `GIT_TERMINAL_PROMPT`. So an exported variable reaches git.

## Mason's download order

`mason-core/fetch.lua` ends with:

```lua
return curl():or_else(wget):or_else(platform_specific)
```

`curl` is tried first, `wget` second, and the PowerShell `Invoke-WebRequest`
branch is only a last resort. Windows 10 1803 and later ship `curl.exe` in
`System32`, so curl effectively always wins and the environment variables apply.

The PowerShell path is worth knowing about anyway, because it behaves differently:
`Invoke-WebRequest` uses the Windows system proxy settings rather than
`HTTPS_PROXY`. If you ever see plugins installing fine while every language server
fails, check whether `curl` is actually on the PATH of the process that launched
Neovim.

For the record, Mason invokes PowerShell as
`powershell -NoProfile -NonInteractive -Command "<inline>"`. That is an inline
command, not a `.ps1` file, so a restrictive ExecutionPolicy does not block it;
ExecutionPolicy governs script files. AppLocker, WDAC or Constrained Language Mode
would block it, but those are less common.

## The environment has to exist in the Neovim process

`export` in `.bashrc` only applies to processes started from that shell. Launching
Neovim from the Start menu, a desktop shortcut, or a Windows Terminal profile that
does not source your shell config means none of those variables are set.

So on Windows, prefer configuration that does not depend on how you launched it:

```bash
# covers lazy.nvim and treesitter, independent of the launching shell
git config --global http.proxy  http://127.0.0.1:7890
git config --global https.proxy http://127.0.0.1:7890
```

```powershell
# covers Mason and anything else started outside a shell
setx HTTPS_PROXY "http://127.0.0.1:7890"
setx HTTP_PROXY  "http://127.0.0.1:7890"
```

## Intercepting corporate proxies

A proxy that terminates TLS presents its own certificate, and git rejects it. On
Windows, point git at the Windows certificate store, where the corporate root CA
is already trusted:

```bash
git config --global http.sslBackend schannel
```

Do not use `http.sslVerify false`. It disables verification for every host.
