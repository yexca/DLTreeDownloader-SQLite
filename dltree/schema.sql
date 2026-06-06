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
