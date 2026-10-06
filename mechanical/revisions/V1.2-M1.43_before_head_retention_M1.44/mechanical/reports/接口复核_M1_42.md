# MORI V1.2-M1.42 · 接口与打样前复核

已应用用户确认的两处头壳拼缝孔配对移动：X±43→±41 mm，Z259→261 mm。最终孔口已清除旧皮膜，嵌件位置不变。两处最小采样孔壁约 1.661 mm；34 处嵌件入口各用216条轴向射线核查，孔壁、盲孔底及螺钉啮合另查。当前本体候选打印件 15 件，没有新增机器人打印件。

34 个嵌件采用 FINE SL-M2×3 / SL-M3×4 目录包络，试配孔分别3.25 /4.05 mm；26 枚 M2 小盘头螺钉使用 GB823名义尺寸。这26处已用 Wiha42415 的PH1 /4mm×60mm刀杆和18mm手柄包络重查，分阶段工具空间通过。下方俯仰舵机保留 M2×14，采用 DIN912 内六角头；PB210.1,5（1.5 mm、50×14 mm）的长端用于单独头托装配，有限工具摆角检查通过。螺纹、压装和手持施力仍需样件。

## 四项任务的实际状态

|项目|状态|结果|
|---|---|---|
|头部传动连接|BLOCKED|按用户选择保留 SCS0009。配套舵盘、花键、短轴与轴向锁紧等厂家资料；已列明所需图纸，原占位件没有当成已定型件。反力连杆暂未改动。|
|嵌件与紧固件|BLOCKED|已采用 34 个目录嵌件、26 枚 GB823 名义包络及一枚 M2×14 内六角螺钉；已核孔口、孔壁、盲孔底和啮合。其余螺母/五金仍有候选与装入方式待确认，未把整机紧固件表标为冻结。|
|WeAct 排母和对插|BLOCKED|已建 Würth 8.5 mm 排母和插头候选。A–D 针脚匹配；E 的排针方向和基板孔阵列不匹配。Rear J3 插头与排母焊脚另有约 0.314 mm³ 交叠。电路交接已写好，原生 PCB 未改。|
|全部打印件与完整装配|FAIL|全件网格/壁厚采样与工具、步骤复核已做；已给相机孔腔、舵机螺母薄壁、轮轴承挡边、下壳孔口及上壳路径分别做好候选，等用户确认后应用和整机重验。当前主模型的问题仍记FAIL。|

## 实物到货前仍要解决

- **相机座旧孔腔 — FAIL**：当前局部约 0.362 mm；填平候选通过实体与 130 姿态检查，待用户确认。 [证据](../studies/interface_completion/thin_mount_comparison.svg)
- **俯仰上侧螺母槽 — FAIL**：当前与轴承孔之间约 0.102 mm；螺母移入现有耳座、M2×8、短侧装口候选已做，待确认。 [证据](../studies/interface_completion/thin_mount_candidates.json)
- **后侧 yaw 螺母薄壁 — FAIL**：原槽局部约 0.192 mm。保留螺母位置、开短前入口并重整4.2AF槽的候选已做；顶面承压材料约2.6 mm，名义装入、两种螺母包络止转和130姿态检查通过。待用户确认，未改反力连杆。 [证据](../studies/interface_completion/yaw_nut_open_candidate.json)
- **四个轮驱连接螺母 — FAIL**：原封闭槽无法装入。5×1.9 mm 短侧装口候选通过插入/止转检查，等待用户选择。 [证据](../studies/interface_completion/drive_nut_entry.svg)
- **轮轴承内侧挡边 — FAIL**：当前0.75 mm。候选内轴承外移0.5 mm，使挡边1.25 mm；同步延长金属轴肩、短隔套改4.5 mm。73姿态/侧及底盖、电机组件拆卸通过，待用户确认。 [证据](../studies/interface_completion/bearing_lip_candidate.json)
- **机身下壳孔口 — FAIL**：当前原长沉孔留下约0.29 mm尖薄片。四拼缝点移位候选消除此处薄片，下壳采样最薄约1.74 mm；待确认并应用。 [证据](../studies/interface_completion/body_seam_complete_checks.json)
- **机身上壳装入/取出 — FAIL**：现有孔位妨碍取壳。四拼缝点移至X±22/Y±71后：卸车轮、下壳及头部/固定桥，上壳带喇叭/后接口板倾斜15°、抬14 mm、后移14 mm再上提。369姿态和工具包络检查通过；尚未应用。 [证据](../studies/interface_completion/body_seam_comparison.svg)
- **WeAct E / 后接口 J3 — BLOCKED**：E 需要用户选择排针路线和电路任务修孔阵列；J3 与长焊脚的冲突需电路任务处理。 [证据](../studies/interface_completion/WEACT_E_HANDOFF.md)

## 本轮实际检查

已实施修改的专项检查为 PASS；主模型现有检查项计 110 PASS / 0 FAIL / 16 BLOCKED / 19 NOT_TESTED。这个统计范围不包括上表新增的完整装配/打印缺陷，所以整机打样前数字审查仍为 FAIL。130 个头部姿态没有检出本轮新增交叠。重复生成、保留非生成对象、STL回读、渲染/导出几何一致性、详细PCB副本与动画检查均分别有报告。

- [实际流水线命令](interface_commands.json) / [接口检查](interface_validation.json)
- [全打印件采样](interface_printability.json) / [孔与嵌件清单](interface_insert_schedule.csv)
- [26处PH1实际规格工具检查](../studies/interface_completion/catalogue_driver_checks.json)
- [一致性](delivery_consistency.json) / [动画检查](../animation/validation.json)
- [电路交接](../studies/interface_completion/WEACT_E_HANDOFF.md)
- [SCS0009配套资料需求](../studies/interface_completion/SCS0009_VENDOR_REQUIREMENTS.md)

全件壁厚采用面积分层、每件最多20000个三角形中心的反向法线射线，不能当作全局最小厚度证明。恰好1 mm的薄面浮点值可能略小于1；尖角、导入边和必要过渡仍逐处分类。已知实际薄壁没有借此豁免。当前模板动画仍只表达步骤；上壳使用独立预装镜头，尚不能据动画判断可装入。

## PA12试片和到货验证

另生成一件60×40×8 mm的辅助试片：M2嵌件孔3.05–3.45、M3嵌件孔3.85–4.25 mm（各0.1 mm步进），M2/M3各三个螺母槽变体；它不是机器人新增零件。[试片STL](../studies/interface_completion/coupons/interface_coupon.stl) / [Blender](../studies/interface_completion/coupons/interface_coupon.blend) / [坐标图](../studies/interface_completion/coupons/map.svg)。同一PA12供应工艺核对孔径、嵌件装入/拉拔、螺母止转后再选择补偿；本文件没有下单。

到货后需核：SCS0009原配舵盘；CAM/相机照片估计尺寸及夹持；SP3040耳厚/孔公差；电池包、线头和绑带；排母插深、完整对插、线束及工具手握；PA12配合、紧固力、蠕变/冲击和实际运动。电气/电池/急停/平衡验证交对应任务，机械几何不代替这些资格。

目录来源：[FINE](https://www.finesz.com/shk.php)、[GB823尺寸参考](https://www.wqjgj.cn/product/luoding/shizicao/2158.html)、[M2×14 DIN912](https://www.westfieldfasteners.co.uk/Bolts-Screws-Metric/Socket-Head-Cap-Screw-M2x14-A2-Stainless.html)、[PB210](https://www.pbswisstools.com/en/tools/quality-hand-tools/precisionbits/product/pb-210)、[Wiha42415](https://wiha.com/tools/screwdrivers/precision-screwdrivers/picofinish/phillips/picofinish-fine-screwdriver/42415)。本轮没有实物测量、采购或制造放行；硬件原生文件和 components.json 保持只读。
