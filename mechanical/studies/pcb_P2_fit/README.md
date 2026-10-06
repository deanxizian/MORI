# MORI 自绘 PCB 尺寸反馈与电源板空间上限

电源板建议按 **80 × 55 mm** 作为当前 PCB 设计上限，板厚按 **1.6 mm**。相较旧 P2 的 80 × 45 mm，前后增加 10 mm，面积增加约 22%。这是一份需要调整局部托板后才能采用的机械输入，S3 电路、板框、孔位仍未冻结。

| 项目 | 当前建议 |
|---|---|
| 电源板左右 × 前后 | 最大 80 × 55 mm |
| 板正面元件高度 | ≤16 mm，从 PCB 正面计；包括插头的部分若超过此高度需重新检查 |
| 板背面元件/焊脚 | ≤3 mm，从 PCB 背面计 |
| 检查用整体装件空间 | 80 × 55 × 20.6 mm；不等于已验证配对插头/线束 |
| 安装位置 | 中心 X=0、Y=3 mm；板底约 Z=119.5 mm，较主托板顶面抬高4.5 mm |
| 有限搜索得到的贴边界限 | 82 × 57 mm；与承重桥、基板、IMU各约1 mm，不作为推荐加工尺寸 |
| 80 × 60 mm | 本次给定摆放位置检查失败，与后方基板冲突；不能直接采用 |

80 × 55 装件保守实体距 Yaw 承重桥最近约 **1.4 mm**，距主托板 **1.5 mm**，距基板和 IMU 各 **2 mm**。这些是名义 CAD 间隙，未包含制造公差、受力变形或实物误差。

## 找到的三块旧板

| 自绘板 | P2板框/名义板厚 | 本次反馈 |
|---|---|---|
| 运动基板（WeAct载板） | 70 × 35 × 1.6 mm | 暂不改板框；后移7 mm、抬起安装，给背面J6/J8及元件让位。排母型号和6 mm试算堆叠仍待确定。 |
| IMU板 | 20 × 16 × 1.6 mm | 暂不改板框；移到左前侧的刚性座。两个原有安装孔保留，支座刚性/工具空间待下一步验证。 |
| 电源板 | 80 × 45 × 1.6 mm | P2为历史参考；S3可在80 × 55范围内重新布局，不能称旧P2已适配S3。 |

源文件位于 `hardware/v1_2/kicad/MORI_motion_P2/`、`MORI_imu_P2/`、`MORI_power_P2/`，对应 `.kicad_pcb`、原始板框、孔位和元件坐标已读取，没有修改原文件。

PCB +X向右、+Y向下；机器人 +X向右、+Y向前、+Z向上。导入只用刚性坐标变换，比例为1。KiCad名义总厚1.6 mm包含叠层；STEP只输出介质芯板，所以运动/IMU芯板厚1.51 mm、电源芯板1.44 mm，铜和阻焊未伪装成介质。容量检查保守按总厚1.6 mm。

## 达到上限所需的机械调整

1. 基板中心从 `(0,-37)` 移到 `(0,-44)` mm，PCB基准面Z=121 mm。后排原孔中心到Y=-59 mm，超出当前托板后边缘3.5 mm；需要局部扩展安装面并核对螺钉边距，不能把基板悬空算安装完成。
2. IMU中心移到 `(-50,33)` mm，Z=123 mm，保持绕Z90°。固定在主框架，不能固定在松动维修盖上。
3. 移动现有两处局部板座；保留4 mm主托板。电源采用短支点/开口托座，替换当前完整平托板；新S3孔位确定后再做最终支点。
4. 头部主线束下端从 `(-42,25,137)` 移到 `(-45,28,137)` mm，在Z=144 mm接回原路径；上方服务环不变。线束仍为半径1.2 mm的路径预留，不是实测线束。
5. 电池、轮驱、头部两轴轴线、扬声器壳体固定和外壳不因本次板框建议而改变。S3端子应在板边分组，配对插头及转弯必须在具体排布后复核；16 mm不能自动包含未知的插头/护套/弯线。

## 实际建模与检查边界

已从三块原生PCB重新导出并导入现有KiCad装件模型，补入WeAct原厂224实体CAD，按P2 U100排针坐标作刚性配准。WeAct与载板现有模型的实体检查未发现穿透；这不能证明尚未选定的排母接触深度正确。裸板贴在旧占位底面的基准试放会让基板背面元件和电源板焊脚穿入旧托板，故必须增加真实安装高度。

KiCad缺少8个XT30UPB-M三维库文件，已按[AMASS原厂2026目录第10页](https://www.china-amass.com/public/upload/20260207/7fa24f5a6f35ec66c7a115c07a34ab06.pdf)补入10.2 × 5.6 × 10.7 mm本体与3 mm焊脚的保守尺寸体。它们是尺寸包络，不是原厂详细STEP；配对插头未包含。电容库模型只有10 mm高，本次按S3要求叠加Ø10 × 16 mm包络，图中以橙色注明。

闭合三角实体通过Manifold64检查相交体积和最短间隙；AABB仅用于粗筛，不拿包围盒不重叠冒充实体验证。本次所有导入实体均可用于实体检查，没有失效网格的包围盒替代。8个XT30仍是上段声明的保守尺寸体。阈值为相交体积0.01 mm³，几何间隙1 mm。搜索限制为水平、与机身轴对齐的矩形板；前后尺寸44–64 mm步长1 mm，Y中心1–10 mm步长1 mm，宽度由承重桥净宽84减两侧间隙推导为82 mm，板高和6组基板位置、9组IMU位置分别核对。这不是任意形状/任意旋转/所有布置的全局最大尺寸证明。

已通过本次名义空间检查：80 × 55装件容量；旧P2电源板补齐所述包络后的试放；WeAct与旧基板模型的内部穿透检查。尚未通过：完整配对插头与线束、真实排母、最终紧固件和支座、装卸路径、热设计、S3电路布局、完整动作复验、实际加工与平衡。

## 交付与复现

- `MORI_P2_PCB_FIT_STUDY.blend`：三块P2板与WeAct独立对象、建议摆放、80 × 55蓝色容量框。S3没有虚构元件。
- `power_capacity_plan.png`：实际模型俯视检查图。承重桥临时隐藏以看清板卡，仍包含在实体检查中。
- `pcb_fit_assembly.png`：实际装件与承重桥位置。
- `native_inventory.json` / `fit_results.json`：源文件哈希、孔位/元件、命令、候选姿态、测量与限制。
- 共享参数：`config/geometry.json#/pcb_capacity_proposal`；接口反馈：`contracts/mechanical_interfaces.json#/custom_pcb_capacity_feedback`。均标明PROPOSED，当前M1.10总装的`layout`未改。

实际使用 KiCad 10.0.6、Blender 5.2.1 LTS、OCP 7.8.1.1.post1、Manifold3D 3.5.3。日志保存在本目录。复现从项目根目录运行：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 mechanical/scripts/prepare_p2_fit.py
/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/scripts/convert_p2_fit.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/analyze_p2_fit.py
/Applications/Blender.app/Contents/MacOS/Blender --background mechanical/mori_v1_2.blend --python-exit-code 1 --python mechanical/scripts/render_p2_fit.py
/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 mechanical/scripts/report_p2_fit.py
```

原生三块PCB、硬件所有者的`contracts/components.json`及M1.10总装.blend均通过哈希复核，保持原样。本次未输出新PCB制造文件、未重新布线、未宣称候选支座可直接打印。
