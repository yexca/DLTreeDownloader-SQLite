# DLTreeDownloader Requirements Overview

## 1. Project Goal

Build a Python + SQLite CLI tool to import a large DL tree Excel workbook, search works by work code, check local free disk space, and download the selected work through MEGAcmd only when storage is sufficient.

The source workbook may be updated by the author, but its format is expected to stay stable. The program therefore needs an import mode that can reuse the same parsing logic for both first-time import and later refresh imports.

## 2. Source Workbook Summary

Observed file:

- `files/DL tree 260308.xlsx`
- Workbook size: about 25 MB
- Sheet count: 1
- Sheet name: `Sheet1`
- Data rows: 74,917
- Columns: 11

Observed columns:

| Column | Meaning | Notes |
|---|---|---|
| `RJcode` | Work code | Unique in current workbook, but values include `RJ...`, `VJ...`, `d_...`, `BJ...`, and other patterns. Internally use `work_code`. |
| `标签` | Tags | Often blank. Separators can include Chinese/Japanese punctuation and slash-like text inside tag names. |
| `MEGA链接` | Download link JSON | Always parseable in the inspected workbook. Root key observed: `C`. Each link item has `F`, `L`, `S`. |
| `销售日期` | Sale date | Some blank values. |
| `声优` | Voice actor names | Some blank values. Multiple names are commonly separated by four spaces. |
| `标题` | Title | Some blank values. |
| `备注` | Notes | Mostly blank or `null`. |
| `类型` | Type/category | Some blank values. |
| `社团` | Circle/group | Some blank values. |
| `档案大小` | Full archive display size | Human-readable value such as `397.64 MB`, `4.10 GB`. |
| `MP3大小` | MP3 display size | Human-readable value. Often `0 B`. |

## 3. Core User Stories

1. As a user, I can import the Excel workbook into a local SQLite database.
2. As a user, I can import a newer workbook later. Existing works are skipped unless their download links changed.
3. As a user, I can search by work code and see whether the work exists.
4. As a user, I can download an existing work only if there is enough free disk space.
5. As a user, I can search a voice actor name and list all visible works involving that voice actor.
6. As a user, I can search a circle name and list all visible works from that circle.
7. As a user, I do not see obsolete download link records after an import detects updated links, but old link records remain stored with `is_deleted = 1`.
8. As a user, I can configure the runtime environment under an `env` folder using a setup script.

## 4. Recommended CLI Scope

Initial commands:

```text
dltree init
dltree import <xlsx_path>
dltree search-code <work_code>
dltree search-voice <name>
dltree search-circle <name>
dltree info <work_code>
dltree download <work_code> [--variant all|mp3|voice|custom] [--output <dir>]
dltree doctor
```

Recommended command responsibilities:

- `init`: create database, config file, and download directory if missing.
- `import`: parse Excel rows and upsert data.
- `search-code`: quick exact lookup by `work_code`.
- `search-voice`: fuzzy search voice actor names and list related works.
- `search-circle`: fuzzy search circles and list related works.
- `info`: show work metadata and active download links.
- `download`: check MEGAcmd login, calculate required bytes, check free disk space, then call `mega-get`.
- `doctor`: check Python version, SQLite database accessibility, MEGAcmd availability, and MEGAcmd login status.

## 5. Non-Goals For The First Version

- GUI application.
- Automatic scheduled imports.
- Automatic MEGA account login credential management.
- Full-text search engine beyond SQLite `LIKE` or optional SQLite FTS.
- Deleting local downloaded files.
- Verifying downloaded archive integrity beyond file size checks.
- Multi-user database access.

## 6. Important Decisions

### Use `work_code` internally

Even though the source column is named `RJcode`, observed values are not limited to RJ codes:

- `RJ_digits`: 73,274 rows
- `d_digits`: 725 rows
- `VJ_digits`: 610 rows
- `other`: 308 rows

The database and Python code should use `work_code` as the canonical internal name, while preserving the import mapping from Excel column `RJcode`.

### Preserve historical download links

When a future import finds the same `work_code` but different link data:

- Keep existing link rows.
- Mark old active link rows as `is_deleted = 1`.
- Insert new link rows as active.
- Keep the work visible through the `works` table.

This preserves history without showing outdated download links to normal users.

### Calculate disk requirement from link item byte sizes

The MEGA JSON contains exact byte size strings in field `S`, for example:

```json
{"F":"RJ01548502.zip","L":"https://mega.nz/file/...","S":"3249155727"}
```

For disk checks, prefer summing active link `size_bytes` values instead of parsing human-readable `档案大小` or `MP3大小`.

Add a configurable safety margin because downloads may temporarily require extra space:

- Default margin: 5% of selected download bytes.
- Minimum margin: 512 MB.

## 7. Open Questions Before Implementation

1. Should `download <work_code>` download all active links by default, or should it ask the user to choose when there are multiple files?
2. Should `.par2` files be downloaded by default? They are commonly present and can be useful, but they increase required space.
3. Should voice actor names be split only by four spaces, or should punctuation separators also split names?
4. Should tags become a normalized table in v1, or remain a text field until tag search is needed?
5. Should the CLI display adult content titles directly by default, or provide a quiet mode that hides titles in search results?

