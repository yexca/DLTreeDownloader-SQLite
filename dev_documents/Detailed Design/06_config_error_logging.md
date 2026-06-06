# Config, Error And Logging Detail

## 1. 配置文件

默认路径：

```text
env/config.toml
```

默认内容：

```toml
[paths]
database = "env/dltree.sqlite3"
downloads = "downloads"

[download]
safety_margin_percent = 5
safety_margin_min_mb = 512
include_par2_by_default = false

[mega]
mega_get = "mega-get"
mega_whoami = "mega-whoami"
```

## 2. 路径解析

相对路径基准：

- 配置文件内相对路径，以项目当前工作目录为基准。
- CLI `--output` 相对路径，也以当前工作目录为基准。

实现时使用 `Path(path).expanduser()`，再在需要展示前执行 `resolve()`。

不要在读取配置时自动创建数据库或下载目录；创建动作由 `init` 或下载命令在前置检查通过后执行。

## 3. 配置校验

必需 key：

```text
paths.database
paths.downloads
download.safety_margin_percent
download.safety_margin_min_mb
download.include_par2_by_default
mega.mega_get
mega.mega_whoami
```

校验规则：

- `safety_margin_percent >= 0`
- `safety_margin_min_mb >= 0`
- `include_par2_by_default` 是 bool。
- mega 命令字段非空。

配置错误统一抛出 `ConfigError`，CLI 映射退出码 2。

## 4. 异常类型

建议异常：

```python
class DLTError(Exception):
    exit_code = 10

class ConfigError(DLTError):
    exit_code = 2

class NotFoundError(DLTError):
    exit_code = 3

class ExternalDependencyError(DLTError):
    exit_code = 4

class DiskSpaceError(DLTError):
    exit_code = 5

class ImportExecutionError(DLTError):
    exit_code = 10

class DownloadExecutionError(DLTError):
    exit_code = 10
```

CLI 捕获 `DLTError`，输出 `str(error)` 并使用 `error.exit_code` 退出。

## 5. 日志策略

v1 不需要复杂日志系统，但建议保留两层：

- CLI 用户输出：Rich 表格和简短提示。
- 审计记录：`imports`、`import_errors`、`downloads` 表。

可选文件日志：

```text
env/logs/dltree.log
```

若实现文件日志：

- 只记录程序执行摘要和异常堆栈。
- 不记录完整 MEGA URL，除非用户启用 debug。
- 不记录 MEGA 凭据。

## 6. 错误展示

配置错误：

```text
Config error: missing paths.database in env/config.toml
```

数据库错误：

```text
Database error: env/dltree.sqlite3 is not initialized. Run dltree init.
```

导入表头错误：

```text
Import failed: missing required columns: MEGA链接, 销售日期
```

MEGAcmd 不可用：

```text
MEGAcmd command not found: mega-get
Install MEGAcmd or set mega.mega_get in env/config.toml.
```

磁盘空间不足：

```text
Not enough disk space.
Required: 3.53 GB
Free: 2.10 GB
Output: downloads/RJ01548502
```

## 7. 安全注意事项

- 不保存 MEGA 账号、邮箱或密码。
- 不把 URL 当 shell 字符串拼接执行。
- 不自动删除旧数据库、旧下载文件或旧链接历史。
- 下载目录由用户配置时，只创建目标目录，不清理任何已有文件。

