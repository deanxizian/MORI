# MORI V1.2-M1.18 · Blender装配预研

M1.18：电池托盘加宽90→94.2mm，配合统一3.6mm平侧板，删除向内伸出的局部固定座。现有底部台阶接到托盘底面；每侧0.3mm为试配间隙，左右M2×6数量不变。电池位置/81mm内通道/软垫保留。见[托盘检查](reports/battery_tray_fit.json)和[安装结构说明](reports/安装结构巡检与修改.md)。

M1.17删除两条长电源托边，改为四个一体矮座和两个对角锁紧点。没有新增打印件，补两枚M2×6与两枚试配嵌件；安装孔取P4设计，P5装件仍待复核。见[电源安装要求](POWER_BOARD_MOUNT_REQUIREMENTS.md)。

M1.16修复电池托盘固定沉孔切穿侧板边缘的问题：左右孔、螺钉和嵌件同步向内移20mm，侧板保持直边，不新增打印件或紧固件。新增完整孔边、螺钉头支承面、装入与工具检查；见[固定孔检查](reports/battery_retention_validation.json)与[安装结构说明](reports/安装结构巡检与修改.md)。

模型：`mori_v1_2.blend`。打开`index.html`查看实际渲染、全部零件和原始检查报告。保存时头壳保持水平零位；仅圆屏/相机的固定安装角为+10°，由`layout_cleanup`参数控制。`MORI_V1__CTRL_Pitch`的X角度用于真实头部俯仰。控制范围仍为绝对pitch−20°～25°、yaw±60°。

装配动画另存为 [mori_assembly_animation.blend](mori_assembly_animation.blend)：54秒、24fps、18个中文步骤标记，每个零件保留独立关键帧。打开后在 `MORI_Assembly_Animation` 场景按空格播放；原总装场景也保留。视频与按步骤跳转见 [动画预览](animation/index.html)，重新生成见 [动画说明](animation/README.md)。动画位移和台面预装是讲解用途，未验证全程工艺路径；不改变尺寸源或候选STL。

本轮逐件检查18个本体打印件，取消承重桥、扬声器后盖、轮驱底盖、反力轴夹口的外伸螺丝耳和外侧长工具槽；固定件收进主体轮廓。没有新增打印件，承重桥两枚螺母改为嵌件，M1.15时五金总数94件，M1.17补齐电源板固定后为98件。见[安装结构巡检与修改](reports/安装结构巡检与修改.md)。

保留的轮驱接口：S288六孔自攻螺钉 → 整体金属法兰轴 → 两只686ZZ独立轴承 → 双扁位轮毂 → M3端部保持。共用底盖同时封住两台电机与四个轴承座，四枚M3固定。M1.14将本体硬质打印件从20件减为18件，M1.17保持18件，另有托架1件和试样4件。当前全机五金98件，含2枚垫圈；传动连接所需紧固件沿用M1.14数量。两根金属轴和四个定长隔套需要按图加工，不能打印或当作已选通用现货。

详细连接、尺寸、轴向剖视及装配顺序见[轮驱设计页](studies/s288_interface_review/index.html)和[设计要求](reports/S288轮驱连接与加工要求.md)。下壳在轮窝中有向壳缝开放的轴槽，拆轮毂和外隔套后可直接向下取壳；无需先抽一体轴。壳缝螺钉Y±54，避开托盘与框架工具路径。之前轮盖、相机遮光座、Yaw转台/U托/线导和固定遮缝环的合并继续保留。

沿用M1.13位于轴承上方的Yaw限位以便拆装；拆下pitch头、Yaw舵机及反力轴横向保持后，一体Yaw/U托连同反力轴一起取出。详见reports/组装与打印.md。沿用M1.12圆脸接齐球面、104mm完整直边Load_Frame和后接口板的一体壳耳。光学倾角、外壳、采购件尺寸与运动轴保持既有方案。

IMU仍置于刚性主托板底面，主托板与两侧短板合并；对称连续轮廓保留明确的声腔和接口让位。删除独立功能按钮。后接口小板24×14×1.6，两面分别布置后向开关与USB-C，外壳安装座已生成；电路和真实连接器由另一任务完成，要求见`INTERFACE_PCB_REQUIREMENTS.md`。WeAct和LCD使用原厂完整CAD；电池Tenergy31013与喇叭CMS-4017-34SP按原厂名义尺寸建模。型号/几何精度/采购阻塞分开列于`reports/采购件选型.md`。

CAM装件坐标/厚度、相机FPC、电池温度检测/均衡、USB-C充电以及实际载板堆叠仍未核全。电源板已在studies/power_P3_detail生成85个库器件加PCB的独立详细参考，14个器件缺CAD；该参考未替换总装容量包络，完整装件及对插适配尚未完成。当前模型采用原生P2基板/IMU参考和80×55电源容量。不是生产或采购放行。未采购、未测量、未打印、未实机平衡。

## 重复运行

使用Blender5.2.1 LTS，脚本自带对应Python3.13/macOS的Manifold3.5.3库。其他平台需安装对应平台的manifold3d和numpy。单位mm，Blender单位比例0.001。

```sh
python3 mechanical/scripts/run_all.py
```

完整流程需要普通Python环境带Pillow（比较拼图），并用独立OCP环境导出金属设计STEP。设置`MORI_CAD_PYTHON`可指定带cadquery-ocp的Python，默认本机`/Users/dean/.cache/codex-runtimes/mori-cad/bin/python`。核心不需要Pillow：

```sh
python3 mechanical/scripts/run_all.py --core
```

分步执行：

```sh
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 --python mechanical/scripts/build.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/validate.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/render.py
/Applications/Blender.app/Contents/MacOS/Blender --background --python-exit-code 1 mechanical/mori_v1_2.blend --python mechanical/scripts/export.py
```

每次脚本只清理自己的MORI命名空间。`check_rebuild.py`实际重建两次并验证外部对象保留；`delivery_check.py`核对几何/变换、渲染、STL、来源哈希和装配螺钉坐标。完整检查含130头部姿态、轮壳每10°及整套轮驱每5°旋转、身体±15°、工具杆、六孔螺钉装入以及四条每1mm拆装路径。局部壁厚使用双精度实体射线并与独立三角面计算核对，避免BVH相邻面重复命中的假薄壁。有限采样不是连续空间证明。

原厂STEP及原生P2板转换缓存保存在sources/和studies/pcb_P2_fit/，Blender运行不需要OpenCascade。重转STEP需独立Python安装cadquery-ocp7.8.1.1.post1，分别执行`convert_vendor_step.py`和`convert_weact_step.py`。保守碰撞代理及其原因见vendor_lcd_import.json和vendor_weact_import.json。

STL仅打印候选和试样，单位mm；不含采购件或轮胎，按零位装配坐标导出、无爆炸偏移。平片、软轮胎、紧固件另行制造/采购。保留M1.12和M1.13只读基线，历史方案不是当前真值。

动画可通过 `mechanical/scripts/run_animation.py` 一次重新生成原生文件、18张步骤图、MP4、读回检查与预览页；使用带 Pillow 的项目 Python 运行。命令和退出码写入 `animation/commands.json`。

M1.17：两条52mm电源托边替换为四个Ø5.6×4.5mm一体矮座。保留PCB底面Z119.5及3mm底面装件容量；两个对角M2×6配两枚试配嵌件固定，没有新增打印件。孔位来自P4原生交接，P5改版与完整装件仍待核。板卡先装，固定Yaw桥后装；详见reports/power_board_mount_validation.json。
