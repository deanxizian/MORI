# 公开资料补查：2026-10-04

线束制作方式已确定为供应商按图制作。公开资料由项目继续检索；路线、固定点、分支和长度基准由机械设计提供。

| 项目 | 本次实际取得或确认 | 尚缺的具体字段 |
|---|---|---|
| JST SH / PH | 两份官方目录再次成功下载，包含胶壳、端子、适用线径及安装参考尺寸；既有逐型号压接数据仍保留其来源版本限制 | CAM 板实际原厂料号、真实互配与针腔视图；具体线材和工具的工艺确认 |
| FEETECH SCS0009 | 官网当前正文仍写 25T，参数表仍写 20T/OD3.95 mm，公开信息矛盾并未消失 | 当前采购版次对应的舵盘料号、完整尺寸、有效啮合和轴向叠层 |
| WeAct V1.1 | 当前官方 Git 树已完整读取，未截断；Hardware 仍只有 STEP、板框 PDF、原理图 PDF 和 V1.0 历史版本 | 成品孔径及公差、实际排针型号和有效插接长度；不能靠官方 STEP 中的相交消除这些问题 |
| BaneBots T81H | 产品页的 Quick Reference 链接仍失败；补查站点根目录的 HTTPS/HTTP 文件地址也均为 404 | 完整轮毂接口图；未取得的文件没有标成已下载 |
| Waveshare CAM33700 | 官方资源页成功下载，硬件资源列 V1/V1.1 原理图 | OV3660 随附完整 FPC 的机械尺寸及补强板、接触面数据 |

本次没有取得能关闭舵盘、相机 FPC、WeAct 成品孔或轮毂接口问题的新图纸；这是本次检索结果，不代表厂家不存在这些资料。

官方来源：[JST SH](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)、[JST PH](https://www.jst-mfg.com/product/pdf/eng/ePH.pdf)、[飞特产品页](https://www.feetechrc.com/6v-23kg-serial-bus-steering-gear_65522.html)、[WeAct 官方 Hardware](https://github.com/WeActStudio/WeActStudio.STM32F4_64Pin_CoreBoard/tree/master/Hardware)、[BaneBots 轮毂](https://banebots.com/t81-hub-6mm-shaft/)、[微雪资源页](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)。

[下载结果与 SHA256](retrievals.json)记录实际成功文件、失败请求和时间。WeAct 当前树为 `ff82fcef8b2c86de17ed5eaca488f3bac27b26ad`。主模型、正式 PCB、线序和既有制造放行状态均未修改。
