# 复核与重建 P1

## 当前 S3 原理图复核

当前电源电路为`MORI_power_S3`，只有原理图；PCB仍保留P2旧电路。用户已推迟PCB更改，不能运行布局生成器来“同步”。

```sh
python3 hardware/v1_2/tools/verify_S3.py
python3 hardware/v1_2/calculations/logic5v_S3.py
```

S3专用重绘为`logic5v_S3.py`，之后重新执行`verify_S3.py`，再用bundled Python运行`export_S3.py`导出阅读PDF。契约/表格使用`publish_S3.py`和`build_reports.py`。以下P1/P2命令为历史工作流，不可用`publish_P1.py`覆盖S3接口。S3脚本不写PCB、机械或正式固件。

在项目根目录执行。所有命令是本地离线计算/CAD检查；不操作串口、刷写、采购或导出制造文件。

## 日常复核

本次实际环境：macOS arm64；KiCad10.0.6；Python计算环境在`hardware/.venv-v1`。精确CLI命令与退出码保存在`reports/cad/各板/validation_commands.json`，报告输入哈希在`reports/cad_validation.json`。

```sh
# 从现有硬件契约重新投影表格，不动CAD
python3 hardware/v1_2/tools/build_reports.py

# 实际机械质量/惯量、头姿态、延迟/饱和和功耗模型
hardware/.venv-v1/bin/python hardware/v1_2/calculations/engineering_model.py
python3 hardware/v1_2/calculations/power_integrity.py
python3 hardware/v1_2/calculations/interface_gate.py
python3 hardware/v1_2/calculations/audit_s288_reference.py

# 原生ERC、DRC、网表/焊盘/引脚与孔位核对；不重建PCB
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/verify_cad.py

# 根据当前结果刷新摘要和未完成项；不覆盖已填写的quote_intake.csv
python3 hardware/v1_2/tools/build_completion.py
python3 hardware/v1_2/tools/validate_baseline.py
python3 hardware/v1_2/tools/package_review.py
```

`verify_cad.py`可通过`KICAD_CLI`指定另一处同版本CLI；Python必须能导入`pcbnew`。本机pcbnew输出wxApp/image-handler诊断，但命令返回0且结果文件已核查；它不是实物测试结果。首次自动网表核对将KiCad的单焊盘`unconnected-(...)`合成网名误判成接线，已修正为“仅一个焊盘且无铜线”的检查；原FAIL保留在`cad_validation_initial_nc_audit.json`。

宇树代码比对中，258组CRC和6组坏帧测试PASS；厂商示例的负位置/uint8/舍入差异为独立FAIL记录。这个FAIL不该通过修改报告消除，仍待实际固件确认。真实电机与全部BENCH/ROBOT项NOT_TESTED。

## P2 当前 Layout 复核

当前原生铜线是 `kicad/MORI_*_P2/*.kicad_pcb`，不是旧 DSN/SES。分别运行：

```sh
python3 hardware/v1_2/tools/run_layout_P2.py motion check
python3 hardware/v1_2/tools/run_layout_P2.py imu check
python3 hardware/v1_2/tools/run_layout_P2.py power check
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/verify_P2.py
python3 hardware/v1_2/calculations/layout_P2_power.py
```

P2 导出：`export_P2.py motion`（或 `imu` / `power`）；功能原理图：bundled Python 执行 `export_readable_review.py P2`；阅读包：bundled Python 执行 `package_layout_P2.py`。本轮完成了原生电气 CAD 检查，但没有把固定转角退让、扇出和测试点规则的补充审查标为全部通过，见 [P2说明](../layout_P2/README.md)。

`layout_P2.py prepare/import`、`refine_P2.py`、各阶段修补脚本会修改或重建铜线，不是日常验证入口。`prepare` 不能从零精确复现后续全部局部修正；保留的最终 native PCB 和相应哈希才是本版交付。P1 历史核对脚本不用于证明 P2。

## 历史 P1 生成与 S2 图纸流程

仅重排原理图时使用以下命令；它不会触碰 PCB、项目设置或共享契约。S2 的人工电路布局在`readable_schematic.py`，原生输出入口为`functional_schematic.py`，从`connectivity.json`读取真实器件和引脚，生成块内连线、分支结点及块间网标。保留原生器件/引脚UUID；修改电路应先更新设计源和契约，再执行完整工程流程，不应把排版脚本当作电路编辑器。

```sh
python3 hardware/v1_2/tools/functional_schematic.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/verify_cad.py
python3 hardware/v1_2/tools/verify_functional_schematic.py
# 分块矢量 PDF 及 QA 渲染（需要 bundled Python 的 pypdf / reportlab）
/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 hardware/v1_2/tools/export_readable_review.py
# 若同时更新了 P2 原理图，核对六份图；不代表 P2 PCB 通过
python3 hardware/v1_2/tools/verify_readability_S2.py
python3 hardware/v1_2/tools/package_review.py
```

`verify_functional_schematic.py`针对当前 S2 绘图，与`revisions/netlabels_before_functional_20260922`中的原始图/网表/PCB哈希比较。`verify_readability_S2.py`还对比`revisions/before_readability_S2_20260922`，独立核对 P2 的 ERC/网表。如果以后实际修改电路或 P2 PCB，这项“修改前后未变”的检查理应失败，不能重写原始证据让它清零；保留该次报告，另记录新的电路/PCB变更。原生 ERC/DRC 仍由`verify_cad.py`负责。

**`native_cad.py`会覆盖自己拥有的P1原理图/板并清空布线。** 日常复核不要运行；修改电路时先复制三个工程和SES/DSN历史。原理设计在`design_P1.py`、`power_P1.py`，原生生成/确定性摆放在`native_cad.py`。它只写`hardware/v1_2/kicad`等硬件生成空间，不应触碰机械/软件。

完整生成器先以临时网标表达导出建板网络，生成PCB后再调用功能块排版器并刷新网表；最终交付的原理图始终是功能块式。此次图纸转换没有运行会清空布线的完整生成流程。

本次布线工具为Freerouting2.4.1，Java25.0.4.1+1；JAR SHA256：`251101c3eeac22d7e7dfcf6796603279e5d1000283eb82d8f093780f7afc6aa9`。各板保存DSN输入、SES结果和autorouter.log；自动布线后仍需覆铜、明确地连接与真实DRC，不靠autorouter的“完成”文字判断。

保持同一几何/网络时，可从随附SES恢复：

```sh
# 示例仅重建IMU板；先备份该工程。不是日常检查命令。
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/native_cad.py MORI_imu_P1
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/route_P1.py MORI_imu_P1 prepare
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/route_P1.py MORI_imu_P1 import
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/route_P1.py MORI_imu_P1 zones
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/v1_2/tools/finish_P1.py MORI_imu_P1
```

若改变网表、引脚、摆放、封装或板框，不可复用旧SES；需新DSN重新布线并记录路由参数。恢复后必须再运行`verify_cad.py`；不能沿用旧PASS或旧哈希。`publish_P1.py`会把审核后的原生连接关系与器件资料发布至硬件拥有的共享契约，随后重跑表格、计算和校验；它不是实物资格批准器。

SVG为原生KiCad导出。STEP仅裸板，文件名带`BARE_BOARD`；不适用于评估插头/线缆/最高器件干涉。本次未导出Gerber、钻孔或可下单制造压缩包。`package_review.py`只生成带PROTOTYPE字样的审查包，不代表制造放行。
