# 在另一台电脑继续

先获取 GitHub 最新 `main`；本整理 PR 合并前，应使用该 PR 分支。安装 Git LFS 后执行 `git lfs pull` 获取正式机器人的三个 Blender 工程。验证车装配在普通 ZIP 内，不需要 LFS。

1. 读根 README 和 VERSIONING，选择 `robot/` 或 `test_rig/`。不要把树莓派控制源码当作成品 STM32 固件。
2. 正式机器人读 `robot/AGENTS.md`、`robot/config/project_baseline.json`、`robot/docs/CURRENT_STATUS.md`。最新模型为 `robot/mechanical/mori.blend`；PCB 为 `robot/hardware/driver/MORI_Driver_C3_R108P.zip`。C3 尚未集成进主模型；40 项 PCB 未连接及固件适配保持待办。
3. 验证车读 `test_rig/project.json`、`test_rig/STATUS.md` 和 `test_rig/control/README.md`。当前采用 R59 组合；控制源码已收录 v184。第 71 轮实测属于 v141/v142，v184 未据此完成实物验收。
4. 在仓库根目录执行 README 的三个离线完整性检查。正式机器人前端/固件工具从 `robot/` 内运行；例如 `cd robot` 后执行 `bash tools/node-env.sh install --frozen-lockfile`、`bash tools/node-env.sh test`。
5. 验证车控制测试：`cd test_rig/control` 后执行 `python3 -m unittest discover -s tests -q`，需 Python 3.12+ 和 C++17 编译器。这不会连接设备。

本地绝对路径、串口别名、标定和设备连接信息不具有跨电脑通用性。没有迁移私人凭据、全部过程缓存或数 GB 实测原始大日志；v184 来源及未随包数据在其证据回执中列明。不要自动部署、烧录或恢复电机运行。

后续任务先核对实时 GitHub PR 和本地未提交改动，保护其他对话的工作。需要用户判断结构方案时先给出具体模型/静态对比；仅在用户要求时生成新视频。
