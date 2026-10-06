# MORI V1-H0.3 国内采购核验

2026-09-22更新屏幕和轮驱取舍；其余行保留原观察日期。当前仍不可整套下单。

**2.1寸圆屏 C55111244 已核单件 ¥105.30、现货10个；旧1.28寸撤回。FIT1034与DRI0058退出主BOM，FOC主型号重选，不能再把旧268元当新轮驱报价。**

[大圆屏与动力复核](../reviews/display_motor_review.md) · [主候选BOM](../bom_candidates.csv) · [分项预算](budget_domestic.json)

|用途|采购型号/国内商品页|单价CNY|观察日期/供货|选择结论|
|---|---|---:|---|---|
|头部 yaw / pitch 位置舵机，模拟位置反馈|[DFRobot SER0046 — 9g 270度金属带模拟值反馈舵机](https://www.dfrobot.com.cn/goods-2594.html)|40.00|2026-09-21 / 有货|国内主候选，替代未核国内价的FT90M-FB|
|两个主控模组|[Espressif ESP32-S3-WROOM-1-N16R8 / 立创C2913202](https://item.szlcsc.com/3198300.html)|待核|2026-09-21 / 商品图片辅助页显示现货7233个（动态快照）|保留原主型号；国内渠道已确认，小批量单价未确认|
|刚性机身IMU|[DFRobot SEN0250 / Gravity BMI160 6轴IMU](https://www.dfrobot.com.cn/goods-1693.html)|49.00|2026-09-21 / 有货|国内主候选，替代Adafruit4438|
|黑底双眼圆屏|[Spotpear 0201213 / 1.28inch-LCD-Module / GC9A01](https://spotpear.cn/index/product/detail/id/742.html)|71.00|2026-09-21 / 在售（未公开件数）|撤回主推荐：显示Ø32.4过小，用户要求放大；保留历史采购证据|
|头部照片/跟踪摄像头|[Spotpear 0204002 / OV5640-Camera-Board-(A)](https://spotpear.cn/index/product/detail/id/260/no/198.html)|103.00|2026-09-21 / 在售（未公开件数）|国内主候选，替代未核国内来源的M0031|
|单I2S麦克风|[DFRobot SEN0327 / I2S MEMS麦克风模块](https://www.dfrobot.com.cn/goods-2567.html)|15.00|2026-09-21 / 有货|保留，国内可售与价格已核|
|扬声器I2S功放|[DFRobot DFR0954 / MAX98357 I2S功放模块](https://www.dfrobot.com.cn/goods-3573.html)|30.00|2026-09-21 / 有货|保留，国内可售与价格已核|
|扬声器，带声腔|[DFRobot FIT0825 / 1W扬声器（带音腔）](https://www.dfrobot.com.cn/goods-3226.html)|12.00|2026-09-21 / 库存15（浏览器快照）|国内主候选，替代缺货Adafruit1890|
|2S CC/CV充电模块|[DFRobot DFR0564 / 7.4V锂电池USB充电模块](https://www.dfrobot.com.cn/goods-1706.html)|30.00|2026-09-21 / 有货|保留为2S充电候选；国内有货不等于整链匹配|
|运动/交互独立3.3V支路|[DFRobot DFR0570 / DC-DC 5.5–28V转3.3V模块](https://www.dfrobot.com.cn/goods-1788.html)|15.00|2026-09-21 / 有货|保留，国内可售与价格已核|
|头部/音频5V稳压支路|[DFRobot DFR0753 / DC-DC 6–14V转5V8A模块](https://www.dfrobot.com.cn/goods-2971.html)|55.00|2026-09-21 / 有货|保留，国内可售与价格已核|
|电池电压/电流/功耗监测|[DFRobot SEN0291 / Gravity INA219数字功率计](https://www.dfrobot.com.cn/goods-1890.html)|39.00|2026-09-21 / 有货|保留，国内可售与价格已核|
|FOC轮驱评估电机（非已通过的轮驱）|[DFRobot FIT1034 / 2804 BLDC+AS5600](https://www.dfrobot.com.cn/goods-4230.html)|99.00|2026-09-21 / 库存8（23:51浏览器快照）|撤回当前直驱/1:1轮驱主推荐；扭矩裕量筛选FAIL|
|FOC轮驱功率板|[DFRobot DRI0058 / SimpleFOCmini](https://www.dfrobot.com.cn/goods-4248.html)|35.00|2026-09-21 / 有货|随FIT1034路线撤回主BOM；保留报价比较，不能锁定新轮驱驱动|
|唯一有刷轮驱备选|[DFRobot FIT0521 / 6V 210RPM金属编码减速电机](https://www.dfrobot.com.cn/goods-1427.html)|99.00|2026-09-21 / 有货；商品页免邮标记|保留唯一关键替代，不自动切换主路线|
|成品高倍率2S保护电池包|[亚博智能 7.4V 2S 2000mAh 高倍率电池（官方选项）](https://detail.tmall.com/item.htm?id=694699380589)|待核|2026-09-21 / 未核实|国内电池优先候选，替代进口ANSMANN；价格/库存未核，不许写已确认|
|被筛除的国内电池比较件（不加入主BOM）|[DFRobot FIT0137 / 7.4V 2500mAh带保护电池](https://www.dfrobot.com.cn/goods-434.html)|148.00|2026-09-21 / 有货|不推荐装机；采购有货，电气适配FAIL|
|黑底双眼圆屏|[TDO 冠显 TS021WVC02NP-B1323B / 立创 C55111244 / TR230S](https://item.szlcsc.com/58799605.html)|105.30|2026-09-22 / 现货10个；1个/袋；最小起订1；最快4小时发货（网页动态快照）|新显示主候选：采购规格/单价/现货已核；机械与驱动尚未放行|

FOC路线已核价部分 ¥548.30，不含尚未选定的轮驱及其他未报价项；整机规划总额暂留空，不能写成零成本补齐。保留有刷备选的含额度情景 ¥1476.30，仍不是成交总价。屏幕本体仅比旧候选增加 ¥34.30，连接件另计。

价格/库存为公开页面快照；未向厂家发消息、未加入购物车、未下单。真实连续扭矩、温升、画面并发和续航均NOT_TESTED。
