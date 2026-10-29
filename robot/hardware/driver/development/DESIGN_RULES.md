# C3 R108P 设计规则接收清单

2026-10-26，从 R108P 发布 ZIP 直接读取，文件未修改。后续候选以原生规则为准；下表为便于阅读的四舍五入显示，不重写源值，也不以摘要替代有条件的规则。

## 原生可执行规则

- [MORI_Interface_C3.kicad_dru](native/MORI_Interface_C3.kicad_dru)：自定义约束及网络/对象条件。**最后匹配的规则优先**，不能把最上面的 0.5 mm 默认值推广到所有对象。
- [MORI_Interface_C3.kicad_pro](native/MORI_Interface_C3.kicad_pro)：默认/GND/VCC 网络分类、规则严重级、全局最小值和网络分配。
- [MORI_Interface_C3.kicad_pcb](native/MORI_Interface_C3.kicad_pcb)：实际六层叠层、区域限制、焊盘栈和局部设置；板内存在大量有对象/层适用范围的禁布区，不能只读 `.dru`。

| 项目 | 原生定义的显示摘要 |
|---|---|
| 信号线宽 R09 | 最小/推荐 0.20 mm，最大 2.00 mm |
| 电源/GND 线宽 R08 | 最小 0.20 mm，推荐 0.50 mm，最大 5.00 mm；推荐值不是载流保证 |
| 常见线–线、线–焊盘、线–孔铜间距 | 0.20 mm；具体以 R05/R06/R07 的网络及对象条件为准 |
| 过孔–焊盘 R01 | 任意网络均有 0.20 mm **物理间距**，同网也适用 |
| 孔–铜 R07 / 孔–孔 R40 | 0.30 / 0.15 mm |
| 过孔 R15/R16 | 直径 0.50–1.00 mm，孔径 0.25–0.50 mm；原生默认孔径另为 0.30 mm |
| 全局最小环宽 / 铜到板边 | 0.10 / 0.50 mm |
| 过孔类型 R32 | 仅通孔；不靠盲埋孔绕过既定工艺 |
| 内层区域间距 R17 | 0.40 mm，具体适用条件和优先级见原文 |
| 内层布线 R13 | In1/In4 禁走线；In2 仅列出的网络允许走线，其余不得擅自加入白名单 |
| 换向 R27 | 原生 `track_angle` 最小 60°；以 KiCad 的角度定义检查，不自行改成另一种角度口径 |
| 过孔计数 R23 | 原生 `via_count (max 500)`；约束作用范围由 KiCad 解释，不当作额外人工豁免 |
| 覆铜连接 R26/R25 | SMD 实连；THT 热焊盘，间隙 0.254 mm、推荐辐条约 0.30 mm、至少 4 条有效辐条 |
| 丝印 R43/R42 | 丝印–丝印约 0.05 mm；丝印–露铜焊盘约 0.01 mm |
| 差分 R39 | 当前无差分对；预设线宽 0.381 mm、间距 0.254 mm、未耦合长度上限 12.7 mm |

板框 70 × 35 × 1.6 mm、四安装孔、68 核心板针位、九连接器及原电气映射是接收约束。移动既定机械接口或改板框必须单独说明，不能为了布通默改。

## 超出 DRC 的项目要求

1. [robot/AGENTS.md](../../../AGENTS.md)：引脚优先向器件外侧出线；布线前比较旋转及小范围成组位置；减少短折返、蛇形和多余避让。2026-10-26 用户明确：避免器件本体下走线主要约束器件所在面；对侧/内层按参考地、耦合和热要求逐项审查，不增加全层投影禁布。全部原生禁布区保持。关键电源/去耦环路不能为了视觉加长。必要同面本体穿越逐个记录 reference/net/reason，不给电源/GND 整类豁免。
2. [R108P 接收证据](../evidence/R108P/README.md)：旧连接组、17 对供电端点、50 项铜宽回归、155 个 GND 焊盘、4 条 Kelvin 取样、关键器件邻接、内层参考地及 37 处敏感区需要回归。历史 PASS 只覆盖原哈希，不自动继承给新候选。
3. [历史回流检查](../evidence/R108P/transition_audit.json)：换参考层孔附近地连接的 2 mm 是项目筛查阈值，**不是 IPC 标准或 EMC 合格值**；目前 7 项 FAIL。相同连续参考面的换层适用性须逐孔解释。
4. [R110 失败记录](../evidence/R110/README.md)：新增孔既可能割裂 In2 供电，也可能破坏旧信号参考地。必须联合回归实际填铜，不能只减少飞线。
5. [当前需求](../../../docs/REQUIREMENTS.md)：单载板、板载 6 V、F412、UPS/BMI323、开机/故障禁驱、显式解锁和保护。自动充电禁驱已取消，保持 NOT_APPLICABLE。

历史记录还引用旧工作区的 `ROUTING_POLICY_20261017.md` 及部分检查脚本；当前仓库没有收录其原文，旧绝对路径也不存在。这里没有声称完整恢复了这些缺失文件。已有原生约束和已发布审查证据仍完整保留；重建的检查必须说明覆盖范围并对原生结果交叉核对。

## 原生验收命令

在候选目录运行（需 KiCad 10；原始包不保存回写）：

```sh
kicad-cli pcb drc --format json --schematic-parity --refill-zones --severity-all --exit-code-violations -o drc.json MORI_Interface_C3.kicad_pcb
kicad-cli sch erc --format json --severity-all --exit-code-violations -o erc.json MORI_Interface_C3.kicad_sch
```

读取 JSON 的 `violations`、`unconnected_items` 和 `schematic_parity` 全部栏目。当前 MCP `run_drc` 摘要遗漏未连接项，不能单独作为验收。历史关闭的 `single_global_label`、`four_way_junction`、`simulation_model_issue`、`footprint_filter` 四类 ERC 另列，不声称全部可能的 ERC 检查均已启用。

基线 KiCad 10.0.7 实跑仍为：40 项未连接，其他 DRC 0，图板差异 0；启用项全严重级 ERC 0。工程 FAIL / PROTOTYPE / UNVALIDATED；不允许以通过数字检查替代热、浪涌、EMC、装配或实物资格。
