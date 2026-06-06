# Coding Guide

本文件夹记录 DLTreeDownloader 的编码实施顺序。它承接：

- `Requirements Analysis/`
- `High-Level Design/`
- `Detailed Design/`
- `documents/`

建议按以下顺序开发：

1. `01_project_skeleton.md`
2. `02_core_rules.md`
3. `03_database_layer.md`
4. `04_excel_import.md`
5. `05_query_commands.md`
6. `06_download_and_megacmd.md`
7. `07_testing_docs_acceptance.md`

## 总体原则

先完成稳定的数据入口，再扩展查询和下载：

```text
项目骨架 -> 纯规则模块 -> 数据库访问 -> Excel 导入 -> 查询命令 -> 下载集成 -> 测试文档验收
```

不要一开始就做下载。这个项目的地基是可靠地把 Excel 导入 SQLite，并保证重复导入、链接变化和行级错误都可追踪。

