# JST SH 详细图纸与手册的实际获取状态

2026-10-04 复核。公开的[SH 系列目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)已经取得并用于名义外形研究；以下详细文件在[官方产品页](https://www.jst-mfg.com/product/index.php?lang=2&series=231)有明确条目，不能描述为“厂家没有资料”。

| 条目 | 页面列出的文件 | 本次实际取得 |
|---|---|---|
| SH 专用手册 | CHM-1-2389.pdf、CHM-1-2146.pdf | 邮件申请页 HTML，未取得手册内容 |
| SSH-003T-P0.2-H 端子图 | SSH-003T-P0.2-H.pdf | 邮件申请页 HTML，未取得该逐型号图 |
| SHR-04V-S 胶壳 STEP | SHR-04V-S.zip | 邮件申请页 HTML，未取得 STEP |
| SHR-04V-S 胶壳尺寸图 | SHR-04V-S.pdf | 邮件申请页 HTML，未取得该逐型号图 |

申请页说明自 2025 年 4 月改为邮件附件发放，并要求公司、部门、姓名、地址、电话及邮箱。本次只读取页面，没有提交这些信息或联系厂家。另检索 JST 日本、美国和德国官方站点，未找到本次可直接取得的两份 SH 专用手册；通用操作注意事项不替代专用手册。

[请求及响应哈希记录](JST_SH_detail_access.json) · [实际申请页](JST_SH_manual_request.html) · [可重跑的只读检查脚本](../check_SH_detail_access.py)。PASS 只表示四个入口及访问方式核对成功，不表示已得到文件内容、实际互配合格或制造放行。

微雪的[CAM Rev1.1 原理图](https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-OVxxxx_Rev1.1.pdf)使用通用 SH1.0 4P 描述，未给出 J11 的完整制造商料号。取得 JST 图纸之后，仍需确认实际板端是否对应这个配套系列，不能仅凭 1 mm 间距代替确认。

项目的定制线长、分支、固定点和装配步骤由机械设计继续完成。[四根 CAM 导线的连续成形和空胶壳外部接近路线](../../harness_A8/cam_wire_forming/lifted_end2/index.html)已完成限定范围的数字检查；端子入壳、锁舌、实际抓持和完整线束仍未关闭。
