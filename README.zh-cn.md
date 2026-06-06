# DLTreeDownloader-SQLite

[English](README.md) | 简体中文

DLTreeDownloader 是一个本地命令行工具，用于把 DL tree 导入 SQLite，按作品编码、配音演员、团队名称查询记录，并通过 MEGAcmd 下载作品文件。

## 安装

Windows 下推荐直接运行根目录的安装脚本：

```bat
run-install.bat
```

脚本会优先使用本机已有的 Python 3.11 或更高版本；如果本机没有可用 Python，会自动把 Python 安装到 `env/python`。项目依赖会安装到根目录 `.venv`，方便 VS Code 自动识别解释器；数据库和配置仍保存在 `env/`。

安装完成后可以直接使用本地命令：

```powershell
.\.venv\Scripts\dltree.exe doctor
```

## 初始化

```powershell
.\.venv\Scripts\dltree.exe init
```

该命令会创建：

- `env/config.toml`
- `env/dltree.sqlite3`
- `downloads/`

重复运行不会覆盖已有配置，也不会删除数据库。

## 检查环境

```powershell
.\.venv\Scripts\dltree.exe doctor
```

`doctor` 会检查配置、数据库、下载路径、`mega-get`、`mega-whoami` 和 MEGA 登录状态。

## 导入 Excel

```powershell
.\.venv\Scripts\dltree.exe import "files/DL tree.xlsx"
```

导入完成后会显示总行数、新增作品、更新作品、跳过作品、链接变化数和行级错误数。重复导入同一个文件不会产生重复的 active links。

导入过程中会显示进度条。如果存在行级错误，命令会把本次导入的错误明细导出到 `logs/import_errors_<import_id>_<timestamp>.csv`，同时仍保留数据库中的 `import_errors` 审计记录。

## 查询

按作品编码精确查询：

```powershell
.\.venv\Scripts\dltree.exe search-code RJ00
```

按配音演员模糊查询：

```powershell
.\.venv\Scripts\dltree.exe search-voice abc --limit 50
```

按团队名称模糊查询：

```powershell
.\.venv\Scripts\dltree.exe search-circle "abc" --limit 50
```

查看作品详情和 active links：

```powershell
.\.venv\Scripts\dltree.exe info RJ00
```

## 下载

先确认已经安装 MEGAcmd，并手动登录：

```powershell
mega-login
```

下载作品：

```powershell
.\.venv\Scripts\dltree.exe download RJ00
```

跳过确认：

```powershell
.\.venv\Scripts\dltree.exe download RJ00 --yes
```

默认会排除 `.par2` 文件。如需包含：

```powershell
.\.venv\Scripts\dltree.exe download RJ00 --include-par2
```

下载前会检查作品是否存在、可下载链接、MEGAcmd、登录状态和磁盘空间。数据库会记录每次下载的 planned、completed、failed 或 blocked 状态。

## 配置

默认配置文件位于：

```text
env/config.toml
```

默认数据库位置：

```text
env/dltree.sqlite3
```

默认下载目录：

```text
downloads/
```

如需修改数据库、下载目录或 MEGAcmd 可执行文件路径，请编辑 `env/config.toml`。

## 开发文档

二次开发文档位于 `documents/`：

- `documents/developer_guide.md`
- `documents/architecture.md`
- `documents/data_contract.md`
- `documents/extension_points.md`
- `documents/testing_guide.md`

设计文档位于 `dev_documents/`。
