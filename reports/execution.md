# 本轮实际执行记录

日期：2026-09-21。工作目录最初为空，没有发现现成 .blend 或参考图片。按用户补充，将交付同步到其已创建的 MORI 项目目录。

环境实际探测到 `/Applications/Blender.app/Contents/MacOS/Blender`，版本 **5.2.1 LTS**，构建哈希 `9e2066aef7ef`，Blender 内置 Python **3.13.13**、numpy **2.3.4**。没有依赖 Blender MCP 连接。

实际执行过版本/接口检查、bpy 建模、Cycles 渲染、毫米 STL 写出与回读、闭合三角实体交集、运动采样、拆卸/工具路径、径向球壳厚度、STL 自交风险筛查及重复生成检查。

## 最终构建与检查命令

下面命令从本任务工作目录执行，项目路径当时为 `outputs/mori_robot`：

```sh
/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 \
  -m pip install --target outputs/mori_robot/scripts/vendor --no-deps manifold3d

/Applications/Blender.app/Contents/MacOS/Blender --background --factory-startup \
  --python-exit-code 1 --python outputs/mori_robot/scripts/verify_rebuild.py

/Applications/Blender.app/Contents/MacOS/Blender --background \
  outputs/mori_robot/models/MORI_assembly.blend --python-exit-code 1 \
  --python outputs/mori_robot/scripts/render.py -- --views all

/Applications/Blender.app/Contents/MacOS/Blender --background \
  outputs/mori_robot/models/MORI_assembly.blend --python-exit-code 1 \
  --python outputs/mori_robot/scripts/export.py

/Applications/Blender.app/Contents/MacOS/Blender --background \
  outputs/mori_robot/models/MORI_assembly.blend --python-exit-code 1 \
  --python outputs/mori_robot/scripts/validate.py
```

安装实际取得 Manifold **3.5.3**；项目 requirements.txt 已固定版本。`verify_rebuild.py` 在同一进程中调用两次完整建模，验证对象名称与数量一致、无关对象保留。检查完成后仅移除验证脚本自己创建的哨兵对象。

项目中的 `scripts/run_all.sh` 是同一建模/渲染/导出/检查流程的方便入口。MORI 目录与交付副本内容一致；脚本通过自身路径确定项目根，不依赖原工作目录。

## 数值与方法

- 所有部件为真实闭合网格；球体均为等比例 UV 球母体。布尔切除/并集使用 Manifold 实体内核，结果写回可编辑 Blender 网格。
- 布尔简化容差 0.001 mm，网格顶点焊接容差 0.00015 mm；打印网格和未截球面弦差另行实测。
- 实体交集体积阈值 0.001 mm³。预期接触独立列出；只对明确匹配的接触面容许 <0.02 mm 极薄数值层或 <0.5 mm³ 且深度 <0.02 mm 的圆柱网格弦差接触，未把未知交叠整批忽略。
- 最近表面距离用 BVH 求值，同时用明确的侧面/Z 分离平面证明下界；上下界吻合时才报告最小间隙。
- 头转采样 ±60° / 5°，轮转 0…360° / 10°，机身俯仰 ±15° / 1°。离散检查不能证明全部内部连续运动空间。
- STL 保存装配帧 1 的坐标与毫米数值。逐件回读三角与边，检查闭合、边关联、绕序、退化面、正体积、法向、数量和包围尺寸。自交风险检查也使用回读的实际三角形。
- 法线射线壁厚仅是筛查；球壳径向壁厚在没有截切/孔/螺柱的采样区单列。全零件最小壁厚与精确自交认证未完成。

最终结果以 validation.md / validation.json 和对应 logs 为准。中间失败几何已从交付目录移出；候选 STL 目录只保留本版实际通过导出检查的文件。
