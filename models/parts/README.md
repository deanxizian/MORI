# MORI 零件拆解

已将总装中的 **96 个零件/占位对象实例 + 4 个试打件** 分别保存为 100 个独立 Blender 文件。重复螺钉、嵌件和轴承滚动体按实例分别编号；这不是 96 种已选定采购件。

先打开 [MORI_parts.blend](MORI_parts.blend)。场景选择器有四个场景：

| 场景 | 内容 |
|---|---|
| 01_Custom_Parts | 25 个自制结构件的分离排布 |
| 02_Hardware_References | 71 个外购参考或待选型硬件/空间占位 |
| 03_Test_Coupons | 4 个试打件 |
| 04_Assembly_Check | 96 个零件回到原装配位置，另有 2 个眼睛显示内容对象 |

总览中同一零件的排布对象和装配对象共享网格。Tab 编辑顶点时，两个场景都会显示修改；对象位置单独保留。原总装的运动控制仍在 `source/MORI_assembly.blend` 中。

[中文零件索引](parts_index.md) 列出了尺寸和独立文件链接；也可用 [CSV 清单](parts_index.csv) 搜索。独立文件位于 `parts/` 的 8 个分组目录，各文件只含一个物理零件网格，附相机、照明和内嵌说明。硬件占位状态保留在对象自定义属性中。

## 尺寸与编辑

坐标数值单位为 mm，Blender 场景单位倍率 0.001，对象缩放 (1,1,1)。独立零件保留装配朝向，只将 XY 包围盒中心平移到原点、最低点移到 Z=0。此朝向不代表推荐打印朝向。N → Item 可查看尺寸；Object → Custom Properties 可看中文名称、接口状态和装配偏移。

归一化只改变位置，没有改变形状或尺寸。`parts_manifest.json` 的 `assembly_offset_mm` 可将零件移回原装配位置；`source_world_matrix` 保留原变换信息。独立文件中的手工修改不会自动写回总览、原总装或参数。

## 重复生成

包中 `source/` 是拆件时的原总装与参数快照；`tools/split_parts.py` 是同一生成脚本，不依赖第三方 Python 包。当前已在 Blender 5.2.1 LTS 实际运行。

在解压目录运行（macOS）：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python tools/split_parts.py -- --source source/MORI_assembly.blend --output regenerated_parts
```

在 MORI 原项目可运行 `scripts/split_parts.py -- --output models/parts_v2`。输出目录非空时脚本拒绝覆盖，避免丢失手工编辑；使用新目录重新生成即可。参数变更应先通过原项目 `build.py` 重建并复核总装，再运行拆件脚本。

## 已验证范围

100 个独立文件均保存为原生 Blender 项目并从磁盘重开验证：每文件一个网格、单位和缩放正确、没有悬空父对象或动画、顶点/面顺序和形状保留、尺寸与装配还原误差小于 0.0001 mm。详见 `split_validation.json`。源总装的 SHA-256 未改变。

此验证确认文件拆分与几何保持，不构成可制造性或实物硬件适配结论。25 个 PRINTABLE 分类是结构原型，其中 19 个曾作为 STL 试打候选；轮毂、薄遮光框和限位块等仍有接口待定。已有候选 STL 继续位于原项目 `exports/stl/`，本次未新增制造承诺。

本次生成的预览来自实际 Blender 网格，相机排布中的所有零件保持真实尺寸比例，小螺钉会明显小于外壳。
