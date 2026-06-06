# Database Schema Detail

## 1. Schema 原则

- 所有时间字段统一保存 UTC ISO-8601 文本，例如 `2026-06-07T01:23:45Z`。
- 布尔字段使用 `INTEGER NOT NULL DEFAULT 0`。
- `work_code` 是作品业务唯一键，不限制为 RJ 编码。
- 普通用户查询必须过滤 `works.is_deleted = 0` 与 `download_links.is_deleted = 0`。
- v1 使用 `PRAGMA foreign_keys = ON`，但不级联删除作品数据。

## 2. Schema SQL

```sql
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT OR IGNORE INTO schema_meta(key, value)
VALUES ('schema_version', '1');

CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_code TEXT NOT NULL UNIQUE,
    title TEXT,
    tags_raw TEXT,
    sale_date TEXT,
    voice_actor_raw TEXT,
    note TEXT,
    work_type TEXT,
    circle_raw TEXT,
    archive_size_raw TEXT,
    archive_size_bytes INTEGER,
    mp3_size_raw TEXT,
    mp3_size_bytes INTEGER,
    source_row_number INTEGER,
    first_imported_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS voice_actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_voice_actors (
    work_id INTEGER NOT NULL,
    voice_actor_id INTEGER NOT NULL,
    PRIMARY KEY (work_id, voice_actor_id),
    FOREIGN KEY (work_id) REFERENCES works(id),
    FOREIGN KEY (voice_actor_id) REFERENCES voice_actors(id)
);

CREATE TABLE IF NOT EXISTS circles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_circles (
    work_id INTEGER NOT NULL,
    circle_id INTEGER NOT NULL,
    PRIMARY KEY (work_id, circle_id),
    FOREIGN KEY (work_id) REFERENCES works(id),
    FOREIGN KEY (circle_id) REFERENCES circles(id)
);

CREATE TABLE IF NOT EXISTS download_links (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    link_group TEXT NOT NULL DEFAULT 'C',
    file_name TEXT NOT NULL,
    mega_url TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    link_order INTEGER NOT NULL,
    content_hash TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_seen_at TEXT NOT NULL,
    is_deleted INTEGER NOT NULL DEFAULT 0,
    deleted_at TEXT,
    FOREIGN KEY (work_id) REFERENCES works(id)
);

CREATE TABLE IF NOT EXISTS imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    source_file_name TEXT NOT NULL,
    source_file_size INTEGER,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    total_rows INTEGER NOT NULL DEFAULT 0,
    inserted_works INTEGER NOT NULL DEFAULT 0,
    updated_works INTEGER NOT NULL DEFAULT 0,
    skipped_works INTEGER NOT NULL DEFAULT 0,
    link_sets_changed INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS import_errors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL,
    row_number INTEGER,
    work_code TEXT,
    error_type TEXT NOT NULL,
    message TEXT NOT NULL,
    raw_value TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (import_id) REFERENCES imports(id)
);

CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL,
    requested_at TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    selected_bytes INTEGER NOT NULL,
    free_bytes_before INTEGER,
    status TEXT NOT NULL,
    mega_exit_code INTEGER,
    message TEXT,
    FOREIGN KEY (work_id) REFERENCES works(id)
);
```

## 3. 索引

```sql
CREATE INDEX IF NOT EXISTS idx_works_code ON works(work_code);
CREATE INDEX IF NOT EXISTS idx_works_visible ON works(is_deleted);
CREATE INDEX IF NOT EXISTS idx_works_title ON works(title);
CREATE INDEX IF NOT EXISTS idx_voice_name_normalized ON voice_actors(name_normalized);
CREATE INDEX IF NOT EXISTS idx_circle_name_normalized ON circles(name_normalized);
CREATE INDEX IF NOT EXISTS idx_work_voice_work ON work_voice_actors(work_id);
CREATE INDEX IF NOT EXISTS idx_work_circle_work ON work_circles(work_id);
CREATE INDEX IF NOT EXISTS idx_download_links_work_active
ON download_links(work_id, is_deleted);

CREATE UNIQUE INDEX IF NOT EXISTS idx_download_links_active_unique
ON download_links(work_id, link_group, file_name, mega_url, size_bytes)
WHERE is_deleted = 0;
```

## 4. 状态值

`imports.status`：

| 值 | 含义 |
|---|---|
| `running` | 导入记录已创建，导入尚未结束。 |
| `completed` | 导入成功完成。 |
| `failed` | 发生硬错误，导入未完成。 |

`downloads.status`：

| 值 | 含义 |
|---|---|
| `planned` | 下载请求已创建，还未调用 MEGAcmd。 |
| `blocked` | 前置检查失败，未调用 MEGAcmd。 |
| `running` | 已开始调用 MEGAcmd。 |
| `completed` | 所有选中链接下载命令成功结束。 |
| `failed` | 至少一个选中链接下载命令失败。 |

## 5. Repository 函数边界

推荐函数：

```python
def init_schema(conn: sqlite3.Connection) -> None: ...
def create_import(conn, source_path: Path, now: str) -> int: ...
def finish_import(conn, import_id: int, status: str, stats: ImportStats, notes: str | None) -> None: ...
def add_import_error(conn, import_id: int, error: ImportRowError) -> None: ...

def get_work_by_code(conn, work_code: str, visible_only: bool = True) -> WorkRecord | None: ...
def upsert_work(conn, row: WorkRow, now: str) -> tuple[int, bool, bool]: ...
def refresh_voice_actor_mappings(conn, work_id: int, names: Sequence[str]) -> None: ...
def refresh_circle_mappings(conn, work_id: int, names: Sequence[str]) -> None: ...

def get_active_links(conn, work_id: int) -> list[LinkRecord]: ...
def replace_active_links_if_changed(conn, work_id: int, links: Sequence[LinkItem], now: str) -> bool: ...

def search_by_voice(conn, query: str, limit: int) -> list[WorkSearchResult]: ...
def search_by_circle(conn, query: str, limit: int) -> list[WorkSearchResult]: ...

def create_download(conn, request: DownloadRequest) -> int: ...
def update_download_status(conn, download_id: int, status: str, exit_code: int | None, message: str | None) -> None: ...
```

`upsert_work` 返回：

```text
(work_id, inserted, metadata_changed)
```

`replace_active_links_if_changed` 返回链接集合是否发生变化。

## 6. 迁移策略

v1 不引入 Alembic。启动 `dltree init` 时：

1. 打开 SQLite。
2. 启用 foreign key。
3. 执行 `schema.sql`。
4. 读取 `schema_meta.schema_version`。
5. 若版本大于当前程序支持版本，提示升级程序并退出。

后续版本可添加 `migrations/`：

```text
dltree/migrations/
  002_add_tags_table.sql
  003_add_download_file_status.sql
```

