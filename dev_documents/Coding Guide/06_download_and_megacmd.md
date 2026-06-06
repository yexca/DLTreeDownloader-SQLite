# 06 Download And MEGAcmd

## 目标

实现下载前置检查、MEGAcmd 诊断和实际下载调用。该阶段应在导入和查询稳定后进行。

## 负责模块

```text
dltree/mega.py
dltree/filesystem.py
dltree/sizes.py
dltree/app.py
dltree/cli.py
dltree/repositories.py
```

## 实现命令

```text
dltree doctor
dltree download <work_code> [--output <dir>] [--include-par2] [--yes]
```

## 下载前置检查顺序

1. 读取配置。
2. 查询作品是否存在。
3. 查询 active links。
4. 应用文件选择规则。
5. 计算 selected bytes 和安全余量。
6. 检查 `mega-get` 是否可用。
7. 检查 `mega-whoami` 是否可用。
8. 执行 `mega-whoami` 检查登录状态。
9. 检查输出目录所在磁盘空间。
10. 展示确认摘要。
11. 用户确认后创建输出目录。
12. 调用 `mega-get`。
13. 写入或更新 `downloads` 记录。

## 文件选择规则

- 默认排除 `.par2`。
- `--include-par2` 包含 `.par2`。
- 配置 `include_par2_by_default = true` 可改变默认行为。

## 空间计算

```text
required = sum(selected link size_bytes) + max(5%, 512 MB)
```

## 完成标准

- `doctor` 能报告配置、数据库、MEGAcmd 和登录状态。
- MEGAcmd 缺失时不会尝试下载。
- 未登录时不会尝试下载。
- 磁盘空间不足时不会尝试下载。
- 下载前展示作品、输出目录、文件数量、大小、余量和可用空间。
- `mega-get` 失败时记录失败状态和摘要。
- 所有选中链接成功时记录 completed。

