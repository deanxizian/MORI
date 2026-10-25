# 机械

当前完整模型为 **V1.2-M1.58**，项目资料版本 1.3.0-dev.1。直接从 [最新模型说明](LATEST_MODEL.md)进入。

| 资料 | 入口 |
|---|---|
| 完整装配 / 电子细模 | [总装](mori_v1_2.blend) · [电子细模](mori_electronics_detail.blend) |
| 外壳与内部视图 | [当前图册](index.html) · [带壳图](renders/ups_controls_M1_58/assembled.png) |
| 打印候选 | [STL](exports/stl/)，15 本体 + 1 维护底座 + 4 试片；不是打印放行 |
| 名义几何检查 | [当前报告](current_report.html) |
| 独立研究和未采用内容 | [研究索引](studies/README.md) |
| 采购/用户实测 | [采购记录](procurement/采购记录.md) |
| 旧版装配参考 | [M1.57-A1 视频](animation/index.html)，与 M1.58 不同步 |

尺寸唯一来源为 `config/geometry.json`，单位 mm，+X 右、+Y 前、+Z 上。主模型仍包含旧载板/外置 Buck；新 C3、完整线束、实际插合与 PA12 强度都未闭合。

## 重建

厂家网格与批准输入按 [恢复说明](../docs/GITHUB_ARCHIVE.md)取回。当前脚本入口为 `scripts/run_off_shelf_deliverables.py`。它默认检查/更新模型、STL和静态图，只有明确传 `--with-animation` 才生成视频。正式硬件合同已晚于模型输入，重建前必须处理当前合同与模型接收基线的差异，不能把旧 PASS 直接继承。

`input_assets/pcb_reference/` 是 M1.58 必需的旧板构建参考，不是当前硬件设计。生成器中有历史阶段，是构造当前几何的依赖，不能只按旧名字删除。未采用研究不得覆盖主模型。
