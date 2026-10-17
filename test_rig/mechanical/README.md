# 模型与打印文件

单位为 **mm、100% 比例**。以下仅打印单件 STEP/STL，不要把完整装配或厂家参考件当作打印件。文件保持原始字节，本次没有改孔位、圆角或支撑。每份文件的来源和 SHA-256 见[导入清单](../import_manifest.json)。

| 打印件 | 数量 | STEP | STL |
|---|---:|---|---|
| R37 一体底板，含两侧舵机支架 | 1 | [底板](print/baseplate_R37.step) | [试装网格](print/baseplate_R37_TRIAL.stl) |
| R41 六辐条轮圈，同件用于两侧 | 2 | [轮圈](print/wheel_hub_R41_TRIAL.step) | [试装网格](print/wheel_hub_R41_TRIAL.stl) |
| R55 第二层平台 | 1 | [平台](print/second_platform_R55.step) | [试装网格](print/second_platform_R55_TRIAL.stl) |
| R59 前视、上仰 40° 支架 | 1，可选 | [当前支架](print/camera_bracket_R59_40deg.step) | [试装网格](print/camera_bracket_R59_40deg_TRIAL.stl) |
| R60 后视、上仰 40°、增高 5 mm | 对比件，不与 R59 同装 | [对比支架](print/camera_bracket_R60_REAR_40deg.step) | [试装网格](print/camera_bracket_R60_REAR_40deg_TRIAL.stl) |

完整可编辑装配包：

- [R41 第一层与轮组](assemblies/test_rig_R41.blend.zip)
- [R55 两层装配，不含新增 Pi 摄像头支架](assemblies/test_rig_R55_TWO_LAYER.blend.zip)
- [R59 两层装配与前视摄像头](assemblies/test_rig_R59_TWO_LAYER_CAMERA.blend.zip)
- [R60 两层装配与后视摄像头对比](assemblies/test_rig_R60_TWO_LAYER_CAMERA.blend.zip)

将 ZIP 解压到本地任意目录后用 Blender 打开。打印几何已在文件中；部分外部来源路径和属性是原制作机器的记录，不能直接作为可用重建路径。

## 接口与版本边界

- 底板 160 × 80 × 4；上方板卡支撑约 4 mm，UPS 下方一体柱 4.5 mm。两侧舵机支架与底板一体；没有独立维护架作为当前打印项。
- R41 轮圈沿用实物原轮圈的 Ø72.5 / Ø64 胎配合参考和浅内凹 2 mm，保留六孔承压深度和内外圆角。橡胶型号 FIT0500，橡胶与打印轮圈的公差、长期防脱仍需实物检查。
- R55 平台 160 × 80 × 4，含短柱总高 9；外周上下沿 R0.4；2 个 8 × 12 长腰孔。四角叠层孔距 **148 × 68、孔 Ø2.8**，内侧扩展孔 **64 × 64、孔 Ø2.8**。
- 两层使用 **M2.5 双通六角螺柱，柱体长 35 mm**。以后同四角叠层可用 M2.5×12 无头连接螺杆穿过 4 mm 板，上下各名义进入 4 mm；这只是接口方案，第三层高度和视野需要重新检查。
- R59/R60 相机孔距 21 × 12.5，孔 Ø2.2；底座使用 64 mm 孔距、Ø2.8。R59 支撑竖直、安装板连接居中，镜头朝 +Y 上仰 40°。
- **R60 不能直接按现有 35 mm 螺柱再叠整块第三层**：最高硬件名义超出约 0.408 mm，光轴也会被遮挡。见[原始检查](../evidence/cad/r60/third_layer_check.json)。单纯加高不能证明视野合格。

参数记录：[R41](parameters/r41.json)、[R55](parameters/r55.json)、[R59](parameters/r59.json)、[R60](parameters/r60.json)。它们是各次变更的原始设计记录，包含历史字段和本机路径；本次没有承诺用这几个 JSON 即可从零重建所有历史修订。精确当前形状以本包 STEP/STL 和原生 Blender 为交付对象。

## 制造状态

打印件分类为 PRINTABLE / ASSUMED（设计尺寸）；装配中的实购参考件依据逐字段分为 VENDOR_DOCUMENTED、MEASURED 或 ASSUMED。厂家模型不等于到货实测，橙色部件和带 REFERENCE 的对象不能因渲染逼真视为尺寸已确认。

底板和第二层已由用户报告到货。本包保留原始几何报告，但没有把到货自动升级为每个孔、每个螺丝和所有模块都试配通过。第二层短柱径向壁厚 1.7–1.9 mm；R59/R60 相机垫柱壁厚 1.2 mm，沿用已选择的细柱版本，未采用 R57 加粗方案。打印材料、公差、支撑去除、强度和厂商审图结论需单独确认。

原始报告在 [CAD 证据目录](../evidence/cad/)。新的交付检查只核对文件、实体和网格，不宣称打印强度、轴承负载或长期运行合格。
