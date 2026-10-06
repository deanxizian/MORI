# 复核 P4

最终源为四个 `hardware/v1_2/kicad/MORI_*_P4/` 工程的 `.kicad_pcb`、`.kicad_sch`、`.kicad_pro`、`.kicad_dru` 及工程内符号/封装库。旧DSN/SES和一次性路由脚本是过程记录，**不要重导入/全量重生成覆盖最后的局部修改**。

实际工具：KiCad10.0.6；CLI为`/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`，KiCad Python为`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`。具体argv、退出码、日志和输入哈希均在各板`check_commands.json`中。

在项目根目录逐板运行：

```sh
python3 hardware/v1_2/tools/run_layout_P4.py motion check
python3 hardware/v1_2/tools/run_layout_P4.py imu check
python3 hardware/v1_2/tools/run_layout_P4.py power check
python3 hardware/v1_2/tools/run_layout_P4.py rear check
```

检查启用全部严重级别、所有走线错误、铺铜刷新与原理图一致性；ERC同样检查全部严重级别。没有添加DRC忽略项。

独立几何审查用KiCad Python执行：

```sh
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/audit_body_routes_P4.py motion imu power rear
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/review_body_exceptions_P4.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/audit_load_paths_P4.py
python3 hardware/v1_2/layout_P4/calculations/estimate_interconnect.py
python3 hardware/v1_2/layout_P4/calculations/estimate_boards.py
```

`export_P4.py <board>`只在零违规报告时导出原生SVG/PNG、坐标表与裸板STEP；`export_track_views_P4.py <board>`在临时副本中去掉铺铜用于检查，保持源PCB不变。原理图PDF实际导出命令见`reports/schematic_exports.json`。以上均不输出Gerber/钻孔/钢网。

`package_P4.py`读取现有原型及检查哈希，写硬件拥有的机械交接和引脚/装配表。`publish_contracts_P4.py`从前版备份与当前原生位号映射发布P4 BOM/接口；它不是适用于未来任意改版的通用更新器，未来改元件须同时修改映射并复核，不能覆盖后来人工补入的采购报价。

预览、原生检查和原始P3R1哈希必须一起复核。完整器件插合、功耗/温升、EMC、协议与动力试验不能由这些命令验收。
