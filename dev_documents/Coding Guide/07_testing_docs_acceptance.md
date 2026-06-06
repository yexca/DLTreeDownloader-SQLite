# 07 Testing, Documents And Acceptance

## 目标

收尾阶段补齐测试、文档和真实数据验收，确保项目可以交给用户使用，也可以交给二次开发者维护。

## 负责内容

```text
tests/
README.md
documents/
setup_env.ps1
requirements.txt
```

## 测试内容

单元测试：

- 文本规范化。
- 声优拆分。
- 社团解析。
- 尺寸解析。
- MEGA JSON 解析。
- 链接集合 hash。
- 下载空间计算。

集成测试：

- schema 初始化。
- 小型 xlsx fixture 首次导入。
- 重复导入。
- 链接变化。
- 查询命令。

下载测试：

- mock `shutil.which`。
- mock `shutil.disk_usage`。
- mock `subprocess.run`。
- 覆盖 MEGAcmd 缺失、未登录、空间不足、下载成功、下载失败。

## 文档内容

普通 README：

- 安装方式。
- 初始化方式。
- 导入示例。
- 查询示例。
- 下载示例。
- MEGAcmd 登录说明。
- 数据库位置。

二次开发文档：

- 架构说明。
- 数据契约。
- 扩展点。
- 测试指南。

## 验收流程

使用真实文件：

```text
files/DL tree 260308.xlsx
```

验收步骤：

1. 运行 `dltree init`。
2. 运行 `dltree doctor`。
3. 导入真实 Excel。
4. 确认 works 行数约为 74,917。
5. 重复导入一次，确认 active links 不重复。
6. 查询已知 work code。
7. 查询已知声优。
8. 查询已知社团。
9. 在 mock 或真实 MEGAcmd 环境下验证下载前置检查。

## 完成标准

- 常规测试通过。
- 真实 Excel 导入通过。
- 重复导入无重复 active links。
- 查询命令可用。
- 下载前置检查可靠。
- README 和 `documents/` 能指导用户和二次开发者继续工作。

