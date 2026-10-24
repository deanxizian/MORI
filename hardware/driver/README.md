# 当前驱动载板：C3 R98I

2026-10-25 接收。**FAIL / PROTOTYPE / UNVALIDATED：45 项未连接、30 个网络，不可制造。** 本次整理没有修改电路、布局或网络。

- [完整 KiCad 工程](MORI_Driver_C3_R98I.zip)：解压到任意新目录，在 KiCad 10 打开 `MORI_Interface_C3.kicad_pro`。带 19 页原理图、PCB、规则和本地符号/封装库；仅库搜索路径改为相对路径，原始路径表另附，原生板和原理图字节未改。标准 3D 模型使用 KiCad 10 库；缺失模型未补画。
- [文件与来源 SHA256](manifest.json)、[本轮状态](status.json)、[DRC](drc.json)、[ERC](erc_all.json)、[未连接清单](remaining_connections.csv)。
- [当前候选 BOM](bom_candidate.csv)、[线束定义](harness/README.md)。价格是各原始记录日期的目录数据，不是本次重新核价；线长未完成、不可据此裁线。
- [硬件作者完整状态快照](SOURCE_STATUS.md)保留局部失败与未验证范围。机械只接收过 R86B 做独立检查，M1.58 主模型仍是旧载板，不能把 R98I 当成装配合格。

完整 PCB 还需完成连线、回流提示、载流/浪涌、全板视觉与整机适配。原生其余 DRC 0、启用项 ERC 0 不是硬件合格或制造许可。没有生成 Gerber，也没有下单。
