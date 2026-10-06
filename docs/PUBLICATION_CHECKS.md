# 本次归档检查

检查日期：2026-10-07；资料快照：2026-10-06。以下只验证本次 GitHub 归档内容。

| 检查 | 结果 |
|---|---|
| 新首页、索引、状态、下载、历史、采购表及本页中的 158 个本地链接 | PASS：目标存在且包含在 Git 索引中 |
| 当前模型／动画／契约及四块原生 PCB 文件的 SHA256 和大小 | PASS：与 [资产清单](current_assets.json) 一致 |
| 几何参数与两份共享契约的整理前后哈希 | PASS：未改工程内容 |
| Git LFS | 4 个实际资产，共 364,106,059 字节；其余文件采用普通 Git |
| 普通 Git 单文件大小 | 最大为装配视频 14,443,094 字节，无超过 100 MiB 的普通对象 |
| 已暂存内容的密钥扫描 | gitleaks 8.30.1，PASS：按下述已审阅配置扫描，0 个待处理发现 |
| 运行目录、真实环境文件和凭据文件路径 | 未进入本次 Git 索引 |
| 原 GitHub Actions | 已改为 workflow_dispatch 手动触发 |

密钥扫描命令：

```sh
gitleaks git --pre-commit --staged --redact --no-banner --report-format json --report-path .state/publication/gitleaks-final.json --timeout 300
```

[扫描配置](../.gitleaks.toml)继承默认规则，只针对准确路径和内容格式豁免已审阅的误报：证据文件 SHA256、数值搜索候选标识、一个连接器封装名和一个历史模拟错误 ID。包含会话／访问字段的原始供应商网页缓存留在本地，路径见 [遗漏清单](omitted_web_snapshots.json)。没有关闭检测器，也没有把这些原始网页改写成原厂文档。

工具：Git 2.54.0、GitHub CLI 2.92.0、Git LFS 3.8.0、gitleaks 8.30.1。Git LFS 与扫描器仅安装到被忽略的本地工具目录。详细结果见 [publication_checks.json](publication_checks.json)。

本次没有重新建模、编译／烧录固件、执行硬件试验或完整跨机器重建。原有 PASS 保留其原日期、版本与范围；整机仍未制造放行。
