# MORI 硬件 BOM 与立创购物车核对

核对日期：2026-09-23（北京时间），按1台MORI。主BOM共97行，含成品模块、器件、机械件、服务、运费和待选型项。

新增 **66种**，保留原购物车 **4种**，合计 **70种**。购物车显示 **¥550.12**，其中本次新增 **¥355.29**；65种现货、4种订货、1种原有海外代购。没有结算、提交订单或付款。

单机用量和购物车数量分别列出；后者按商城起订量/增量增加。订货项当前无现货，显示金额与交期不构成最终报价；邮费未核。

## 文件

- [完整97行BOM及采购结果](MORI_单机硬件BOM_含采购结果.csv)
- [立创实际导出购物车Excel](立创商城购物车详情_20260923.xls)
- [购物车明细CSV](立创购物车明细.csv)
- [机械物料明细，含打印件与占位件](MORI_机械物料明细_含占位件.csv)
- [结构化核验和选型更正](procurement_result.json)

## 选型更正

电源板U20、U40：**LM393BDR → TI LM393BIDR（C2865059）**。采用LM393B的完整可订货料号，保留SOIC-8封装。原生符号8个引脚与TI资料逐项一致：1OUT1、2IN1−、3IN1+、4GND、5IN2+、6IN2−、7OUT2、8VCC。单机2个，商城5个起，已加入5个。台架验证为NOT_TESTED。[TI订货信息](https://www.ti.com.cn/product/cn/LM393B/part-details/LM393BIDR) · [TI数据手册，第3页引脚表](https://www.ti.com/lit/ds/symlink/lm393b.pdf)。

“本次采购选型”列是本任务采用的采购BOM。P5由另一任务继续布局，本次没有覆盖原生KiCad、contracts/components.json或原设计BOM；U20/U40的完整订货号待硬件任务同步，电路与封装无意改变。四块P5导出的位号/元件值与P4比较无差异；源文件哈希已保存。

AO3400A / AO4407A采用原选型AOS，分别为C20917 / C16072。没有加入自动匹配的UMW同名替代料。商城RC0603电阻料号多一个连字符，是格式差异，未更改阻值或封装。

## 非现货与缺项

|项目|实际处理|
|---|---|
|PESD5V0L1BA,115 / C85380 ×5|购物车订货区；搜索页有订货渠道，当前无现货，数量、价格、交期需商家最终核价。|
|EEUFR1C102 / C407878 ×2|购物车订货区。|
|MS-202V-G3 / C42378287 ×1|购物车订货区；保留既定后板开关的机械接口。|
|AC05000001009JAC00 / C1575735 ×5|购物车订货区；外接10Ω泄放电阻，脉冲与散热未实测。|
|CMS-4017-34SP ×1|原购物车海外代购，页面交期8–14个工作日，保留原项。|
|AC05000005608JAC00 ×1|未取得可加入购物车的商品编号和报价；这是外接5.6Ω泄放电阻。|
|开发板、摄像头/显示模块、舵机、Pololu模块|按用户后续要求停止继续商城搜索，仍保留在整机BOM。|
|电池、充电器、外置保险座、未定线束/排母、紧固件|精确规格尚未确定，保留BLOCKED，未按占位参数购买。|
|自制PCB、打印、金属加工、贴装|没有提交制造订单。|

全部59类PCB散件、ICM芯片、TPS54302、后板开关及6类PH线束端子都有对应购物车项，其中3类板载器件为订货。开发板U100单列。DNP的电源J6、数量为0的独立功能按钮不计入购买数量。CAM板载麦克风、codec、功放不重复购买。

整机仍是PROTOTYPE / UNVALIDATED。当前购物车未覆盖全部电机、开发板、电池、加工和运费，不能据此宣称整机≤1000元。

## 整机模块、机构及服务

|ID|项目/型号|单机数量|采购结果|
|---|---|---:|---|
|wheel_servo|Unitree YS-342026-S288|2|按用户后续要求：开发板/成品模块不继续商城搜寻|
|head_servo|FEETECH SCS0009|2|按用户后续要求：开发板/成品模块不继续商城搜寻|
|motion_mcu|WeAct STM32F4 64Pin CoreBoard V1.1 / STM32F412RET6|1|按用户后续要求：开发板/成品模块不继续商城搜寻|
|body_imu|TDK ICM-42688-P / MORI_imu_P4 daughterboard|1|原购物车已有 / C1850418|
|interaction_cam|Waveshare ESP32-S3-CAM-OV3660 / SKU33700|1|按用户后续要求：开发板/成品模块不继续商城搜寻|
|display|Waveshare 1.85inch Touch LCD Module / SKU35079|1|按用户后续要求：开发板/成品模块不继续商城搜寻|
|speaker|Same Sky CMS-4017-34SP（机械选型/购物车原有）|1|原购物车已有 / D2884871|
|battery|成品3S 2200–2600mAh电池组（未选定）|1|BLOCKED：精确型号或规格待定|
|battery_protection|与成品3S匹配方案；随包则合并价格，当前未知|1|BLOCKED：精确型号或规格待定|
|usb_charge|UNSELECTED finished3S USB-C CC/CV module|1|BLOCKED：精确型号或规格待定|
|wheel_power|Pololu D36V50F9 #4094 9V buck (engineering reference)|1|按用户后续要求：开发板/成品模块不继续商城搜寻|
|head_power|Pololu D24V22F6 #2859|1|按用户后续要求：开发板/成品模块不继续商城搜寻|
|logic_power|TPS54302DDCR|2|本次已加入 / C311983|
|lcd_cable|Waveshare LCD35079 supplied FFC18P 0.5mm 200mm same-side contacts|1|随LCD供货清单；未另购|
|user_button|C&K PTS645SL50SMTR92LFS candidate + printed cap|0|NOT_APPLICABLE：数量0|
|physical_disable|SOFNG MS-202V-G3|1|本次已加入 / C42378287|
|tyres|Ø105×18轮胎/胎圈（机械要求，具体商品未选）|2|BLOCKED：精确型号或规格待定|
|wheel_couplers|M1.14 custom metal flanged shaft / double-D hub interface, candidate|2|BLOCKED：精确型号或规格待定|
|wheel_bearings|686ZZ candidate; exact manufacturer/order suffix pending|4|BLOCKED：精确型号或规格待定|
|head_bearings|yaw32OD/20ID、pitch12OD/5ID试配方案|1|BLOCKED：精确型号或规格待定|
|carrier_pcb|MORI_motion_P4 + MORI_imu_P4 + MORI_power_P4 + MORI_rear_P4|1|定制制造/服务/运费；未下单|
|harness|额定线规/防呆端子/压接/应力释放待选|1|BLOCKED：精确型号或规格待定|
|fasteners|机械装机套件待核量|1|BLOCKED：精确型号或规格待定|
|printing|按机械体积/填充/损耗核量|1|定制制造/服务/运费；未下单|
|shipping|实际店铺合单/地址结算待核|1|定制制造/服务/运费；未下单|
|usb_adapter|UNSELECTED: dependent on qualified3S charger|1|BLOCKED：精确型号或规格待定|
|usb_charge_cable|UNSELECTED: dependent on qualified3S charger|1|BLOCKED：精确型号或规格待定|
|p1_dump_wheel|Vishay AC05000005608JAC00 candidate|1|BLOCKED：未获得可加购编号/报价（外接5.6Ω泄放电阻）|
|p1_dump_head|Vishay AC05000001009JAC00 candidate|1|本次已加入 / C1575735|
|p4_external_master_fuse|6.3A DC inline fuse + holder; exact part UNSELECTED|1|BLOCKED：精确型号或规格待定|
|p4_assembly_service|Qualified small-batch double-sided PCBA service; quote pending|1|定制制造/服务/运费；未下单|
|p4_motion_module_sockets|WeAct V1.1 matching socket/header set; exact MPN/stack height UNSELECTED|1|BLOCKED：精确型号或规格待定|

## PCB散件与PH线束端子

|ID|商城型号|厂家|单机用量|立创编号|购物车数量|渠道|显示小计¥|
|---|---|---|---:|---|---:|---|---:|
|p4_001|0451001.MRL|Littelfuse(美国力特)|1|C3099|5|现货|7.72|
|p4_002|0451002.MRL|Littelfuse(美国力特)|1|C99547|5|现货|10.5|
|p4_003|045101.5MRL|Littelfuse(美国力特)|1|C185113|5|现货|8.78|
|p4_004|61300211121|Wurth(伍尔特)|2|C2915055|5|现货|3.84|
|p4_005|XT30UPB-M|AMASS(艾迈斯)|7|C428721|10|现货|16.11|
|p4_006|AO3400A|AOS|4|C20917|5|现货|2.6|
|p4_007|AO4407A|AOS|4|C16072|5|现货|9.97|
|p4_008|B2B-PH-K-S(LF)(SN)|JST|9|C131337|20|现货|4.33|
|p4_009|B2B-XH-A(LF)(SN)|JST|1|C158012|20|现货|4.97|
|p4_010|B3B-PH-K-S(LF)(SN)|JST|2|C131339|10|现货|2.76|
|p4_011|B3B-XH-A(LF)(SN)|JST|3|C144394|10|现货|3.33|
|p4_012|B4B-PH-K-S(LF)(SN)|JST|2|C131334|10|现货|2.79|
|p4_013|B540C-13-F|DIODES(美台)|2|C72264|5|现货|7.1|
|p4_014|B8B-PH-K-S(LF)(SN)|JST|4|C157974|5|现货|2.88|
|p4_015|BAT54H,115|Nexperia(安世)|3|C426769|5|现货|4.42|
|p4_016|BZT52H-C10,115|Nexperia(安世)|4|C179379|20|现货|4.39|
|p4_017|CL10A105KA8NNNC|SAMSUNG(三星)|1|C5673|50|现货|8.46|
|p4_018|CL10A106KP8NNNC|SAMSUNG(三星)|1|C19702|20|现货|3.91|
|p4_019|CL10A225KP8NNNC|SAMSUNG(三星)|1|C1607|20|现货|2.45|
|p4_020|CL10B103KB8NNNC|SAMSUNG(三星)|6|C1589|50|现货|3.13|
|p4_021|CL10B104KB8NNNC|SAMSUNG(三星)|12|C1591|100|现货|5.77|
|p4_022|CL32B226KAJNNNE|SAMSUNG(三星)|8|C309062|8|现货|17.37|
|p4_023|EEUFR1C102|PANASONIC(松下)|2|C407878|2|订货|11.3|
|p4_024|GRM1885C1H750JA01D|muRata(村田)|2|C426100|20|现货|4.18|
|p4_025|GRM188R71H104KA93D|muRata(村田)|5|C77055|50|现货|5.17|
|p4_026|INA180A1IDBVR|TI(德州仪器)|1|C122228|5|现货|8.8|
|p4_027|LM393BIDR|TI(德州仪器)|2|C2865059|5|现货|3.49|
|p4_028|MMBT3904LT1G|onsemi(安森美)|1|C81464|50|现货|5.07|
|p4_029|PESD5V0L1BA,115|Nexperia(安世)|2|C85380|5|订货|3.11|
|p4_030|RC0603FR-07100KL|YAGEO(国巨)|2|C14675|100|现货|1.24|
|p4_031|RC0603FR-07100RL|YAGEO(国巨)|2|C105588|100|现货|1.86|
|p4_032|RC0603FR-0710KL|YAGEO(国巨)|14|C98220|100|现货|2.07|
|p4_033|RC0603FR-071KL|YAGEO(国巨)|5|C22548|100|现货|2.09|
|p4_034|RC0603FR-072K2L|YAGEO(国巨)|4|C114662|100|现货|1.51|
|p4_035|RC0603FR-0733RL|YAGEO(国巨)|4|C108661|100|现货|1.99|
|p4_036|RC0603FR-0747KL|YAGEO(国巨)|1|C105579|100|现货|1.86|
|p4_037|RC0603FR-0747RL|YAGEO(国巨)|1|C114623|100|现货|2.81|
|p4_038|RC0603FR-0768RL|YAGEO(国巨)|2|C126362|100|现货|3.71|
|p4_039|RC0603JR-070RL|YAGEO(国巨)|2|C95177|100|现货|1.67|
|p4_040|RT0603BRD07100KL|YAGEO(国巨)|4|C122538|20|现货|3.58|
|p4_041|RT0603BRD0710KL|YAGEO(国巨)|4|C95204|20|现货|3.78|
|p4_042|RT0603BRD0713K3L|YAGEO(国巨)|2|C861117|20|现货|4.52|
|p4_043|RT0603BRD0716K5L|YAGEO(国巨)|1|C728584|10|现货|3.65|
|p4_044|RT0603BRD0718K7L|YAGEO(国巨)|1|C705732|20|现货|4.3|
|p4_045|RT0603BRD071ML|YAGEO(国巨)|2|C326730|10|现货|3.36|
|p4_046|RT0603BRD0727KL|YAGEO(国巨)|2|C309651|20|现货|3.63|
|p4_047|RT0603BRD0733K2L|YAGEO(国巨)|1|C705767|20|现货|4.31|
|p4_048|RT0603BRD0737K4L|YAGEO(国巨)|1|C326727|20|现货|5.59|
|p4_049|S5B-PH-K-S(LF)(SN)|JST|1|C157923|10|现货|4.74|
|p4_050|SMF24A|Littelfuse(美国力特)|1|C315999|5|现货|6.09|
|p4_051|SN74LVC1G74DCUR|TI(德州仪器)|1|C70285|5|现货|9.09|
|p4_052|SN74LVC2G125DCUR|TI(德州仪器)|2|C21404|5|现货|6.35|
|p4_053|SN74LVC2G32DCUR|TI(德州仪器)|1|C91874|1|现货|3.36|
|p4_054|SRP7050TA-100M|BOURNS|2|C2041441|2|现货|17.44|
|p4_055|TL431BIDBZR|TI(德州仪器)|2|C41283|5|现货|2.42|
|p4_056|TLV803EA29DBZR|TI(德州仪器)|1|C1852114|1|现货|2.74|
|p4_057|TXU0202DCUR|TI(德州仪器)|1|C5186957|1|现货|4.84|
|p4_058|TYPE-C-31-M-12|韩国韩荣|1|C165948|5|现货|5.26|
|p4_059|WSL2512R0100FEA|VISHAY(威世)|1|C844901|5|现货|10.25|
|p4_phr_2|PHR-2|JST|9|C157955|50|现货|4.05|
|p4_phr_3|PHR-3|JST|2|C265393|50|现货|5.48|
|p4_phr_4|PHR-4|JST|2|C111514|50|现货|5.16|
|p4_phr_5|PHR-5|JST|1|C265394|50|现货|6.31|
|p4_phr_8|PHR-8|JST|4|C157950|20|现货|3.55|
|p4_ph_contacts|SPH-002T-P0.5S|JST|69|C111515|100|现货|5.24|

## 核验记录

- 从已登录购物车读取初始4项，逐项加入66项并核对商品编号和数量；原有数量不变。
- 通过购物车“更多操作 → 导出至Excel”下载70项明细。与采购BOM一对一对应，行金额合计¥550.12，和购物车显示一致。
- 初始自动匹配错误包含其他厂家的同名MOS管、裸芯片代替开发板、SKU编号误作数量。这些错误项没有加入购物车；云端原始草稿已重命名“含误匹配，勿下单”并全部取消勾选。
- 源文件：hardware/v1_2/bom.csv、四块P5 assembly_bom.csv、两个contracts文件、mechanical/reports/bom.csv；读取哈希见source_hashes.json。
- 工具：Codex浏览器UI、Python csv/json/hashlib、xlrd 2.0.2。解析依赖放在/tmp/mori_bom_pydeps，未改变项目依赖。
- 重建命令：PYTHONPATH=/tmp/mori_bom_pydeps python3 hardware/v1_2/procurement/lcsc_cart_20260923/build_report.py。
- 未修改电路/布局，没有重新运行ERC/DRC；购物车准备不等于硬件资格验证。
