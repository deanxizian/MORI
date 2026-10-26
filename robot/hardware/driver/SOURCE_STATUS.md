# C3 R108P 状态与边界

2026-10-25，当前采用稿为 R108P。原始作者记录见 [状态原文](evidence/R108P/source_status_original.txt)；文件下载以[当前入口](README.md)为准，历史记录中的路径不作为当前入口。

| 项目 | 结果 |
|---|---|
| 全板 | **FAIL / PROTOTYPE / UNVALIDATED**；40 项未连接、27 个网络 |
| KiCad 原生检查 | 其余 DRC 0、图板差异 0、启用项全严重级 ERC 0 |
| 历史 ERC 忽略项 | single_global_label、four_way_junction、simulation_model_issue、footprint_filter；本次未增加 |
| 本轮局部视觉 | 作者已查看 14 张 R108P 原生局部图；全板逐线视觉 **NOT_TESTED** |
| 回流 | 7 项历史提示尚未闭合；新孔距离原始筛查仍 FAIL，不以局部检查覆盖 |
| 采购预算 | **FAIL**；本次没有重新核价或制造报价 |
| 热、浪涌、EMC、平衡、续航 | **NOT_TESTED** |
| 机械与合同 | M1.58 主模型尚未采用 C3；正式接口合同仍 IF-C1-R4 |
| 制造 | `manufacturing_release=false`，无制造数据、无下单 |

R108P 将 R304 下拉支路并入 D1601/J101/R903/U901 的 ARMED 分组；ARMED 仍有 5 个独立组，不能宣称使能链已经完整。原作者记录的 17 对供电端点、50 项铜宽回归、155 个 GND 焊盘、4 条 Kelvin 取样、327 段内层参考地及 37 处敏感区域检查是限定范围的数字检查，未证明载流、热或整机安全。

[R110 A–J](evidence/R110/README.md) 尝试未达到采用门槛，未连接数或供电、回流、DRC 出现回退，当前仍采用 R108P。原作者完整试验目录留在工程工作区，本发布只带摘要和审查数据，不把失败候选当成新 PCB。

PCB SHA256：`e27000e1cd67cc78f690aaae9a34fa0c78ac2b3bf15b6a7396be5a9e2f846d77`。
