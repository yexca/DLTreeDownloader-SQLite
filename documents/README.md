# DLTreeDownloader Developer Documents

本目录面向二次开发者，说明如何理解、扩展和维护 DLTreeDownloader。

建议阅读顺序：

1. `developer_guide.md`
2. `architecture.md`
3. `data_contract.md`
4. `extension_points.md`
5. `testing_guide.md`

## 文档定位

这些文档不是普通用户使用手册，而是项目推送后给维护者和二次开发者看的说明：

- 项目由哪些模块组成。
- 根目录 `run-install.bat` 如何准备本地运行环境。
- 数据库和 Excel 输入有什么契约。
- 新增命令、字段、下载策略时应改哪里。
- 测试 fixture 如何构造。
- 哪些规则是 v1 的稳定约束，哪些是未来可扩展点。

## 与设计文档的关系

- `Requirements Analysis/` 记录需求和数据画像。
- `High-Level Design/` 记录概要架构与关键决策。
- `Detailed Design/` 记录实现级设计。
- `documents/` 记录二次开发者如何使用这些设计来继续开发。

实现阶段若设计发生变化，应同步更新本目录，避免后续维护者只看代码猜规则。
