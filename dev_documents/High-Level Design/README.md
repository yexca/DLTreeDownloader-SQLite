# High-Level Design

本文件夹记录 DLTreeDownloader 的概要设计成果，承接 `Requirements Analysis` 中的需求分析。

建议阅读顺序：

1. `01_system_context.md`
2. `02_architecture.md`
3. `03_data_import_design.md`
4. `04_cli_download_design.md`
5. `05_quality_and_decisions.md`

## 设计目标

DLTreeDownloader 是一个本地 Python + SQLite 命令行工具，用于导入 DL tree Excel 工作簿、查询作品信息，并在本地磁盘空间充足且 MEGAcmd 可用时下载指定作品。

概要设计阶段重点解决：

- 系统边界和外部依赖。
- 模块划分和主要职责。
- 数据导入、查询、下载的主流程。
- 关键数据一致性策略。
- 质量属性、风险和待确认决策。

## 主要设计结论

- 采用单机 CLI 架构，不引入后台服务或 GUI。
- 使用 SQLite 作为本地持久化数据库。
- 使用 `work_code` 作为内部作品编码字段，导入时映射 Excel 的 `RJcode` 列。
- Excel 导入采用“按 `work_code` upsert，下载链接保留历史”的策略。
- 下载前必须完成作品存在性检查、活动链接检查、MEGAcmd 状态检查和磁盘空间检查。
- 默认下载非 `.par2` 文件，`.par2` 通过配置或命令参数显式包含。

## 与需求分析的关系

本阶段不替代需求分析中的字段画像和表结构建议，而是把它们组织成可实现的系统方案。详细字段、约束、测试样例仍以 `Requirements Analysis` 中的分析为依据。

