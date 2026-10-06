# 四板 PH 成品孔修正候选 PHC1

2026-10-02。**18 个 PH 接口、69 个通孔已在独立原生候选中修正，四板 KiCad ERC/DRC 均为 0。** 本轮没有移动器件、改变连接器朝向或重布走线；正式四板与机械模型未替换。候选数字检查 PASS，制造仍 BLOCKED。

本包基于正式运动/后接口 P5R7、电源 P5R6、IMU P5R4。电源 J10 保留正式板的直出线座；本包不混入尚未闭合的 J10 侧出线 C2。以后采用侧出线方案时，需要将孔径改动合并到它的新工程并重新检查。

| 候选原生工程 | 接口 / 孔数 | ERC | DRC 违规 / 未连接 / 原理图差异 |
|---|---:|---:|---:|
| [运动板](candidates/MORI_motion_P5R7_PHC1/MORI_motion_P5R7_PHC1.kicad_pro) | 8 / 31 | 0 | 0 / 0 / 0 |
| [电源板](candidates/MORI_power_P5R6_PHC1/MORI_power_P5R6_PHC1.kicad_pro) | 7 / 21 | 0 | 0 / 0 / 0 |
| [后接口板](candidates/MORI_rear_P5R7_PHC1/MORI_rear_P5R7_PHC1.kicad_pro) | 2 / 9 | 0 | 0 / 0 / 0 |
| [IMU 板](candidates/MORI_imu_P5R4_PHC1/MORI_imu_P5R4_PHC1.kicad_pro) | 1 / 8 | 0 | 0 / 0 / 0 |

## 孔径、铜盘与加工约束

[JST 官方 FAQ](https://www.jst.com/resources/faq/) 对 B*B-PH-K-S / S*B-PH-K-S 在玻纤环氧镀通孔板的建议，指的是**镀后成品孔**：2P 为 0.80–0.85 mm，3–16P 为 0.85–0.90 mm。2026-10-02 核验的官方页面已随既有审查保存，路径/hash 见 `proposal.json`。

| 接口 | 原孔 / 铜盘 | 候选孔 / 铜盘 | 拟定成品孔公差 | 图面单边环宽 |
|---|---|---|---|---:|
| 2P | Ø0.75 / 1.35 mm | Ø0.85 / 1.45 mm | +0 / −0.05 mm | 0.30 mm |
| 3–16P（本项目使用 3/4/5/8P） | Ø0.75 / 1.35 mm | Ø0.90 / 1.50 mm | +0 / −0.05 mm | 0.30 mm |

上述公差是工程提出的要求，**不是已取得的板厂能力承诺**。不能直接套用板厂默认孔公差，也不能把孔的 CAD 名义值当作实际钻头直径。钻刀补偿、镀铜厚度、对位、实际剩余环宽与孔检方式仍需加工方确认。若不能保证此区间，应先与 JST/选定供应商及板厂核对适配，不能放宽尺寸后继续宣称符合这份建议。

所有孔中心、针号、网络、焊盘形状与极性保持。对应本地封装库、原理图封装引用及器件表已同步，避免只有 PCB 内嵌焊盘被改而更新封装后丢失。所有其他焊盘（包括 MCU 排针、安装孔、USB-C 等）未改变。

## 邻线和规则检查

- `verify.py` 对 69 个 PH 焊盘逐一比较原生铜形状，检查所有铜层上的异网焊盘、走线及过孔，使用不超过 0.001 mm 的距离区间；本轮最小下界为 0.500 mm。**此数值不包括铺铜面，也不是整块板所有网络的最小间距。** 原生 DRC 另检查铺铜、热焊盘、净距与未连接。
- 0.30 mm 是图面几何环宽，未加钻偏/制造补偿，因此不是成品环宽保证。
- 1782 个既有走线段与过孔的 UUID、起终点、网络、层、线宽/孔径均与基准一致；本轮需要挪动的器件、需旋转的连接器、需改动的邻线均为 **0**。
- 用户 KiCad 项目衍生的 `.kicad_dru` 原样保留，项目 `design_settings` 完全一致，DRC exclusions 仍为空。没有通过降低规则清零。
- 本轮未改变任何本体禁布区或走线，因此未增加新的穿本体、反折或抖动。正式基准已有的例外/限制仍需保留，不能由这次孔径检查宣称整个设计已完成物理资格验证。

逐孔数据：[69 孔尺寸与邻近铜表](PH_69_finished_holes_and_neighbours.csv)。完整前后不变量、每孔最近邻对象/层/间距区间：[validation.json](validation.json)。249 个正式源文件均通过 hash 保留检查。

## 原生检查与复现

工具：KiCad **10.0.6**。每块板的实际命令、退出码、输入 hash 和输出在 `reports/<板名>/initial_commands.json`；报告以 `initial_erc.json`、`initial_drc.json` 命名，因为首轮便通过，之后没有修改原生 CAD，不需要另造一次“最终检查”。

ERC 使用 `--severity-all --exit-code-violations`；DRC 另使用 `--all-track-errors --schematic-parity --refill-zones`。八个检查的退出码均为 0，所有警告也包含在检查范围。CLI 输出包含 Fontconfig 配置提示，已保留原 stderr；未将其隐藏或当作电气违规。

在项目根目录用 KiCad 随附 Python 执行：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 hardware/v1_2/ph_hole_candidates_20261002/verify.py
```

若需要重新运行某板原生检查：`build.py check motion recheck`（将 `motion` 换为 `power`、`rear`、`imu`）。结果另存，不覆盖首次检查。`build.py init` 只允许在候选目录不存在时生成，禁止用它重置已交接候选。

## 交接边界

独立 A4 交接为 `hardware/v1_2/handoff/mechanical_P5R7_prearrival_A4_PH.json`。正式工程、组件的真实外形、机械板框与安装位置、针脚接口均不变。接收方只需保留尺寸修正与待加工确认，不需要为这次修正移动支架、接口或重新定义孔中心。

机械任务已独立读取四套正式板与四套候选板，核对 **185 个封装实例**的位置/朝向/层别与 3D 模型引用、69 个 PH 孔以及板框/安装孔/非 PH 焊盘，接口一致性 PASS。正式 249 个源文件、候选 264 个源文件和原生检查报告 hash 均匹配。原始[机械接收记录](reports/mechanical_A4_receipt.json)及[硬件接收校验](reports/mechanical_receipt_validation.json)已保存；此项不是制造或实物插装验证。机械仍保持 M1.47，十四根线联合检查尚未作为已通过结果接收。

PH 孔径的数字修正已完成；**正式四板尚未应用，成品孔公差、匹配实物插装、焊接与拉力为 NOT_TESTED / BLOCKED**。J10 侧出线 C2 的 26 处未连接、14 条警告及实际出线高度问题不由本包解除。其他电池/充电/急停及整机实测缺项同样保留。

未导出 Gerber、钻孔或贴装制造文件，未采购或下单。需要板厂书面确认孔要求及后续明确的正式版本发布后，才能推进制造资料。
