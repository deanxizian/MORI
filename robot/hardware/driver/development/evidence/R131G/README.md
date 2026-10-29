# C3 R131G：接入 ARMED 下拉电阻

2026-10-26，从 R129D 调整 R1207 并将 R1201 移到现有 ARMED 过孔旁。替换一段明确的 ILM 旧线，新增八段背面线，不增加过孔。PCB SHA256：`6f9d92ebf5a36598421f064cf29523081d8004d28d2e60ef7a0c36ff8b9bd099`。

原生填铜后 **32 项未连接 / 0 其他 DRC / 0 图板差异 / 0 启用 ERC**；1162 段、309 孔、215 个器件。ARMED 从四组减为三组，R1201 已接入主组，U301.3 和 U1302.3 尚未接入。155 个 GND 焊盘仍为一组。

严格几何回归保留 **FAIL**：两只电阻、四个焊盘、两个所属 BODY 区域及一段旧线发生明确变更。2501 项精确计划核对 PASS；旧连接、50 项供电铜宽、63 项关键邻接和旧参考地无退化。77 个非 PCB 工程成员保持原字节，板框、安装孔、MCU/连接器接口和电气规则不变。

R1207 的 ILM 铜线总长由 6.958560 减到 6.224676 mm，退出 L901 名义 Fab 本体投影。新 ARM 连接长 1.135660 mm，地桥长 1.558883 mm；无新换层孔。新地桥在正面 L901 投影下，R1201 本体也位于电感输出侧投影内，已分别审查；不能把带焊盘窗口的 BODY 禁布区当作完整器件本体。局部 In4 参考连续，六项旧回流提示保持未关闭。

[TI TPS25947 Rev C §8.4.1](https://www.ti.com/lit/ds/symlink/tps25947.pdf) 要求限流节点短、低寄生且远离开关噪声；[TPS54302 Rev C §7.4.1](https://www.ti.com/lit/ds/symlink/tps54302.pdf) 的开关/反馈与接地要求也已核对。这里的几何改善不证明 ILM 寄生小于 50 pF，也不证明低噪声星形/Kelvin 地、磁耦合或热性能合格。电感及泄放电阻附近的热态偏置、故障脉冲和装配仍 NOT_TESTED。

- [精确修改计划](edit_plan.json)、[原生命令](commands.json)、[DRC](drc.json)、[ERC](erc.json)。
- [原始逐步审计](step-regression.json)、[计划差异核对](planned-delta.json)、[名义尺寸测量](local_measurements.json)、[只读测量脚本](review_local.py)。
- [实际看图记录](visual_review.json)、[图像哈希](image_manifest.json)、[剩余连接](remaining_connections.csv)。
- [未采用的 R130/R131 比较](../R130_R131_trials/README.md)。

只采用到本任务独立开发稿。发布仍为 R108P，机械主模型和软件未采用；完整工程仍 FAIL / PROTOTYPE / UNVALIDATED，不可制造。整板审查和实物验证未完成。
