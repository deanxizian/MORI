# MORI V1.2-M1.31 当前机械交付

保留原来的直角安装座，只清除接角处旧几何叠加留下的窄条和弧形残料。安装座外形、座面、螺孔、嵌件和舵机位置保持，没有增加斜撑、零件或螺钉。 [本轮修改](舵机座直角清理.md)

两只SCS0009按厂家尺寸图重建：修复安装耳悬空，纠正耳座高度，补齐输出端。固定支架改为连续底面和简单耳座，撤掉预估走线孔、斜切和线夹。 [本轮修改与精度范围](小舵机与固定座.md)

走线已延后；舵盘配合和打印强度未验证。

已实际建立、验证和渲染原生PCB装件模型；当前总装保留M1.22的承重桥与短Yaw限位。

| 电路板 | 裸板 mm | 当前模型 |
|---|---|---|
| 运动基板 | 70 × 35 × 1.6 | P5R2：原生板框、全部安装孔、原生装件位置；WeAct 核心另用原厂 CAD |
| IMU 板 | 20 × 16 × 1.6 | P5R2：原生板框/孔/装件；保持刚性安装于托板背面 |
| 电源板 | 80 × 55 × 1.6 | P5R2：装件替换旧容量盒；两只 EEUFR1C102 电容改为 Ø10 × 16 |
| 后接口板 | 24 × 25 × 1.6 | P5R2：双面装件、开关与 USB 按原生坐标；已适配板框和固定座 |

精度分三层：原生 PCB 的板框、孔、位号、位置、转角和安装面来自已交接 KiCad 文件；有原厂 STEP 的模组保留 1:1 原网格；缺 CAD 的封装按原厂尺寸图重建或使用 KiCad 名义库模型。后两者不等于每颗所选料号的实测外形。焊点、涂层公差、全部配对插头和导线折弯仍不完整。几何颜色仅帮助识别材质，绿色不表示已实测或可下单。

电源板的 XT30、保险丝、电感、TPS54302、16mm 电容，以及后板开关和 USB 已补上有尺寸依据的模型。XT30 是保守壳体/焊脚包络，未画成原厂完整接触结构；小封装引脚折弯及壳体倒角有简化。每个元件的 evidence、dimension_basis、limitations 写入独立模型对象与源 JSON。

LCD35079、WeAct V1.1 延用已有原厂 CAD；现有 Pololu D36V50Fx、D24V22Fx 家族原厂 CAD，分别对应硬件任务的 D36V50F9、D24V22F6 工程参考。家族外形不证明电压版本、热能力或额定电流已适配。

CAM33700 仍只有官方37×37板框与32.6mm孔网格可靠；完整装件高度、连接器、双麦精确坐标、FPC和实物厚度缺来源。M1.23建模时核对官方资源页，仅找到原理图与示例，未找到完整装件 STEP，不能用别家 ESP32-S3-CAM 代替。独立3S充电/PD板仍未选定，后接口板本身不是充电器。

实际检查{'PASS': 79, 'FAIL': 0, 'NOT_TESTED': 17, 'BLOCKED': 18}；静态穿插0项；候选STL 20/20；重复生成PASS；当前输入/渲染/STL一致性PASS。Blender5.2.1 LTS，KiCad10.0.6。完整命令见commands.json和sources/populated_P5/export_commands.json。

必须继续处理后接口板开关可操作性、配对插头/走线、CAM完整资料、排母和充电板选型。详见[PCB反馈](../PCB_LAYOUT_FEEDBACK_M1_23.md)。不能把裸装件通过当成整机已可制造。

生成：主模型、逐位号详细模型、当前装配动画Blender、实际渲染、部件表和候选STL。
通过的项目及条件见[validation.json](validation.json)，完整来源见[电路板模型报告](电路板精细模型.md)。打印、载荷、热与实机平衡仍未实测。

| 检查 | 状态 | 内容 |
|---|---|---|
| static_rigid_solids | BLOCKED | 刚性实体采样 / 原厂两接插件仅完成保守代理检查 |
| combined_yaw_pitch | BLOCKED | Yaw/Pitch 联合采样 / 两接插件精确网格待核 |
| face_mask_body_clearance | PASS | 圆屏外面罩与身体在联合姿态中的实际间隙 |
| sampled_cable_allocations | NOT_TESTED | 走线已按用户要求延后，未验证 |
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
| vertical_rear_ports | BLOCKED | 按原生PCB显示上下接口；开关深度和旧8mm操作间距要求未满足 |
| enclosed_speaker_nominals | PASS | 福声箱体、原厂耳和孔距按提供图纸生成；未缩放采购件 |
| speaker_shell_attachment | PASS | 喇叭原厂耳直锁上壳一体座；取消打印后盖、与内框架无连接 |
| speaker_shell_tool_access | PASS | 上壳拆出后喇叭两枚螺钉可装入并有工具路径 |
| speaker_blind_boss_skin | PASS | 原厂耳有实际支承面，壳内盲孔末端有材料 |
| speaker_max_box_envelope | PASS | 箱体最大标注外形公差与周边实体 |
| speaker_rear_vent_reserve | PASS | 未定坐标泄气孔：整个后表面保留2mm开放空间 |
| speaker_removal_path | PASS | 上壳台面状态下喇叭沿背面40mm抽出路径 |
| speaker_front_grille_paths | PASS | 原有15个外壳声孔对准新喇叭圆形前面且通路开放 |
| speaker_physical_audio_fit | BLOCKED | 喇叭实物、耳厚/孔距公差配合、线长接头、振膜行程与实际声音待核 |
| weact_vendor_CAD_import | PASS | WeAct V1.1原厂224实体按毫米刚性导入 |
| selected_battery_speaker_nominals | PASS | 成品电池与扬声器采用明确型号的名义尺寸 |
| onboard_microphone_registration | BLOCKED | 两颗板载MIC与声孔已示意，已取消打印导管；位置、进声面和封装仍待实板确认 |
| microphone_open_path_nominal | PASS | 取消两根打印导管，保留板载双麦与模型中的开放进声路径 |
| microphone_open_cavity_audio | NOT_TESTED | 无导管方案的拾音、双麦串音及扬声器/舵机噪声影响尚未录音验证 |
| belly_relayout_datums | PASS | 横躺轮驱、头内Yaw与降低电池/板卡区的实际坐标和支承分组 |
| head_yaw_bench_removal | PASS | 倒装Yaw与可拆反力轴的规定顺序取出检查 |
| head_yaw_ear_tools | PASS | 头内Yaw两安装耳的直线工具杆空间 |
| flat_head_support_envelope | PASS | 平板头托在球壳内的名义包络与材料体积 |
| module_screwdriver_access | PASS | 新增短螺钉的规定装配阶段工具杆路径 |
| simple_module_removal | PASS | 屏幕组件、侧板与Yaw座的有限直线拆装采样 |
| all_fasteners_assembly | NOT_TESTED | 其余紧固件长度、嵌件热压头、工具手柄与完整逐件装配路径尚待阶段 B；当前候选孔仅供试打 |
| real_hardware_fit | BLOCKED | 已检查原厂CAD、原生PCB和注明来源的名义器件几何；CAM完整装件、实际配对插头、公差、螺纹与热/负载仍缺验证，不能宣称整机实物装配已通过 |
| cable_service_loops | NOT_TESTED | 走线方案延后；旧示意已隐藏，后续需重建服务环与应力释放 |
| hard_stop_contact_angles | NOT_TESTED | 有限角度限位件已布置；准确触点角度、强度与舵机失控冲击需专门验证，不能用软件限角代替 |
| power_interface_operations | NOT_TESTED | 已布置 USB-C、电源开关与操作空间；独立功能键已取消。实物插拔、开关急停可达性、线缆拉力待阶段B；原生后板拨柄缩进另列BLOCKED |
| simplified_structure_strength | NOT_TESTED | 简单分件与短连接仅为结构设计改动；FDM层间强度、蠕变、冲击、疲劳及紧固预紧未进行仿真或实测 |
| hardware_populated_layout | BLOCKED | 已只读核对V1.2-H0.5-P5R2：四块自绘PCB按交接原生文件装入，两路板载5V电路及名义装件已建模。缺CAD器件保留尺寸图重建/库模型标记；配对插头、CAM完整装件和后板开关操作性仍未通过。 |
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
| latest_hardware_contract_integration | BLOCKED | 已接入PCB版本与硬件任务当前契约的同步状态 |
| all_purchased_parts_dimensioned | BLOCKED | 缺完整尺寸或未选型的部件仍有待核项；原厂CAD、尺寸图与库封装并非实测，不能宣称全部精确实物建模 |
| face_rim_on_sphere | PASS | 黑色圆脸外缘与头球面接齐，消除倾斜造成的非对称凹台 |
| load_frame_uncut_side_lands | PASS | 托板左右整边收窄，轮窝附近底面仍保留完整4mm平板 |
| imu_underside_rigid_mount | PASS | 原生20×16 IMU装到主托板底面，器件向下；检查电池及插头空间 |
| removed_redundant_parts | PASS | 移除独立功能键；两侧短板与主托板合并，删除独立电源托板 |
| level_head_independent_optics | PASS | 头底切面保持水平，屏幕/相机单独固定上仰 |
| new_PCB_bench_tool_access | PASS | IMU底面与后接口板的台面装配工具杆空间 |
| imu_three_anchor_recommendation | BLOCKED | P3交接指出IMU两孔与厂家至少三固定点建议仍需结构适配 |
| static_same_group_wire_passages | NOT_TESTED | 走线延后，当前不检验同组走线孔槽 |
| merged_frame_and_rear_PCB_removal | PASS | 一体短侧板主框与后接口板的规定台面拆出路径 |
| native_populated_sources | PASS | 四块原生PCB按已交接版本导入；板框/孔/装件坐标与来源哈希检查 |
| native_populated_rigid_fit | PASS | 已建模电路板与总装实体的静态交集检查 |
| buck_underside_mount_access | PASS | 两块降压板一体短座、底面螺钉工具路径与电池间距 |
| rear_native_switch_reach | BLOCKED | 后接口板真实尺寸已适配；原生开关拨柄仍缩在壳内，需要电路布局或拨杆方案调整 |
| populated_mated_thermal_fit | BLOCKED | 裸装件检查不包含全部对插线束、CAM完整装件、排母选型和独立充电板 |
| head_cleanup_preserved_hardware | PASS | 历史头部修改范围核对；本版舵机与固定座另有专项检查 |
| head_cleanup_single_solids | PASS | 三个大件各为连续封闭实体，无悬空碎片 |
| head_planar_walls | PASS | 头托两面平齐、轴孔承压环连续；相机立柱两侧等宽 |
| head_face_nut_insertion | PASS | 屏幕叉架螺母从内侧装入；孔后实际承压材料仍连续 |
| head_rear_corner_profile | PASS | 头托恢复双侧大折角，斜壁等厚及其余零件原位核对 |
| head_servo_front_foot | PASS | 仅清除原直角接角处的残留填充；原直角柱、座面和所有硬件保持 |
| head_servo_detailed_interfaces | PASS | 小舵机壳体连续、安装耳孔座对齐、输出轴原位及台面装配路径 |
| head_routing_deferred | NOT_TESTED | 按用户要求延后走线；撤掉头部预估线孔、线夹并隐藏旧线束示意 |
| head_servo_horn_engagement | BLOCKED | 输出轴按厂图定位；现有舵盘仍为占位，不可据此加工花键配合 |
| head_surface_normals | PASS | 头部平面法线正确；几何变化限定在已声明的当前修改范围 |
| drive_cleanup_preserved_datums | PASS | 轮驱既有修改范围核对；本轮头部变化另行验证 |
| drive_cleanup_continuous_solids | PASS | 上座、底盖与主托板各为连续闭合实体 |
| drive_cleanup_flat_faces | PASS | 轮驱外侧壁平齐，无锁紧柱凸条与顶沿台阶 |
| drive_cleanup_contact_material | PASS | 原电机软垫平面与M3锁紧承压材料保留 |
| physical_part_consolidation | PASS | 本体打印件最终数量与合并实体检查；保留固定/转动分组 |
| wheel_positive_drive_and_axial_stack | PASS | 双扁位实体止转、轴肩止挡与端部锁紧座 |
| s288_six_hole_flange_installation | PASS | 两侧六孔连接、螺钉伸入量及装轴承前的工具通道 |
| complete_wheel_drive_sweep | PASS | 法兰、螺钉、整轴、隔套和轮毂共同旋转一周 |
| wheel_drive_service_sequence | PASS | 下壳、共用底盖与两套电机/轴承组件的顺序拆装 |
| wheel_cap_tools | PASS | 共用底盖四枚螺钉的下方工具通道 |
| wheel_shell_local_walls | PASS | 轮窝指定区域的真实壁厚与独立算法交叉核对 |
| wheel_drive_strength_and_fit | NOT_TESTED | 轮驱载荷粗算与试配边界 |
| crossbolt_yaw_bridge_mount | PASS | 承重桥插接与横向M3穿栓；肩面承托，侧向装配及头部运动复核 |
| other_fastener_feature_cleanup | PASS | 其余打印件安装特征巡检；喇叭、底盖与夹口收进主体轮廓 |
| battery_retention_closed_edges | PASS | 电池托盘两侧固定孔的闭合孔边、螺钉支承面与装入路径 |
| short_power_board_mounts | PASS | 取消两条长托边，四个一体矮座与对角双螺钉；板底间隙及规定台面装配路径 |
| wide_battery_tray_flat_sides | PASS | 加宽托盘配合平侧板，取消局部凸块；底部实际承托与抽取间隙 |
| compact_yaw_stops | PASS | 环内短限位、正常间隙及转台/轴承上提路径 |
