# 03 Database Layer

## 目标

实现 SQLite schema 和数据库访问层，为导入幂等、查询和下载记录打基础。

## 负责模块

```text
dltree/db.py
dltree/schema.sql
dltree/repositories.py
```

## 实现内容

- 初始化 schema。
- 启用 `PRAGMA foreign_keys = ON`。
- 创建 `schema_meta` 版本表。
- 创建核心表：
  - `works`
  - `voice_actors`
  - `work_voice_actors`
  - `circles`
  - `work_circles`
  - `download_links`
  - `imports`
  - `import_errors`
  - `downloads`
- 创建必要索引。
- 实现 repository 函数：
  - work upsert。
  - 声优映射刷新。
  - 社团映射刷新。
  - active links 查询。
  - 链接变化替换。
  - import 记录。
  - import error 记录。
  - download 记录。

## 关键规则

- `work_code` 是作品唯一键。
- 普通查询必须过滤 `works.is_deleted = 0`。
- 普通下载链接查询必须过滤 `download_links.is_deleted = 0`。
- 链接变化时旧 active links 只标记 deleted，不物理删除。

## 完成标准

- schema 可重复初始化。
- repository 测试通过。
- 重复插入同一个作品不会产生重复作品。
- 重复插入同一批 active links 不会产生重复 active links。
- 链接变化时旧链接变 deleted，新链接 active。

