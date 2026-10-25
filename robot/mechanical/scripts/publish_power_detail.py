"""Publish evidence from the independent power-board extraction."""
from pathlib import Path
import json
import html

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'studies/power_P3_detail'
inv = json.loads((OUT/'inventory.json').read_text())
check = json.loads((OUT/'conversion_check.json').read_text())
cam = json.loads((OUT/'cam_resource_audit.json').read_text())
rows = [f for f in inv['footprints'] if f['reference'] in inv['missing_component_references']]
table = '\n'.join(f"| {f['reference']} | {f['value']} | {f['xy_mm']} / {f['rotation_deg']:g}° / {f['side']} |" for f in rows)
text = f'''# 电源板详细模型与CAM资料核对

这份是原生P3电源板的独立机械参考。已实际导出STEP、转成可编辑Blender对象并渲染；没有把它替换进MORI总装，没有修改硬件电路或布线。

- [Blender模型](MORI_power_P3_detail.blend)
- [部分装件STEP](MORI_power_P3_POPULATED_PARTIAL.step)
- [斜视实际渲染](oblique.png) / [顶视实际渲染](top.png)
- [尺寸和来源清单](inventory.json) / [CAD转换检查](conversion_check.json)

## 电源板可以细化到什么程度

来源：[MORI_power_P3.kicad_pcb](../../../hardware/v1_2/kicad/MORI_power_P3/MORI_power_P3.kicad_pcb)，SHA256 `{inv['source_sha256']}`。

原生板上有{inv['footprint_count']}个封装位置：{inv['existing_model_references']}个有可解析三维库模型，14个器件没有可用模型，另外8个为4个安装孔和4个测试点。实际STEP含{check['components']}个组件（85个器件加PCB），{check['solids']}个实体，OCC实体有效性检查全部通过。每个器件保持原PCB坐标、旋转和面别，没有缩放硬件。

板框80×55mm；KiCad原生设计目标总厚1.6mm。当前STEP板芯几何为1.44mm，铜/阻焊等完整层叠没有在本参考中逐层建模，不把1.44mm宣称为成品实测板厚。图中绿色、灰色、白色为审查配色，不是实物颜色认证。

橙色问号仅标示缺失器件的原生封装位置，不代表器件实体或高度：

| 位号 | 器件/功能 | PCB坐标mm / 旋转 / 面别 |
|---|---|---|
{table}

8个XT30、2个保险丝、2个电感、2个TPS54302待补匹配CAD或有来源的包络。J6虽有DNP字样，仍须按最终装配选项核对。其余KiCad库模型也需与实际采购封装版本核准；对插插头、导线出口、弯曲半径、焊料和工具空间未包含，因此不能由这份图宣称全装件适配已经通过。

找到更新的P3R1工作文件；本次对比的器件位置、角度和面别与P3相同，未找到P3R1机械正式交接，未将其直接升格为当前机械真值。P3布线风格被用户退回的问题仍存在，机械可视化不构成电气设计验收。

## 微雪CAM的资料情况

核对型号：Waveshare ESP32-S3-CAM-OV3660，SKU33700。已检查[官方说明](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx)、[资源页](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)及[官方仓库](https://github.com/waveshareteam/ESP32-S3-CAM-OVxxxx)。仓库树 `{cam['tree_sha']}` 共{cam['files_examined']}个文件，返回未截断；未找到STEP/STP/IGES/PCB布局/网格文件，Schematic目录只有原理图PDF。检查记录见[cam_resource_audit.json](cam_resource_audit.json)。这表示此次公开资源中未找到，不是断言厂商没有内部CAD。

现有可核对尺寸是37×37mm板框与32.6×32.6mm安装孔中心距。板厚、孔径、完整装件高度、麦克风/天线/接插件精确坐标及镜头/FPC仍不完整。照片和原理图可以帮助辨识器件、做明确标注估计值的分件示意，却不能恢复精确安装三维几何。没有把其他品牌的ESP32-S3-CAM模型混用，也没有把照片推算升级为厂商核准尺寸。

## 重复生成

在MORI项目根目录依次运行：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3.9 mechanical/scripts/power_detail_reference.py inventory
/Users/dean/.cache/codex-runtimes/mori-cad/bin/python mechanical/scripts/power_detail_reference.py mesh
/Applications/Blender.app/Contents/MacOS/Blender --background --python mechanical/scripts/power_detail_reference.py -- blend
python3 mechanical/scripts/publish_power_detail.py
```

原生输入的只读快照、STEP导出日志、转换日志、Blender日志保留在本目录。KiCad {inv['kicad_version']}；Blender版本见blender_check.json。主总装、共享geometry与硬件合同保持原状态。
'''
(OUT/'README.md').write_text(text)
missing = ''.join(f"<tr><td>{html.escape(f['reference'])}</td><td>{html.escape(f['value'])}</td></tr>" for f in rows)
page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MORI 电源板详细参考</title>
<style>body{{margin:0;background:#151b22;color:#e2e9ee;font:16px/1.7 system-ui}}main{{max-width:1150px;margin:auto;padding:28px}}a{{color:#86d6e4}}p{{color:#bbc9d3}}.note{{background:#263542;padding:20px;border-radius:12px}}img{{width:100%;display:block;border-radius:12px;margin:24px 0}}td{{padding:8px 16px;border-bottom:1px solid #3a4651}}h2{{margin-top:36px}}</style>
<main><h1>电源板 · P3装件参考</h1><p>原生KiCad位置与三维库模型 · 独立Blender模型</p>
<div class="note"><b>85个器件模型 + PCB · 14个器件待补CAD</b><p>橙色问号是缺失模型的位置标记。本图尚未替换总装中的电源板包络，不代表完整装配已经通过。</p></div>
<p><a href="MORI_power_P3_detail.blend">打开Blender文件</a> · <a href="MORI_power_P3_POPULATED_PARTIAL.step">STEP</a> · <a href="README.md">完整说明</a> · <a href="../../index.html#parts">返回整机</a></p>
<img src="oblique.png" alt="P3电源板实际Blender斜视渲染"><img src="top.png" alt="P3电源板实际Blender顶视渲染">
<h2>当前缺少的器件CAD</h2><table>{missing}</table><p>85个已显示器件采用KiCad封装库；采购版本、对插插头和线束仍需核准。板框80×55mm；设计总厚1.6mm，STEP板芯1.44mm，未逐层呈现铜与阻焊。</p>
<h2>微雪CAM板</h2><p>官方文档及官方仓库此次未发现完整STEP或PCB布局文件。37×37mm板框和孔心距已有依据，但装件高度、精确器件位置与镜头排线尚不完整；当前CAM模型没有改成貌似精确的照片推算模型。</p>
<p><a href="https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents">微雪官方资源</a> · <a href="cam_resource_audit.json">本次查询记录</a></p></main></html>'''
(OUT/'index.html').write_text(page)
print('POWER_DETAIL_REPORT_COMPLETE')
