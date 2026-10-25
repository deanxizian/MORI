# 版本与目录规则

仓库不再用一个总版本号覆盖两个项目。`projects.json` 只列项目入口；正式机器人的版本真源是 `robot/config/project_baseline.json`，验证车的真源是 `test_rig/project.json`。

| 层次 | 正式机器人 | 验证小车 |
|---|---|---|
| 项目资料快照 | 1.3.0-dev.2 | 0.1.0-dev.1（首次独立编号） |
| 已采用结构 | V1.2-M1.58，显示简称 M1.58 | R37＋R41＋R55＋R59 |
| 最新采用 PCB | C3 R108P | 成品模块组合 |
| 软件实现 | 1.2.0-dev.1 | v184 |

这次增加资料快照号表示目录拆分、稳定文件名和来源整理。没有新结构、控制算法或硬件设计变更；没有以改号代替工程适配。R60 和 C3 R110 属于未采用比较，不能用最大的数字代替当前版本。

当前文件用固定名字，例如 `robot/mechanical/mori.blend`、`robot/firmware/motion/controller/`、`robot/tools/test-motion.sh`。真实修订号保留在模型元数据、PCB 工程包及版本清单中。下次修改内容时，更新相应领域修订和来源记录。

原始需求、厂家资料、许可证、历史检查和实验记录保留来源版本及文件字节，例如 `MORI_SPEC_V1_2.md`、`software/inputs/v1_2/`、v142 实测快照。这里的 1.2 不表示存在第二套当前项目。历史生成脚本、报告和原始档案中的路径是执行当时的记录，不全局改写。

旧目录到新目录的主要映射：

| 原入口 | 当前入口 |
|---|---|
| `mechanical/mori_v1_2.blend` | `robot/mechanical/mori.blend` |
| `hardware/driver/` | `robot/hardware/driver/` |
| `firmware/motion/v1_2/` | `robot/firmware/motion/controller/` |
| `tools/build-motion-v1_2.sh` | `robot/tools/build-motion.sh` |
| `config/`、`contracts/`、`apps/`、`backend/` | `robot/` 内同名目录 |
| `test_rig/` | 保持原位置，补齐独立版本与 v184 |

完整映射见 [迁移清单](robot/docs/organization/path_migration.json)。历史构建输入中的相对路径以 `robot/` 为根；不会恢复到仓库顶层。原工作区的忽略目录和实验原件没有移动或清理。
