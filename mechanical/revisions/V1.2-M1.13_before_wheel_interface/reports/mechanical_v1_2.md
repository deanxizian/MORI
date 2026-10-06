# MORI V1.2-M1.13 机械交付

已实际运行build、validate、render、export及重复生成检查。本轮按用户确认实施物理合并：本体打印件26→20，已示意紧固件78→74（取消2螺钉+2螺母）。轮盖由轮毂自身外观面替代；相机遮光座并入前壳；开口线导和Yaw转台并入U托；固定遮缝环并入Yaw承重桥。未以悬空网格拼组冒充连通实体。

维修分界保留：电池托盘、轮驱底盖、屏幕叉架、扬声器后盖及前后/上下外壳。新的头部维护顺序要求释放反力轴横向保持后，将反力轴随一体Yaw/U托取出；不是继续沿用旧版先拆U托底部螺钉的方式。CAD采购件保持1:1，轮轴、轮径、光学安装和外壳位置保持原方案。圆脸接齐球面、104mm整边主托板和接口板一体壳耳延续M1.12。[接口板设计要求](../mechanical/INTERFACE_PCB_REQUIREMENTS.md)。

正常装配宽×深×高约158.5×157.9×282.0mm；头部零位0°，切面Z=175.5mm水平。轮径105、轮宽18、球腹离地20mm，轮壳最小采样间隙4.00mm。全头动作包围尺寸[158.5, 157.9, 282.0]mm，yaw±60°/10°步长、pitch−20…+25°/5°步长，共130姿态；有限采样不是连续证明。±15°机身倾斜仍仅作几何测试。

IMU采用原生P2库CAD，器件向下。电池最小名义实体间距约11.8mm。P2运动载板和WeAct已1:1摆入，排母6mm仍是假设；电源板80×55只是容量。P3已另行生成85个库器件加PCB的详细参考，14器件仍缺CAD；该独立参考尚未替换总装电源容量包络，完整装件与对插空间未适配。当前P2参考没有改名冒充P3。接口板24×14是机械提案，两孔Ø2.2，顶面开关、底面USB-C都向后；真实器件未选择，不能按橙色包络下单或冻结外壳加工。

估重约1.27kg，估计质心[-0.4, -0.4, 116.9]mm，pitch运动件约185g。详见mass_budget.json的材料/填充和附件质量，至少±35%不确定，未测平衡、扭矩或惯量。新增PCB库几何不等于整板实测质量。

实际检查{'PASS': 49, 'FAIL': 0, 'NOT_TESTED': 12, 'BLOCKED': 14}。Blender5.2.1 LTS / Python3.13.13 / Manifold3.5.3。重复生成PASS；最终输入、渲染与STL一致性PASS。24候选STL已回读检查毫米尺寸。

新增[一体Yaw限位复查](../mechanical/reports/integrated_stop_check.json)：沿两方向每1°检查，64°样本尚无正体积交集，65°样本在限位凸耳高度出现接触穿入；这只是离散几何挡止区间，正常工作角仍为±60°。不代表可运行到65°，也不验证公差、冲击和打印强度。

新增[M1.13 S288轮驱接口复查](../mechanical/studies/s288_interface_review/README.md)：电机是按原厂关键尺寸制作的简化模型；输出盘安装六孔及转接锁紧未完成。转接盘与另外预留的轮轴轴向啮入为0；轮毂孔Ø4.4与轴Ø3.98之间尚无止转/夹紧，轴向防脱和轴承保持也未定型。当前轮组不能按候选STL直接装车。这是待完成的传动接口设计，不能用同轴布局、有限干涉检查或动画旋转代替。

| 检查 | 状态 | 说明 |
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
| camera_recess_and_default_pitch | PASS | 相机镜筒/保护窗均在头球轮廓内；头壳默认水平，仅光学安装上仰10° |
| default_pose_height | PASS | 默认水平头姿态的实际尺寸 |
| vertical_rear_ports | PASS | 电源/禁驱开关在USB-C正上方，无独立外置重置件 |
| speaker_shell_attachment | PASS | 扬声器压盖落在外壳固定座，内框架无连接 |
| speaker_shell_tool_access | PASS | 抬出上壳并断开音频插头后的压盖工具空间 |
| speaker_blind_boss_skin | PASS | 扬声器从壳内安装，盲孔末端保留外表皮 |
| weact_vendor_CAD_import | PASS | WeAct V1.1原厂224实体按毫米刚性导入 |
| selected_battery_speaker_nominals | PASS | 成品电池与扬声器采用明确型号的名义尺寸 |
| onboard_microphone_registration | BLOCKED | 两颗板载MIC实体、声孔和独立声道已示意；位置/封装仅照片估计 |
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
| hardware_populated_layout | BLOCKED | 已只读核对V1.2-H0.3-P3：S3两路5V改为板载TPS54302；芯片包络不等于转换器或PCB尺寸。P3原生坐标/板框交接已读取，但完整P3装件和对插尚未整合；当前80×55板框、+16/−3装件高度是机械容量，最终固定仍待适配 |
| lower_body_com_estimate | PASS | 当前布局与基准的质量模型比较（包含选型质量变化，不以重心更低作为通过条件） |
| mass_inertia_estimates | PASS | 已输出有假设的质量与惯量估算（不是载荷验收） |
| structure_mass_targets | BLOCKED | 当前结构的估算质量与V1.2工程目标 |
| head_torque_and_balance | NOT_TESTED | 舵机扭矩、头部加速载荷、支架强度、轴承寿命与实机自平衡尚未验证 |
| dock_nominal_COM_projection | PASS | 托架四点名义支撑多边形内的重心投影 |
| dock_mesh_contacts | PASS | 实际托架网格接触、轮胎离地与实体干涉 |
| dock_physical_stability | NOT_TESTED | 软垫变形、地面摩擦、插线拉力及真实重心必须实测；托架稳定不代表机器人断电可自立 |
| budget_and_runtime | BLOCKED | 1000 元总预算和 60 分钟混合工况续航未验证；未提供完整报价与实测平均功耗 |
| display_active_aperture | PASS | 真实45.68mm发光区到观察侧的遮挡检查 |
| head_front_display_center | PASS | 圆屏按球面径向安装，各光学层沿10°法线同轴；头壳仍水平 |
| head_allocations_inside_outer_envelope | PASS | 头内主板/屏板/相机/舵机位于声明头外形内 |
| wheel_coaxial_geometry | PASS | 双轮同轴且轮轴高度等于实际轮胎半径 |
| usb_plug_approach_allocation | PASS | USB插头外壳与前端插拔预留 |
| display_full_vendor_outline | BLOCKED | 原厂LCD外形已回写 / 两接插件精确实体待核 |
| actual_board_antennas_microphones | BLOCKED | CAM37×37板框已核；两颗板载麦克风已示意，坐标与厚度仍为照片估计，精确PCB装件CAD和FPC尺寸缺失 |
| purchased_dimension_provenance | PASS | 采购件尺寸来源、原厂CAD比例与未知项标签 |
| all_purchased_parts_dimensioned | BLOCKED | 尚未选定/缺少完整尺寸的采购件保持橙色占位，不能宣称全部按实物建模 |
| face_rim_on_sphere | PASS | 黑色圆脸外缘与头球面接齐，消除倾斜造成的非对称凹台 |
| load_frame_uncut_side_lands | PASS | 托板左右整边收窄，轮窝附近底面仍保留完整4mm平板 |
| imu_underside_rigid_mount | PASS | 原生20×16 IMU装到主托板底面，器件向下；检查电池及插头空间 |
| removed_redundant_parts | PASS | 移除独立功能键；两侧短板与主托板合并，删除独立电源托板 |
| level_head_independent_optics | PASS | 头底切面保持水平，屏幕/相机单独固定上仰 |
| new_PCB_bench_tool_access | PASS | IMU底面与后接口板的台面装配工具杆空间 |
| rear_interface_double_sided_selection | BLOCKED | 后接口板已生成板框、壳体安装座及上下开口；双面侧出器件待另任务选型 |
| native_P3_handoff | BLOCKED | P2原生基板/IMU已1:1摆入，电源80×55容量已纳入；P3原生坐标已交接，完整装件与插头适配仍未完成 |
| imu_three_anchor_recommendation | BLOCKED | P3交接指出IMU两孔与厂家至少三固定点建议仍需结构适配 |
| static_same_group_wire_passages | PASS | 全部已画线束预留与同组实体的通孔/槽检查 |
| merged_frame_and_rear_PCB_removal | PASS | 一体短侧板主框与后接口板的规定台面拆出路径 |
| physical_part_consolidation | PASS | 26→20本体打印件，合并件均为单一连通实体；保留固定/转动分组 |

[装配与打印](../mechanical/reports/组装与打印.md)。已生成模型与候选件；完成的几何检查见表。采购选型/P3交接、局部试打、强度/热/音频/续航和实机自平衡仍未完成。完整精确实物干涉仍BLOCKED：LCD两个接插件使用保守代理，CAM镜头/FPC等未取得完整尺寸。没有掩盖这些边界。
