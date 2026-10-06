> **历史版本**：当前硬件已迁移到 [V1.2-H0.1](../v1_2/README.md)。以下报价、屏幕和轮驱分析仅供追溯，不用于新S288/3S方案。H0.3发布器遇到V1.2活动基线会拒绝覆盖契约。

# MORI V1-H0.3：大圆屏与轮驱重选

屏幕主候选改为 TDO TS021WVC02NP-B1323B（立创C55111244）：实际显示Ø53.28mm、480×480、QSPI/SPI，单件105.30元，2026-09-22页面现货10个。旧1.28寸小屏撤回。

FIT1034 2804 + DRI0058退出当前主BOM，FOC路线保留，具体新轮驱待选。旧268元轮驱报价和1322元整机情景不能当成新方案成本。轮端连续约0.10Nm、短时峰值至少0.20Nm是后续筛选目标，尚非已验证能力。

- [本次复核、尺寸与计算结果](reviews/display_motor_review.md)
- [主候选BOM](bom_candidates.csv) / [国内采购核验](procurement/BOM_国内采购核验.md)
- [可复算脚本](calculations/review_display_motor.py) / [48组仿真JSON](reviews/display_motor_review.json)
- [显示模块端号表](interfaces/display_TR230S_V1-H0.3.csv)：没有擅自分配MCU GPIO

共享契约已交接新屏分件包络并撤销旧轮驱主候选；机械母球、现有模型和固件未改。H0.1 GPIO表不能用于新器件接线。

全部硬件试验NOT_TESTED。V1 KiCad/PCB尚未完成、ERC/DRC未执行，未采购或导出制造文件。历史H0.2文件在revisions/V1-H0.2/。本次仅完成屏幕取舍和轮驱裕量审查，不宣称整机硬件工程已经完成。
