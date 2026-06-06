# Data Contract

## 1. Excel 输入契约

v1 依赖以下表头名称：

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

表头按名称匹配，列顺序可以变化。

`RJcode` 在程序内部映射为 `work_code`。它不只包含 RJ 编码，也可能包含 `VJ`、`BJ`、`d_` 或其他格式，因此实现不能用 `RJ\d+` 限制。

## 2. MEGA 链接契约

`MEGA链接` 是 JSON 文本。当前观察到根 key 为 `C`，但实现应遍历所有根 key。

每个链接 item：

```json
{
  "F": "file name",
  "L": "https://mega.nz/file/...",
  "S": "3249155727"
}
```

字段含义：

| 字段 | 含义 |
|---|---|
| `F` | 文件名。 |
| `L` | MEGA URL。 |
| `S` | 文件 byte 数，字符串或整数均可接受。 |

`S` 是下载空间计算的权威来源。

## 3. 数据库可见性契约

普通查询只展示：

```text
works.is_deleted = 0
download_links.is_deleted = 0
```

旧链接不删除，只标记：

```text
download_links.is_deleted = 1
download_links.deleted_at = now
```

这样可以追踪工作簿更新带来的链接变化。

## 4. 规范化契约

文本：

- trim 首尾空白。
- 空字符串和字面量 `null` 转为 null。
- raw 字段保留原始含义，不做激进拆分。

声优：

- 连续两个及以上空格可拆分。
- `、`、`，`、`,` 可拆分。
- 需要保留 `works.voice_actor_raw`。

社团：

- v1 把整格视为一个社团名。
- 不按 `/`、`&` 或标点拆分。

日期：

- 优先保存 `YYYY-MM-DD`。
- 异常日期不应导致整批导入失败。

## 5. 下载契约

下载候选文件来自 active links。

默认：

- 排除 `.par2`。
- 使用 `--include-par2` 或配置项包含 `.par2`。
- 输出目录默认 `downloads/<work_code>/`。

空间需求：

```text
sum(selected link size_bytes) + max(5%, 512 MB)
```

调用 MEGAcmd 前必须完成：

- 作品存在检查。
- active links 检查。
- MEGAcmd 可执行检查。
- `mega-whoami` 登录检查。
- 磁盘空间检查。

