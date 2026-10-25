# R110 — 安全信号与供电通道审查

**FAIL / PROTOTYPE / UNVALIDATED。当前仍采用 R108P，40 项未连接。** A–J 十个原生候选均未采用，CURRENT_WORKING.json 和当前 PCB 未改变，没有制造导出。

| 候选 | 未连接 | 其他 DRC | 图板差异 |
|---|---:|---:|---:|
| A | 40 | 7 | 0 |
| B | 44 | 0 | 0 |
| C | 42 | 8 | 0 |
| D | 40 | 6 | 0 |
| E | 43 | 24 | 0 |
| F | 42 | 2 | 0 |
| G | 41 | 5 | 0 |
| H | 42 | 2 | 0 |
| I | 40 | 11 | 0 |
| J | 40 | 1 | 0 |

完整哈希、原生违规对象与网络分组变化见 [audit_A_J.json](audit_A_J.json)。build_*_commands.json 保留实际命令、退出码与日志；各独立候选下保留 drc.json。

## 查明的问题

- B 接通一段 ARMED，却切断四个供电网络；“其他 DRC 零项”不能代表通过。
- CAM_BAT_OUT 的 In3 铜路和 HEAD_VM 的 In2 铜路在中央区域同时变窄。F/G/H 仅新增过孔便造成供电分裂。
- I 把 D301 移近 J105.7，缩短了 NRST，但违反 C1401/C1402 的真实 courtyard、J105 PTH 和已有铜线间距。只看 Fab 或线段端点不足以判断可摆放。
- J 用 NRST 孔替换 (34.9,15.9) 无外层引线的 GND 缝合孔，避免增加孔位。50 项供电铜宽回归 PASS，但 NRST 孔仍悬空；旧 F 面 Net-(D1601-K) 线段 `eb0fbc1f-ca52-4b8c-8d5c-c80b04b5f34f` 新增 0.049295009505 mm² 参考地缺口。保留 FAIL，不豁免。
- J 的 run_checks.py 中 integrity 子进程因 via_dangling 退出 1。retained_reference_regression.json 也为 FAIL；其他子进程退出 0 不等于全部报告通过。

## 实际查看与坐标校正

已查看原生填充多边形诊断图 central_In2_Cu.png、central_In3_Cu.png，以及 KiCad 导出的 reset_review_candidate_6L_R108P/reset_area_B.png。前两张是数据绘图，不冒充 KiCad 截图。候选完整逐线视觉仍 NOT_TESTED。

U1601 实际为 F 面 (37.5,15.25)、90°；D301 为 B 面 (33.15,14.95)、180°。此前基于错误坐标或朝向的推测无效；后续采用原生焊盘、courtyard 和所有穿越区域的线段。

export_placement.py 只读导出 215 个封装的 courtyard 和 D301 的 8 个正反面/转向变体。scan_d301.py 的 0.25 mm 网格筛查只产生候选，不替代原生检查，也不能证明整板放不下。

## 后续工作

联合调整中央 D301、D1602、相关过孔和电源通道。不能继续只挪一个孔并接受新的供电割裂。若使用 J 的孔位，必须先恢复上述旧信号的连续地参考，并回归全部 GND 焊盘、保留信号、供电和敏感保护。

现有直接 In2 NRST 路径会跨断 HEAD_VM，不能再次当作有效方案。信号跨越与替代供电通道需联合验证。保持板框、孔、核心针位、连接器和电气规则；完整原生、供电、回流及逐线视觉通过后才发布新工作稿。

本轮定位了限制条件，没有新增采用的 PCB 完成量。实物全部 NOT_TESTED，整板仍未完成。
