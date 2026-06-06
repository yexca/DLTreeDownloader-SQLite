# Test Design

## 1. 测试分层

| 层级 | 目标 | 示例 |
|---|---|---|
| 单元测试 | 验证纯函数规则。 | size parser、voice parser、link parser。 |
| 集成测试 | 验证 SQLite + importer + repository。 | 小型 xlsx fixture 导入两次。 |
| CLI 测试 | 验证命令参数、退出码和主要输出。 | Typer CliRunner。 |
| 外部依赖 mock | 验证 MEGAcmd 与磁盘检查。 | mock subprocess、mock disk usage。 |

## 2. fixture 设计

`tests/fixtures/sample.xlsx` 建议包含 6 到 10 行：

| 行 | 目的 |
|---|---|
| 正常单链接作品 | 基础导入成功。 |
| 多链接作品 | 下载大小求和。 |
| 含 `.par2` 作品 | 默认排除和 include 规则。 |
| 多声优作品 | 声优拆分。 |
| 空标题/空社团作品 | null 展示和查询稳定性。 |
| 非 RJ 编码作品 | `work_code` 不限制格式。 |
| 非法 size 作品 | 行级错误但继续导入。 |
| 非法 MEGA JSON 作品 | 作品 upsert，链接跳过。 |

## 3. 单元测试清单

### Size parser

```text
0 B -> 0
117 KB -> 119808
397.64 MB -> int(397.64 * 1024 * 1024)
4.10 GB -> int(4.10 * 1024 * 1024 * 1024)
bad -> None
```

### Text normalizer

```text
None -> None
"" -> None
" null " -> None
"  A  " -> "A"
```

### Voice actor parser

```text
"神代そら" -> ["神代そら"]
"神代そら    海音ミヅチ" -> ["神代そら", "海音ミヅチ"]
"A、B，C,D" -> ["A", "B", "C", "D"]
```

### Circle parser

```text
"N&R" -> ["N&R"]
"&MORE" -> ["&MORE"]
"リリムワークス /【兎月りりむ。公式】" -> 原样一个名称
```

### Link parser

```text
valid JSON -> LinkItem list
invalid JSON -> row error
missing F/L/S -> item error
non-integer S -> item error
multiple root groups -> preserve link_group
```

## 4. 导入集成测试

### 初始化 schema

断言：

- 所有表存在。
- 所有关键索引存在。
- `schema_meta.schema_version = 1`。

### 首次导入

断言：

- `works` 行数等于 fixture 有效 work_code 行数。
- 声优和社团映射正确。
- active links 行数等于有效 link item 数。
- `imports.status = completed`。
- 行级错误数符合预期。

### 重复导入

同一 fixture 导入两次：

- `works` 行数不变。
- active links 行数不变。
- 第二次导入的 skipped works 大于 0。
- 不违反 active unique index。

### 链接变化

修改一个作品的 link JSON：

- 旧 active links 变为 `is_deleted = 1`。
- 新 links 为 active。
- 普通 `info` 只展示新 links。
- `link_sets_changed += 1`。

## 5. 搜索测试

`search-code`：

- 精确 code 命中。
- 非 RJ code 命中。
- 缺失 code 返回 not found。

`search-voice`：

- 用完整声优名命中。
- 用部分名称命中。
- 限制 `--limit` 生效。

`search-circle`：

- `N&R` 作为整体命中。
- 不因 `&` 或 `/` 被错误拆分。

## 6. 下载检查测试

文件选择：

- 默认排除 `.par2`。
- `--include-par2` 包含 `.par2`。
- 只剩 `.par2` 时给出明确提示。

空间计算：

- selected bytes + 5%。
- 小文件使用最小 512 MB margin。
- 空间不足抛出 `DiskSpaceError`。

MEGAcmd：

- `mega-get` 缺失 -> `ExternalDependencyError`。
- `mega-whoami` 失败 -> 登录失败提示。
- `mega-get` 失败 -> `downloads.status = failed`。
- 所有链接成功 -> `downloads.status = completed`。

## 7. CLI 测试

使用 Typer `CliRunner`：

```python
from typer.testing import CliRunner
```

覆盖：

- `dltree init` 可重复执行。
- `dltree import tests/fixtures/sample.xlsx` 输出统计。
- `dltree search-code <code>` 输出 code。
- `dltree download <code> --yes` 在 mock MEGAcmd 下成功。
- 配置错误时退出码为 2。

## 8. 验收测试

使用真实文件 `files/DL tree 260308.xlsx`：

1. `dltree init`
2. `dltree import "files/DL tree 260308.xlsx"`
3. 断言 works 约 74,917 行。
4. 重复导入一次，断言 active links 不重复。
5. 用已知声优搜索。
6. 用已知社团搜索。
7. 在 mock 或真实 MEGAcmd 环境下运行 `dltree doctor`。

