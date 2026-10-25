# 证据与可复核范围

## 第 71 轮：有限 60 秒无人接触

- [完整原始 JSON 压缩包](balance/trial71-raw.json.zip)：解压后 114,483,111 字节，SHA-256 `c64fa4451acb139a08da24aebb75465c557cf2bfc3dfcc8c7dc4e6cc94647ab1`。包含控制/IMU/电机遥测，不含私人照片或录音。
- [结果与用户确认](balance/trial71-result-review.json)、[分窗口摘要](balance/trial71-window-summary.json)、[控制台](balance/two-deck-balance-71-console.jsonl)、[UPS 同期采样](balance/two-deck-71-active-ups.json)。
- [v142 原始源码清单](balance/trial71-v142-source-manifest.json)与 v159 的清单不同。[v142 完整源码包](balance/trial71-v142-source.zip)按 233 个原始文件哈希从现有源码、历史副本和部署 tar 中重组，逐文件匹配；另含原清单。本次在临时目录重跑其 410 项离线测试通过，不混用当时 v159 源码宣称历史复现。

可在仓库根目录重新计算已发布原始日志中的时长、周期和第 7–60 秒窗口指标：

```sh
python3 test_rig/tools/verify_trial71.py
```

这能验证摘要与原始数据一致；“全程未接触”来自操作者确认，无法仅靠编码器反推。编码器折算位移也不是地面外部测量。

## 第 95 轮：保护退出

[保存回执](balance/trial95-durable-save-receipt.json)、[控制台](balance/two-deck-balance-95-console.jsonl)、[操作者事件](balance/trial95-operator-events.jsonl)和[状态快照](balance/trial95-status-snapshots.jsonl)随包提供。原记录里的 `logs/...` 指当时的 Pi 或本机运行目录，不都是本仓库相对路径。

完整原始文件 `two-deck-balance-95-native-causal.json` **只确认在 Pi 保存**，3,008,090,504 字节，SHA-256 `f106107468c8aabc808c9d5f03e8d52e1938c505913889bc4656b6d5fcb103fd`；本包没有该文件。保存回执的 PASS 与运动结果 FAIL 是两个不同字段。第 95 轮源码对应[部署回执](balance/native_causal_v159-deployment.json)，部署时的 `hardware_tested: false` 不是后来实际运行结果；两者时间分开保留。

## 机械与相机

[CAD 目录](cad/)保留原报告字节，路径和命令属于原工作站；它们是当时检查记录，不是本包可以逐条照抄的构建脚本。单体、网格和装配报告里的 PASS 有各自限定范围。R55 的[短柱制造建议检查](cad/r55/printability_check.json)同时保留了通用空心柱建议不满足的 FAIL，不能只引用最上面的数字拓扑 PASS。

[Pi Camera 3 Wide 检查](camera/camera-verification.json)保留枚举/单张拍照结果和照片哈希。私人 JPEG 不公开；相机连续视频和人物检测接入未验证。

`history/` 是原始说明的快照，可能含未打包的相对路径、曾经的“下一步”或已变化参数，不作为当前施工/运行入口。当前结论以[STATUS](../STATUS.md)、[装配表](../ASSEMBLY.md)和[接线说明](../hardware/WIRING.md)为准。

## 当前 v184 来源

[原状态摘录](software/v184/local_status_excerpt.txt)与[来源回执](software/v184/receipt.json)记录了 324 文件部署清单及本机核对。第 128 轮 v183 的完整报告没有纳入仓库；v184 尚无新实物改善证据。旧第 71/95 轮报告、源码和状态不因本次更新而改写。
