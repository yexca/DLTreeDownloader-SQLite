# Download Runtime Detail

## 1. 下载命令

```text
dltree download <work_code> [--output <dir>] [--include-par2] [--yes]
```

默认行为：

- 下载该作品所有 active 非 `.par2` 文件。
- 输出目录默认是 `downloads/<work_code>/`。
- 若配置 `download.include_par2_by_default = true`，默认包含 `.par2`。
- 命令行 `--include-par2` 优先于配置。
- 未传 `--yes` 时，在调用 `mega-get` 前要求确认。

## 2. 下载前置检查顺序

严格按以下顺序：

1. 读取并校验配置。
2. 查询 visible work。
3. 查询 active links。
4. 根据 `.par2` 规则选择文件。
5. 计算 selected bytes 与安全余量。
6. 检查 MEGAcmd 可执行文件。
7. 执行 `mega-whoami` 检查登录状态。
8. 解析输出目录，并检查所在磁盘可用空间。
9. 写入 `downloads` planned 记录。
10. 若需要确认，展示摘要并等待用户确认。
11. 创建输出目录。
12. 按链接调用 `mega-get`。
13. 更新 `downloads` 状态。

前置检查失败时，不创建输出目录，不调用 `mega-get`。

## 3. 文件选择规则

`.par2` 判断：

```python
file_name.casefold().endswith(".par2")
```

选择函数：

```python
def select_download_links(
    links: Sequence[LinkRecord],
    include_par2: bool,
) -> tuple[list[LinkRecord], list[LinkRecord]]:
    ...
```

返回：

- selected links。
- excluded par2 links。

如果 selected links 为空：

- 提示没有可下载文件。
- 若被排除的 `.par2` 大于 0，提示使用 `--include-par2`。
- 退出码 2。

## 4. 空间计算

```python
selected_bytes = sum(link.size_bytes for link in selected_links)
margin_bytes = max(
    int(selected_bytes * safety_margin_percent / 100),
    safety_margin_min_mb * 1024 * 1024,
)
required_bytes = selected_bytes + margin_bytes
```

默认配置：

```toml
[download]
safety_margin_percent = 5
safety_margin_min_mb = 512
include_par2_by_default = false
```

磁盘检查：

- 输出目录存在：检查该目录。
- 输出目录不存在：向上查找最近存在的父目录。
- 父目录也不存在：配置或参数错误，退出码 2。
- `free_bytes < required_bytes`：磁盘不足，退出码 5。

## 5. MEGAcmd wrapper

函数边界：

```python
def command_available(executable: str) -> bool: ...
def check_login(mega_whoami: str, timeout_seconds: int = 30) -> MegaCheckResult: ...
def run_mega_get(mega_get: str, mega_url: str, output_dir: Path, timeout_seconds: int | None = None) -> MegaRunResult: ...
```

调用规则：

```python
subprocess.run(
    [mega_get, mega_url, str(output_dir)],
    check=False,
    capture_output=True,
    text=True,
)
```

不得使用：

```python
subprocess.run(f"{mega_get} {mega_url} {output_dir}", shell=True)
```

## 6. 下载执行策略

v1 串行下载：

```text
for selected link:
  run mega-get
  collect result
  if failed:
    stop remaining downloads
    mark download failed
```

理由：

- MEGAcmd 和本机磁盘压力更可控。
- 错误记录更简单。
- 避免多个大文件同时写入导致空间估算失真。

后续若要并行下载，必须重新设计：

- 每个文件状态。
- 并发数配置。
- 部分成功恢复策略。

## 7. `downloads.message`

写入摘要，不保存过长日志。

建议截断策略：

```text
stdout first 1000 chars
stderr first 1000 chars
failed link file_name
failed link order
```

成功示例：

```text
Downloaded 2 files. selected=3249155727 free_before=12345678900
```

失败示例：

```text
mega-get failed for RJ01548502.zip.par2 with exit code 1. stderr=...
```

## 8. 用户确认内容

确认前展示：

```text
Work: RJ01548502
Title: ...
Output: downloads/RJ01548502
Files: 1 selected, 1 .par2 excluded
Selected size: 3.03 GB
Safety margin: 512 MB
Required space: 3.53 GB
Free space: 120.10 GB
```

用户拒绝时：

- 不调用 `mega-get`。
- 可把 `downloads` 记录为 `blocked`，message 为 `cancelled by user`。
- 退出码 0 或 2 均可；建议 0，因为这是用户主动取消。

