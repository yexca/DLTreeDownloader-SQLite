# Extension Points

## 1. 新增搜索命令

示例：新增按标题搜索。

推荐步骤：

1. 在 `repositories.py` 增加 `search_by_title(conn, query, limit)`。
2. 在 `search.py` 增加应用层函数，统一处理 query normalizer 和 limit。
3. 在 `cli.py` 增加 `search-title` 命令。
4. 添加 CLI 测试。
5. 更新 README 和本文件。

注意：

- 搜索 visible works 时始终过滤 `works.is_deleted = 0`。
- 查询结果默认限制 50 条。

## 2. 新增 tag 规范化

v1 中 `tags_raw` 只保存原文。若后续需要 tag 搜索，可新增：

```text
tags
work_tags
```

推荐策略：

- 不删除 `works.tags_raw`。
- 先用小样本分析分隔符。
- 分隔规则写成纯函数并测试。
- 在导入时刷新 tag 映射，类似声优映射。

## 3. 新增下载文件选择

可能选项：

```text
--file-pattern <pattern>
--only-mp3
--exclude <pattern>
--interactive
```

约束：

- 文件选择必须发生在空间计算前。
- 确认摘要展示最终 selected links。
- `downloads.selected_bytes` 写最终选中文件总大小。
- 测试要覆盖 selected links 为空的情况。

## 4. 新增迁移

v1 不使用迁移框架，但保留 `schema_meta`。

后续新增 schema 版本时：

1. 增加迁移 SQL。
2. 程序启动读取当前版本。
3. 按顺序执行缺失迁移。
4. 更新 `schema_meta.schema_version`。
5. 添加从旧版本数据库升级的测试。

不要在未备份的情况下删除或重建用户数据库。

## 5. 新增外部下载器

如果未来支持非 MEGAcmd 下载器，应抽象接口：

```python
class Downloader:
    def check_available(self) -> CheckResult: ...
    def check_login(self) -> CheckResult: ...
    def download(self, url: str, output_dir: Path) -> DownloadResult: ...
```

MEGAcmd 作为一个实现。

约束：

- 应用层仍负责作品、链接和磁盘检查。
- 下载器只负责外部命令或网络下载。
- 不能把账号凭据保存到项目数据库。

## 6. 新增 GUI 或 Web API

如果后续增加 GUI 或 Web API：

- 复用 `app.py` 中的用例函数。
- 不从 GUI 直接调用 repository。
- 不绕过下载前置检查。
- 输出展示可以替换，业务规则不要复制一份。

