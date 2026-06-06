# 04 Excel Import

## 目标

实现核心导入流程，把 Excel 工作簿可靠写入 SQLite，并支持后续重复导入和链接历史追踪。

## 负责模块

```text
dltree/importer.py
dltree/app.py
dltree/cli.py
```

同时依赖：

```text
dltree/normalizers.py
dltree/sizes.py
dltree/link_parser.py
dltree/repositories.py
```

## 实现内容

- 实现 `dltree import <xlsx_path>`。
- 使用 `openpyxl.load_workbook(read_only=True, data_only=True)`。
- 按表头名称校验必需列。
- 逐行读取数据。
- 转换为 `WorkRow`。
- 解析 `MEGA链接` 为 `LinkItem` 列表。
- upsert `works`。
- 刷新声优映射。
- 刷新社团映射。
- 判断链接集合是否变化。
- 写入导入统计。
- 写入行级错误。

## 必需表头

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

## 完成标准

- 小型 fixture 可导入。
- 真实 `files/DL tree 260308.xlsx` 可导入。
- 重复导入不重复作品。
- 重复导入不重复 active links。
- 链接变化时旧链接标记为 deleted，新链接 active。
- 非法行记录到 `import_errors`，不让整个导入静默失败。

