# 模块与厂家资料

这里是验证车清单，不修改主项目的 `contracts/components.json`。没有整理价格、库存或下单状态。

| 模块 | 数量 | 来源与尺寸依据 | 当前用途 |
|---|---:|---|---|
| Raspberry Pi 4B | 1 | 官方机械图；装配外形为第三方参考 STEP，不能视为全部官方 CAD | 本机平衡计算、USB、I²C、SSH |
| Unitree S288 | 2 | 官方 STEP / J288-S288 手册 | 两轮驱动，当前 ID 0 / 1 |
| Unitree USB 单总线调试板 | 1 | 官方接口说明；用户量板边 30 × 40 mm、USB 所在短边 30 mm、无孔；细部照片估算 | USB 至 6 Mbps 半双工 TTL |
| Waveshare UPS Module 3S + 18650 | 1 套 / 3 节 | 官方简化 STEP / 原理图；保护盖、焊脚和电芯完整尺寸未由简化模型证明 | 车载电池、5 V 输出、BAT 输出、充电 |
| DFRobot Fermion BMI323 SEN0693 | 1 | 官方 STEP / 图纸，16 × 16 mm、两孔距 11 mm | 六轴姿态输入，无需磁力计 |
| DFRobot FIT0500 橡胶轮胎 | 2 | [原产品](https://www.dfrobot.com/product-1535.html)；用户原轮圈 Ø72.5 / Ø64 为配合参考 | 套在打印轮圈外 |
| Waveshare ESP32-S3-CAM-OV3660（33700） | 1 | [产品](https://www.waveshare.net/shop/ESP32-S3-CAM-OV3660.htm)；详细外形含照片估算 | 屏幕、音频及原配 OV3660 |
| Waveshare 1.85 英寸圆形触摸屏（35079） | 1 | 原厂 CAD，原尺寸保留 | 当前第二层平放显示 |
| CAM 附赠喇叭 | 1 | 用户粗量 26 × 26 ×约 3.5 mm，具体 SKU 未知 | 屏幕下方背胶固定 |
| Waveshare DC BUCK Adapter 6 V | 1 | [产品](https://www.waveshare.net/shop/DC-BUCK-Adapter-6V.htm)；CAD 用 7.2 V 同系列参考，6 V 版本外形一致性未实测确认 | 预留头部供电，当前两层无头部舵机负载 |
| Raspberry Pi Camera Module 3 Wide 彩色版 | 1，可选 | 官方 Wide STEP，镜头为 IMX708 Wide；已枚举和单张拍照 | 独立 CSI 摄像头、R59/R60 支架 |

选用模块的原始 PDF/厂家 CAD 包见 [specifications](specifications/)。[来源清单](specifications/source_manifest.json)保留下载日期、URL、字节数和 SHA-256；这些是当时的厂家资料，不宣称本次重新查验了最新修订。未重新发布已取消的独立急停选型资料，也没有把原厂 STEP 简化件扩展成实测完整装配。

Camera Module 3 至 Pi 4B 用 15-pin / 1.0 mm CSI 排线；CAM33700 的 OV3660 为其板载 DVP 相机连接，不能因为叫“摄像头排线”就互换。延长线还需确认端子数量、间距、触点方向和长度；本包不冻结未来头部排线方案。

本包保留平衡控制和有限实测证据。其他会话的云语音凭据、私人录音/照片、蓝牙配对资料、CAM 构建缓存和全部云交互工程未纳入；不把第二层部件在模型中出现等同于提供了所有应用固件的一键部署包。
