# MEGAcmd 命令解析

本文说明 DLTreeDownloader 如何发现和调用本机 MEGAcmd 命令，供二次开发和维护时参考。

## 1. 责任边界

MEGAcmd 相关逻辑集中在 `dltree/mega.py`：

- `resolve_command()` 负责把配置里的命令名或路径解析为实际可执行文件。
- `command_available()` 只判断解析是否成功。
- `check_login()` 使用解析后的 `mega-whoami` 检查登录状态。
- `run_mega_get()` 使用解析后的 `mega-get` 执行下载。

应用层 `dltree/app.py` 不应直接用 `shutil.which()` 判断 MEGAcmd。`doctor` 应通过 `resolve_command()` 显示最终解析到的真实路径，便于用户排查 Windows PATH 问题。

## 2. 解析顺序

配置项仍然是：

```toml
[mega]
mega_get = "mega-get"
mega_whoami = "mega-whoami"
```

解析流程：

1. 如果配置值看起来像路径，检查该路径本身。
2. Windows 上如果路径没有后缀，按 `PATHEXT` 尝试 `.exe`、`.cmd`、`.bat` 等后缀。
3. 如果配置值是命令名，先用 `shutil.which()` 查 PATH。
4. Windows 上 PATH 找不到时，再检查常见安装目录：
   - `%LOCALAPPDATA%\MEGAcmd`
   - `%ProgramFiles%\MEGAcmd`
   - `%ProgramFiles(x86)%\MEGAcmd`
   - `%USERPROFILE%\AppData\Local\MEGAcmd`

这样可以兼容 MEGAcmd 已安装但没有写入当前 shell PATH 的情况。

## 3. 调用规则

正常情况下外部命令仍然通过参数列表调用，不拼接 shell 字符串，避免 MEGA URL 或路径中的特殊字符被 shell 重新解释。

Windows 上如果解析结果是 `.cmd` 或 `.bat`，使用：

```text
cmd.exe /d /c call <command> <args...>
```

这是为了兼容批处理入口文件。只有 `.cmd` 和 `.bat` 走这个包装；`.exe` 仍然直接调用。

## 4. 测试要求

MEGAcmd 测试不依赖真实账号和网络，应 mock：

- `shutil.which()`
- `subprocess.run()`
- `resolve_command()` 或 Windows 安装目录环境变量

需要覆盖：

- PATH 中可以找到命令。
- PATH 找不到，但 Windows 常见安装目录可以找到命令。
- `check_login()` 使用解析后的真实路径。
- `doctor` 显示解析后的真实路径。
- 缺失 MEGAcmd 时仍给出清晰错误。
