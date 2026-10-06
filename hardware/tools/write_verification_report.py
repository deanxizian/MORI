#!/usr/bin/env python3
"""Publish observed verification results; physical tests stay NOT_TESTED."""
from pathlib import Path
import datetime, hashlib, json, re

R=Path(__file__).resolve().parents[1]
read=lambda p:json.loads((R/p).read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
erc=read('reports/erc.json');drc=read('reports/drc.json');audit=read('reports/project_audit.json')
software=read('reports/verification_commands_software.json')
erc_count=sum(len(s.get('violations',[])) for s in erc['sheets'])
host=(R/'reports/host_tests.log').read_text().strip()
build=next(x for x in software if x['name']=='idf_build')
host_ok=next(x for x in software if x['name']=='host_tests')['exit_code']==0 and 'PASS' in host
snapshot=(R/'reports/snapshot_host_tests.log').read_text()
snapshot_ok='Exit: 0\n' in snapshot and 'PASS' in snapshot
bins={}
for p in ['mori_hardware_validation.bin','bootloader/bootloader.bin','partition_table/partition-table.bin']:
    f=R/'firmware/build'/p
    bins[p]=dict(size_bytes=f.stat().st_size,sha256=sha(f))
source_files=[p for p in (R/'firmware').rglob('*') if p.is_file()
              and not {'build','managed_components'}.intersection(p.relative_to(R).parts)
              and (p.suffix in {'.c','.h','.yml','.lock'} or p.name in {'CMakeLists.txt','Kconfig.projbuild','sdkconfig','sdkconfig.defaults'})]
provenance=dict(date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    tool_versions_log='toolchain_versions.log',idf_version='v5.5.2',
    idf_commit='30aaf64524299d3bde422ca9a2848090d1bc5d0f',
    source_sha256={str(p.relative_to(R)):sha(p) for p in sorted(source_files)},
    built_binaries=bins,build_exit_code=build['exit_code'],flashed=False,
    hardware_validation='NOT_TESTED',git_note='MORI workspace is not a Git repository; file SHA256 used')
(R/'reports/build_artifacts.json').write_text(json.dumps(provenance,indent=2)+'\n')
text=f'''# 验证记录 · Rev A0.4 / HW-SW-0.4

2026-09-21。已完成工程文件、参数计算、真实固件构建、主机模拟输入测试和原生 KiCad 检查。**未进行采购、烧录或实物测试；承载板尚未布线，不能生产或直接上电。**

|检查|结果|证据和适用边界|
|---|---|---|
|质量、重心、惯量、动力/电源计算|PASS|[计算报告](calculations.md)、[脚本原始输出](calculation_run.log)；只证明所述模型与算术，不证明闭环稳定|
|ESP-IDF真实构建|{'PASS' if build['exit_code']==0 else 'FAIL'}|[构建日志](idf_build.log)，退出码{build['exit_code']}；v5.5.2、ESP32-S3目标，功率级/平衡/头部三个开关均关闭|
|主机安全状态测试|{'PASS' if host_ok else 'FAIL'}|[主机日志](host_tests.log)：{host}；Clang ASan/UBSan；没有真实传感器/电机|
|解压后独立主机测试|{'PASS' if snapshot_ok else 'FAIL'}|[快照复现日志](snapshot_host_tests.log)，只验证快照脚本与代码的可搬移性|
|KiCad ERC|{'PASS' if erc_count==0 else 'FAIL'}|[ERC JSON](erc.json)：{erc_count}违规；[原命令日志](erc_run.log)|
|KiCad DRC|FAIL|[DRC JSON](drc.json)：{len(drc['unconnected_items'])}未连接、{len(drc['violations'])}其他违规、{len(drc['schematic_parity'])}原理图一致性问题；启用exit-code-violations，真实退出码5|
|跨文件一致性|{audit['status']}|[审计](project_audit.json)：{len(audit['checks'])}项；GPIO/编码器/原生网络与焊盘/孔位/机械哈希/预算/快照相符|
|硬件尺寸直接替换|FAIL|[选型尺寸表](../dimensions/selection_size_checklist.csv)：电池、IMU、屏幕、舵机局部与头轴承等存在冲突；主控包络仍待实测|
|A–H实物验证|NOT_TESTED|[空白记录](../tests/physical_test_record.csv)与[测试计划](../test_plan.md)；未填写任何虚构成功记录|
|生产输出|NOT_APPLICABLE|未导出Gerber/钻孔。原理图/PCB为PROTOTYPE / UNVALIDATED|

编译器为 xtensa-esp-elf GCC 14.2.0（esp-14.2.0_20251107），KiCad 10.0.6。工具版本、IDF提交和干净状态的实际输出见[版本日志](toolchain_versions.log)。MORI工作区本身没有Git仓库，未伪造Git提交；[源码/二进制SHA256](build_artifacts.json)与[软件交接清单](../handoff/baseline_manifest.json)用于对应版本。

原始执行参数、工作目录、时间、退出码与日志SHA256分别见[软件执行记录](verification_commands_software.json)和[KiCad执行记录](verification_commands_cad.json)。KiCad输出了Fontconfig/wx环境警告；文件生成、重新加载和检查成功，保留了原日志。默认规则中未启用项列在ERC/DRC JSON的ignored_checks；没有用忽略未连接的方式伪装DRC通过。

## 复核命令

在 `/Users/dean/Documents/MORI` 执行：

```sh
python3 hardware/tools/sync_mechanics.py
python3 hardware/calculations/calculate.py
python3 hardware/tools/create_design.py
python3 hardware/tools/run_verification.py software
python3 hardware/tools/run_verification.py cad
python3 hardware/tools/write_docs.py
python3 hardware/tools/export_size_checklist.py
python3 hardware/tools/update_handoff.py
/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 hardware/tools/audit_project.py
```

`cad`组会因当前未布线而返回1；其中DRC原命令返回5，这就是当前真实状态。生成器会重建其管理的原型原理图和未布线PCB，进入人工布局阶段后应停止自动重建并先保存人工修改。下载依赖需要可访问Espressif组件仓库；本机已有锁定依赖。没有自动flash命令。

## 当前主要阻塞

- **采购**：电池长度、最大充电电流、BMS阈值/均衡/回灌及充电器匹配；最终显示光学要求；精确皮带/带轮/轮轴；头轴承改座与轴向叠层。可先购台架主控、IMU、两电机、驱动、舵机、测量/保护器件，按BOM的具体状态分批执行。
- **上电**：改装nSLEEP与0.39Ω限流后核验；独立负载验证看门狗/急停/吸能；USB先断J12而保留J14。母线示波峰值必须<10V；LDO、驱动和吸能电阻热验证不能由额定值推断。
- **控制**：真实质量/重心/惯量、左右/IMU轴向、死区与齿隙、有效扭矩/温升、带传动滑移/弹性、416Hz全链路延迟。当前恢复计算是瞬时筛选，尤其低电量和恢复增速不能省略。
- **定板/装机**：A–F通过并完成机械变更/插拔空间/头部全行程检查后才能细化布线；通过DRC后仍需样板上电与热/噪声验证；自由平衡与低速运动分别走G/H。

并行软件已有独立修改，应使用[更新提示](../handoff/并行软件更新提示.md)合并差异；硬件任务没有覆盖software/，也未替该分支宣称测试通过。
'''
(R/'reports/verification.md').write_text(text)
print('Wrote observed verification report and build hashes')
