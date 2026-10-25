# C3 R108P — ARMED 下拉支路

**FAIL / PROTOTYPE / UNVALIDATED；40 项未连接，不可制造。**

本轮将 R304 下拉接入 D1601.2、J101.20、R903.2、U901.5 所在支路，未连接项 41→40。ARMED 全网仍有 5 个分离连接组，本轮没有完成整条安全链。

- R304 移到背面 (5.5,32.5)，旋转 180°；D1601 平移 (+0.20,-0.05)；C1201 平移 (0,-0.15) mm。
- 保留原 3.3V 转接孔 (5.5,29.4)。ARMED 孔向左，OVLO 孔向上，C910 接地孔向左 0.30 mm，保住 In2 供电铜区和参考地。
- 增 14 段线、4 孔，替换 8 段线、2 孔；1107 段线、305 孔。其余 212 个封装、所有焊盘电气及热连接、原理图/BOM/规则、板框、安装孔、68 个核心板针位和叠层不变。

实际运行 KiCad 10.0.6：除 40 项未连接外，DRC 0、图板差异 0、启用全严重级 ERC 0。历史关闭的 ERC 类别未变。147 个原连接组、17 对供电端点、50 项铜宽回归、155 个 GND 焊盘、327 段内层参考地、37 个敏感保护区通过；既有 4 条 Kelvin 路径保持。这些是设计检查，不能证明载流、温升或实物安全。

原始 OVLO 新孔距地孔 2.390 mm，2 mm 筛查保留 FAIL。它仅连接 B/In3，共用同一连续 In4；按既有 R69，换参考地检查为 NOT_APPLICABLE，没有修改阈值。历史 7 项换层提示未消除；历史电源宽度/地回流的精确处置仍须完整复核。

已实际查看新区域 10 张分层/叠图及 R304 原位置 4 张外层图；20 张生成图中另外 6 张没有标为已阅。18 个新增铜对象逐项记录。没有新增本体穿越例外；D1601 出线与背面 R1202 的投影重叠仅落在 D1601 自身焊盘内，没有焊盘外穿越。全板逐线视觉、完整线束装配、最终报价和实物检查仍未完成。

本轮根因：H/I/J 中新增信号孔的反焊盘切窄了 **In2** 供电通道，移动原 3.3V 孔或增加短桥没有修复。K 起保留原电源孔，把信号孔移到左侧才通过全部 50 项宽度回归。失败候选和搜索结果保留，不等同于板框无法容纳的证明。

[原生 PCB](../working_power_20261016/group_closure_20261016/candidate_6L_R108P/MORI_Interface_C3.kicad_pcb) · [DRC](../working_power_20261016/group_closure_20261016/candidate_6L_R108P/drc.json) · [数值审计](audit_P.json) · [原生结构与连接证据](../working_power_20261016/group_closure_20261016/candidate_6L_R108P/structure_and_contacts.json) · [逐线复核](per_copper_review_P.csv) · [视觉记录](visual_review_record_P.json) · [A–P 候选比较](trial_summary_A_P.json)

复现：用 `plan_P.json` 和 `build_trial.py P` 生成不存在的独立候选目录；随后执行 R90 的 `run_checks.py <候选目录> <plan_P.json>`、`verify_structure_P.py` 和 `render_P.py <候选目录>`。现有 P 目录是证据，不可覆盖。构建、检查及渲染的实际命令分别保存在 build_P_commands.json、候选 R90_check_commands.json、verify_structure_P_command.json、视觉目录 commands.json。
