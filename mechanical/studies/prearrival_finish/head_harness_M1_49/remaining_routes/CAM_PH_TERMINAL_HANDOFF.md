# CAM身体端PH端子：机械研究交接待统一项

状态：BLOCKED。此文件只是机械交接记录，未发送给供应商，未改hardware/或contracts/components.json，也没有选定替换料号。

| 来源/对象 | 已知字段 | 当前含义 |
|---|---|---|
| hardware/v1_2/handoff/mechanical_P5R7.json，motion J5 | B4B-PH-K-S(LF)(SN)，PHR-4，SPH-002T-P0.5S | 保留正式交接原值；板端和胶壳几何没有改 |
| JST PH目录第2页 | SPH002绝缘OD0.8–1.5mm，30–24AWG、0.05–0.22mm² | 当前细线OD0.6604mm低于其目录下限，外径检查FAIL |
| 同页SPH-004T-P0.5S | OD0.5–0.9mm，32–28AWG、0.032–0.08mm² | 当前细线仅OD检查PASS；导体、绝缘、具体压接工具/工艺仍须硬件与线束供应商确认 |
| 同页通用PH端子图 | 名义长5.7mm、横截面2.08×1.5mm | 不是某料号/线材组合的压接后最大外形；无权据此放行真实裸端穿线 |

新离机预装方案需要先装好CAM端，把身体端暂留在PHR-4胶壳外，穿导向/颈部后再入壳。它与此前CAM端先不入壳的装配方案方向不同，完整过线过程尚未验证；供应商制线图必须在最终方案确定后明确标出哪一端不入壳、针腔视图和末端长度基准。

需要硬件任务统一：确切线材/端子组合、PHR-4胶壳匹配、所用压接规范以及裸端最大外形。SPH004为条件比较项，不是本机械任务擅自替换的BOM。

[原厂PH目录](../../supplier_made_harness/recheck_20261004/JST_PH.pdf)（本次读取既有2026-10-04下载文件，第2页）；[来源下载记录](../../supplier_made_harness/recheck_20261004/retrievals.json)。目录图采用PDFium复核，Poppler因缺Adobe-Japan1映射而未正确显示文字，没有根据缺字图认读尺寸。

[局部穿口条件检查](cam_restraints/PH_terminal_gate/review.json)。该结果不会覆盖正式端子选型、实际压接或动态线束验证的BLOCKED/NOT_TESTED状态。
