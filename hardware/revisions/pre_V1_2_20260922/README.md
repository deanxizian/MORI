> **V1 更新（2026-09-21）**：主规格见 `MORI_SPEC_V1.md`；四执行器、双轴头部与摄像头模型见 `mechanical/README.md`。V1 尺寸唯一来源 `config/geometry.json`，接口 `contracts/mechanical_interfaces.json`。以下原项目说明与 root `params.json/scripts/models/reports` 属于保留的 A0 历史。

# MORI 可编辑 Blender 项目

这是面向后续硬件与实物制作的第一阶段结构预研。所有图片由真实 `.blend` 网格渲染；没有参考图片，因此本轮未做图片对照。硬件包络未选型，23 个 STL 是候选试打件，不能当作加工放行文件。

打开 `models/MORI_assembly.blend`，选择场景 `MORI_Assembly`。

- **帧 1：装配；帧 80：爆炸。** 时间轴有标记，切换不复制几何。
- `MORI__CONTROLS / MORI__Head_Pivot` 的自定义属性 `yaw_deg` 控制头部绕 Z 转动，初始 ±60°。
- `MORI__Wheel_L_Pivot`、`MORI__Wheel_R_Pivot` 的 `spin_deg` 控制轮组绕 X 转动。
- `MORI__DATUMS` 保存原始正球母体，默认隐藏；`ANNOTATIONS` 为尺寸标注；`COUPONS` 为小样，不属于整机。
- `PRINTABLE`、`PURCHASED_REFERENCE`、`PLACEHOLDER` 分开管理。每件都有中文名称、材料建议、接口确认状态和是否导出的属性。
- 可直接编辑网格；修改参数并重建时，仅本项目带所有权标记的对象会被替换。重要手工修改请另存版本或复制为不带 `mori_owner` 的自有对象。

## 单位与参数

所有设计尺寸和次级结构尺寸在 `params.json`。参数及网格坐标均用毫米；Blender 的 `scale_length=0.001` 负责显示换算。因此坐标 `100` 对应 100 mm，STL 直接写入 `100`，不会再乘或除 1000。

固定基准：头 Ø100、身 Ø140、轮 Ø95×18；身体球心高 90；轮轴高 47.5；腹部离地 20；轮胎到外壳 4；侧截后身体宽 112；轮距 138。当前整机最大宽约 158.8、高 236 mm；精确模型测量值见 `reports/validation.json`。

`params.json` 的主要尺寸控制派生定位。硬件型号改变后，也要调整对应包络、接口和 details_mm，重新运行验证；本项目不会自动把不可能的参数组合修成“看起来合理”。

## 重新生成

本机实际测试：Blender 5.2.1 LTS、内置 Python 3.13、Manifold 3.5.3。`scripts/vendor` 已带本机 macOS arm64 / CPython 3.13 的依赖及许可证。其他平台使用该平台 Blender 的 Python 安装 `requirements.txt`；bpy、numpy 等由 Blender 提供。

```sh
cd /Users/dean/Documents/MORI
sh scripts/run_all.sh
```

脚本路径均相对项目目录解析，交付包解压到其他目录也可执行。非默认 Blender 路径：

```sh
BLENDER_BIN="/path/to/blender" sh scripts/run_all.sh
```

需要重新安装布尔依赖时，在 macOS 本机执行：

```sh
/Applications/Blender.app/Contents/Resources/5.2/python/bin/python3.13 \
  -m pip install --target scripts/vendor --no-deps -r requirements.txt
```

实际流水线顺序是建模 → 渲染 → 候选 STL 导出/回读 → 检查。渲染、导出和检查都会复位到装配帧与零转角。`reports/logs` 保存最后执行日志；`reports/execution.md` 记录本轮命令。

```sh
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender
"$BLENDER" --background --factory-startup --python-exit-code 1 --python scripts/build.py
"$BLENDER" --background models/MORI_assembly.blend --python-exit-code 1 --python scripts/render.py -- --views all
"$BLENDER" --background models/MORI_assembly.blend --python-exit-code 1 --python scripts/export.py
"$BLENDER" --background models/MORI_assembly.blend --python-exit-code 1 --python scripts/validate.py
```

## 文件导航

| 文件 | 内容 |
|---|---|
| `models/MORI_assembly.blend` | 可编辑独立部件、转轴、两种姿态、真实相机与灯光 |
| `params.json` / `spec.md` | 毫米尺寸、器件包络、基准关系、设计决策与修改原因 |
| `scripts/` | 建模、渲染、检查、导出、姿态与重复生成检查脚本 |
| `renders/` | 正/侧/后/俯/仰正交、45°、爆炸、内部布局、尺寸检查及轮壳局部放大 |
| `reports/bom.csv` / `bom.json` | 逐件名称、数量、材料建议、类别、确认状态和候选导出状态 |
| `reports/validation.md` / `.json` | 实际 PASS / FAIL / NOT_CHECKED、数值、方法、步长与范围 |
| `reports/interference_pairs.json` / `expected_contacts.json` | 实体交集与明确列出的预期接触 |
| `reports/export_manifest.json` | 实际导出件数量、毫米尺寸、拓扑及回读误差 |
| `reports/assembly_and_printing.md` | 拆装前提、打印方向、配合小样和未解决连接 |
| `exports/stl/` | 通过本轮拓扑/回读检查的候选打印件；不含电机、屏幕、电池、PCB 或轴承 |
| `ROADMAP.md` | 后续硬件、试打、电气及实物主动自平衡推进步骤 |

## 如何理解“通过”

外部间隙用三角表面最近点与分离平面下界相互核对；碰撞检查使用闭合三角实体求交体积及 BVH；完整轮转每 10°，头转每 5°，机身俯仰每 1°。电池拆出每 3 mm 检查，框架螺钉检查了工具包络。预期轴承/安装座接触单独列出。

球壳径向壁厚检查仅覆盖保留球面的采样区域。全部件的最薄壁、稳健自交认证、所有工具和真实线缆路径仍有未验证项。STL 闭合与尺寸正确不等于切片、材料、强度、压配和装配已通过。

本轮没有质量/重心、执行器能力和闭环控制实测，**不承诺断电自立、稳定行驶或摔倒自起**。两台轮电机将承担后续主动自平衡；当前只是为此预留了刚性 IMU 位置、主控、驱动及电源空间。
