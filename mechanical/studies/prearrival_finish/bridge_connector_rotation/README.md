# 身体端 PH 插头：带转动的独立路径诊断

状态 **BLOCKED：本轮限时搜索未找到完整路径**。这不证明无法装入，也不是实物适配结论。

前一版仅允许固定朝向平移。本轮允许 24 种正交朝向及 90° 转动，保留 122 件本装配阶段的真实源部件、29 个插接空间分配和全部 14 根既有身体导线。
偏航及俯仰总成按明确工序尚未安装。共同 PH 插头使用原有未实测的 9.8 × 4.5 × 6.85 mm 分配及 0.3 mm 余量；没有改小插头、移动电路板或移除障碍。

| 搜索 | 已展开状态 | 尚待搜索状态 | 结果 |
|---|---:|---:|---|
| 原闭合实体布尔检查 | 206 | 663 | 150 秒预算内未找到路径 |
| 凸体与 BVH 辅助检查 | 272 | 801 | 150 秒预算内未找到路径 |

初始轴向退出 8 mm 仍通过。后续阻挡包括 MCU、承重桥、已有插头和相邻身体导线。
辅助检查用 398 次实体布尔抽查核对，没有发现“辅助判空、实体相交”的抽查样本；2 次辅助检查保守拒绝。
这不能将未遍历的搜索空间判为失败，更不能证明所有转动、弯线或装配次序都不可行。

本轮只研究刚性插头空间，**四根相连 CAM 导线的供线、手部操作、真实插头朝向和厂家配合仍未验证**。
当前需要继续完成身体供线和分步装配设计；裁线图仍未放行。主模型未修改。

[布尔搜索记录](../harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/PH_rotated_entry/screen.json) · [辅助检查记录](../harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/PH_rotated_entry_fast/screen.json) · [完整线长与分步装配](../harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/split_assembly/index.html) · [总进度](../index.html)
