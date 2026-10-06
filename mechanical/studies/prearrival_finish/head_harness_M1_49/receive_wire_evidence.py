"""Receive the hardware-owned wire evidence without executing or editing it."""
from pathlib import Path
import datetime,hashlib,json
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
OUT=HERE/'remaining_routes';SOURCE=ROOT/'hardware/v1_2/harness_feasibility_20261006'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
manifest=read(SOURCE/'delivery_manifest.json');handoff=read(SOURCE/'mechanical_handoff.json')
for name,digest in manifest['files'].items():assert sha(SOURCE/name)==digest,name
assert len(manifest['files'])==manifest['count']
baseline=read(SOURCE/'inputs/protected_baseline.json')
for name,digest in baseline['files'].items():assert sha(ROOT/name)==digest,name
assert read(SOURCE/'results/package_validation.json')['status']=='PASS'
source_hash=sha(ROOT/'mechanical/mori_v1_2.blend')
assert source_hash==handoff['request_reported_blend_sha256']
assert handoff['evidence_work_status']=='PASS' and handoff['status']=='BLOCKED'
assert not any(handoff[k] for k in ['formal_edits','BOM_edits','pinmap_edits','mechanical_main_edits','supplier_contacted','purchases'])
assert handoff['pinout']['J9']=={'1':'GND','2':'H_VM','3':'H_BUS'}
assert handoff['pinout']['J18']=={'1':'+5V_CAM','2':'GND'}
facts=read(SOURCE/'facts.json')
report=dict(status='PASS',scope='Read-only receipt and file/source integrity; no wire or endpoint selection',
    received_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    source_package=str(SOURCE.relative_to(ROOT)),source_files_checked=manifest['count'],
    protected_hardware_files_checked=len(baseline['files']),
    inputs={str((SOURCE/name).relative_to(ROOT)):digest for name,digest in manifest['files'].items()},
    manifest_sha256=sha(SOURCE/'delivery_manifest.json'),main_blend_sha256=source_hash,
    pinmap_changed=False,main_changed=False,wire_selection='BLOCKED',full_harness='BLOCKED',
    finished_USB_endpoint='BLOCKED',SCS_tail_endpoint='BLOCKED',physical_qualification='NOT_TESTED',
    manufacturing_release=False,script_sha256=sha(Path(__file__)))
(OUT/'hardware_wire_evidence_receipt.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'HARDWARE_REVIEW_RECEIPT.md').write_text('''# 细线和头部端部资料的机械接收

已只读接收 2026-10-06 硬件独立证据包，并核对 75 个包内文件、254 个受保护硬件文件及当前 M1.49 主模型哈希。原生电源板仍是 P5R6；运动/后板属于 P5R7，不把它们统一误称为电源 P5R7。

- Alpha2622 与无 N 后缀的 SXH-001T-P0.6 仅 AWG/绝缘外径目录字段匹配。压接、实际载流、供应商工艺和价格未定，不是新选定 BOM。
- SXH-001T-P0.6N 的绝缘外径下限过大；Alpha2622 也不能直接压入 CAM 的 GH 端子。这两种组合排除。
- 喇叭独立布局候选可继续使用 Alpha2626 的最大外径 0.889 mm 参考；GH 目录字段匹配不代表实配、压接或动态寿命合格。
- 新备选 Alpha6713 最大外径 1.2954 mm，按同一保守口径要求中心半径至少 7.1247 mm，不能直接替换现有 R6.5 路线。未将它应用到模型。
- CAM USB 成品供电尾线仍未选定。Adafruit5978 的原装受电端 CC 配置不能直接作为供电端；GCT USB4151-GF-C 只有裸公头厂图，尚无完整终端板、焊线、绝缘和应力释放包络。
- SCS0009 尾线及分线板的完整型号、出线坐标和长度基准仍缺失。保留按功能对应，不擅自镜像针号。

已有压降计算采用明确的旧版厂商电流参考和设计工况，所列 0.20/0.35/0.50 m 是敏感性例子，均不是裁线尺寸。目录计算不替代端到端电压、温升、动态弯折和实配验证。

[硬件完整报告](../../../../../hardware/v1_2/harness_feasibility_20261006/README.md) · [只读接收记录](hardware_wire_evidence_receipt.json)

本次没有改电路、针序、主模型，也未联系供应商或采购。完整线束仍为 BLOCKED。
''')
print('HARDWARE_WIRE_RECEIPT',manifest['count'],len(baseline['files']),flush=True)
