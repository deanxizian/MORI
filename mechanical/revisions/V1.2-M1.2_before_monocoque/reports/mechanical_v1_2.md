# MORI V1.2 机械交付与证据

生成日期：2026-09-22。依据用户提供的MORI_SPEC_V1_2.md和01_CODEX_MECHANICAL.md。未提供/未找到模板、REFERENCES、交接清单和种子文件；没有声称读过或合并这些缺失文件。AGENTS保留不冲突规则并更新V1.2优先级。

## 完成范围

- M1已完成：实际Blender参数化双方案、同相机前/侧/45°对比，选择B主线、初步内部包络与缺失清单。
- M2部分完成：4执行器链、独立承重轴承/短轴、CAM在头内、分运动组、相机外参、联合姿态、质量/惯量预估。LCD原厂CAD和CAM板框已回写，剩余器件/高度/线缆/最终孔位与完整装拆仍BLOCKED；不能称为已适配生产结构。
- M3候选文件已生成：40件STL、平片模板、逐件预览、装配/试打说明。待打印和实机平衡验证；未进行采购、PCB放行或上电测试。

## 实际尺寸与造型

正常宽×深×高 **160.2×157.8×287.0mm**，头名义120、身160、胎95×18、腹部25mm。身体底部由声明曲面的实际局部最低点−80mm推得球心Z105mm；轮轴Z47.5mm。身体顶部Z177，头中心Z227，正常高287，均由共享参数推导。

B仅作4.5%随高度变化的肩腹修形、Y深度减1.5%；保留母球和原始基准，没有把真实硬件缩放进壳。A接近双球；B保留圆肩、略收腹。两套内部器件、相机、屏幕、轮比和渲染相机相同。容积比较见mechanical/reports/parameter_comparison.json；容积不是可装入矩形板的证明。分件、COM和内部干涉按最终B另检。

轮壳实际最小采样间隙 **4.00mm**（两轮各37姿态、10°步进，轮胎/毂/盖对实际壳网格）。腹部保留曲面，轮胎最低Z0。两轮轴线同轴。身体±15°检查仅几何意义。

130组头部联合姿态（yaw−60…60每10°，pitch−20…25每5°），包络宽深高 **160.2×157.8×287.0mm**；全姿态最高点 287.0mm。叠加身体±15°的4030组包络 **160.2×213.8×287.0mm**，最高点 287.0mm。离散采样不是连续空间、回差或变形保证。

## 原厂资料、假设和接口

- [S288原厂手册](https://www.unitree.com/download/DigitalServo/)第2页已下载并检查：20×34投影、本体轴向20、两端输出总外廓26、输出中心距端9.5、孔间距30×16、Ø1.7深度最多3的自攻孔。模型保留本体、两端输出、待定转接盘与独立双轴承；没有假定舵机轴径向承载合格。
- [SCS0009规格书](https://www.feetech.cn/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf)2020 A/0第4/6页：表格23.2、图纸23.3存在差异；模型按23.3、12.1、25.25和安装耳/20T输出预研。13.2±1g是该文件数据。购买版本、耳孔、舵盘和锁紧仍需确认。
- [CAM33700原厂产品与尺寸图](https://www.waveshare.com/esp32-s3-cam-ov5640.htm?sku=33700)：板框37×37mm、孔中心距32.6×32.6mm、边距2.2mm、外角R2.25。R2.25不是孔半径；孔径、PCB厚度与含元件总高未标。当前37×12×37mm中的12仅为橙色预留厚度。照片确认USB在板底边，已移除旧版假定的后向实体插头；精确插口坐标、麦克风、天线和原装FPC仍缺尺寸。H/V57°/44°仅用于光学预研，真实镜头待标定。
- [LCD35079原厂CAD与图纸](https://github.com/waveshareteam/1.85inch-Touch-LCD-Module/tree/main/dimensions)：113实体STEP REV1、2026-07-02、毫米、刚性1:1转换，包含圆形玻璃、背板、已装连接器和三根固定柱。玻璃外径55、有效区45.68、视窗46.08、玻璃厚0.7、PCB厚1.6mm。STEP整套深度9.35mm，PDF标9.1参考值；固定柱坐标也有约0.06mm差异，保留两份证据而不擅自统一。M2最终孔/螺钉待购买版本确认。完整原厂轮廓替代旧55×55假设矩形，因此旧版“必须增大头径才能装入”条件推论已撤销。
- 屏幕整件上移0.8mm，相机及独立透光孔上移3mm，按三柱位置重做打印后支架；未缩放采购件。黑面罩直径68mm不等于屏幕有效区，双眼只在45.68mm有效圆内。
- STEP的113实体在源CAD中均通过BRep检查；其中两个连接器子实体转三角网格后仍非流形。渲染保留所有原厂三角面，碰撞检查对这两件采用源CAD保守外接框，其他111件采用实体网格。即使零碰撞，完整精确装配检查也为BLOCKED；未以替代框伪造全实体PASS。详见vendor_lcd_import.json、mesh_topology.json。原始STEP、DXF、PDF、尺寸图与哈希保存在mechanical/sources/v1_2_verified_dimensions/。

本次M1.2简化承重支架。硬件P1的80×45电源板和完整装件尚未布局，旧44×16×10预留不代表P1实板，电源/主控安装面仍待重排。LCD35079已按原厂113实体STEP以1:1导入；CAM33700板框已改为原厂37×37mm，12mm厚度仍仅为预留。电池80×65×30mm、STM32载板70×35×12mm、电源44×16×10mm及其他未选型件均为占位。橙色代表缺尺寸或待选型；原厂资料核对不等于已拿到实物测量。

contracts/components.json由硬件拥有，V1.2-H0.2-P1已只读核对，机械任务未修改该文件。P1的80×45电源板、WeAct模块及外部稳压器还没有全部整合进本次Blender布局；这项独立阻塞在validation中单列。新尺寸事实和待回写字段在ADR-MECH-013-purchased-dimensions.md交接，未擅改硬件契约。机械接口仅记录原厂字段、设计限制和待确认项；旧H0.3、A4屏幕/电机数据已保存在mechanical/revisions/V1-A4_before_V1_2，不再作为当前装机真值。当前没有重复独立音频板或额外FOC占位。

完整固定/旋转对象与坐标在assembly_instances.json；相机变换在camera_kinematics.json：T_body_axle_camera=T(head_center) Rz(yaw) Rx(pitch) T(pupil) R_CV。CV光轴+Y，图像右+X，下−Z；角度需带时间，反馈/标定尚未实测。

## M1.2 支架简化

本次涉及的打印支撑件11→8。头部拱形骨架合并CAM与相机座，Pitch叉架合并舵机安装托；Yaw四柱改为双侧板壁，轮轴承经宽板连接到底盘。电机座保留可拆短法兰，电池四长吊杆改为两侧滑轨承托和两枚短限位螺钉。完整说明见mechanical/reports/结构简化说明.md；对比图只展示本次结构，未把隐藏的器件删掉。结构变化不等于刚度、疲劳、层间强度或跌落可靠性已提高，相关测试仍NOT_TESTED。

## 质量、负载与维护

整机约 **1.07kg**，pitch活动件约 **160g**，yaw连同头部约 **200g**。pitch COM在装配坐标约 [0.1, 0.2, 235.4]mm，Ixx约 0.0003kg·m²。按当前COM的pitch采样重力矩最大约 0.005N·m；另需Iα、线缆阻力和摩擦，不能拿堵转扭矩当连续可用能力。

质量按网格体积、PLA1.24g/cm³、外壳有效98%/支架65%与独立附件假设计算；电池190g、CAM板18g等未测，至少±35%不确定度。估算表与完整惯量矩阵见mass_budget.json，不是空壳重量或实测。

电池向下取出会被轮驱挡住；当前路径为释放外壳及两侧短限位螺钉后+Y120mm、41姿态验证；托盘嵌件随托盘移动。前序需卸车轮/抽轮轴以释放下壳，完整工具和插头步骤未认证。此版维护代价明确保留，不宣称快换。IMU固定框架，主板后置，电池中部；未用“越低越好”代替平衡控制评估。

外置托架把车轮抬离地8mm，驱动必须DISARM。实际垫/身体接触和假设COM投影已检查；摩擦、线拉力、真实重心和软垫仍待实测。无运行第三支点，不证明断电自立。

## 实际运行与检查

Blender 5.2.1 LTS（9e2066aef7ef）、Python 3.13.13、Manifold3.5.3。实际命令、时间和返回码在mechanical/reports/commands.json，各脚本日志同目录。build/validate/render/export、重复生成、4030姿态包络、A/B渲染、逐件图册均实际执行。

计数：{'PASS': 21, 'FAIL': 0, 'NOT_TESTED': 12, 'BLOCKED': 9}。重复生成：PASS；最终模型/渲染/STL/输入哈希一致性：PASS。STL全部通过边关联、绕序、正体积、退化检查及Blender实际重新导入，mm单位误差<0.01。打印件不含采购硬件；生成式图片未参与交付。

| 检查 | 结果 | 范围 |
|---|---|---|
| static_rigid_solids | BLOCKED | 刚性实体采样 / 原厂两接插件仅完成保守代理检查 |
| combined_yaw_pitch | BLOCKED | Yaw/Pitch 联合采样 / 两接插件精确网格待核 |
| sampled_cable_allocations | PASS | 联合姿态中的线束预留体与不同运动组实体 |
| continuous_motion_proof | NOT_TESTED | 有限采样不是连续空间数学证明；弹性、制造公差、舵机回差未建模 |
| wheel_360_clearance | PASS | 两侧轮胎、轮毂及轮盖完整转动与壳体实际间隙 |
| assembled_size | PASS | 装配真实包围尺寸 |
| declared_mothers_and_sculpted_surface | PASS | 原始母球保留；实际外壳按声明卵形公式逆变换检查 |
| ground_contacts | PASS | 腹部离地、两轮接地与其他零件不穿地 |
| body_tilt_geometry | PASS | 绕轮轴前后倾斜 ±15°，每 1° |
| mesh_topology | BLOCKED | 实际网格拓扑 / 两原厂接插件转换网格问题保留 |
| printable_connected_solids | PASS | 候选结构件连通且无未声明封闭内孔 |
| exact_self_intersection | NOT_TESTED | Manifold 接受网格不等价于独立、可靠的全部自交证明；未运行精确全三角自交算法 |
| nominal_shell_wall_samples | PASS | 未截切区域壳厚径向射线抽查 |
| wheel_pocket_service_wall_samples | PASS | 轮窝附近四处下壳工具沉孔的指定截面余厚 |
| global_minimum_wall | NOT_TESTED | 孔边、布尔窄区和所有支架的全局最小壁厚尚无可靠全覆盖算法；需切片与实体试样 |
| camera_nominal_fov | PASS | 相机独立开口、假设视场与脸框遮挡 |
| camera_fov_body_motion | PASS | 相机联合姿态视场与固定机身遮挡 |
| camera_calibration_reflections | NOT_TESTED | 真实镜头视场、透明窗折射、保护片反光和实际外参待选型与标定；无实测舵机反馈时头角为估计 |
| head_opening_exposure | NOT_TESTED | 下护罩按屏幕扫掠让位；极端俯仰开口是否可接受需查看角度渲染并做实体遮光试验，不宣称完全封闭 |
| battery_extraction | PASS | 拆除上下壳、两侧短限位螺钉并断开电池后沿+Y取出 |
| frame_screwdriver_path | PASS | 下壳移除后的四处框架螺丝刀杆路径 |
| all_fasteners_assembly | NOT_TESTED | 其余紧固件长度、嵌件热压头、工具手柄与完整逐件装配路径尚待阶段 B；当前候选孔仅供试打 |
| real_hardware_fit | BLOCKED | 只验证阶段 A 包络；保留共享契约中硬件候选的适配失败。最新型号与包络见 contracts/mechanical_interfaces.json；真实轮驱、屏幕、相机、舵机和完整连接器仍需阶段 B 回写，不能靠外观调整宣称已适配 |
| cable_service_loops | NOT_TESTED | 已建服务环、线束路径和约束点；实际柔性扫掠与连接器受力未验证 |
| hard_stop_contact_angles | NOT_TESTED | 有限角度限位件已布置；准确触点角度、强度与舵机失控冲击需专门验证，不能用软件限角代替 |
| power_interface_operations | NOT_TESTED | 已布置 USB-C、按钮、电源开关与插头/手指包络；实物插拔、开关急停可达性、线缆拉力待阶段 B |
| simplified_structure_strength | NOT_TESTED | 整体板肋替代细杆仅为结构设计改动；FDM层间强度、蠕变、冲击、疲劳及紧固预紧未进行仿真或实测 |
| hardware_P1_populated_layout | BLOCKED | 已读取V1.2-H0.2-P1：80×45电源板及完整装件/稳压模块尚未装入；旧44×16×10预留不能代表P1实板，本次支架简化不冻结电源/主控安装面 |
| mass_inertia_estimates | PASS | 已输出有假设的质量与惯量估算（不是载荷验收） |
| head_torque_and_balance | NOT_TESTED | 舵机扭矩、头部加速载荷、支架强度、轴承寿命与实机自平衡尚未验证 |
| dock_nominal_COM_projection | PASS | 托架四点名义支撑多边形内的重心投影 |
| dock_mesh_contacts | PASS | 实际托架网格接触、轮胎离地与实体干涉 |
| dock_physical_stability | NOT_TESTED | 软垫变形、地面摩擦、插线拉力及真实重心必须实测；托架稳定不代表机器人断电可自立 |
| budget_and_runtime | BLOCKED | 1000 元总预算和 60 分钟混合工况续航未验证；未提供完整报价与实测平均功耗 |
| display_active_aperture | PASS | 真实45.68mm发光区到观察侧的遮挡检查 |
| head_allocations_inside_outer_envelope | PASS | 头内主板/屏板/相机/舵机位于声明头外形内 |
| wheel_coaxial_geometry | PASS | 双轮同轴且轮轴高度等于实际轮胎半径 |
| usb_plug_approach_allocation | PASS | USB插头外壳与前端插拔预留 |
| display_full_vendor_outline | BLOCKED | 原厂LCD外形已回写 / 两接插件精确实体待核 |
| actual_board_antennas_microphones | BLOCKED | CAM37×37板框、32.6孔中心距已核；实际装件厚度、孔径、USB/麦克风/天线坐标与FPC仍缺尺寸 |
| purchased_dimension_provenance | PASS | 采购件尺寸来源、原厂CAD比例与未知项标签 |
| all_purchased_parts_dimensioned | BLOCKED | 尚未选定/缺少完整尺寸的采购件保持橙色占位，不能宣称全部按实物建模 |

AABB用于初筛；刚性/联合干涉主要采用闭合三角网格实体交集，但LCD的两个接插件明确采用保守AABB实体代理，完整精确CAD检查仍BLOCKED。轮壳采用实体最小距离；有意接触不能豁免体积穿透。线束只是保守管状/环状预留，未模拟柔性、疲劳及拉力。壁厚为指定面成对射线抽查，不等同全局最小壁厚；精确全自交算法未执行。

## 交接与停止边界

1. 硬件任务继续补全components.json：CAM装件高度/孔径/声口/FPC、LCD购买版本/图纸差异/对插线束、SCS版本/附件、S288输出连接/径向允许值、3S电池与全部电源模块、扬声器和接插件。
2. 当前STM32后架只能容纳70×35，不能默认70×50矩形板一定装入；旧电源架44×16×10与硬件P1的80×45实板设计冲突，必须调整布局；P1装件高度、稳压板、线束和新板架需独立重跑检查。禁止缩放真实板。
3. 软件无需本次更改角度范围；接收相机外参与质量预算后再更新仿真，不把默认角度当实测反馈。电气/软件契约未擅改。
4. 预算≤1000元和60分钟混合工况续航均未验证。预算缺价/超支暂停采购批准与PCB冻结；继续结构预研。
5. 下一阶段：实物尺寸回写、打印接口小样、逐个紧固件/插头装拆、热/结构/音频/射频验证，再在可靠保护条件下进行台架和实机平衡。
