# 01 Project Skeleton And Environment

## 目标

建立最小可运行项目，让后续模块有统一入口、配置路径和数据库初始化能力。

## 负责模块

```text
dltree/__init__.py
dltree/cli.py
dltree/app.py
dltree/config.py
dltree/db.py
dltree/schema.sql
requirements.txt
setup_env.ps1
```

## 实现内容

- 创建 `dltree/` Python 包结构。
- 创建 `requirements.txt`。
- 创建 Windows 环境初始化脚本 `setup_env.ps1`。
- 实现默认配置文件创建逻辑。
- 实现 SQLite schema 初始化。
- 实现 `dltree init` 命令。

默认配置：

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

## 完成标准

- 能运行 `dltree init`。
- 自动创建 `env/config.toml`。
- 自动创建 `env/dltree.sqlite3`。
- 自动创建默认下载目录。
- 重复运行 `dltree init` 不覆盖用户已有配置，不破坏已有数据库。

