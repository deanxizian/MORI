# 来源与证据

访问日期2026-09-21。缓存和SHA256见sources/manifest.json；PASS只表示该文件下载成功，不证明规格、库存或实物通过。未能缓存ST文档的条目保留FAIL；资料核对使用厂家网页/源码并在实测前复核原版。

|ID|原始资料|缓存状态|
|---|---|---|
|motor|[motor](https://www.pololu.com/product/5216)|PASS|
|motor_specs|[motor_specs](https://www.pololu.com/product/5216/specs)|PASS|
|motor_alternative|[motor_alternative](https://www.pololu.com/product/5214/specs)|PASS|
|motor_drawing|[motor_drawing](https://www.pololu.com/file/0J1487/pololu-micro-metal-gearmotors-rev-6-1.pdf)|PASS|
|driver_module|[driver_module](https://www.pololu.com/product/2130)|PASS|
|driver_datasheet|[driver_datasheet](https://www.ti.com/lit/ds/symlink/drv8833.pdf)|PASS|
|imu|[imu](https://www.adafruit.com/product/4438)|PASS|
|imu_pinouts|[imu_pinouts](https://learn.adafruit.com/lsm6dsox-and-ism330dhc-6-dof-imu/pinouts)|PASS|
|imu_application|[imu_application](https://www.st.com/resource/en/application_note/an5272-lsm6dsox-alwayson-3d-accelerometer-and-3d-gyroscope-stmicroelectronics.pdf)|FAIL|
|esp_board|[esp_board](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide_v1.1.html)|PASS|
|esp_schematic|[esp_schematic](https://dl.espressif.com/dl/schematics/SCH_ESP32-S3-DevKitC-1_V1.1_20221130.pdf)|PASS|
|display|[display](https://www.waveshare.com/1.28inch-lcd-module.htm)|PASS|
|display_docs|[display_docs](https://docs.waveshare.net/1.28inch_LCD_Module/)|PASS|
|display_alternative|[display_alternative](https://docs.waveshare.com/1.46inch_Touch_LCD_Module)|PASS|
|servo|[servo](https://www.pololu.com/product/2818)|PASS|
|servo_datasheet|[servo_datasheet](https://www.pololu.com/file/0J1435/FS90-specs.pdf)|PASS|
|regulator|[regulator](https://www.pololu.com/product/2858)|PASS|
|current|[current](https://www.adafruit.com/product/904)|PASS|
|current_datasheet|[current_datasheet](https://www.ti.com/lit/ds/symlink/ina219.pdf)|PASS|
|battery|[battery](https://www.batteryspace.com/polymer-li-ion-battery-7.4v-2000-mah-14.8wh-4.2a-rate-with-pcb.aspx)|PASS|
|charger|[charger](https://www.batteryspace.com/Smart-Charger-1.2A-for-7.4V-Li-ion/Polymer-Rechargeable-Battery-Pack.aspx)|PASS|
|gate|[gate](https://www.ti.com/lit/ds/symlink/sn74hc08.pdf)|PASS|
|clamp_comparator|[clamp_comparator](https://www.ti.com/lit/ds/symlink/lm393.pdf)|PASS|
|clamp_reference|[clamp_reference](https://www.ti.com/lit/ds/symlink/tl431.pdf)|PASS|
|watchdog|[watchdog](https://www.ti.com/lit/ds/symlink/cd74hc123.pdf)|PASS|
|imu_datasheet|[imu_datasheet](https://www.st.com.cn/resource/en/datasheet/lsm6dsox.pdf)|FAIL|
|regulator_logic|[regulator_logic](https://www.pololu.com/product/2831)|PASS|
|estop|[estop](https://www.se.com/us/en/product/XB5AS8444/)|FAIL|
|motor25|[motor25](https://www.pololu.com/product/4863)|PASS|
|motor25_specs|[motor25_specs](https://www.pololu.com/product/4863/specs)|PASS|
|motor25_drawing|[motor25_drawing](https://www.pololu.com/file/0J1634/25d-metal-gearmotor-dimension-diagram.pdf)|PASS|
|motor25_datasheet|[motor25_datasheet](https://www.pololu.com/file/0J1829/pololu-25d-metal-gearmotors.pdf)|PASS|
|servo270|[servo270](https://www.dfrobot.com/product-1106.html)|PASS|
|encoder_level|[encoder_level](https://www.ti.com/lit/ds/symlink/sn74lvc14a.pdf)|PASS|
|ansmann_candidate|[ansmann_candidate](https://batterie-boutique.fr/media/d3/cd/ed/1762344143/2447-0105_Lithium-Ionen-Akkupack.pdf?ts=1762344143)|PASS|
|large_display|[large_display](https://www.displaymodule.com/products/2-4-inch-round-ips-high-brightness-display-480x480-octagon-with-mipi)|PASS|

选型取舍：小电机/FS90和大电池缓存保留用于审计，主配置以README/BOM为准。旧文件名micro-motor-rev-6-1.pdf的下载内容实际页脚为2026-02 Rev6.2；25D图纸为2019-02，完整电机曲线为厂家数据。SER0037宣传简介与规格表不一致，工程采用较低的规格表扭矩/电流及明确的270°位置控制定义。

ANSMANN技术信息PDF由厂家署名，托管在经销商域；信息页列出尺寸、容量、最大放电与认证名称，未提供完整BMS阈值/均衡/充电电流，因此这些项目没有被补造。CH-L7412SM与ANSMANN的匹配尚未确认。

预算中价格类型必须一起读；无中国交期承诺，没有执行购买。PCB原生规则和主机测试的证据由工具生成，所有真实电机/显示/头/温升/平衡记录为NOT_TESTED。

轴承补充核对：NSK官方[600系列目录](https://www.nsk.com/content/dam/nsk/am/pt_br/product/bearings-/ball-bearings/self--aligning-ball-bearings/guide.pdf)的686ZZ条目给出6×13×5mm、2.69g；[6805ZZ官方计算页](https://www.oss.nsk.com/mea/calculation/calculate/index/sku/6805ZZ-APN/)给出25×37×7mm。2026-09-21读取官网搜索索引结果；整份目录16.25MB超过web读取上限、产品页超时，未冒充完整缓存成功。尺寸用于候选筛选，公差/实际样品和具体订货后缀待采购确认。
