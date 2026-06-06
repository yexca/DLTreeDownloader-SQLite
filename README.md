# DLTreeDownloader-SQLite

English | [简体中文](README.zh-cn.md)

DLTreeDownloader is a local command-line tool for importing DL tree workbooks into SQLite, searching records by work code, voice actor, or circle, and downloading work files through MEGAcmd.

## Installation

On Windows, run the installer script from the project root:

```bat
run-install.bat
```

The script uses an existing Python 3.11 or newer installation when available. If no supported Python installation is found, it installs Python into `env/python`. Project dependencies are installed into the root `.venv` directory so VS Code can detect the interpreter automatically. The database and configuration remain under `env/`.

After installation, you can run the local command directly:

```powershell
.\.venv\Scripts\dltree.exe doctor
```

## Initialization

```powershell
.\.venv\Scripts\dltree.exe init
```

This command creates:

- `env/config.toml`
- `env/dltree.sqlite3`
- `downloads/`

Running it again does not overwrite an existing configuration or delete the database.

## Environment Check

```powershell
.\.venv\Scripts\dltree.exe doctor
```

`doctor` checks the configuration, database, download path, `mega-get`, `mega-whoami`, and MEGA login status.

## Import Excel

```powershell
.\.venv\Scripts\dltree.exe import "files/DL tree.xlsx"
```

After import, the command shows total rows, inserted works, updated works, skipped works, link changes, and row-level errors. Re-importing the same file does not create duplicate active links.

The import command displays a progress bar. If row-level errors are found, it exports the details for that import to `logs/import_errors_<import_id>_<timestamp>.csv` while keeping the `import_errors` audit records in the database.

## Search

Search by exact work code:

```powershell
.\.venv\Scripts\dltree.exe search-code RJ00
```

Search by voice actor:

```powershell
.\.venv\Scripts\dltree.exe search-voice abc --limit 50
```

Search by circle:

```powershell
.\.venv\Scripts\dltree.exe search-circle "abc" --limit 50
```

Show work details and active links:

```powershell
.\.venv\Scripts\dltree.exe info RJ00
```

## Download

First make sure MEGAcmd is installed and log in manually:

```powershell
mega-login
```

Download a work:

```powershell
.\.venv\Scripts\dltree.exe download RJ00
```

Skip the confirmation prompt:

```powershell
.\.venv\Scripts\dltree.exe download RJ00 --yes
```

By default, `.par2` files are excluded. To include them:

```powershell
.\.venv\Scripts\dltree.exe download RJ00 --include-par2
```

Before downloading, the tool checks that the work exists, has downloadable links, MEGAcmd is available, MEGA is logged in, and enough disk space is available. The database records each download as `planned`, `completed`, `failed`, or `blocked`.

## Configuration

Default configuration file:

```text
env/config.toml
```

Default database path:

```text
env/dltree.sqlite3
```

Default download directory:

```text
downloads/
```

To change the database path, download directory, or MEGAcmd executable paths, edit `env/config.toml`.

## Developer Documents

Developer documentation is available under `documents/`:

- `documents/developer_guide.md`
- `documents/architecture.md`
- `documents/data_contract.md`
- `documents/extension_points.md`
- `documents/testing_guide.md`

Design documents are available under `dev_documents/`.
