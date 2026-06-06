# SQLite Database Design

## 1. Design Goals

The database should support:

- Exact lookup by work code.
- Search by voice actor.
- Search by circle.
- Repeat imports from updated Excel files.
- Historical preservation of obsolete download links.
- Fast download size calculation.

The user's initial idea was four tables:

- Voice actors
- Circles
- Work information
- Download links

Recommended implementation expands this slightly with join tables because a work can have multiple voice actors.

## 2. Recommended Tables

### `works`

Stores one row per work.

```sql
CREATE TABLE works (
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
```

Notes:

- `work_code` is unique.
- `is_deleted` is reserved for future cases where a work disappears from a later full import.
- `source_row_number` helps debug import problems.

### `voice_actors`

```sql
CREATE TABLE voice_actors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);
```

### `work_voice_actors`

```sql
CREATE TABLE work_voice_actors (
    work_id INTEGER NOT NULL,
    voice_actor_id INTEGER NOT NULL,
    PRIMARY KEY (work_id, voice_actor_id),
    FOREIGN KEY (work_id) REFERENCES works(id),
    FOREIGN KEY (voice_actor_id) REFERENCES voice_actors(id)
);
```

### `circles`

```sql
CREATE TABLE circles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    name_normalized TEXT NOT NULL
);
```

### `work_circles`

Even if v1 treats each work as having one circle, a join table keeps the model flexible.

```sql
CREATE TABLE work_circles (
    work_id INTEGER NOT NULL,
    circle_id INTEGER NOT NULL,
    PRIMARY KEY (work_id, circle_id),
    FOREIGN KEY (work_id) REFERENCES works(id),
    FOREIGN KEY (circle_id) REFERENCES circles(id)
);
```

### `download_links`

Stores current and historical link records.

```sql
CREATE TABLE download_links (
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
```

Recommended constraints and indexes:

```sql
CREATE UNIQUE INDEX idx_download_links_active_unique
ON download_links(work_id, link_group, file_name, mega_url, size_bytes)
WHERE is_deleted = 0;

CREATE INDEX idx_download_links_work_active
ON download_links(work_id, is_deleted);
```

### `imports`

Stores import history and makes troubleshooting easier.

```sql
CREATE TABLE imports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_path TEXT NOT NULL,
    source_file_name TEXT NOT NULL,
    source_file_size INTEGER,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    total_rows INTEGER DEFAULT 0,
    inserted_works INTEGER DEFAULT 0,
    updated_works INTEGER DEFAULT 0,
    skipped_works INTEGER DEFAULT 0,
    link_sets_changed INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    notes TEXT
);
```

### `import_errors`

```sql
CREATE TABLE import_errors (
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
```

### `downloads`

Optional but recommended for tracking user activity.

```sql
CREATE TABLE downloads (
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

## 3. Indexes

```sql
CREATE INDEX idx_works_code ON works(work_code);
CREATE INDEX idx_works_title ON works(title);
CREATE INDEX idx_voice_name_normalized ON voice_actors(name_normalized);
CREATE INDEX idx_circle_name_normalized ON circles(name_normalized);
CREATE INDEX idx_works_visible ON works(is_deleted);
```

Optional for better text search:

```sql
CREATE VIRTUAL TABLE works_fts USING fts5(
    work_code,
    title,
    tags_raw,
    voice_actor_raw,
    circle_raw,
    content='works',
    content_rowid='id'
);
```

FTS can be deferred until normal `LIKE` search feels too slow.

## 4. Link Change Detection

For each imported work, parse active link items into normalized tuples:

```text
(link_group, link_order, file_name, mega_url, size_bytes)
```

Create a stable `content_hash` over the normalized active link set:

```text
sha256(json.dumps(sorted_links, ensure_ascii=False, sort_keys=True))
```

Compare with the currently active link set in the database:

- If no active link set exists: insert imported links.
- If hash is the same: update `last_seen_at`, skip link replacement.
- If hash differs:
  - Set existing active links for that work to `is_deleted = 1`, `deleted_at = now`.
  - Insert imported links as active.
  - Increment `link_sets_changed`.

Use the full set hash for change detection, not only individual URL uniqueness, because file count, file names, order, and size can also change.

## 5. Work Metadata Update Policy

When an existing work appears in a later import:

- Update metadata fields from the latest workbook.
- Update `last_seen_at`.
- Rebuild voice actor mappings for that work.
- Rebuild circle mappings for that work.
- Apply link replacement only if the active link set changed.

When a row has the same work code but changed title, tags, date, or size display fields, treat the workbook as the new source of truth.

## 6. Transaction Policy

Recommended import transaction model:

- Use one database transaction for the whole import.
- Use batched commits only if memory or lock duration becomes a real issue.
- Always write an `imports` row at start.
- If the import fails hard, mark `imports.status = 'failed'` with the error.

For v1, whole-import transaction is simpler and protects against partial updates.

