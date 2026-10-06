# 审查意见逐项处理

用户批准对 `MORI_FourBoards_P5R5_P5R4_Review_Bundle.zip` 中值得优化的项目实施局部修改。依据 [独立评估](../reviews/fourboards_P5R5_P5R4_external_20260925/assessment.md)，未执行包内脚本，未将其中制造输出建议当作下单授权。

| 意见 | 处理 | 证据与边界 |
|---|---|---|
| 运动 BAT54H,115 焊盘匹配 | PASS：三颗改成厂商 SOD123F 铜/paste图形；型号和极性不变 | `reports/motion/diode_final_native_evidence.json`；铜1.2平方、距2.8、paste1.1平方。供应商最终阻焊/钢网、回流焊 NOT_TESTED；通用3D模型不是厂商STEP |
| BOOT 一端短但 SW 回路绕行 | PASS：C62/C72旋转并小幅平移，完整两端总平面线长分别减少约34%/32% | `reports/power/bootstrap_and_SW_banks.json`。BOOT腿稍增，SW腿明显缩短；无输入去耦/FB回退。高频稳定性 NOT_TESTED |
| 四处 SW 主电流单孔 | PASS：各两颗0.8/0.3孔，两面都实际连铜 | 逐孔接触记录和DC敏感性计算。两组串联、每组两孔并联；不把bootstrap孔混计；电流均分/孔铜/温升 NOT_TESTED |
| M5_EN 两处直角例外 | PASS：新斜向避让通道消除，不增加微小抖动 | `reports/power/EN_smooth_geometry.json`；原(31,28)/(31,29.1)两个自由直角不再存在，原生DRC通过 |
| R61/R71 接地应更独立 | 原意见降级，保留已有独立安静回地 | 原生逐线几何相同，重新核验保存填铜的全线宽和孔环隔离。In1仍是对用户R13的局部偏离；噪声 NOT_TESTED |
| J6 外置5V陈旧说明、H-BUCK错字 | PASS：统一BAT_MON SERVICE / DNP | 原理图、板面、库、装配表同步。J6仍DNP、数量0，原GND/BAT_MON针序不变 |
| J15 充电功率口误认风险 | PASS：CHG_N、INTERLOCK、1:CHG_N 2:GND | 实际F/B丝印，不依赖编辑器网名 |
| TP71与TP70文字混淆 | PASS：TP71 GND移至(32,45.5)，位于其上方 | TP71(34.5,48)，TP70(35,51)位置不变；TP70 +5V文字保留，丝印与焊盘原生检查通过 |
| 后板完全没有可见文字 | PASS：板名/版本、J2、J3联锁及针号、ON触点 | J2印1 F / 2 G / CC1 / CC2 / 5 R，并有1:FUSED及5:RAW全名；G=GND。J3印1RET/2GND/3LOOP/4CLR；含两组回路 |
| SW1 ON方向 | NOT_TESTED：图只明确接触组合，不能确认拨杆朝向 | 实际印ON和1-2+4-5；用万用表测定后在装配记录补拨杆方向，再决定是否追加箭头。不伪造方向PASS |
| IMU继续移动去耦或更改paste | NOT_APPLICABLE：保持已改善P5R4，重跑原生检查 | C1/GND6、MISO33Ω、局部paste保持。100µm钢网的制造方确认仍BLOCKED |
| 后板D2额外接地孔 | 本轮不改铜 | 不是已有证据支持的必改缺陷。D1/C1/D3局部保护保持；ESD实验NOT_TESTED |
| 加RAW源端保护/冻结PD终端 | BLOCKED | 需要明确PD/3S模块及输入/检测方案，用户已确认仍未选定。不桥接J2.1与J2.5，不盲加CC电阻 |
| 更新制造包并下单 | NOT_APPLICABLE | 本任务交付原生原型工程、检查、装配数据和预览；充电/工艺/机械阻塞未闭合，不导出制造数据或下单 |

四块当前板本轮都重跑 KiCad 10.0.6 原生 ERC/DRC，均0问题/0未连接/0parity；没有忽略清单。仍保留后板CC2严格倒角FAIL和历史IMU短GND例外，不把静态规则通过说成已实测合格。

厂商证据：

- [Nexperia BAT54H，2024-10-08，第5页Figure5](https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf#page=5)：本轮铜和paste图形依据。下载副本、访问日期与哈希见 `reports/vendor_sources.json`。
- [TI TPS54302 Rev C，§7.4、第21–22页](https://www.ti.com/lit/ds/symlink/tps54302.pdf#page=21)：输入回路、自举、反馈和内/底层SW布置依据；不是对本板动态性能的认证。
- SOFNG MS-202V-G3 厂商接触示意只用于触点组定义，拨杆实际方向待测；保留本地原图。
