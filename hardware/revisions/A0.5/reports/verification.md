# A0.5 实际验证记录

日期2026-09-21。本报告的PASS有明确范围；物理硬件状态统一为NOT_TESTED。

|检查|结果|证据/边界|
|---|---|---|
|ESP-IDF5.5.2编译|PASS，exit0|idf_build.log、idf_build_command.json；未flash|
|原LEDC问题复现|旧初始化失败，修复后通过|ledc_before.log / ledc_after.log；模拟驱动契约|
|主机核心状态测试|PASS，163项断言|host_tests.log；ASan/UBSan，模拟输入|
|电机适配层及默认锁定|PASS，22+10项断言|adapter_tests.log；不证明物理时序|
|KiCad10.0.6 ERC|PASS，0违规|erc.json；原生工具|
|KiCad DRC|PASS，0违规、0未连接|drc_routed.json；包含原理图一致性检查|
|原理图/PCB一致性|PASS，0问题|drc_routed.json；未禁用未连接规则|
|网表/PCB/接线|PASS，242针网、94行载板接线|audit.json；另7行外部线束保留待实物连续性测试|
|GPIO与默认锁定|PASS|pinmap与A0.4相同，三项运动编译门=n|
|原机械源保持|PASS|params、derived和原Blender哈希未变|
|A0.4固件档案保持|PASS，18文件|baseline_firmware_hashes.json、audit.json|
|新STL几何|PASS，2个闭合单实体|fit_review.json；不是打印/强度验证|
|Blender/STL重开|PASS|mechanical/reopen_check.json；独立重开后尺寸误差<0.002mm|
|主控整机装配|FAIL当前保守包络|与Load_Frame相交640.179mm³；主控高度仍需实测|
|最终载板布局放行|NOT_TESTED / 未放行|局部去耦与回流尚需优化，详见electrical_changes.md|
|实际上电/急停/热/头行程/平衡|NOT_TESTED|没有设备测量与运行日志|

最终板：80封装、1074走线/过孔、2覆铜区。制造允许=false。无Gerber/钻孔输出、无采购/付款、无烧录。原生板SHA256：`9fdfdb99cf219452565bb680c331b3180dc0a1aa6d1fc7838382ce6cf01059cd`。

最终路由过程的日志为autorouter_clean_03.log，随后通过finish_ground.py补齐U6接地并重新覆铜。较早路由日志保留失败记录；不能拿早期自动布线计数代替最终原生DRC。

本版源码哈希见verified_source_hashes.json。机械报告只检查候选包络与理想内球面/既有Load_Frame；不是完整装配或线束运动扫掠。整机质量、惯量、扭矩和供电余量继续以A0.4假设为基线，不把这些静态检查宣称为实物性能。
