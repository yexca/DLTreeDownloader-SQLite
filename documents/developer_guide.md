# Developer Guide

## 1. 项目简介

DLTreeDownloader 是本地 Python + SQLite CLI 工具，用于导入 DL tree Excel 工作簿、查询作品信息，并通过 MEGAcmd 下载作品文件。

v1 的核心边界：

- 不提供 GUI。
- 不托管后台服务。
- 不管理 MEGA 登录凭据。
- 不做多用户并发写入。
- 不自动删除历史下载链接。

## 2. 推荐开发环境

推荐使用根目录的安装脚本准备本地环境：

```bat
run-install.bat
```

脚本职责：

- 如果本机没有 Python 3.11+，自动安装 Python 到 `env/python`。
- 创建或复用根目录虚拟环境 `.venv`，方便 VS Code 自动识别解释器。
- 安装项目依赖和开发依赖。
- 初始化 `env/config.toml`、`env/dltree.sqlite3` 和 `downloads/`。

运行依赖：

```text
Python 3.11+
openpyxl
typer
rich
pytest
```

推荐本地目录：

```text
env/
  python/
  config.toml
  dltree.sqlite3
.venv/
downloads/
logs/
files/
  DL tree 260308.xlsx
```

## 3. 启动流程

实现完成后的典型流程：

```text
.venv/Scripts/dltree.exe init
.venv/Scripts/dltree.exe doctor
.venv/Scripts/dltree.exe import "files/DL tree 260308.xlsx"
.venv/Scripts/dltree.exe search-code RJ01548502
.venv/Scripts/dltree.exe info RJ01548502
.venv/Scripts/dltree.exe download RJ01548502
```

`doctor` 应在导入前后都可运行，用来确认配置、数据库和 MEGAcmd 状态。

## 4. 模块阅读入口

如果要理解命令入口，先看：

```text
dltree/cli.py
dltree/app.py
```

如果要理解数据导入，先看：

```text
dltree/importer.py
dltree/link_parser.py
dltree/normalizers.py
dltree/repositories.py
```

如果要理解下载，先看：

```text
dltree/mega.py
dltree/filesystem.py
dltree/sizes.py
```

如果要理解数据库，先看：

```text
dltree/schema.sql
dltree/db.py
dltree/repositories.py
```

## 5. 开发原则

- 保持 CLI、应用服务、领域规则、数据库访问、外部进程调用的边界。
- 新增 SQL 优先放到 repository 层，不要散落在 CLI 中。
- 新增解析规则时保留 raw 字段，不要破坏原始数据。
- 下载流程新增能力时，必须保持下载前置检查先于 `mega-get`。
- 对 Excel 格式的假设必须写入测试 fixture。
- 对外部命令的测试使用 mock，不依赖真实 MEGA 网络。

## 6. 常见修改路径

新增 CLI 命令：

1. 在 `app.py` 增加用例函数。
2. 在 `repositories.py` 增加需要的查询。
3. 在 `cli.py` 增加 Typer command。
4. 添加 CLI 测试。
5. 更新 `documents/extension_points.md`。

新增导入字段：

1. 更新 schema。
2. 更新 Excel 表头映射。
3. 更新 `WorkRow`。
4. 更新 upsert SQL。
5. 添加 fixture 行和导入测试。
6. 更新 `documents/data_contract.md`。

新增下载策略：

1. 在应用层增加文件选择规则。
2. 保持空间检查基于最终 selected links。
3. 更新确认摘要。
4. mock MEGAcmd 增加测试。
