# MORI V1-H0.2：国内采购核验更新

用户已允许预算适度超出1000元。当前需要闭合的是可采购SKU、电压/控制接口与安装包络；不再把原1000元硬预算作为不能继续的理由。

本次逐项核到16种国内公开有货/在售器件，15种有人民币公开单价；含不同轮驱评估件和被筛除的电池，不能全部相加。**完整BOM尚未冻结，也没有达到可整套下单状态。**

- [国内采购核验表](procurement/BOM_国内采购核验.md) / [CSV](procurement/BOM_国内采购核验.csv)：具体商品链接、选项、价格、库存观察、日期、供货与适配分栏。
- [当前主/备选候选BOM](bom_candidates.csv) / [JSON](bom_candidates.json)：保留USB-C、保护、回灌、线束、机械件、PCB、打印和运费等必要未报价项；没有记作免费已有。
- [国内预算计算](procurement/budget_domestic.json)：FOC国内已核标价部分782元，加入尚未报价额度的情景为1322元；有刷相应为767/1442元。均非含运费成交总价，风险余量100元未额外计入。
- [机械交接](procurement/mechanical_handoff_H0.2.md)：新器件真实公开尺寸已写共享机械契约，旧模型分配未变；未知孔位/高度/净质量保留null。
- [冲突表](conflicts.csv)：逐项说明供货问题已解决到哪一步，以及仍不能定板的具体原因。

头部主候选改SER0046×2，机身IMU改SEN0250，摄像头改OV5640-A，扬声器改FIT0825；圆屏使用国内Spotpear0201213。双主控仍ESP32-S3-WROOM-1-N16R8×2，功能和四执行器数量未删。

FOC评估对象现为FIT1034+DRI0058×2，电机/编码器/驱动共268元；供应商可售，但驱动最低8V，2S低压区不兼容，且没有轮端连续力矩证明。它不是Hover同款，也不能套旧UART接口。有刷FIT0521只作为一套备选，其成品H桥国内供货尚未核完。

电池优先候选为亚博2S2000mAh高倍率成品保护包，厂家国内销售链接已找到，选项价格/库存未取得。国内有货148元的FIT0137持续仅2.5A，不因有货就用来代填。

**接口状态：** shared electrical contract仍保留H0.1引脚作为历史候选，新增procurement_update明确H0.2器件不可照旧表接线。新FOC为3PWM，IMU为I2C，摄像头型号已变；要先审核资源并发布新的pinmap，再画原理图。

**验证状态：** 没有实物。全部硬件试验NOT_TESTED。V1原生KiCad工程/PCB仍未创建，ERC/DRC未执行；未导出制造文件、未采购。旧A0工程的检查不证明V1。H0.1质量/动力/续航是旧器件假设的敏感性分析，不能直接作为新BOM结果。

历史[H0.1完整报告](revisions/V1-H0.1/README.md)、[计算脚本](calculations/README.md)、[测试计划](test_plan.csv)仍保留。软件可继续[协议与模拟设备工作](software_parallel_prompt.md)，新外设驱动和实机使能需要候选接口闭合。

复算本次采购输出：`python3 hardware/v1/tools/build_domestic_bom.py`，然后运行`python3 hardware/v1/tools/publish_procurement_handoff.py`。旧H0.1生成脚本应在历史副本运行，不能覆盖本版。

新增[数值筛选](procurement/calculation_checks.json)可用`python3 hardware/v1/tools/check_domestic_feasibility.py`复算。亚博包14.8Wh按80%可用SOC和90%容量余量得到约10.7Wh；沿用旧11.34W压力情景仅约56分钟，故不能沿用进口大电池的92分钟估算。新BOM实际功耗/质量/惯量仍需补数据。
