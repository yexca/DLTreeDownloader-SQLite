# Detailed Design

本文件夹记录 DLTreeDownloader 的详细设计，承接 `Requirements Analysis` 与 `High-Level Design`。

建议阅读顺序：

1. `01_project_structure.md`
2. `02_database_schema.md`
3. `03_import_detail.md`
4. `04_query_and_cli_detail.md`
5. `05_download_runtime_detail.md`
6. `06_config_error_logging.md`
7. `07_test_design.md`

## 详细设计目标

本阶段把概要设计中的系统边界、模块划分和流程，细化为可以直接进入实现的设计约束：

- Python 包目录和模块职责。
- SQLite schema、索引、状态值和迁移策略。
- Excel 导入的函数边界、数据规范化、事务和幂等规则。
- CLI 命令参数、输出结构和退出码。
- MEGAcmd 下载前置检查和执行记录。
- 配置、错误、日志和测试策略。

## v1 设计结论

- 项目以 `dltree` Python 包为核心，CLI 使用 Typer，终端展示使用 Rich。
- SQLite 采用显式 schema 初始化，v1 不引入复杂迁移框架，但保留 `schema_meta` 版本表。
- 导入以 `work_code` 作为作品唯一标识，Excel 的 `RJcode` 只作为导入层字段名。
- 导入时先更新作品元数据，再刷新声优、社团映射，最后处理下载链接集合。
- 下载链接集合用稳定哈希判断是否变化；变化时旧活动链接标记为 deleted，新链接插入为 active。
- 下载默认排除 `.par2`，除非配置或命令行显式包含。
- 下载命令必须先完成作品、链接、MEGAcmd、登录状态和磁盘空间检查，再调用 `mega-get`。

## 与后续实现的关系

实现时应优先保持本文件夹中的模块边界和状态语义。若实现阶段发现真实数据或 MEGAcmd 行为与本设计冲突，应更新对应详细设计文档，再修改代码。

