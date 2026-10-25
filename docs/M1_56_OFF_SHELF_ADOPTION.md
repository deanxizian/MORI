> 阶段采用记录，保留当时输入和检查范围；当前进度以 [CURRENT_STATUS](CURRENT_STATUS.md) 为准。

# M1.56 · 成品模块与 UPS 无托盘直固

2026-10-13。用户确认“采用直固方案”；此前已确认 WeAct＋载板居中、BMI323 和微雪 6 V Buck 分列两侧。本轮正式写入唯一几何源并重建主模型。本地分支 `codex/off-shelf-ups-direct`，未提交或推送。

> 2026-10-13 复核更正：下文原先把 20 个 STL 的组成写错。实际为 15 件本体件、1 件维护底座和 4 件试片；四块软垫只在场景中参考，未导出。保留原交付记录文字供追溯，文件清单以 export_manifest 为准。

## 已采用

- UPS 后移 12 mm，原高度和方向保持；四个短座合入 Load_Frame，原厂四孔使用四枚 M3×25 穿栓和四枚 M3 螺母。
- 取消 Battery_Tray、两枚托盘侧锁 M2 螺钉和两个嵌件。机器人打印件 16→15，没有新增独立支架。
- 主控、载板及插接／五金共 14 件整组旋转 90°，载板中心 X0／Y−6、降低 1 mm。BMI323 中心 X−30／Y0，Buck 中心 X30／Y0。
- 旧小型电池、旧电源板、旧 IMU、两块旧 Buck 和相关固定件退出机械总装；电气功能没有据此自动迁移。
- 保留 CAM USB 朝右、C6、R2、防脱压板、轮驱和四个执行器位置。

维修：打开前后身体壳，托住 UPS，用短 L 扳手及下方套筒拆四组固定件，下降 0.5 mm 后向前退出 120 mm。长直螺丝刀被头部遮挡；已检查短工具直线进入，未验证完整扳手摆动和人手托持。

## 来源与精度

| 器件 | 来源 | 边界 |
|---|---|---|
| Waveshare UPS Module 3S | 用户样品项目中的原厂 STEP，1:1 | 简化 CAD，电芯／绝缘板和完整接插件装件待复核 |
| DFRobot SEN0693 BMI323 | 官方 STEP，1:1 | 按用户配置去掉未焊排针；保留原始小插座曲面，插合待核 |
| Waveshare 6 V Buck | 同系列官方 7.2 V STEP | 6 V 完整装件一致性未知，PLACEHOLDER／ASSUMED，标橙色 |
| 新螺钉螺母 | 标准名义包络 | 采购五金，非打印件；供应商、公差和实物螺纹尚未确认 |

[来源及 SHA256](../mechanical/sources/off_shelf_20261013/source_receipt.json)。311 个原厂闭合实体网格保持，另保留 BMI323 原始插座开放曲面。没有缩放硬件或把厂家 CAD、估算当成实物测量。

## 执行结果

工具：Blender 5.2.2 LTS（d13f752e3b9c）、Python 3.13.13、manifold3d 3.5.3。

| 检查 | 范围与结果 |
|---|---|
| 采用范围 | 193 个零件对象；159 件原对象不变、14 件主控搬位、Load_Frame 改变、32 件旧对象退出、19 件新模块／五金进入 |
| 与批准候选比较 | Load_Frame 对称实体差约 0.00121 mm³，来自浮点存储与极小三角面清理；没有改变结构方案 |
| 主模型 | 13 PASS / 0 FAIL / 8 BLOCKED / 8 NOT_TESTED；含 130 个组合头姿态和记录的刚体检查 |
| 固定与维修 | 四孔承压、螺钉／螺母装入、短工具进入、四组板卡装入、UPS 66 个取出位置通过 |
| 身体前后壳 | 每片 275 个名义路径位置通过，含原附件，不含新插头和完整软线 |
| STL | 20/20 导出与 Blender 回读通过：15 件本体打印件＋5 件维护托架部件 |
| 电子细模 | 842 个分解参考对象位置差 0，不等于独立采购物料数 |
| 动画 | M1.56-A1，22 步、2178 帧、24 fps、1280×720、90.75 秒；190 个物体网格／终态通过，UPS 239 次半帧抽样、身体 956 次、防脱 705 次声明抽样通过 |
| 保护范围 | 846 个硬件源文件字节不变；渲染和回读没有反向修改主模型 |

193 个零件含 5 件维护托架，不含 4 个历史试片。动画排除维护托架、增加 2 个屏幕显示对象，因此为 190 个物体。试片未包含在 20 个本次 STL 中。

[当前检查](../mechanical/current_report.html) · [采用范围](../mechanical/reports/off_shelf_scope.json) · [固定与取出](../mechanical/reports/off_shelf_mount_validation.json) · [视频回读](../mechanical/animation/validation.json)

## 仍未采用的 USB／走线约束

居中 WeAct 的 USB 朝前。移除前壳及喇叭后，10×4.5×16 mm 假设插头包络及 100 mm 前方插拔空间通过；12×6×20 和 14×8×24 mm 更大包络不通过。旧 J5 向左出线会挡 USB，镜像向右仅在小包络条件下不相交。这只是容量研究，没有选定 USB 线、采用完整路线或增加打印件开孔。[检查记录](../mechanical/reports/off_shelf_usb_capacity.json)

DC 入口、UPS／Buck 并发负载、物理断电／互锁、BMI323 I²C 与载板适配、完整新线束、端接和应力释放仍未完成。旧身体线束不再证明新布局成立。6 V Buck 实物修订、实际舵盘／锁紧、FPC、喇叭插头及 PA12 强度／配合待补。后接口板保留历史 P5R7 几何，不能作为新的最终充电接口。

本轮只有确认的机械采用和名义复核，没有采购、制造、上电放行，也未认定 UPS 满足全部并发用电工况。

## 本地重放与历史

正式文件为 [mori_v1_2.blend](../mechanical/mori_v1_2.blend)，构造尺寸仅来自 `config/geometry.json#/off_shelf_modules`；候选网格仅作独立对照。完整交付同步命令：

```sh
python3 mechanical/scripts/run_off_shelf_deliverables.py
```

加 `--rebuild` 会先重建主模型。脚本遇到缺失输入或步骤失败即停止。当前实际逐条执行记录在 `mechanical/reports/off_shelf_executed_commands.json`，日志在 `mechanical/studies/off_shelf_modules_20261013/`；不声称本轮运行过新总控入口。已有文件检查与报告刷新：

```sh
python3 mechanical/scripts/off_shelf_delivery.py --check-only
python3 mechanical/scripts/off_shelf_delivery.py
```

重放依赖历史缓存、M1.55 R2 输入、当前来源包和批准候选对照；维护托架独立求值对照仍引用本地候选 Blender。尚未形成公开可恢复归档，干净克隆缺这些输入时不能宣称全部复测成功。

历史图册保留为 `mechanical/index_M1_55_history.html`。旧 render_manifest、线束、质量和 delivery_consistency 保留历史；当前入口使用专门的 M1.56 执行证据，不将旧结果改版本号充作复测。
