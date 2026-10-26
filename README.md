# MORI：正式机器人与可行性验证小车

本仓库包含两个独立维护和编号的项目。各项目的版本、模型、硬件、软件与验证状态见对应入口；两者的实测结果不互相继承。

| 项目 | 用途 | 入口 |
|---|---|---|
| 正式机器人 | WeAct STM32F412 主控、四执行器机器人 | **[robot/](robot/README.md)** |
| 可行性验证小车 | 树莓派 4B 两轮平衡与模块验证 | **[test_rig/](test_rig/README.md)** |

## 目录结构

```text
MORI/
├── robot/          正式机器人：尺寸、合同、机械、PCB、固件、应用、文档与工具
├── test_rig/       验证小车：结构、模块、控制源码、关键实测记录
├── projects.json   两个项目的入口与版本清单位置
├── tools/          仓库级完整性检查
└── .github/        两项目独立检查工作流
```

## 资料入口

- [版本与目录规则](VERSIONING.md)
- 正式机器人：[当前需求](robot/docs/REQUIREMENTS.md) · [当前状态](robot/docs/CURRENT_STATUS.md) · [资料索引](robot/docs/PROJECT_INDEX.md)
- 验证小车：[装配说明](test_rig/ASSEMBLY.md) · [当前状态](test_rig/STATUS.md) · [控制源码](test_rig/control/README.md)
- [正式机器人下载与重建](robot/docs/GITHUB_ARCHIVE.md)

## 离线检查

Python 3.12+ 离线检查，不连接硬件：

```sh
python3 tools/check_workspace.py --allow-lfs-pointers
python3 robot/tools/check_project.py --allow-lfs-pointers
python3 test_rig/tools/check_release.py
```
