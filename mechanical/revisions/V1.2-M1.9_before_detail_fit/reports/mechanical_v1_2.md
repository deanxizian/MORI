# MORI V1.2-M1.9 — 参数化装配预研报告

本次完成横躺轮驱与头内倒装Yaw的联合调整，目标是给电池、电源板、运动/驱动接口板留连续空间。结果为可编辑Blender、脚本、候选STL及同几何实际渲染；不是实物装配或生产发布。

电池80×65×30、运动载板70×35×12、电源板80×40×18均是空间预留。S3电源PCB尚无完整外形、装件高度、孔位和插头CAD；新托板只固定到机械框架，PCB专用夹片仍待设计。LCD按原厂CAD1:1导入，但两连接器使用保守检查代理。橙色表示资料未全；未采购、未实物测量、未打印或实机平衡。

## 结果与空间

| 项目 | M1.8 | M1.9 |
|---|---:|---:|
| 轮驱机身最高点 | 77mm | 62.5mm |
| 电池中心Z | 103mm | 91mm |
| 主安装板上表面Z | 127mm | 115mm |
| 电源板空间预留 | 44×16×10mm | 80×40×18mm |
| 主体支撑打印组件 | 11 | 13 |

电池到板底名义间隙5.0mm；电源预留底面落在独立托板上，与Yaw承重桥最小网格距离2.0mm。连接器、实际散热面、手指和容差需另留，不能把全部包络体积视为可装任意PCB。

外观尺寸、轮地关系和屏幕保持：装配宽×深×高158.5×157.8×282.0mm；名义头120、身体160、轮胎105×18mm；球腹离地20mm、轮轴52.5mm、身体中心100mm、头中心222mm。轮壳计算最小间隙4.00mm。282mm低于原285～295mm偏好，但满足300mm产品上限，这是已记录的用户低身位调整。母球保留；身体B采用声明的轻微卵形公式，未称其修形面为严格正球。

全头动作包围尺寸[158.5, 157.8, 282.0]mm；130组离散姿态，yaw−60～60°步长10°、pitch−20～25°步长5°。身体±15°几何检查与4030组身体/头组合包络见body_head_envelope.json，不代表安全控制范围。

## 机构、维护与走线

Yaw舵机机壳固定在头内yaw框架，输出/舵盘经可拆D形反力轴固定到身体。机壳转动驱动头左右转；关系为head_yaw=−shaft_relative_angle，真实舵机零位、角反馈方向和限位须台架标定。Pitch仍独立双侧支撑，不增加机械roll。负载经转台/独立承重轴承/宽侧板桥传给框架，不经过细舵机轴悬臂。

反力轴的D形槽、横向防退和舵盘夹口均为明确候选几何。舵盘实际型号、夹紧预载、扭矩、打印层强度、轴承保持尚未验证。没有把圆滑的占位连接当成已经可承载的真实花键。电源平托板有4枚试配短螺钉；最终PCB孔位和固定夹片未编造。

IMU在刚性平板局部座上绕Z90°放置，其坐标与轴标记已更新；不能安装在维修盖上。运动载板后置，CAM随pitch头运动。Yaw服务环、下段至头部引线、pitch环和线端只是保守空间，静态路由冲突、跨运动组碰撞分别报告；柔性、连接器拔插和线疲劳尚未实测。

完整拆装和打印建议见mechanical/reports/组装与打印.md。电池仍须禁驱、托架支撑、拆轮/抽轴并解除壳体后取出，不宣称快换。头内Yaw维修先取pitch头，再取Yaw舵机、U托、反力轴；有限抽出轨迹和工具杆空间实际检查，不以爆炸图代替。

## 质量、惯量和控制交接

整机估重约1.31kg；pitch运动件约180g，含完整头的yaw运动组约270g。pitch质心[0.1, 0.2, 229.3]mm，绕俯仰轴Ixx约0.00032kg·m²。采样重力矩峰值约0.005N·m，未计真实加速度、摩擦和线力。

统一假设下COM离地约118.7→115.6mm，相对轮轴66.2→63.1mm。变化3.1mm。为避免将预留空盒当实心材料，未知电源板在两版比较均统一假设30g；旧版存档原估算因此与这里的标准化比较不同。其它密度/有效填充保持一致；新增结构按真实网格计重。

PLA1.24g/cm³、外壳98%/当前支撑95%/其它65%有效实体量，电池190g、CAM18g等是假设。至少±35%不确定。低重心不是控制验收，必须按新COM、惯量、Yaw方向和IMU安装姿态复核控制模型。相机外参仍按T_body_axle_camera=T(head) Rz(yaw) Rx(pitch) T(pupil) R_CV导出，CV光轴+Y。相机内外参、零位和时序需实机标定。交接见ADR-MECH-021。

外置无源维护托架将车轮抬高8mm，要求DISARM/DOCKED_MAINTENANCE。假设COM投影和网格接触已检查；软垫、摩擦、插线拉力和实物防倾覆未测，不代表机器人断电可站立。

## 已执行验证

Blender 5.2.1 LTS（9e2066aef7ef），Python 3.13.13，Manifold 3.5.3。实际命令、返回码、日志在mechanical/reports/commands.json。重复执行build两次：PASS；输入/模型/渲染/STL一致性：PASS。导出34件候选STL并实际重新导入检查毫米尺寸；不含采购件、轮胎和爆炸位移。

检查计数：{'PASS': 32, 'FAIL': 0, 'NOT_TESTED': 12, 'BLOCKED': 10}。AABB只作初筛，干涉用三角网格体积交集；有意接触不豁免穿透。LCD两个连接器使用披露的保守代理，完整精确适配仍BLOCKED。全自交、全局最小壁厚、真实线束柔性、紧固扭矩和动态平衡未通过验证。有限采样不构成连续空间证明。

| 检查 | 结果 | 范围 |
|---|---|---|
| static_rigid_solids | BLOCKED | 刚性实体采样 / 原厂两接插件仅完成保守代理检查 |
| combined_yaw_pitch | BLOCKED | Yaw/Pitch 联合采样 / 两接插件精确网格待核 |
| face_mask_body_clearance | PASS | 圆屏外面罩与身体在联合姿态中的实际间隙 |
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
| separate_forehead_camera | PASS | 相机窗口与圆屏黑面罩分离，中间保留真实白色球壳 |
| battery_extraction | PASS | 拆除上下壳、两侧短限位螺钉并断开电池后沿+Y取出 |
| integral_motor_seat_insertion | PASS | 整体电机舱从下方装入两台S288的路径 |
| frame_screwdriver_path | PASS | 下壳移除后的四处框架螺丝刀杆路径 |
| belly_relayout_datums | PASS | 横躺轮驱、头内Yaw与降低电池/板卡区的实际坐标和支承分组 |
| head_yaw_bench_removal | PASS | 倒装Yaw与可拆反力轴的规定顺序取出检查 |
| head_yaw_ear_tools | PASS | 头内Yaw两安装耳的直线工具杆空间 |
| flat_head_support_envelope | PASS | 平板头托在球壳内的名义包络与材料体积 |
| module_screwdriver_access | PASS | 新增短螺钉的规定装配阶段工具杆路径 |
| simple_module_removal | PASS | 屏幕组件、侧板与Yaw座的有限直线拆装采样 |
| all_fasteners_assembly | NOT_TESTED | 其余紧固件长度、嵌件热压头、工具手柄与完整逐件装配路径尚待阶段 B；当前候选孔仅供试打 |
| real_hardware_fit | BLOCKED | 只验证阶段 A 包络；保留共享契约中硬件候选的适配失败。最新型号与包络见 contracts/mechanical_interfaces.json；真实轮驱、屏幕、相机、舵机和完整连接器仍需阶段 B 回写，不能靠外观调整宣称已适配 |
| cable_service_loops | NOT_TESTED | 已建服务环、线束路径和约束点；实际柔性扫掠与连接器受力未验证 |
| hard_stop_contact_angles | NOT_TESTED | 有限角度限位件已布置；准确触点角度、强度与舵机失控冲击需专门验证，不能用软件限角代替 |
| power_interface_operations | NOT_TESTED | 已布置 USB-C、按钮、电源开关与插头/手指包络；实物插拔、开关急停可达性、线缆拉力待阶段 B |
| simplified_structure_strength | NOT_TESTED | 简单分件与短连接仅为结构设计改动；FDM层间强度、蠕变、冲击、疲劳及紧固预紧未进行仿真或实测 |
| hardware_populated_layout | BLOCKED | 已只读核对V1.2-H0.3-S3：S3两路5V改为板载TPS54302；芯片包络不等于转换器或PCB尺寸。完整S3装件尚未整合，新80×40×18是机械容量预留而非实板；电源PCB专用固定及主控装件接口未冻结 |
| lower_body_com_estimate | PASS | 当前布局与基准采用一致质量假设的重心比较（不以重心更低作为通过条件） |
| mass_inertia_estimates | PASS | 已输出有假设的质量与惯量估算（不是载荷验收） |
| structure_mass_targets | BLOCKED | 当前结构的估算质量与V1.2工程目标 |
| head_torque_and_balance | NOT_TESTED | 舵机扭矩、头部加速载荷、支架强度、轴承寿命与实机自平衡尚未验证 |
| dock_nominal_COM_projection | PASS | 托架四点名义支撑多边形内的重心投影 |
| dock_mesh_contacts | PASS | 实际托架网格接触、轮胎离地与实体干涉 |
| dock_physical_stability | NOT_TESTED | 软垫变形、地面摩擦、插线拉力及真实重心必须实测；托架稳定不代表机器人断电可自立 |
| budget_and_runtime | BLOCKED | 1000 元总预算和 60 分钟混合工况续航未验证；未提供完整报价与实测平均功耗 |
| display_active_aperture | PASS | 真实45.68mm发光区到观察侧的遮挡检查 |
| head_front_display_center | PASS | 圆屏、面罩与双眼中心对齐头部正前方中心 |
| head_allocations_inside_outer_envelope | PASS | 头内主板/屏板/相机/舵机位于声明头外形内 |
| wheel_coaxial_geometry | PASS | 双轮同轴且轮轴高度等于实际轮胎半径 |
| usb_plug_approach_allocation | PASS | USB插头外壳与前端插拔预留 |
| display_full_vendor_outline | BLOCKED | 原厂LCD外形已回写 / 两接插件精确实体待核 |
| actual_board_antennas_microphones | BLOCKED | CAM37×37板框、32.6孔中心距已核；实际装件厚度、孔径、USB/麦克风/天线坐标与FPC仍缺尺寸 |
| purchased_dimension_provenance | PASS | 采购件尺寸来源、原厂CAD比例与未知项标签 |
| all_purchased_parts_dimensioned | BLOCKED | 尚未选定/缺少完整尺寸的采购件保持橙色占位，不能宣称全部按实物建模 |

## 硬件与交付边界

只读核对V1.2-H0.3-S3。components.json由硬件拥有，机械任务未修改。S3电源PCB尺寸未定，TPS54302的2.9×2.8×1.1mm仅是IC封装。运动载板70×35×12、CAM37×37×12、电池80×65×30及扬声器/充电模块占位须回写真实装件和插头。缺项详见purchased_dimensions.md与purchased_geometry_audit.json。

已生成：参数、接口、模型、候选打印件、实际视图、逐件表和装配说明。已执行几何检查：见上表及各JSON原始证据。待硬件选型/PCB：真实舵盘、安装孔、连接器、供电模块和电池。待打印：间隙/孔/夹口试样、切片与承载。待实机：称重、IMU/相机/舵机标定、热/声学/射频及自平衡。预算≤1000元和续航尚未验证，没有采购或PCB冻结。
