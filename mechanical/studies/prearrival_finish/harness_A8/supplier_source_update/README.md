# 供应商按图制作：资料和设计进度分开记录

2026-10-05。供应商按图制作已经确定，不再等待制造方式确认。MORI 的线路、分支、长度基准和装配图由项目完成。未发送供应商消息或下单。

## 最新：原桥座的简化套线顺序未通过

已用原M1.47实体复核：带轴承桥座直接套线、4组左侧临时排布、轴承后装的4组直立排布均未通过。所试线尾位置的上下可通过范围错开；一处端子请求空间碰底面，另一候选的一处导线中心已在桥座材料内。中心小孔仍存在，不是桥座完全封闭。上壳的5条所试路线也未通过，涉及后接口插头对IMU线及线端对上壳的问题。
这只排除了具体测试路线；没有扩大孔口、改小配件或修改主模型。之前的PH带线插接局部通过保留，完整穿颈/装配还没接起来。
[原桥座剖面与装配诊断](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/bridge_tail_order_review/index.html)。

## 此前：PH带四根完整导线的插接阶段通过

采用自由线尾先留在颈部外侧的顺序，PH随圆滑路径转向。171个全线位置、174个全线连续区间和875个插头/线根扫掠包络通过；保持原名义总长，未修改结构。
随后穿颈、H01/H04后装、其他跨关节线、FFC、扎带与手部工具仍未完成，完整线束图继续BLOCKED。
[带线动作图和连续检查](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/PH_guided_wire_entry/index.html)。

## 此前：找到PH上方插接路径，继续核对带线装配

裸PH胶壳从上方开口进入的7段平移路径已通过封闭实体扫掠复核，采用H02/H03先装、H01/H04延后的顺序。四根导线前5mm直段另有24段扫掠通过，余下柔性导线随插头移动仍需检查。
颈部CAM1/2和身体插头附近CAM3/4的原局部间隙问题已单独定位；提前调高度和扭线仍未解决原带线后移路线。
又比较了上壳保持打开后连接身体端PH的顺序，裸胶壳结果和明确延后的H01/H04分别列出，不能当作完整线束通过。
[局部三向图、候选结果与范围](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/shell16_packing_diagnosis/index.html)。主模型和制造放行状态保持。

## 此前：外壳与桥的四段刚体路径已走通，完整线束仍待衔接

插头包络与零件尺寸保持。外壳倾斜16°并抬高14mm，桥上抬18mm，二者一起后移20mm，再向上提离。
297个刚体检查记录、294个不同位置通过，包含身体/后板插头与14根固定身体线。
前两段含四根CAM线的61+37个检查记录通过；CAM后移的单根分步路径也已取得结果，但四根线共同移动及后续提离仍未整体完成。
[装配顺序图、来源核对和每段检查范围](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/shell16_joint_feed/index.html)。
主模型M1.47和制造图保持；使用既有未采用的结构候选，完整线束仍BLOCKED。

## 此前：CAM 与 H02 抬升走向已配合，暴露了外壳插头路径问题

H02第二根线只调整中段，两个端口、针序、端后直段和弯曲半径保持，名义路线增加约0.55mm。
4根CAM与2根H02在桥上抬0–18mm的37个有限位置通过线形检查；H02的201个提前装入位置、
408个身体位置及130个头部姿态复核通过。这些是分别限定的检查，不能当作整套装配通过。
补查后板插头随外壳移动时，原保持位置的J2插头保守包络与Load Frame有约0.03635mm³重叠。
后移桥的弯线、继续抬高外壳及后板带线拔插时机仍需处理。
[新旧走向、阶段检查与插头重叠图](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/CAM_H02_joint_lift/index.html)。
这部分属于项目尚未完成的设计，不应归为等待实物；主模型和制造图状态保持。

## 此前：CAM 分段送线的位置检查与中途问题

保持身体端 PH 胶壳不动，桥上移18mm、以及再后移14mm，两处分别找到四根CAM线的排布。
两处对当前零件、14根身体线、29个插头空间、自绕、邻线及端子占位检查通过，完整名义线长保留。
当时从坐稳位置逐步抬升尚未闭合；第4根线与H02的走向问题现已在上面的联合研究中取得37位置通过。
六种收弯时序经细化仍有间隙不足或相交；还补查了临时降低中段的候选。
两处独立位置通过不代表完整装配通过。[对比图、检查与限制](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/feed_pose_packing/index.html)。

## H02 提前连接，H01 / H04 继续处理

六个裸插头路径加上现有名义线长后，H02 和 H04 部分位置不满足必要长度下界；裸插头通过不能代表整束可装。
H02 已有较低的新走向，保留针序、端点和弯曲半径，在开敞机身内提前接好。两端插头与完整线形的
201个装入位置、随后408个身体装配位置和130个头部姿态复核通过；不改打印结构或PCB。
H01/H04 的10根导线尚未完成带线装配工序。进一步尝试提前连接：H01 每根821组，
H04每根106组，均未形成完整通过的组合。让 CAM 插头和导线留在身体侧、桥单独运动，
又在桥上移18mm的保存位置发现实际相交。需要设计分段送线，不能直接沿用固定线形的桥路径。
[进一步诊断与范围](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/body_fixed_CAM/index.html)。
人手工具、线尾、扎带和供应商裁线图仍未完成。
[H02走向与线长复核](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/H02_preinstalled/index.html)。
此前六条裸插头路径作为对照保留，不能直接用于完整线束制作。
[顺序与路径图](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/review/index.html)。

相机支架上沿另有局部清理候选，已通过名义几何复核，仍等待用户采用；主模型保持。
[相机上沿候选](../../camera_top_clearance/index.html)。

## 其他局部候选与此前装配检查

同一较大端子预留现在已有独立的颈部候选：临时下弯道改为 R10、竖直起点上移1 mm，
扩宽两件已有候选的通道；四方向连续穿入、颈部尾线和回位检查通过，保存网格已复核。
端子/导线间隙保守下界约0.308/0.306 mm；轴颈径向壁厚最小样本从1.60变为1.48 mm。
这是未采用的局部几何结果，强度、全长供线和整机顺序尚未完成。
[候选剖面与证据](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/larger_neck_candidate/index.html)。

此前[分步装配与完整线长补查](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/split_assembly/index.html)：
22件偏航与舵盘先装、14件头托与CAM后装的有限刚体路径通过。四根名义全长及共同PH插头已经
建入，约153–162mm线尾先存放在头部上方；当时身体线束已装的动作存在间隙或相交问题。
LCD代理姿态误报已修正。相机上角候选和新的CAM先装顺序见上节；主模型和主动画保持。

上部已通过的连续检查仍保留。原颈部路径此前沿用较小端子方盒，换成同样的
1×1.8×4.1 mm 空间分配后，下弯道首个间隙不足位置约0.252 mm，小于0.3 mm。
保持打印件不变的49组位置/滚转角尝试均未通过。该尺寸是请求的空间预留，
不是厂家完整压接成品外形。

原身体上壳动作只检查了承重桥，加入完整头部后有碰撞；10种同步动作和下部
框架直装也未通过。仍需设计分步穿线和身体端接入，不能把这些未完成设计归为
等实物。[本轮剖面与结果](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/index.html)。

## 新取得的厂家资料

已从 [JST 官方网站](https://www.jst-mfg.com/product/pdf/eng/eAPSH.pdf)下载 APSH 目录，并查看第 1 页 Contact 图。图中端子为 **SSH-003T-P0.2-H**，与 SH 目录同料号；没有改选 APSH 胶壳。

相比 SH 简版目录，该图给出接触段及压接翼的轴向位置，并多出 **1.55 mm 的轴向尺寸**。它不是整个端子的高度。0.8 mm 宽、1.35 mm 接触体高度和 3.9 mm 长度均为图示名义值；接触体下方的小突出和压接后轮廓仍没有完整尺寸、公差。旧方盒不能因此升级为真实端子的完整最大外形。

本目录也明确列出 AP-K2N、MKS-L-10-3 和 APLMK SSH/L003-02 工装，以及 32–28 AWG / 0.4–0.8 mm 绝缘外径的适用范围。这些是可交供应商核对的来源，不能代替实际线材与模具组合的工艺确认。

[保存的厂家 PDF](../ssh_catalogue_addendum/apsh/JST_eAPSH.pdf) · [原页预览](../ssh_catalogue_addendum/apsh/page1_mupdf.png) · [尺寸解读](../ssh_catalogue_addendum/apsh/README.md) · [下载及哈希记录](../ssh_catalogue_addendum/apsh/retrieval.json)

复查 [JST LBT 官方目录](https://www.jst-mfg.com/product/pdf/eng/eLBT.pdf)后，确认下载与项目已存 PDF 逐字节相同，复用原文件，没有新版本或新增尺寸。第 2 页同料号 SSH-003T-P0.2-H 的尺寸与工装信息已记录；LBT 的 28 AWG / 0.6–0.8 mm 应用范围与 SH/APSH 的 32–28 AWG / 0.4–0.8 mm 分开保留，没有据此改选 MORI 线材或胶壳。[既有核对说明](../ssh_catalogue_addendum/README.md) · [原图](../ssh_catalogue_addendum/contact_page2.png) · [本次复查](../ssh_catalogue_addendum/live_recheck_142240.json)

### 新核对 M5Stack 的舵机资料和摇臂模型

[M5Stack 官方 StackChan 页面](https://docs.m5stack.com/en/base/StackChan_Body)提供 SCS0009 PDF 和结构仓库。下载的 PDF 与项目已有 A/0 规格书逐字节相同；已查看第 7 页，内容为 **No Accessories**，不是新增的配套舵盘图。

官方仓库另有自己的 `StackChan-ServoArm.stl`。已下载并按 Git blob 哈希核对；3744 个三角面，剖面确有带齿孔，径向轮廓的主要周期为 20。STL 不携带单位声明，不能把数值观察升级成飞特齿形、公差或 MORI 配套认证。它提供了一个官方整机连接参考，但还缺型号配套、材料/工艺和轴向装配确认，未替换主模型。

[M5Stack 原始摇臂](../public_source_extensions/StackChan-ServoArm.stl) · [模型预览](../public_source_extensions/m5_arm_views.png) · [剖面](../public_source_extensions/m5_arm_section.png) · [检查记录](../public_source_extensions/inspection.json)

另已实际读取 JST 德国站的 SSH 端子与 SHR-04V-S 胶壳页面，只有规格表，没有找到逐型号图纸/CAD 下载链接。TE 2151515 工装图的公开索引可检索，实际 PDF 下载仍失败；未将索引片段当作已取得、已检查的工艺图。

## 找到入口但尚未取得的文件

本次再次打开 [JST SH 官方页](https://www.jst-mfg.com/product/index.php?lang=2&series=231)的端子逐型号图、SHR-04V-S STEP 和 CHM 专用手册链接。三个入口均显示邮件附件申请页，需要填写联系资料；没有返回相应图纸。另核对 [JST 英国 SH 页面](https://www.jst.co.uk/productSeries.php?pid=7929)，其专用手册和2D/3D入口仍指向上述日本官网申请流程。未提交表单。应记录为“入口已找到、文件尚未取得”，不能称为资料不存在，也不能假称已下载。

微雪 [CAM 资源页](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)仍提供 V1/V1.1 原理图；本次未在该页找到完整相机 FPC 尺寸图。SCS0009 的舵盘、CAM 实际板端连接器料号等缺项仍见[原资料清单](../../supplier_made_harness/SOURCE_REVIEW.md)。

## 现在仍要由项目完成的装配设计

**上部候选已有进展：**按几何槽位 3→2→1→0 逐根穿入，先暂缓上端收拢，再一起回到固定位置。较大端子请求空间通过 1228 个穿入连续区间和 256 个回位连续区间；同样预留尺寸的后续入座 256 个连续区间、四段弯线 1735 个连续区间也已通过。弯线调整了两处临时动作，结构和最终线形不变。本轮已补建四根完整名义线长、上方暂存线尾及共同PH插头；完整身体供线过程仍未通过，不是再加额外裁线长度。扎带和真实端子入壳仍未完成。[上部路线与材料账](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/ordered_feed_recovery/index.html) · [后续尺寸统一复核](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/large_contact_downstream/index.html)。

以下保留旧方案的具体失败范围，不代表新候选仍以同样方式失败：

| 具体尝试 | 检查范围 | 结果 |
|---|---|---|
| 端子沿最终上部弯线穿入 | 4 槽位 × 2 朝向 × 2 明示空间分配，共 16 组 | 16 组均未通过；有结构或邻线问题 |
| 先向上引出，再同步整理四线 | 21 个位置 | 未通过；整理途中对俯仰支架的预留间隙不足 |
| 整理时临时上抬弯曲段 | 2 / 3 / 4 mm 三种最大抬高量，各 21 个位置 | 均未通过；支架或舵机的间隙问题仍在 |
| 颈部出口先竖直引出端子 | 4 槽位 × 2 种明示空间分配，整段扫掠 | 8 组局部通过；实际端子外形、下方供线和手部操作未验证 |
| 从下往上逐段整理导线 | 41 个位置 | 未通过；中段支架和后段邻线的间隙界限不足 |
| 整理中先延长临时切线，再转向竖直 | 4 / 8 / 12 / 16 mm 四种最大延长量 | 四种均在首个检查位置未通过；未改打印件 |

保持了离散线段总长，机器人零件没有改变；只按工序暂不装根部扎带。检查中的 0.002 mm 数值余量是临时筛查分配，尚无完整积分误差证明；21 个位置也不是连续运动证明。记录里继承的目标线形半径值不能当作整个暂态线形的半径认证。间隙未达标不一概解释为实物相撞，失败也不证明所有装法都不可行。

端子两种检查对象分别为旧名义方盒和额外请求的空间分配。后者不是厂家最大尺寸，也不是把端子放大后认定为完整外形。没有因这些尝试失败而修改打印件、孔位或主模型。

竖直引出使用未应用的 J3M/CAM 研究几何，暂未安装根部扎带；端子对打印结构检查 0.3 mm 余量，对其他导线和端子检查名义不相交。整段方盒扫掠的局部通过不能代表完整穿线或真实端子入壳。逐段整理采用临时 0.003 mm 曲线误差分配，41 个位置不是连续证明；末段较保守的间隙界限未过，不等于已证明原目标线形发生实体相交。

[端子穿入诊断](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/upper_terminal_feed/screen.json) · [直接整理](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/upright_staging/screen.json) · [临时抬高整理](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/raised_staging/screen.json) · [已完成的局部入座](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/aligned_tails/README.md)

[竖直引出检查](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/vertical_free_feed/screen.json) · [逐段整理诊断](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/progressive_staging/screen.json)

延后转向的四个候选仍在俯仰支架或局部入线座附近未达到既定间隙；它们只排除了所测试的动作，不证明所有装法都不可行。[诊断记录](../cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/delayed_recovery/screen.json)。该尝试与前面的 41 个位置使用临时 0.003 mm 曲线误差分配；都不构成全程曲率或连续装配证明。

完整穿线、扎带穿绕与收紧、真实端子入壳、其他七根跨关节线、LCD/相机 FPC 和最终裁线尺寸仍未完成。制造图继续 BLOCKED；不能全部归到“等待实物”。主模型、配置和硬件合同保持，来源校验见[本次记录](verification.json)。
