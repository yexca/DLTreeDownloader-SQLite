# Import Detail

## 1. 输入约束

导入命令：

```text
dltree import <xlsx_path>
```

输入文件要求：

- 文件必须存在。
- 扩展名建议为 `.xlsx`，但实际打开失败才视为硬错误。
- 使用第一张 sheet，当前观察为 `Sheet1`。
- 第 1 行是表头。
- 必需表头必须按名称匹配，不依赖固定列号。

必需表头：

```text
RJcode
标签
MEGA链接
销售日期
声优
标题
备注
类型
社团
档案大小
MP3大小
```

## 2. 导入主流程

```text
validate xlsx path
open workbook read_only=True data_only=True
validate headers
create imports row with status=running
begin transaction
for each data row:
  normalize workbook row into WorkRow
  upsert works
  refresh voice actor mappings
  refresh circle mappings
  parse MEGA JSON into LinkItem list
  compare active link set and replace if changed
  update in-memory ImportStats
commit transaction
finish imports row with status=completed
```

硬错误时：

```text
rollback transaction
finish imports row with status=failed
return exit code 10
```

行级错误时：

```text
write import_errors
increment error_count
continue next row if possible
```

## 3. 字段映射

| Excel 列 | WorkRow 字段 | 规则 |
|---|---|---|
| `RJcode` | `work_code` | trim；空值是行级错误。 |
| `标签` | `tags_raw` | trim；空字符串和 `null` 转为 null。 |
| `MEGA链接` | `LinkItem[]` | JSON 解析；异常写入 import_errors。 |
| `销售日期` | `sale_date` | 转 ISO date；空值为 null。 |
| `声优` | `voice_actor_raw` / `voice_actor_names` | 保留 raw；解析映射名。 |
| `标题` | `title` | trim；空值为 null。 |
| `备注` | `note` | trim；空字符串和 `null` 转为 null。 |
| `类型` | `work_type` | trim；空值为 null。 |
| `社团` | `circle_raw` / `circle_names` | v1 整格视为一个社团名。 |
| `档案大小` | `archive_size_raw` / `archive_size_bytes` | raw 保留；可解析则写 bytes。 |
| `MP3大小` | `mp3_size_raw` / `mp3_size_bytes` | raw 保留；可解析则写 bytes。 |

## 4. 文本规范化

`normalize_optional_text(value)`：

- `None` -> `None`
- 非字符串先转字符串，但日期类型除外。
- trim 首尾空白。
- `""` -> `None`
- 大小写不敏感的 `"null"` -> `None`
- 其他文本原样保存。

`normalize_search_text(value)`：

- trim。
- 连续空白压缩为单个空格。
- 使用 `casefold()`。

`normalize_work_code(value)`：

- trim。
- 不强制大写。
- 不限制编码前缀。
- 空值报 `missing_work_code`。

## 5. 日期规范化

`销售日期` 可来自 Excel datetime、date 或字符串：

- `datetime.date` / `datetime.datetime` -> `YYYY-MM-DD`
- 字符串先 trim；空为 null。
- 已经是 `YYYY-MM-DD` 的字符串原样保存。
- 其他字符串暂时原样保存，并记录 warning 类型行级错误：`invalid_sale_date_format`。

该策略避免因为少量日期格式异常阻断整批导入。

## 6. 尺寸解析

支持单位：

```text
B
KB
MB
GB
TB
```

规则：

- 大小写不敏感。
- `KB/MB/GB/TB` 按 1024 进制。
- 解析失败返回 `None`，保留 raw，并写入 `invalid_size` 行级错误。
- 下载空间计算不使用 `archive_size_bytes` 或 `mp3_size_bytes`，而使用 MEGA JSON 的 `S`。

## 7. 声优解析

`parse_voice_actors(raw)`：

1. raw 为空时返回空 tuple。
2. 优先按连续两个及以上空格拆分。
3. 再按 `、`、`，`、`,` 拆分每个片段。
4. trim。
5. 去空。
6. 按首次出现顺序去重。

示例：

| 输入 | 输出 |
|---|---|
| `神代そら    海音ミヅチ` | `神代そら`, `海音ミヅチ` |
| `A、B，C,D` | `A`, `B`, `C`, `D` |
| 空值 | 空列表 |

## 8. 社团解析

`parse_circles(raw)`：

- raw 为空时返回空 tuple。
- v1 不拆分 `/`、`&`、括号或标点。
- trim 后整格作为一个社团名。

这样可以保留类似 `N&R`、`&MORE`、`リリムワークス /...` 的真实名称。

## 9. MEGA JSON 解析

输入形态：

```json
{
  "C": [
    {"F": "RJ01548502.zip", "L": "https://mega.nz/file/...", "S": "3249155727"}
  ]
}
```

解析规则：

- JSON 根必须是 object。
- 遍历根 object 的每个 key，key 保存为 `link_group`。
- 每个 group 的 value 必须是 array。
- 每个 item 必须包含：
  - `F`: 文件名，非空字符串。
  - `L`: MEGA URL，非空字符串。
  - `S`: byte 数，可转为非负整数。
- `link_order` 按同一个 group 内的数组顺序，从 0 开始。
- 单个 item 异常记录 `invalid_mega_link_item`，继续解析其他 item。
- 根 JSON 完全无法解析时记录 `invalid_mega_json`，该作品仍可 upsert，但没有活动链接更新。

## 10. 链接集合哈希

`content_hash` 代表同一作品的完整活动链接集合：

```python
payload = [
    {
        "link_group": item.link_group,
        "link_order": item.link_order,
        "file_name": item.file_name,
        "mega_url": item.mega_url,
        "size_bytes": item.size_bytes,
    }
    for item in links
]
digest = sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
```

比较步骤：

1. 查询该作品所有 active links。
2. 用同一算法计算当前 active link set hash。
3. 若 hash 相同：
   - 更新当前 active links 的 `last_seen_at`。
   - 不插入新链接。
4. 若 hash 不同：
   - 当前 active links 置 `is_deleted = 1`，`deleted_at = now`。
   - 插入新 links，`is_deleted = 0`。
   - 新 links 的 `content_hash` 均写入本次集合 hash。

## 11. 导入统计

统计项：

| 字段 | 递增条件 |
|---|---|
| `total_rows` | 每读取一条数据行。 |
| `inserted_works` | 新增 works。 |
| `updated_works` | 已存在作品且元数据发生变化。 |
| `skipped_works` | 已存在作品且元数据、链接集合均无变化。 |
| `link_sets_changed` | 链接集合 hash 不同并完成替换。 |
| `error_count` | 每条行级错误。 |

若同一行既更新元数据又更新链接：

- `updated_works += 1`
- `link_sets_changed += 1`

## 12. 行级错误类型

| 类型 | 场景 | 是否跳过整行 |
|---|---|---|
| `missing_work_code` | work code 为空。 | 是 |
| `invalid_sale_date_format` | 日期字符串不可规范化。 | 否 |
| `invalid_size` | `档案大小` 或 `MP3大小` 不可解析。 | 否 |
| `invalid_mega_json` | `MEGA链接` 不是合法 JSON。 | 否，仅跳过链接更新 |
| `invalid_mega_group` | 某个根 group 不是数组。 | 否，跳过该 group |
| `invalid_mega_link_item` | item 缺字段或字段非法。 | 否，跳过该 item |

