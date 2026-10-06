# MORI V1.2 / P4 硬件原型

**2026-09-23 用户复核：布线要求 FAIL，P4 不作为合格 layout 交付。** 此前同面器件筛查漏检短折返、抖动、绕路及完整引脚逃线，不能支持布线 PASS。原生 ERC/DRC 结果只保留其电气检查含义。当前复核与整改证据见 [用户圈选复核](user_review_20260923/README.md)。

当前改版包含运动承载板、身体 IMU 板、电源板和后部 Type-C／物理电源开关板。原生工程分别位于 `../kicad/MORI_{motion,imu,power,rear}_P4/`。保留 P2、S3、P3 与 P3R1 历史项目。

**PROTOTYPE；实机 NOT_TESTED；禁止据此直接宣称生产验证。** 未采购、未下单 PCB，没有导出制造文件。

- 检查状态与源码哈希：`reports/verification.json`；各板目录内有真实 KiCad `drc.json`、`erc.json`、命令、退出码和日志。未连接和违规不会被隐藏。
- 常用接插件与充电边界：`接插件与充电接口说明.md`、`connector_catalog.csv`。
- 全部板端引脚：`connector_pinmap.csv`；原生装配清单：`assembly_bom_all_boards.csv`；采购MPN对应位号：`assembly_parts_with_mpn.csv`；线束：`harness.json`。
- 机械交接：`../handoff/mechanical_P4.json`；裸板 STEP 在 `../mechanical/`，不代表完整器件插合模型。
- KiCad 原生导出预览在 `previews/`，含上下层、装配、去铺铜走线视图和原理图 PDF；`drafts/` 仅为过程检查视图。
- 可运行电气估算：`python3 calculations/estimate_interconnect.py`。铜厚、电镀和热敏感系数明确记为假设，没有伪造实测电流或温升。

## 路由要求与检查边界

继承 `/Users/dean/Documents/KiCad/Rules/pcb-rules.json` 的 47 条源规则；副本 `pcb-rules-source.json`。运动板采用四层，内层只用于 GND 与3.3V平面，不用内层信号走线绕过 R13。其余为双层。

分别检查器件同面实体、外向逃线通道和异网跨体路线。模块承载板中架空 WeAct 模块的投影与器件实体不同：载板需要在模块下承载电路；这不能推广为贴片电阻、二极管、MOSFET下随意穿线的许可。对面投影和实际同面穿体应在审查文件中分开列明。

KiCad 的零 DRC 不是用户布线风格全部通过。源规则 R14 的每个倒角严格0.499999 mm退让、全部扇出网格和完整三维装配不由一般 DRC 证明；当前不能宣称47条全部合格。任何尚存的几何审查候选和例外都要见独立记录，不能用全局 GND/电源豁免来清零。

## 机械与采购仍需闭合

电源板80×55、运动板70×35、IMU20×16均保留当前授权板框。后部板24×25是电气试排提案，旧结构24×14占位不成立；必须核对孔、口、开关操作距离、PH5板外伸出和插拔路径。PH直插的8mm插合高度不包含线弯。PCB设计尺寸不是已测尺寸。

成品3S电池、匹配的保护/充电/PD/电源路径和若干外接转换模块仍未取得完整定型证据；价格、线束和配对插头也未取得结算报价。电路原型与模块目录可继续审查，但采购释放、完整充电、60分钟续航和整机预算均不能标PASS。

## 本轮收尾

四板KiCad10.0.6 ERC/DRC/未连接/原理图一致性均为0；当前输入哈希匹配，无忽略项。独立走线复核见[逐项记录](body_route_review/README.md)，主电流宽铜连通见[电源审计](reports/MORI_power_P4/load_path_audit.json)。接插件旋转后的正负极和位号重新核对，位号跟随实际器件面及位置。

[四板预览](previews/index.html) · [电源树与接线](power_and_wiring.md) · [实测和阻塞项](实测与阻塞项.md) · [复核命令](REPRODUCE.md)。保留源规则R14未全面落实的FAIL，不声称47条全合格。后板只是充电接口，外部PD/3S充电器仍未选定。

[BOM价格门槛](reports/budget_gate.json)：96条数量大于零的条目中，95条没有单价；206元为旧头舵机型号报价小计且精确变体/税运未确认。完整到货总价与超预算金额均未知，不能以缺价当零。

新增厂商资料仅作为产品参考，未因此取得再许可：JST/HRO/SOFNG资料及哈希见connector_sources.json。继承的KiCad库许可见[库许可记录](../licenses/README.md)；按尺寸重建的本地封装不是厂商授权认证，也不代表可替代实物确认。
