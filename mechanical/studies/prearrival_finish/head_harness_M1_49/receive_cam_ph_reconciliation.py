"""Read-only receipt of the hardware owner's CAM/PH research handoff."""
from pathlib import Path
import datetime, hashlib, json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
OUT = HERE / 'remaining_routes'
SOURCE = ROOT / 'hardware/v1_2/cam_ph_terminal_reconciliation_20261006'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text())

manifest = read(SOURCE / 'delivery_manifest.json')
for file, digest in manifest['files'].items():
    assert sha(SOURCE / file) == digest, file
handoff = read(SOURCE / 'handoff.json')
formal = ROOT / handoff['formal_source']['path']
assert sha(formal) == handoff['formal_source']['sha256']
assert handoff['evidence_review'] == 'PASS'
assert not handoff['formal_changes'] and not handoff['received_candidate']['formally_selected']
assert handoff['bare_contact_envelope']['generic_is_finished_bounding_box'] is False

report = dict(
    status='PASS', scope='Read-only receipt; not contact selection or harness release',
    utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    hardware_thread_id='01a0c24f-ddc2-7f03-a9d4-d09dff26d30f',
    hardware_turn_id='01a10f32-873b-7123-b3a6-86db1a8456c3',
    hardware_turn_status='COMPLETED', hardware_revision=handoff['revision'],
    source_manifest_sha256=sha(SOURCE / 'delivery_manifest.json'),
    received_files={str((SOURCE / p).relative_to(ROOT)): h for p, h in manifest['files'].items()},
    checked_file_count=len(manifest['files']),
    formal_contact=handoff['formal_source']['contact'],
    research_candidate=handoff['received_candidate'],
    complete_crimped_envelope='BLOCKED', manufacturing_release='BLOCKED',
    physical_tests='NOT_TESTED', main_changed=False, hardware_changed=False,
    source_handoff=str((SOURCE / 'handoff.json').relative_to(ROOT)),
    source_missing_inputs=str((SOURCE / 'missing_inputs.csv').relative_to(ROOT)),
    script_sha256=sha(Path(__file__)))
target = OUT / 'CAM_PH_RECEIPT.json'
existing = read(target) if target.exists() else None
# A repeated read-only check must not churn timestamps and invalidate all
# downstream study input hashes when the received package did not change.
if existing is not None and all(existing.get(k) == value for k, value in report.items() if k != 'utc'):
    report = existing
else:
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
(OUT / 'CAM_PH_RECEIPT.md').write_text('''# CAM 身体端 PH 资料已接收

已接收硬件任务 2026-10-06 的 CAM-PH-RECON-R1；62 个交付文件逐个核对哈希。
这是研究资料接收，不是替换正式 BOM 或批准线束制造。

- 正式 P5R7 仍为 SPH-002T-P0.5S。它要求绝缘外径至少 0.8 mm，与当前研究线材最大 0.6604 mm 不匹配。
- 硬件此前已接收 Alpha 2841/7＋SPH-004T-P0.5S 研究组合。AWG 和绝缘外径范围匹配；镀银导体、PTFE 绝缘与具体压接工艺尚未批准。
- 5.7×2.08×1.5 mm 是目录通用未压接端子的标注，不含已确认的成品公差、锁舌、毛刺、喇叭口或临时保护件。当前机械检查只能作为名义筛选。
- 先安装 CAM 端、身体端 PH 暂不入壳仍是候选工序。裸端的完整保护与穿线、最终入壳视图和线长基准都未放行。
- 原厂零件图和手册入口存在，但本次公开检索没有拿到正文。硬件任务保存了申请页／目录页，未提交身份资料或联系供应商。

[硬件交接说明](../../../../../hardware/v1_2/cam_ph_terminal_reconciliation_20261006/README.md) · [结构化交接](../../../../../hardware/v1_2/cam_ph_terminal_reconciliation_20261006/handoff.json) · [缺项清单](../../../../../hardware/v1_2/cam_ph_terminal_reconciliation_20261006/missing_inputs.csv) · [本次接收校验](CAM_PH_RECEIPT.json)

M1.49 C5＋K1 主模型、STL、动画和原生 PCB 未因这份接收改变。后续机械候选继续分开记录名义几何、实际端子资料和实物验证。
''')
print('CAM_PH_RECEIVED', report['hardware_revision'], report['checked_file_count'], flush=True)
