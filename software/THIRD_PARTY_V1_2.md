# V1.2 第三方来源与版本

完整commit和许可文件SHA256：`software/references_v1_2.lock.json`；保留V1来源 `refs/sources.lock.json` 与根 `THIRD_PARTY_NOTICES.md`。这里描述采用的版本，不声称它们是所有上游的最新版。

| MORI文件/构建内容 | 上游与采用文件 | 用法 / 许可 |
|---|---|---|
| motion/v1_2/s288.c、simulation/s288_replay.py | [Unitree digital_servo](https://github.com/unitreerobotics/digital_servo/tree/75c1ed63579dc7bb759e2990bd4b804c11b57daf) App/protocol.h/.c、crc_ccitt.h、specs/protocol.md、python/servo_demo.py | 显式独立序列化；差分测试编译原厂C。README限定非商业研究/教育/DIY，商业大批量生产需原厂正式授权；不改标MIT、不宣称商业发布许可完备 |
| motion/v1_2/sensors.c SCS部分 | [FTServo_Arduino](https://github.com/ftservo/FTServo_Arduino/tree/64922cda46e56b21b8c1d9e830d936a1941645ae) src/SCSCL.cpp/.h、SCS.cpp | 按寄存器/字节序独立解析，参考MIT，©2024 ftservo |
| STM32 startup/system/device headers | ST cmsis-device-f4 v2.6.10，commit5f41fb29d22773896c780052bf61e47fc924d524 | 原文件编译/包含；Apache-2.0 |
| STM32 HAL system/RCC/GPIO/DMA/UART/SPI | ST stm32f4xx-hal-driver v1.8.3，commitc2e1406d7ea4b73aa42b98ddeb75a8670b1a5a16 | 原文件编译；BSD-3-Clause；没有复制Unitree整套STM32应用 |
| Cortex-M4 core header | ARM CMSIS_5 tag5.9.0，commit2b7495b8535bdcb306dac29b9ded4cfb679d7e5c | 原文件包含；Apache-2.0 |
| interaction/main/board_v12.c | [微雪CAM官方例程](https://github.com/waveshareteam/ESP32-S3-CAM-OVxxxx/tree/72af9302030bb6f018d5c21b1225005481e09fda) ESP-IDF-v5.5.1/04_dvp_camera_display BSP header/codec初始化参考 | MORI门控API适配；Apache-2.0参考；未复制演示main/固定引脚/整套GUI |
| interaction/managed_components | esp32-camera2.1.4、esp_lcd_st77916 1.0.1、esp_codec_dev1.5.4、custom_io_expander_ch32v003 1.0.1及锁定依赖 | 原组件，许可随包保留；主要Apache-2.0，完整依赖SHA见dependencies.lock |
| 两端双眼C/TS | 原bloub参考与MORI8状态映射 | V1已保留MIT通知；代码许可不授予xAI形象/商标权；皮肤可替换 |
| ESP-SR2.2.0/LVGL9.2.2/小智兼容协议 | 原V1锁文件与通知 | 未拼接三套应用main；ESP-SR特定许可、唤醒模型权利按原文件保留 |

原厂资料：[S288产品页](https://www.unitree.com/mobile/DigitalServo/)标称0.6Nm为反向工况最大/堵转，不能当连续扭矩；[TDK ICM42688-P v1.6](https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/ds-000347-icm-42688-p-v1.6.pdf)用于WHO/burst/量程核对；[ST77916 1.0.1](https://components.espressif.com/components/espressif/esp_lcd_st77916/versions/1.0.1/readme)和[codec1.5.4](https://components.espressif.com/components/espressif/esp_codec_dev/versions/1.5.4/readme)在本SDK中实际编译。组件可编译不证明板上线路/并发/实时性。

Arm工具链原厂下载并校验SHA256，记录在 reports/v1_2/arm_toolchain.json；执行版本14.2.1（14.2.Rel1发布）。未改用无界latest。

参考仓库按锁文件下载在refs/v1_2，.gitignore不默认把整个参考仓库纳入MORI分发。未来对外发布/销售需复核采用文件与模型/形象的实际权利；本轮不发布或代签授权。
