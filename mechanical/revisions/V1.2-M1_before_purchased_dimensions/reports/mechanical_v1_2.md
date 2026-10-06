# MORI V1.2 机械交付与证据

生成日期：2026-09-22。依据用户提供的MORI_SPEC_V1_2.md和01_CODEX_MECHANICAL.md。未提供/未找到模板、REFERENCES、交接清单和种子文件；没有声称读过或合并这些缺失文件。AGENTS保留不冲突规则并更新V1.2优先级。

## 完成范围

- M1已完成：实际Blender参数化双方案、同相机前/侧/45°对比，选择B主线、初步内部包络与缺失清单。
- M2部分完成：4执行器链、独立承重轴承/短轴、CAM在头内、分运动组、相机外参、联合姿态、质量/惯量预估。最终器件孔位、真实板框和完整装拆仍BLOCKED；不能称为已适配生产结构。
- M3候选文件已生成：43件STL、平片模板、逐件预览、装配/试打说明。待打印和实机平衡验证；未进行采购、PCB放行或上电测试。

## 实际尺寸与造型

正常宽×深×高 **160.2×157.8×287.0mm**，头名义120、身160、胎95×18、腹部25mm。身体底部由声明曲面的实际局部最低点−80mm推得球心Z105mm；轮轴Z47.5mm。身体顶部Z177，头中心Z227，正常高287，均由共享参数推导。

B仅作4.5%随高度变化的肩腹修形、Y深度减1.5%；保留母球和原始基准，没有把真实硬件缩放进壳。A接近双球；B保留圆肩、略收腹。两套内部器件、相机、屏幕、轮比和渲染相机相同。容积比较见mechanical/reports/parameter_comparison.json；容积不是可装入矩形板的证明。分件、COM和内部干涉按最终B另检。

轮壳实际最小采样间隙 **4.00mm**（两轮各37姿态、10°步进，轮胎/毂/盖对实际壳网格）。腹部保留曲面，轮胎最低Z0。两轮轴线同轴。身体±15°检查仅几何意义。

130组头部联合姿态（yaw−60…60每10°，pitch−20…25每5°），包络宽深高 **160.2×157.8×287.0mm**；全姿态最高点 287.0mm。叠加身体±15°的4030组包络 **160.2×213.8×287.0mm**，最高点 287.0mm。离散采样不是连续空间、回差或变形保证。

## 原厂资料、假设和接口

- [S288原厂手册](https://www.unitree.com/download/DigitalServo/)第2页已下载并检查：20×34投影、本体轴向20、两端输出总外廓26、输出中心距端9.5、孔间距30×16、Ø1.7深度最多3的自攻孔。模型保留本体、两端输出、待定转接盘与独立双轴承；没有假定舵机轴径向承载合格。
- [SCS0009规格书](https://www.feetech.cn/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf)2020 A/0第4/6页：表格23.2、图纸23.3存在差异；模型按23.3、12.1、25.25和安装耳/20T输出预研。13.2±1g是该文件数据。购买版本、耳孔、舵盘和锁紧仍需确认。
- [CAM33700官方文档](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx)确认整板集成双麦和音频、OV3660对角68°。尺寸图片获取返回HTML挑战，未将其当成尺寸图。50×45×12为限制包络，板孔/麦克风坐标/天线/FPC和USB方向均待核。H/V57°/44°是用于遮挡测试的假设，真实内外参需标定。
- [LCD35079原厂页](https://www.waveshare.com/product/1.85inch-touch-lcd-module.htm)支持45.68有效区和55×55外廓。圆形板边、整套厚度与连接器保留假设；显示只在有效圆区，外黑面罩不是整块屏幕。完整55×55矩形加假设8mm厚度已保留为KEEP_OUT并测得与当前头壳/支架的条件冲突，见display_outline_review.json；圆形后部对象只是构造模板，不是原厂PCB边界。不能宣称整屏已装入。若完整矩形角均占用，纯球腔需要名义头径至少约132.3mm（未加公差），或把该矩形中心由Y42后移至约Y33；这两种最小改动均须重算屏面、相机与双轴，不直接冻结。先取得真实边界，若方形角确实占用，则后移整屏/面罩或有限扩大头颊，再重跑光学和运动检查。相机在有效区外的真实透光孔，使用平片。

尺寸图并不等于实物装配合格。CAM整板50×45×12 mm、电池80×65×30 mm、STM32载板70×35×12 mm、电源44×16×10 mm和扬声器外形仍是限制包络；不能把它们当成已选器件的实测尺寸。

contracts/components.json由硬件拥有，本次开工时不存在，收尾时发现V1.2-H0.1并已只读核对，未修改。机械接口仅记录原厂字段、设计限制和待确认项；旧H0.3、A4屏幕/电机数据已保存在mechanical/revisions/V1-A4_before_V1_2，不再作为当前装机真值。当前没有重复独立音频板或额外FOC占位。

完整固定/旋转对象与坐标在assembly_instances.json；相机变换在camera_kinematics.json：T_body_axle_camera=T(head_center) Rz(yaw) Rx(pitch) T(pupil) R_CV。CV光轴+Y，图像右+X，下−Z；角度需带时间，反馈/标定尚未实测。

## 质量、负载与维护

整机约 **1.06kg**，pitch活动件约 **160g**，yaw连同头部约 **200g**。pitch COM在装配坐标约 [0.1, -0.7, 234.7]mm，Ixx约 0.0003kg·m²。按当前COM的pitch采样重力矩最大约 0.006N·m；另需Iα、线缆阻力和摩擦，不能拿堵转扭矩当连续可用能力。

质量按网格体积、PLA1.24g/cm³、外壳有效98%/支架65%与独立附件假设计算；电池190g、CAM板18g等未测，至少±35%不确定度。估算表与完整惯量矩阵见mass_budget.json，不是空壳重量或实测。

电池向下取出会被轮驱挡住；最终路径为释放外壳/吊杆后+Y120mm、41姿态验证。前序需卸车轮/抽轮轴以释放下壳，完整工具和插头步骤未认证。此版维护代价明确保留，不宣称快换。IMU固定框架，主板后置，电池中部；未用“越低越好”代替平衡控制评估。

外置托架把车轮抬离地8mm，驱动必须DISARM。实际垫/身体接触和假设COM投影已检查；摩擦、线拉力、真实重心和软垫仍待实测。无运行第三支点，不证明断电自立。

## 实际运行与检查

Blender 5.2.1 LTS（9e2066aef7ef）、Python 3.13.13、Manifold3.5.3。实际命令、时间和返回码在mechanical/reports/commands.json，各脚本日志同目录。build/validate/render/export、重复生成、4030姿态包络、A/B渲染、逐件图册均实际执行。

计数：{'PASS': 23, 'FAIL': 0, 'NOT_TESTED': 11, 'BLOCKED': 4}。重复生成：PASS；最终模型/渲染/STL/输入哈希一致性：PASS。STL全部通过边关联、绕序、正体积、退化检查及Blender实际重新导入，mm单位误差<0.01。打印件不含采购硬件；生成式图片未参与交付。

| 检查 | 结果 | 范围 |
|---|---|---|
| static_rigid_solids | PASS | 装配态全部刚性实体两两体积干涉 |
| combined_yaw_pitch | PASS | Yaw/Pitch 联合采样 |
| sampled_cable_allocations | PASS | 联合姿态中的线束预留体与不同运动组实体 |
| continuous_motion_proof | NOT_TESTED | 有限采样不是连续空间数学证明；弹性、制造公差、舵机回差未建模 |
| wheel_360_clearance | PASS | 两侧轮胎、轮毂及轮盖完整转动与壳体实际间隙 |
| assembled_size | PASS | 装配真实包围尺寸 |
| declared_mothers_and_sculpted_surface | PASS | 原始母球保留；实际外壳按声明卵形公式逆变换检查 |
| ground_contacts | PASS | 腹部离地、两轮接地与其他零件不穿地 |
| body_tilt_geometry | PASS | 绕轮轴前后倾斜 ±15°，每 1° |
| mesh_topology | PASS | 实际装配网格闭合、非流形边、绕序、退化与正体积 |
| printable_connected_solids | PASS | 候选结构件连通且无未声明封闭内孔 |
| exact_self_intersection | NOT_TESTED | Manifold 接受网格不等价于独立、可靠的全部自交证明；未运行精确全三角自交算法 |
| nominal_shell_wall_samples | PASS | 未截切区域壳厚径向射线抽查 |
| wheel_pocket_service_wall_samples | PASS | 轮窝附近四处下壳工具沉孔的指定截面余厚 |
| global_minimum_wall | NOT_TESTED | 孔边、布尔窄区和所有支架的全局最小壁厚尚无可靠全覆盖算法；需切片与实体试样 |
| camera_nominal_fov | PASS | 相机独立开口、假设视场与脸框遮挡 |
| camera_fov_body_motion | PASS | 相机联合姿态视场与固定机身遮挡 |
| camera_calibration_reflections | NOT_TESTED | 真实镜头视场、透明窗折射、保护片反光和实际外参待选型与标定；无实测舵机反馈时头角为估计 |
| head_opening_exposure | NOT_TESTED | 下护罩按屏幕扫掠让位；极端俯仰开口是否可接受需查看角度渲染并做实体遮光试验，不宣称完全封闭 |
| battery_extraction | PASS | 拆除上下壳、吊杆并断开电池后沿+Y取出 |
| frame_screwdriver_path | PASS | 下壳移除后的四处框架螺丝刀杆路径 |
| all_fasteners_assembly | NOT_TESTED | 其余紧固件长度、嵌件热压头、工具手柄与完整逐件装配路径尚待阶段 B；当前候选孔仅供试打 |
| real_hardware_fit | BLOCKED | 只验证阶段 A 包络；保留共享契约中硬件候选的适配失败。最新型号与包络见 contracts/mechanical_interfaces.json；真实轮驱、屏幕、相机、舵机和完整连接器仍需阶段 B 回写，不能靠外观调整宣称已适配 |
| cable_service_loops | NOT_TESTED | 已建服务环、线束路径和约束点；实际柔性扫掠与连接器受力未验证 |
| hard_stop_contact_angles | NOT_TESTED | 有限角度限位件已布置；准确触点角度、强度与舵机失控冲击需专门验证，不能用软件限角代替 |
| power_interface_operations | NOT_TESTED | 已布置 USB-C、按钮、电源开关与插头/手指包络；实物插拔、开关急停可达性、线缆拉力待阶段 B |
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
| display_full_vendor_outline | BLOCKED | 完整55x55矩形限制包络与当前曲面/框架存在冲突；真实非矩形边界/厚度未给，圆形构造模板不能当作已适配PCB |
| actual_board_antennas_microphones | BLOCKED | CAM板框、实际USB/麦克风/天线位置和FPC长度尚未取得可用原厂图；整板50x45x12仅是安装限制包络，不能据此采购冻结或打印最终支架 |

AABB只用于初筛，刚性/联合干涉采用闭合三角网格实体交集，轮壳采用实体最小距离；有意接触不能豁免体积穿透。线束只是保守管状/环状预留，未模拟柔性、疲劳及拉力。壁厚为指定面成对射线抽查，不等同全局最小壁厚；精确全自交算法未执行。

## 交接与停止边界

1. 硬件任务继续补全components.json：真实CAM尺寸/高度/孔/声口/FPC、LCD完整外廓与厚度、SCS版本/附件、S288输出连接/径向允许值、3S电池与全部电源模块、扬声器和接插件。
2. 当前STM32后架只能容纳70×35，不能默认70×50矩形板一定装入；电源架44×16×10。选型超过限制需调整机械布局，并重跑检查，禁止缩放真实板。
3. 软件无需本次更改角度范围；接收相机外参与质量预算后再更新仿真，不把默认角度当实测反馈。电气/软件契约未擅改。
4. 预算≤1000元和60分钟混合工况续航均未验证。预算缺价/超支暂停采购批准与PCB冻结；继续结构预研。
5. 下一阶段：实物尺寸回写、打印接口小样、逐个紧固件/插头装拆、热/结构/音频/射频验证，再在可靠保护条件下进行台架和实机平衡。
