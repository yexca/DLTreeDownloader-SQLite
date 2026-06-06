# Implementation Plan

## Phase 1: Project Skeleton

Create:

```text
DLTreeDownloader/
  dltree/
    __init__.py
    cli.py
    config.py
    db.py
    importer.py
    models.py
    mega.py
    search.py
    sizes.py
  env/
  tests/
  requirements.txt
  setup_env.ps1
```

Recommended dependencies:

```text
openpyxl
typer
rich
```

## Phase 2: Database Initialization

Implement:

- `dltree init`
- SQLite schema creation
- Config creation
- Database path resolution from `env/config.toml`

Acceptance checks:

- Running `dltree init` creates `env/dltree.sqlite3`.
- Running it twice is safe.
- Required tables and indexes exist.

## Phase 3: Excel Import

Implement:

- Workbook header validation.
- Row streaming with `openpyxl.load_workbook(read_only=True, data_only=True)`.
- Text normalization.
- Size parsing.
- MEGA JSON parsing.
- Work upsert.
- Voice actor normalization and join-table refresh.
- Circle normalization and join-table refresh.
- Link set hashing and replacement.
- Import statistics.

Acceptance checks:

- Import current `DL tree 260308.xlsx`.
- Database has 74,917 works.
- Active link count equals parsed link item count.
- Duplicate import should not duplicate works or active links.
- Re-import after modifying one row's link JSON should mark old links deleted and add new active links.

## Phase 4: Search Commands

Implement:

- `search-code`
- `info`
- `search-voice`
- `search-circle`

Acceptance checks:

- Exact code lookup finds existing works.
- Missing code returns a clear message.
- Voice actor search returns works for known actor samples.
- Circle search returns works for known circle samples.

## Phase 5: MEGAcmd Integration

Implement:

- `doctor`
- MEGAcmd executable checks.
- Login check through `mega-whoami`.
- Download command dry validation.
- Download execution through `mega-get`.
- Download result logging.

Acceptance checks:

- If MEGAcmd is missing, `doctor` reports it clearly.
- If not logged in, download stops before disk check or network call.
- If insufficient disk space, download stops before calling `mega-get`.
- If enough space and logged in, each selected URL is passed to `mega-get`.

## Phase 6: Tests

Minimum tests:

- Size parser:
  - `397.64 MB`
  - `4.10 GB`
  - `0 B`
  - `117 KB`
- Voice actor parser:
  - one actor
  - actors separated by four spaces
  - actors separated by `、`
- Link parser:
  - valid JSON
  - invalid JSON
  - missing `S`
  - non-integer `S`
- Import idempotency:
  - import same sample twice
  - active links remain unique
- Link update:
  - old active links become deleted
  - new active links are visible
- Disk check:
  - enough space
  - insufficient space
- MEGAcmd wrapper:
  - use mocked subprocess calls

## Phase 7: Documentation

Create:

```text
README.md
```

Include:

- Setup instructions.
- Import example.
- Search examples.
- Download example.
- MEGAcmd login note.
- Database location.

## Risks And Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Future workbook changes column order | Import breaks | Validate by header names, not fixed positions. |
| Future workbook adds link root keys besides `C` | Missing links | Store `link_group` dynamically for each root key. |
| Voice actor separators are inconsistent | Search misses works | Store raw string and normalized split mappings; improve parser iteratively. |
| MEGAcmd first call fails after login | Download unreliable | Run `mega-whoami` before `mega-get`. |
| Disk space check underestimates temporary usage | Download may fail midway | Add configurable safety margin. |
| Large import is slow | Bad UX | Use read-only workbook streaming, transactions, and indexed SQLite writes. |

## Suggested Defaults

- Database: `env/dltree.sqlite3`
- Config: `env/config.toml`
- Downloads: `downloads/<work_code>/`
- Download default: exclude `.par2`, unless `include_par2_by_default = true`
- Search result limit: 50 rows, with `--limit` override
- Import mode: upsert by `work_code`

