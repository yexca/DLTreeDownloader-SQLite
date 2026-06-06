# 02 Core Rules

## 目标

先实现不依赖数据库、Excel 和 MEGAcmd 的纯规则模块，为导入、查询和下载提供稳定基础。

## 负责模块

```text
dltree/models.py
dltree/normalizers.py
dltree/sizes.py
dltree/link_parser.py
```

## 实现内容

- 定义核心数据结构：
  - `WorkRow`
  - `LinkItem`
  - `ImportStats`
  - 查询结果 DTO
  - 下载请求和结果 DTO
- 文本规范化：
  - trim。
  - 空字符串转 null。
  - 字面量 `null` 转 null。
- work code 规范化：
  - 使用 Excel `RJcode` 列。
  - 内部字段命名为 `work_code`。
  - 不限制为 RJ 编码。
- 声优拆分：
  - 连续两个及以上空格。
  - `、`、`，`、`,`。
- 社团处理：
  - v1 整格作为一个社团名。
  - 不按 `/`、`&` 或标点拆分。
- 日期规范化。
- 人类可读尺寸解析：
  - `B`
  - `KB`
  - `MB`
  - `GB`
  - `TB`
- MEGA JSON 解析：
  - 遍历根分组。
  - 读取 `F`、`L`、`S`。
  - 生成 `LinkItem`。
- 链接集合 hash。

## 完成标准

- 所有纯规则函数都有单元测试。
- 不需要真实 Excel 文件即可测试。
- 不需要 SQLite 即可测试。
- 不需要 MEGAcmd 即可测试。

