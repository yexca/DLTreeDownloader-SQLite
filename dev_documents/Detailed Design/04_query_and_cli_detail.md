# Query And CLI Detail

## 1. CLI 总体约定

命令：

```text
dltree init
dltree import <xlsx_path>
dltree search-code <work_code>
dltree search-voice <name> [--limit 50]
dltree search-circle <name> [--limit 50]
dltree info <work_code>
dltree download <work_code> [--output <dir>] [--include-par2] [--yes]
dltree doctor
```

输出原则：

- 成功命令输出摘要，不刷屏。
- 搜索结果用表格。
- 失败信息给出原因和下一步动作。
- 缺失字段显示 `-`。
- 所有命令都从配置解析数据库路径，除非未来增加 `--db`。

## 2. 退出码

| 场景 | 退出码 |
|---|---:|
| 成功 | 0 |
| 参数或配置错误 | 2 |
| 目标记录不存在 | 3 |
| 外部依赖不可用 | 4 |
| 磁盘空间不足 | 5 |
| 导入或下载执行失败 | 10 |

## 3. `init`

职责：

- 创建 `env/`。
- 创建默认 `env/config.toml`，已存在则不覆盖。
- 创建默认下载目录。
- 初始化 SQLite schema。

幂等要求：

- 重复运行不删除数据库。
- 重复运行不覆盖用户配置。
- schema 初始化可重复执行。

成功输出：

```text
Initialized DLTreeDownloader
Config: env/config.toml
Database: env/dltree.sqlite3
Downloads: downloads
```

## 4. `import`

参数：

```text
dltree import <xlsx_path>
```

成功输出字段：

```text
Import completed
Source: files/DL tree 260308.xlsx
Rows: 74917
Inserted works: ...
Updated works: ...
Skipped works: ...
Link sets changed: ...
Errors: ...
Database: env/dltree.sqlite3
```

若 `Errors > 0`，提示用户可通过后续扩展命令或直接查 `import_errors` 排查。

## 5. `search-code`

输入：

```text
dltree search-code RJ01548502
```

查询：

```sql
SELECT ...
FROM works
WHERE work_code = ?
  AND is_deleted = 0;
```

显示字段：

```text
work_code
title
sale_date
circle_raw
voice_actor_raw
archive_size_raw
active_link_count
active_link_bytes
```

未找到时：

```text
No local work found for RJ01548502. Import the latest workbook and try again.
```

退出码为 3。

## 6. `search-voice`

输入：

```text
dltree search-voice 柚木つばめ --limit 50
```

查询策略：

- 规范化输入为 `query_normalized`。
- 在 `voice_actors.name_normalized LIKE '%query%'` 上搜索。
- join `work_voice_actors` 和 `works`。
- 过滤 `works.is_deleted = 0`。
- 排序：`sale_date DESC NULLS LAST`，再 `work_code DESC`。
- 默认 `limit = 50`。

显示列：

```text
work_code | sale_date | title | circle | archive_size
```

SQLite 没有标准 `NULLS LAST` 时，可用：

```sql
ORDER BY works.sale_date IS NULL, works.sale_date DESC, works.work_code DESC
```

## 7. `search-circle`

输入：

```text
dltree search-circle ホロクサミドリ --limit 50
```

查询策略：

- 规范化输入。
- 在 `circles.name_normalized LIKE '%query%'` 上搜索。
- join `work_circles` 和 `works`。
- 过滤 visible works。
- 排序同 `search-voice`。

显示列：

```text
work_code | sale_date | title | voice_actor | archive_size
```

## 8. `info`

输入：

```text
dltree info RJ01548502
```

展示：

- 作品编码。
- 标题。
- 销售日期。
- 类型。
- 标签。
- 备注。
- 声优 raw。
- 社团 raw。
- 档案大小 / MP3 大小。
- active links 表格：
  - 序号。
  - group。
  - file_name。
  - display size。
  - 是否 `.par2`。

不直接显示完整 MEGA URL，除非未来增加 `--show-url`。原因是普通查看详情时 URL 会占满屏幕。

## 9. `doctor`

检查项：

| 检查 | 成功标准 |
|---|---|
| 配置文件 | 可读取、必需 key 存在。 |
| 数据库 | 文件可打开，schema version 支持。 |
| 下载目录 | 路径可解析；不存在时父目录存在。 |
| MEGAcmd | `mega-whoami` 与 `mega-get` 可执行。 |
| MEGA 登录 | `mega-whoami` 返回成功。 |

输出建议：

```text
Config       OK
Database     OK
Downloads    OK
mega-get     OK
mega-whoami  OK
Login        OK
```

若未登录：

```text
Login        Not logged in
Run mega-login manually, then run dltree doctor again.
```

