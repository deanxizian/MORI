# 本次官方资料核对

检索日期：2026-10-03（Asia/Shanghai）。用于核对已有选型，不是采购批准。

- [CAM33700 官方文档](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx)：核对 24PIN 摄像头和 18PIN 屏幕接口；页面区分 V1 / V1.1，不能把型号相同当作购入版次相同。已保存本次页面及 SHA256。
- [CAM FAQ](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/FAQ)：本次可读取内容没有提供原配 OV3660 完整 FPC 尺寸。不是对所有厂家资料的穷尽性结论。
- [LCD35079 官方文档](https://docs.waveshare.com/1.85inch_Touch_LCD_Module)：核对 18PIN 外接 FPC 插座位置。官方接口图保存为 `sources/lcd_connector_photo.webp`；对应实际 STEP 的 Connector_108。中央 Connector_107 为屏本体内部连接。
- [LCD 官方产品页](https://www.waveshare.com/product/1.85inch-touch-lcd-module.htm)：搜索摘要与既有 A5 接收证据均列出随屏 18PIN、0.5mm、200mm、同面接触排线。直接打开本次返回 403，未声称重新取得完整产品页；宽厚、弯曲半径、CAM 配对方向仍未核实。
- 本次官方域名检索词：`ESP32-S3-CAM-OV3660 camera FPC length extension`、`OV3660 排线 长度 ESP32 S3 CAM`、`OV3660 extension cable length`。没有找到可据以冻结完整原配排线长度的结果。没有用其他厂家的 OV3660 排线或通用 24PIN 延长线替代原配证明。

网页获取记录见 `sources/retrievals.json`。原有 CAM 官方照片及原理图仍以 `mechanical/sources/waveshare_detail/source_manifest.json` 的文件/哈希为准。照片可以辅助定位和估计外形，不能证实隐藏排线长度、插座出线方向或电气兼容性。

当前剖面使用保存模型及其明确的接插件检查代理；读前启用了 Blender 的隐藏检查集合，以便正确求出当前屏幕倾角的世界坐标。没有更改主场景。先前固定线研究和主校核已采用同样的检查集合启用方式。
