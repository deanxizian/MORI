# 需求及追踪

原始用户全文保留在 requirements_original.txt；机械尺寸交接保留在 dimensions/。下表标的是交付物，不是实机能力。

|需求|实现文件|实物状态|
|---|---|---|
|三电机、纯两轮主动平衡、不得缩放器件|AGENTS.md；mechanical_interfaces.json|NOT_TESTED|
|真实结构与器件尺寸对照|tools/sync_mechanics.py；mechanical_change_requests.md|NOT_TESTED|
|模型体积、质量/重心/惯量和动力学|calculations/；reports/model_volume_mass.json|NOT_TESTED|
|采购型号、预算和来源|bom.csv；sources.md|NOT_TESTED|
|供电、回灌、急停/默认禁用|architecture.md；power_budget.md；KiCad|NOT_TESTED|
|GPIO、端子视图、线序、线径|pinmap.csv；wiring.csv|NOT_TESTED|
|模块化固件、安全门、非阻塞交互|firmware/|NOT_TESTED|
|构建、模拟输入/故障测试|reports/idf_build.log；reports/host_tests.log|只证明对应软件检查|
|原生KiCad、规则检查、板框对齐|kicad/；reports/erc.json；reports/drc.json|未布线，不允许生产|
|从断电到自由运动的风险递增验证|test_plan.md；tests/physical_test_record.csv|NOT_TESTED|

目标环境为室内平整硬地面；0.3m/s为设计目标、初测0.1m/s；头±60°为目标、调试±50°。不承诺断电自立、摔倒自起、自动回充。充电时必须断开机器人电源连接；无第三运行接点。
