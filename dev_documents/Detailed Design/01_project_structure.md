# Project Structure Detail

## 1. 推荐目录结构

```text
DLTreeDownloader/
  dltree/
    __init__.py
    cli.py
    app.py
    config.py
    db.py
    schema.sql
    importer.py
    link_parser.py
    normalizers.py
    models.py
    repositories.py
    search.py
    sizes.py
    mega.py
    filesystem.py
    exceptions.py
  tests/
    fixtures/
      sample.xlsx
    test_sizes.py
    test_normalizers.py
    test_link_parser.py
    test_importer.py
    test_search.py
    test_download_checks.py
  env/
  downloads/
  documents/
  requirements.txt
  setup_env.ps1
  README.md
```

## 2. 模块职责

| 模块 | 主要职责 | 不应负责 |
|---|---|---|
| `cli.py` | 定义 Typer 命令、参数、Rich 输出、退出码。 | SQL 拼接、Excel 解析、subprocess 细节。 |
| `app.py` | 编排用例，例如 import/search/download/doctor。 | 用户界面展示细节。 |
| `config.py` | 创建、读取、校验 `env/config.toml`。 | 初始化数据库 schema。 |
| `db.py` | SQLite 连接、事务边界、schema 初始化。 | 业务查询和导入规则。 |
| `schema.sql` | 数据库 DDL、索引、初始 schema version。 | Python 逻辑。 |
| `importer.py` | Excel 行读取、字段映射、导入统计、事务内 upsert。 | CLI 输出、MEGAcmd 调用。 |
| `link_parser.py` | 解析 `MEGA链接` JSON，生成链接项和集合哈希。 | 数据库写入。 |
| `normalizers.py` | 文本、日期、声优、社团、work code 规范化。 | 下载检查。 |
| `models.py` | dataclass / TypedDict 数据结构。 | 持久化实现。 |
| `repositories.py` | 所有数据库读写函数。 | Rich 展示或 Excel 文件读取。 |
| `search.py` | 搜索用例和结果 DTO。 | CLI 参数解析。 |
| `sizes.py` | 人类可读尺寸解析、byte 展示、空间需求计算。 | 文件系统实际空间查询。 |
| `mega.py` | MEGAcmd 可用性、登录检查、`mega-get` 调用。 | 选择下载文件。 |
| `filesystem.py` | 路径解析、最近存在父目录、磁盘空间查询。 | 下载业务规则。 |
| `exceptions.py` | 用户可见异常类型和退出码映射。 | 具体业务处理。 |

## 3. 依赖方向

推荐依赖方向：

```text
cli -> app -> repositories / importer / search / mega / filesystem
importer -> normalizers / link_parser / repositories / sizes
search -> repositories
mega -> subprocess
filesystem -> pathlib / shutil
```

约束：

- `cli.py` 只捕获应用层异常，并把异常转换为用户可见提示和退出码。
- `repositories.py` 是唯一直接执行业务 SQL 的模块。
- `importer.py` 允许使用数据库事务，但数据库连接由 `app.py` 或 `db.py` 注入。
- `mega.py` 所有命令必须使用列表参数调用，不通过 shell 字符串执行。

## 4. 关键数据结构

建议使用 `dataclasses.dataclass(frozen=True)` 表示解析后的不可变输入：

```python
@dataclass(frozen=True)
class WorkRow:
    source_row_number: int
    work_code: str
    title: str | None
    tags_raw: str | None
    sale_date: str | None
    voice_actor_raw: str | None
    voice_actor_names: tuple[str, ...]
    note: str | None
    work_type: str | None
    circle_raw: str | None
    circle_names: tuple[str, ...]
    archive_size_raw: str | None
    archive_size_bytes: int | None
    mp3_size_raw: str | None
    mp3_size_bytes: int | None
```

```python
@dataclass(frozen=True)
class LinkItem:
    link_group: str
    link_order: int
    file_name: str
    mega_url: str
    size_bytes: int
```

```python
@dataclass
class ImportStats:
    total_rows: int = 0
    inserted_works: int = 0
    updated_works: int = 0
    skipped_works: int = 0
    link_sets_changed: int = 0
    error_count: int = 0
```

## 5. 实现顺序建议

1. `config.py`、`db.py`、`schema.sql`。
2. `normalizers.py`、`sizes.py`、`link_parser.py` 及单元测试。
3. `repositories.py` 基础 CRUD。
4. `importer.py` 和导入集成测试。
5. `search.py` 与查询命令。
6. `mega.py`、`filesystem.py` 与下载命令。
7. `doctor`、README、二次开发文档。

