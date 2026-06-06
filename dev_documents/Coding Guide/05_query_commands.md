# 05 Query Commands

## 目标

在导入稳定后，实现用户查询入口，让用户能够确认作品是否存在、查看详情、按声优和社团检索。

## 负责模块

```text
dltree/search.py
dltree/app.py
dltree/cli.py
dltree/repositories.py
```

## 实现命令

```text
dltree search-code <work_code>
dltree search-voice <name> [--limit 50]
dltree search-circle <name> [--limit 50]
dltree info <work_code>
```

## 实现内容

`search-code`：

- 按 `work_code` 精确查询。
- 只查 visible works。
- 显示 compact metadata。

`search-voice`：

- 按规范化声优名称模糊查询。
- join `voice_actors`、`work_voice_actors`、`works`。
- 默认限制 50 条。

`search-circle`：

- 按规范化社团名称模糊查询。
- join `circles`、`work_circles`、`works`。
- 默认限制 50 条。

`info`：

- 展示作品完整元数据。
- 展示 active links。
- 默认不展示完整 MEGA URL。

## 完成标准

- 能按 work code 精确查询。
- 能按声优模糊查询。
- 能按社团模糊查询。
- `info` 能展示 active links 数量和大小。
- 缺失标题、声优、社团、日期时不会报错。
- 未找到作品时返回清楚提示和正确退出码。

