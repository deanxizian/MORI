# 供应商按图制作：补充资料检索结果

2026-10-03。用户已确认供应商按图制作，见 [决定记录](DECISION.md)。本页记录新取得的证据和检索边界；未更改 M1.47 主模型、正式硬件或原硬件交接清单。

## 新找到并已检查

### SCS0009 系列 STEP

[Robotopian 的 SCS0009 资料页](https://robotopian.com/products/feetech-scs0009-servo-motor)实际链接到 `SCS009-20230110-S.stp`。下载文件约 2.3 MB，内部顶层名称为 `SCS009-20201118-S_ASM`，子装配名称包含 `SCS0009-20201118-S_ASM`。毫米单位、未缩放，OCP 读取到 4 个有效实体：上壳、中壳、底壳和输出齿轮。**没有配套舵盘、中心锁紧螺钉或完整线缆。**

同页 PDF 与项目已用的飞特 SCS0009 A/0 规格书 SHA256 完全一致。这加强了型号关联，但不能证明 STEP 的厂家原始来源或采购版次。参考件分类为 PURCHASED_REFERENCE；对当前实际采购件的完整匹配仍为 ASSUMED。

独立 CAD 包络中，壳体宽约 12.101 mm、底壳长约 23.301 mm、安装耳总跨度约 32.500 mm；包含输出齿的轴向总高度约 28.510 mm，原图重建值为 28.45 mm。齿轮箱最高点按同一底面计约 25.610 mm，与原图重建 25.25 mm 不同。不能在未核实这些差异前宣称完全相同并替换主模型。

[检查记录](servo_step_inspection.json) · [独立预览](servo_reference.png) · [原 STEP](sources/SCS009-20230110-S.stp)。检查脚本递归记录局部零件，同时另按完整装配变换导出世界坐标；局部输出齿轮坐标不能直接当整机装配坐标。

### JST SH 预压接线厂家图

取得 [GAM-050 图纸](https://gam-gec.com/wp-content/uploads/2018/10/GAM-050.pdf)，图框为 JST，装配料号 `ASSHSSH28K152`，最新可见更改为 2018-07-02。已检查整页原图，文件保存在 `sources/JST_GAM-050.pdf`。

- 两端端子：SSH-003T-P0.2-H；线材：UL1571、28 AWG、BLACK-BCD。
- 图示线内长度 152.4±5.0 mm；端到端参考长度 160.2±5.0 mm。不能混用两个长度基准。
- 适用壳体表列出 SHR-04V-S 和 SHR-04V-S-B。
- 图纸没有给出绝缘外径、公差、弯曲半径或动态寿命，也没有证明 CAM 板上的实际插座就是对应 JST 原厂料号。

因此它是供应商定长压接的**具体参考规格**，不再只有泛称“SH 线”。不是选用 152.4 mm 作为 MORI 最终长度，也未以它替换研究用 Alpha5853 并重新宣布动态线合格。该图及本次选择已补交硬件对话，等待线径/压接和实际插座核对。

## 找到入口，但未取得文件

2026-10-04 补查 SH 系列：官方也明确列出 `CHM-1-2389.pdf / CHM-1-2146.pdf` 专用手册、`SSH-003T-P0.2-H.pdf` 端子图，以及 `SHR-04V-S` 的 STEP 和尺寸图。四个链接实际均返回邮件申请页，尚未取得文件内容。详见[SH 详细资料获取状态及请求记录](recheck_20261004/SH_DETAIL_ACCESS.md)。这属于已找到入口、需要按厂家方式取得文件；不能写成资料不存在，也不能用通用手册替代专用入壳说明。

[JST 官方 PH 产品页](https://www.jst-mfg.com/product/index.php?lang=2&series=199)确有 `PHR-8`、`S8B-PH-K-S` 的逐型号 IGES、STEP、3D-PDF 和 2D-PDF 条目。页面链接的 doc=1 为 IGES、doc=2 为 STEP、doc=3 为 3D-PDF、doc=4 为 2D-PDF。

实际打开下载条目返回资料申请表。页面说明自 2025 年 4 月改用邮件附件发送，必填公司、部门、姓名、地址、电话和邮箱；没有直接返回 CAD。本次保存的是申请页 HTML，不是假称已取得 STEP。未提交用户资料、未绕过申请流程。公开 PH 系列目录可继续用于已有尺寸重建；最终插合止挡、实际出线与夹持空间仍不能标为完成。

## 本次仍未取得的关键资料

- **匹配 SCS0009 的原配舵盘**：新 STEP 不含舵盘；规格书仍为 A/0、配件页无完整舵盘图。飞特官方产品页的正文 25T 与表格 20T/3.95 mm 仍冲突。官方资料入口可用 HTTP 读取，公开产品资料查询本次对 SCS0009、009、SC-0090、舵盘均返回 0 条；不是证明厂家不存在资料。原官方 PDF、Seeed 镜像和 Switch Science 镜像均未提供所需完整舵盘尺寸。Pollen 的 AmazingHand 仓库有 custom_servo_horn 模型，但属于该项目的改制件，不能替代原配舵盘图。
- **CAM33700 原配 OV3660 完整 FPC**：[官方中英文文档](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx)、[资源页](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)及[官方商品资料](https://www.waveshare.com/product/arduino/boards-kits/esp32-s3-cam-ov5640.htm)可核对接口/套装/镜头信息；本次未找到能冻结完整 FPC 长度、厚度、补强板和接触面的图纸。资源页硬件部分列的是 V1/V1.1 原理图，没有完整相机 FPC 尺寸文件。其他 OV3660 或 Raspberry Pi 相机排线不构成此 SKU 的兼容证明。
- **BaneBots T81H-RM61 轮毂完整图**：[官方页面](https://banebots.com/t81-hub-6mm-shaft/)给出 6 mm 轴、紧定螺钉和卡簧信息，但页面实际 Quick Reference 链接本次返回 404。既有轮胎外包络研究仍有效，真实轮毂接口不因此放行；未绕过 3D 查看器下载限制。

这些是资料问题，不能笼统归为只能等实物。已取得的文件用于继续设计和询证；未取得的字段继续留在问题单，到货后的配合、压接、活动寿命和结构强度仍需验证。

## 复核范围

- 源文件 URL、响应类型和 SHA256 见 retrievals.json、retrievals_addendum.json 及 delivery.json。
- OCP 实体有效性 PASS 只说明这份参考 CAD 可读取，不说明型号完全一致、负载合格或采购放行。
- 仅更新选择、来源和独立参考预览；主模型及已交硬件的 HEAD_HARNESS_REQUIREMENTS.md 哈希保持。
