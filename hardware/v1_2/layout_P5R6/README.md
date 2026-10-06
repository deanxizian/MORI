# MORI P5R6：四板审查后的局部收尾

2026-09-25 · V1.2-H0.5-P5R6 · **PROTOTYPE / 实物 NOT_TESTED**。

当前工程：运动、电源、后接口 P5R6；IMU 保留 P5R4。旧工程完整保留。电路拓扑和 GPIO 针序不变，没有采购、制造订单或制造文件导出。

[可切换图层的前后对比](index.html) · [逐项意见处理](review_disposition.md) · [原生检查与例外](reports/verification.json) · [机械交接](../handoff/mechanical_P5R6.json)

**2026-09-25 后续复审补充：** [P5R6 与四板线宽审查处理](../reviews/P5R6_and_width_external_20260925/README.md)。核对全部 1502 段线宽、明确 R08/R09/R39 范围、补查全程采样线和原生锡膏预览；四板新一轮 ERC/DRC 均为 0，六个临时错误线宽均由对应规则检出。没有新的必须改铜线的问题，原生工程未改。U70 自举总长 9.675 mm 是线段端点口径，加上焊盘中心到起点的 0.175 mm 为 9.850 mm；旧“焊盘内部长度不计”表述应按此补充理解。

## 本轮改变

- **运动 D1/D2/D3**：保留 BAT54H,115 料号和极性，改用 Nexperia SOD123F 图形。铜焊盘 1.20×1.20 mm、中心距 2.80 mm；局部锡膏收缩到 1.10×1.10 mm。焊盘原来是 0.90×1.20 mm、中心距 3.30 mm。同步原理图、原生库和装配表。原走线仍完整落在新焊盘内，未增加补接小线段。阻焊继承项目工艺，最终阻焊/钢网/焊接仍需制造方确认。3D 使用 KiCad 通用 SOD123F 模型，不能当作厂商 STEP。
- **电源 C62/C72**：比较旋转和局部摆位后横放，整理 SW 支路。BOOT 与 SW 两端的总平面走线指标由 13.207／14.207 mm 降至 8.749／9.675 mm，约减少 34%／32%；采用实际线段端点口径，计入路径中完整线段，不额外添加焊盘中心连接或过孔垂直长度，不能代替回路电感或稳定性实测。
- **电源四处 SW 主通路换层**：每处由一颗 1.00/0.45 mm 孔改为两颗 0.80/0.30 mm 孔。每一孔都在 F/B 两侧与实际铜线相连，两组孔在每一路中串联，每组内部并联；另有 bootstrap 支路孔，不混算作主电流并联。更新孔铜厚度/输入铜温/电流的 DC 敏感性模型，无“每孔固定额定电流”声明。
- **电源 M5_EN**：用连续斜线通道代替 R60 旁两个原保留直角；电源板自由直角筛查 FAIL 从 2 项降为 0。反馈与独立地返回不动。
- **真实丝印和说明**：J6 统一为 BAT_MON SERVICE / DNP，仍不装配；J15 标 CHG_N / INTERLOCK；TP71 GND 文字移至对应测试点上方，远离 TP70 +5V_CAM。后板印上版本、J2 功能、J3 两组联锁针号、SW1 的 ON 触点组合。后板 G=GND、F=FUSED、R=RAW，CC1/CC2 印全名；完整针表见 [connector_pinmap.csv](connector_pinmap.csv)。SW1 仅印“ON 1-2+4-5”，未猜拨杆方向。

原生证据：[二极管焊盘/锡膏](reports/motion/diode_final_native_evidence.json)、[自举路径与双孔](reports/power/bootstrap_and_SW_banks.json)、[保留的去耦/反馈回地](reports/power/buck_returns.json)、[载流模型](reports/power/DC_model.json)、[所有线段](all_segments.csv)、[铜线差异](copper_changes.csv)。

## 已运行检查

KiCad **10.0.6**。四块当前板都重跑 native ERC、DRC（包含原理图一致性和重新填铜）、网络导出；结果均为 ERC=0、DRC=0、未连接=0、parity=0；没有增加 ignored checks 或 DRC exclusions。完整命令、退出码、检查输入哈希在 `reports/{motion,power,rear,imu}/check_commands.json`。

三块改版与源文件逐项比对：板框、安装孔、连接器/主控模块位置、层数、焊盘网络与原理图拓扑不变。只有三颗二极管的 land pattern 与两颗 bootstrap 电容位置发生已列出的变化；运动/后接口的线段和过孔几何不变。原 P5R5/P5R4 工程及检查输入哈希保持一致。

用户 KiCad 规则源为 `/Users/dean/Documents/KiCad/Rules/pcb-rules.json`，47 项、44 启用，SHA-256 `5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0`。新工程自定义 `.kicad_dru` 与各自源版完全相同。每个候选变更先通过原生 DRC，再做本体/转角/接口筛查。**不把 DRC=0 宣称成完整规则或审美偏好全部通过。**

保留的明确例外：电源两条独立 GND 回路使用 In1（源 R13 的局部偏离）；后板 CC2 在 (13.25,8.5) 的精确 0.5 mm 倒角与现有避让冲突，仍记 R14 FAIL；IMU P5R4 的两处短 GND 引出按原记录保留。本轮未新增器件下方异网穿越候选；连接器自身引出和架高 U100 投影仍逐项列在 `body_review_final.json`，不是整块器件下方通行许可。

## 尺寸与交接

电源 80×55×1.6 mm、运动 70×35×1.6 mm、IMU 20×16×1.6 mm、后接口 24×25×1.6 mm 均不变。更改后的精确本体投影、位置、引脚在 [mechanical_P5R6.json](../handoff/mechanical_P5R6.json) 与 [placements.csv](placements.csv)。机械文件未改；尚未完成最新完整带器件/插头的机械接收验证，不能声称整机安装 PASS。

## 尚需实物/外部输入

- 外部 USB-PD / 3S 充电模块仍未选定。RAW 检测线在源端的短路保护、CC 终端/短接 VBUS 防护、输入耐压和充电联锁仍 BLOCKED。后板 J2.1 与 J2.5 禁止桥接。
- 6.48 A 并发预算与主保险 6.3 A 名义值的持续时间/温度/熔断曲线配合待验证，不擅自换大保险。
- 厂商孔铜与叠层、IMU 100 µm 钢网及贴装工艺待确认。D1/D2/D3 的 land 校核不等于实物焊接通过。
- 用户现有万用表、限流电源可完成初步检查；开关纹波/瞬态/启动、温升和 ESD 仍需要相应测量条件。[测试计划](test_plan.md) 与 [空白记录](test_records.csv) 均保留 NOT_TESTED。

## 复核命令

在项目根目录使用 KiCad 自带 Python：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/check_review_P5R6.py check motion power rear imu
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/publish_review_P5R6.py
```

第二条只验证并重建硬件交接快照，不加 `--publish` 不更新当前硬件引用。不要将阶段编辑脚本当作“一键重建最终板”，原生已审核工程才是本版交付。`init`、`power_local`、`motion_diodes`、`en_cleanup` 等是历史候选编辑步骤，不能再次对已完成板运行。
