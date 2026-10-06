# 当前官方资料复核

供应商按图制作线束已经确定。MORI 的线路、分支、长度基准和装配要求由项目完成；通用零件资料由项目主动查找。尚未发出询价、供应商消息或制造订单。

| 项目 | 这次实际核对的内容 | 仍未覆盖 |
|---|---|---|
| JST SH | [官方目录](https://www.jst-mfg.com/product/pdf/eng/eSH.pdf)给出 SSH-003T-P0.2-H、SHR-04V-S 等型号，端子跨度 0.8×1.35×3.9 mm、AWG32–28、绝缘外径 0.4–0.8 mm | 不等于实际 CAM 插座已确认为 JST 原厂；也不是完整压接轮廓、动态线材或定长成品图 |
| SCS0009 | [官方页面](https://www.feetechrc.com/6v-23kg-serial-bus-steering-gear_65522.html)的当前下载文字为 SC-0090-C001.pdf；实际[下载文件](https://www.feetechrc.com/Data/feetechrc/upload/file/20260622/6391771873533994748433885.pdf)仍是 SCS0009 A/0、2020-11-23，配件页无舵盘尺寸。下载 SHA256 与项目已有文件完全相同 | 原配舵盘轮廓、完整孔位、配套版本仍不能由此确定；网页正文25T与参数表20T/OD3.95 mm仍冲突 |
| CAM33700 / OV3660 | [官方资源页](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx/Resources-And-Documents)列有 V1、V1.1 原理图和芯片资料 | 本次页面未提供原配相机完整 FPC 的长度、补强板和接触面尺寸，不能拿其他 OV3660 排线替代确认 |

下载链接看起来较新，不代表文件修订更新。这次官方舵机 PDF 与此前保存文件同为 SHA256 `e3f15b33dea0f76efc69f4e66f6dfb2e03f488c30110b9c030f4706891221ea3`；没有重复保存一份，也没有替换主模型。

[本次来源与下载记录](current_official_download_check.json) · [已保存的同一份规格书](../../supplier_evidence/SC-0090-C001.pdf) · [线束装配的当前几何问题](../../harness_A8/cam_wire_forming/lifted_end2/index.html)

资料缺项与设计未完成分开记录：已找到的端子尺寸已经用于模型；原四线逐根动作在连续检查中发现相交，修正这条装配路线属于现在可以继续做的工作，不应归入“只能等实物”。
