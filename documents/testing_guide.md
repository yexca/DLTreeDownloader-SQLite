# Testing Guide

## 1. 测试目标

测试应优先覆盖会影响数据一致性和下载安全的规则：

- 重复导入不产生重复 active links。
- 链接变化保留历史。
- 声优和社团映射可查询。
- 下载前检查能阻止明显失败的下载。
- MEGAcmd 调用不通过 shell。

## 2. Fixture 原则

不要用完整 Excel 文件做常规测试。完整文件只用于验收测试。

常规测试使用小型 fixture：

```text
tests/fixtures/sample.xlsx
```

fixture 应覆盖：

- 正常单链接。
- 多链接。
- `.par2`。
- 多声优。
- 非 RJ 编码。
- 空字段。
- 非法 size。
- 非法 MEGA JSON。

## 3. 单元测试

本地测试使用安装脚本创建的虚拟环境运行：

```text
.venv/Scripts/python.exe -m pytest
```

`pyproject.toml` 已限制 pytest 只扫描 `tests/`，避免误扫 `env/python` 内的 Python 自带文件。

推荐覆盖：

```text
sizes.parse_size_to_bytes
sizes.format_bytes
normalizers.normalize_optional_text
normalizers.parse_voice_actors
normalizers.parse_circles
link_parser.parse_mega_links
link_parser.hash_link_set
```

这些函数应尽量不依赖数据库和文件系统。

## 4. 集成测试

使用临时 SQLite 文件：

```text
tmp_path / "dltree.sqlite3"
```

导入测试关注：

- schema 初始化。
- 首次导入。
- 重复导入。
- 链接变化。
- 行级错误记录。

搜索测试关注：

- `work_code` 精确查询。
- 声优 partial query。
- 社团整体名称 query。

## 5. 下载测试

不要依赖真实 MEGA 网络。

mock：

- `subprocess.run`
- `shutil.disk_usage`
- `shutil.which`

覆盖：

- MEGAcmd 缺失。
- 未登录。
- 空间不足。
- 默认排除 `.par2`。
- include `.par2`。
- `mega-get` 成功。
- `mega-get` 失败。

## 6. 验收测试

完整验收可以使用真实文件：

```text
files/DL tree 260308.xlsx
```

验收项：

- 导入完成。
- works 行数接近 74,917。
- 重复导入 active links 不重复。
- 查询已知作品、声优、社团可返回结果。
- `doctor` 能清楚报告 MEGAcmd 状态。

如果本机没有 MEGAcmd，验收不要求真实下载，但必须确认失败提示清楚。
