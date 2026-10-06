# H01–H04 静态线束接收与厂家证据补充

2026-10-02。**资料核对 PASS；采购、压接、整机装拆、上电放行仍为 BLOCKED / NOT_TESTED。** 本轮没有修改任何 PCB、机械模型或正式引脚分配；正式原生板仍为运动/后接口 P5R7、电源 P5R6、IMU P5R4。

## 1. 十四根线的几何报告已接收

对机械 `fourteen_validation.json` 及其四个依赖文件逐一核对 SHA-256，确认对应 M1.47 主模型。检查了报告的 14 个独立线体、91 个不重复线对、130 个头部姿态及端点/针号一致性。H01–H03 六根保留，H04 的 1–5 脚走左后侧、6–8 脚走右后侧，**端点仍为同号对应，不能按空间左右重新编号**。

报告中最小保守净空：H04_4 与 H04_5 为 **0.3327 mm**；H04_2 与 Body_Upper 为 **0.4681 mm**。这两个数来自机械的有限采样、膨胀线体报告；本轮做的是来源与结果一致性检查，没有另行重跑全部 Blender 几何。其端子横向出线位置仍为假设，不是实际安装净空保证。

**后续身体装配检查为 FAIL。** 已接收 `fourteen_body_sequence.json`（SHA-256 `74ed4fdb…bc7acc`），对应同一十四线报告和 M1.47。在 407 个装配位置中，上壳及随壳运动的后板/插头包络会与部分 H04 线相交；两处桥螺钉工具通道为 PASS。静态 PASS 不覆盖这个失败。机械继续研究通道，未因此改变电路，也未批准裁线、固定、完整带线装拆或正式模型采用。

见 [可运行核对脚本](receive_and_check.py)、[接收及范围检查](receipt_and_range_checks.json)、[14 根逐针候选表](fourteen_static_candidates.csv)。表中几何线长**不是裁线长**，裁线长字段留空。`imu_wide_joint.json` 中“十四根联合检查待做”的旧文字，已由消费该精确文件 hash 的 `fourteen_validation.json` 后续结果覆盖；装拆、固定和服务余量仍未完成。

## 2. PH 端子与压接路线

| 候选线材 | 用途 | AWG | 厂家外径范围 mm | 按最大外径算 5D mm | SPH-002T-P0.5S 目录范围 |
|---|---|---:|---:|---:|---|
| Alpha 6712，颜色/包装后缀待定 | H01 两根 | 24 | 1.0414–1.1430 | 5.715 | PASS，仅范围筛查 |
| Alpha 6711，颜色/包装后缀待定 | H02/H03/H04 十二根 | 26 | 0.9144–1.0160 | 5.080 | PASS，仅范围筛查 |

Alpha 官网给出的弯曲参数为 5 倍外径；这里用于静态候选筛查，**没有取得反复弯折寿命额定**。不能把旧 5853/5854 的 10D 改成 5D，也不能把其他“同 AWG 硅胶线”套进这些路线。[Alpha 6711](https://www.alphawire.com/products/wire/ecogen/ecowire/6711)、[6712](https://www.alphawire.com/products/wire/ecogen/ecowire/6712)

当前 JST PH 目录将 SPH-002T-P0.5S 限定为 AWG30–24、绝缘外径 0.8–1.5 mm。两个候选的公差范围均落入其中，但尚无这两款 mPPE 线的压接高度、剥线长度、拉脱力和截面合格记录。低插拔力后缀 `P0.5L` 的压接高度与抗振条件不同，不能自行替代 `P0.5S`。[JST PH，PDF 第 2 页](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)

可识别的原厂工艺路线：

- 链带 SPH-002T-P0.5S：JST AP-K2N 压机、MKS-L 模具座与 APLMK SPH002-05S 配模；或 YRS-240 链带手工具。
- 原厂散装 BPH-002T-P0.5S：目录列 YRM-240 / WC-240；WC-240 有 24、26、28/30 AWG 三档。不得把剪下的链带端子自动当成已符合散装供料要求。
- EJ-PH 是退针工具，不是压接工具。厂家明确要求实际导线试压后检查拉力和端子变形；固定模具并不适配目录范围内的每一种绝缘结构。这些工具不批准一孔双线压接。

来源：[JST 工具目录，第 2、4 页](https://www.jst.fr/doc/jst/family/pdf/eTOOL-5A.pdf)、[JST WC-240](https://jst.co.uk/productSeries.php?cat=71&pid=10689)。本轮没有取得上述工具的国内报价，也没有把它们记为“已有”。

**建议的首台执行路线是让线束加工方完成规定料号的试压及成品线束，先报价再决定；不要求用户先购买专用压机/钳具。** [LCSC C111515](https://www.lcsc.com/product-detail/Housing-Contact_JST-SPH-002T-P0-5S_C111515.html) 能确认原厂 SPH-002T-P0.5S 的供应目录；页面还提供 [LCSC 定制线束入口](https://lcsccable.com/)，标示可小批量制作。但这**不能证明**加工方已有 Alpha 6711/6712、兼容配模或 MORI 的合格工艺。还需其书面回复完整线材、端子批次、压接工艺与价格。只核实到服务入口，没有上传项目、联系供应商或下单。

仅 H01–H04 的装机量：PHR-2 ×4、PHR-3 ×2、PHR-8 ×2、SPH 接点 ×28；不含报废/试压余量及其余线束。H03 两端第 3 孔留空。线材全后缀、分切小量供货、加工费、运费尚未定，不以每米摊销价假装可低价买到整卷。

## 3. J10 侧出线的实际出线位置仍缺依据

已复核公开 JST 外形图：PHR-8 端子节距 2 mm、跨针距 14 mm、壳宽 17.8 mm；S8B-PH-K-S 外宽 17.9 mm、侧出本体高 4.8 mm。公开图**没有标出压接后导线中心相对 PCB 表面的 Z 坐标及公差**。因此 A3 的 Z=2.4/3.0 mm 等敏感性算例不能任选一个通过值写成厂家尺寸。

[PHR-8 官方详细图/CAD 入口](https://www.jst-mfg.com/product/index.php?doc=2&filename=PHR-8.zip&series=199&type=10) 当前通过填写真实联系信息后邮件交付。没有提交表单、代填身份或取得受限文件。需要匹配 S8B-PH-K-S 的插合剖面：端子锁止位置、实际出线中心及容差、完全脱离行程、抓持/退针空间；CAD 本身也不能替代厂家尺寸/实测确认。

J10 C2 当前仍是 [布局候选](../prearrival_20261002/j10_refinement_C2/README.md)，受影响网络未完成重布线。其 ERC 0、DRC 26 个未连接项及 14 个警告的状态没有被本报告改变。A4 的四板 PH 孔径候选虽然 ERC/DRC 全零，电源 J10 仍是直出座，**不能把 A4 检查结果套给 C2**。

## 4. 原配电机线与屏幕 FFC

| 对象 | 本轮能确认的厂家信息 | 仍不能确定 |
|---|---|---|
| Unitree S288 | 手册注明随附 PH2.0 线；第 3 页定义 ①SIGNAL、②VCC、③GND，左右插口在外形图中呈镜像 | 精确壳/端子厂家料号、原线 AWG/外径/长度/弯曲与振动条件；不能据“PH2.0”认定 JST 原厂。J288/S288 共用手册的供电文字不改变 MORI 已有 9 V 设计 |
| FEETECH SCS0009 A/0，2020-11-23 | 第 4 页列 5264-3P、15 cm；表内 1=GND、2=VCC、3=TTL；第 8 页配套线/分线小板有照片 | 第 8 页示例原理图 P2/P5 却为 1=DATA、2=电源、3=GND。可能涉及视图/示例端口差别，但未得到厂家解释；完整配套壳端子、原线外径/AWG、反复弯折条件未知 |
| Waveshare LCD35079 随屏 FFC | 官网列 18P、0.5 mm、200 mm、同向触点；引脚功能沿用 A2 表 | 原线独立料号、总宽/厚度、补强、露铜、最小静态弯曲半径及动态寿命；“同向”不足以单独确认两块板的触点面/针 1 对应 |

来源：[Unitree 下载页](https://www.unitree.com/cn/mobile/download/DigitalServo/)、[FEETECH 原始 PDF](https://www.feetechrc.com/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf)、[Waveshare 产品页](https://www.waveshare.com/product/1.85inch-touch-lcd-module.htm)。关键页已保留本地 PDF/PNG，见 `sources/`。

电源板 J7/J8 的 1=GND、2=W_VM、3=W_BUS（轮电机总线），应按**功能**对应手册③、②、①；这是手册符号对应，不等于已验证压接壳孔号。J9 保持 1=GND、2=H_VM、3=H_BUS（头部总线），与 SCS0009 第 4 页功能对应，但供应端编号争议未解除。完整连接器视图和原配线导通关系确认前，不发电机线制造图。见 [适配及冲突表](vendor_harness_interfaces.csv)。

不能把 SCS0009 的电位器寿命或舵机摆动测试次数当作电缆弯折寿命。也不从照片颜色推断线规、载流或端子方向。

弯曲要求按实际运动关系划分：当前机械脚本把 CAM_Mainboard、Display_PCB 和 Camera_PCB 放在同一 pitch 运动组。**若线两端及固定点都随这个刚体运动，LCD FFC 不因转头本身变成反复弯折线**；首先应核对静态弯曲、固定和拆装。跨 body/yaw/pitch 相对运动的供电、串口与舵机线才需要相应动态服务环。不要因动态额定未知而把本可静态安装的 FFC 无条件改型，亦不能把跨关节线假定为静态。

## 5. 下一步的最少输入

已整理 [可发给供应商的资料询问稿](supplier_request_DRAFT_NOT_SENT.md) 和 [到货后的最小检查](acceptance_plan.csv)。均未发送，未制作线束。

1. JST 或匹配供应商：PHR-8 + S8B-PH-K-S 的完整插合/出线图，SPH002 + 指定 Alpha 线的工艺确认；国产线替代需完整型号、OD 公差与弯曲数据后重新筛查。
2. 线束加工方：这四条小量成品的可制作性、同号孔位图、工艺记录、报价和运费。长度目前只能评估几何范围，最终下料需补装拆/应力释放/服务余量。
3. FEETECH / Unitree / Waveshare：表中缺失线材资料，并澄清 SCS0009 的视图/编号。没有这些，不作动态线束及 J10 实际弯曲空间放行。

复核命令：`python3 hardware/v1_2/harness_evidence_20261002/receive_and_check.py`。本轮检查同时确认 249 个正式 KiCad 源文件 SHA-256 未变。未对未变 PCB 重跑 ERC/DRC；本报告没有新增制造数据。
