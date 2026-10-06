# 电源板详细模型与CAM资料核对

这份是原生P3电源板的独立机械参考。已实际导出STEP、转成可编辑Blender对象并渲染；没有把它替换进MORI总装，没有修改硬件电路或布线。

- [Blender模型](MORI_power_P3_detail.blend)
- [部分装件STEP](MORI_power_P3_POPULATED_PARTIAL.step)
- [斜视实际渲染](oblique.png) / [顶视实际渲染](top.png)
- [尺寸和来源清单](inventory.json) / [CAD转换检查](conversion_check.json)

## 电源板可以细化到什么程度

来源：[MORI_power_P3.kicad_pcb](../../../hardware/v1_2/kicad/MORI_power_P3/MORI_power_P3.kicad_pcb)，SHA256 `777341fd3ff7ef0608aedb902dde0b6807e15a6bd74f9273688697ce3e094f02`。

原生板上有107个封装位置：85个有可解析三维库模型，14个器件没有可用模型，另外8个为4个安装孔和4个测试点。实际STEP含86个组件（85个器件加PCB），86个实体，OCC实体有效性检查全部通过。每个器件保持原PCB坐标、旋转和面别，没有缩放硬件。

板框80×55mm；KiCad原生设计目标总厚1.6mm。当前STEP板芯几何为1.44mm，铜/阻焊等完整层叠没有在本参考中逐层建模，不把1.44mm宣称为成品实测板厚。图中绿色、灰色、白色为审查配色，不是实物颜色认证。

橙色问号仅标示缺失器件的原生封装位置，不代表器件实体或高度：

| 位号 | 器件/功能 | PCB坐标mm / 旋转 / 面别 |
|---|---|---|
| J3 | WHEEL BUCK 9V RETURN | [40.0, 7.0] / 0° / F |
| L60 | 10uH / SRP7050TA-100M | [20.5, 20.0] / 180° / F |
| F60 | 1A / 125V / very fast | [38.0, 13.0] / 0° / F |
| J5 | HEAD BUCK 6V RETURN | [4.0, 46.0] / 90° / F |
| J2 | WHEEL BUCK VIN | [23.0, 7.0] / 0° / F |
| J4 | HEAD BUCK VIN | [4.0, 33.0] / 90° / F |
| L70 | 10uH / SRP7050TA-100M | [20.5, 40.0] / 180° / F |
| U60 | TPS54302DDCR | [30.0, 23.0] / 0° / F |
| J1 | PACK AFTER 6.3A FUSE / MASTER | [9.0, 7.0] / 0° / F |
| U70 | TPS54302DDCR | [30.0, 43.0] / 0° / F |
| F70 | 2A / 125V / very fast | [35.5, 33.0] / 90° / F |
| J12 | HEAD DUMP 10R EXTERNAL | [65.0, 48.0] / 0° / F |
| J6 | RAW BAT SERVICE / DNP | [40.0, 51.0] / 0° / F |
| J11 | WHEEL DUMP 5R6 EXTERNAL | [65.0, 7.0] / 0° / F |

8个XT30、2个保险丝、2个电感、2个TPS54302待补匹配CAD或有来源的包络。J6虽有DNP字样，仍须按最终装配选项核对。其余KiCad库模型也需与实际采购封装版本核准；对插插头、导线出口、弯曲半径、焊料和工具空间未包含，因此不能由这份图宣称全装件适配已经通过。

找到更新的P3R1工作文件；本次对比的器件位置、角度和面别与P3相同，未找到P3R1机械正式交接，未将其直接升格为当前机械真值。P3布线风格被用户退回的问题仍存在，机械可视化不构成电气设计验收。

## 微雪CAM的资料情况

核对型号：Waveshare ESP32-S3-CAM-OV3660，SKU33700。已检查[官方说明](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx)、[资源页](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)及[官方仓库](https://github.com/waveshareteam/ESP32-S3-CAM-OVxxxx)。仓库树 `72af9302030bb6f018d5c21b1225005481e09fda` 共4986个文件，返回未截断；未找到STEP/STP/IGES/PCB布局/网格文件，Schematic目录只有原理图PDF。检查记录见[cam_resource_audit.json](cam_resource_audit.json)。这表示此次公开资源中未找到，不是断言厂商没有内部CAD。

现有可核对尺寸是37×37mm板框与32.6×32.6mm安装孔中心距。板厚、孔径、完整装件高度、麦克风/天线/接插件精确坐标及镜头/FPC仍不完整。照片和原理图可以帮助辨识器件、做明确标注估计值的分件示意，却不能恢复精确安装三维几何。没有把其他品牌的ESP32-S3-CAM模型混用，也没有把照片推算升级为厂商核准尺寸。

## 重复生成

在MORI项目根目录依次运行：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 mechanical/scripts/power_detail_reference.py inventory
/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/scripts/power_detail_reference.py mesh
/Applications/Blender.app/Contents/MacOS/Blender --background --python mechanical/scripts/power_detail_reference.py -- blend
python3 mechanical/scripts/publish_power_detail.py
```

原生输入的只读快照、STEP导出日志、转换日志、Blender日志保留在本目录。KiCad 10.0.6；Blender版本见blender_check.json。主总装、共享geometry与硬件合同保持原状态。
