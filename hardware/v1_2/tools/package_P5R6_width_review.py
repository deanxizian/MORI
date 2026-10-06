#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Package immutable native projects plus the bounded P5R6 review addendum."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[3]
H = ROOT / 'hardware/v1_2'
REVIEW = H / 'reviews/P5R6_and_width_external_20260925'
OUTPUT = H / 'MORI_FourBoards_P5R6_WidthReview_20260925.zip'


def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    verification = json.loads((REVIEW / 'verification.json').read_text())
    assert verification['width_values'] == verification['native_rule_probe'] == 'PASS'
    assert all(v['status'] == 'PASS' for v in verification['native'].values())
    for board in verification['source_inputs'].values():
        for path, wanted in board.items():
            assert digest(ROOT / path) == wanted, ('stale validation', path)
    files = set()
    for kind, rev in [('power', 'P5R6'), ('motion', 'P5R6'), ('rear', 'P5R6'), ('imu', 'P5R4')]:
        directory = H / 'kicad' / ('MORI_' + kind + '_' + rev)
        for p in directory.rglob('*'):
            if not p.is_file() or p.suffix in ['.kicad_prl', '.lck']:
                continue
            if any(part.startswith('.') for part in p.relative_to(directory).parts):
                continue
            files.add(p)
    files.update(p for p in REVIEW.rglob('*') if p.is_file() and p.name != 'package_result.json')
    files.update(H / 'tools' / name for name in [
        'audit_width_scope_P5R6.py', 'check_paste_P5R6.py', 'package_P5R6_width_review.py'])
    files.update(H / 'layout_P5R6' / name for name in [
        'test_plan.md', 'test_records.csv', 'assembly_parts_with_mpn.csv', 'connector_pinmap.csv', 'placements.csv',
        'reports/power/buck_returns.json', 'reports/power/load_path_audit.json', 'reports/power/bootstrap_and_SW_banks.json'])
    entries = {str(p.relative_to(ROOT)): p.read_bytes() for p in sorted(files)}
    start = '''# MORI P5R6 线宽与上轮修改复审

先看 [复审处理](hardware/v1_2/reviews/P5R6_and_width_external_20260925/README.md)。

电源、运动、后接口 P5R6；IMU P5R4。PCB/SCH/PRO/DRU 及本地库保持原版。
1502 段线宽复核，四板原生 ERC/DRC/未连接/parity 均为 0。
合理改动为补齐规则范围和修正长度计算说明；没有新增必须改铜线的问题。

包含四份完整原生工程及 .pro/.dru/本地符号封装库、源规则快照、外部报告、逐项处理、
新一轮检查日志和两份可运行审查脚本。软件 KiCad 10.0.6；3D 通用模型依赖正常 KiCad 安装。

rule_probe/ 下的 DRC 错误来自故意错误线宽的临时副本，用于验证规则会正确报错；
临时板已删除，这不是设计版本或当前板 DRC。当前四板检查在 native/。

PROTOTYPE。实物 NOT_TESTED，制造放行 BLOCKED。局部 Paste SVG/PNG 仅供检查，
不是钢网或 Gerber 制造文件。没有制造订单、采购或量产资格声明。
报告中指向本 ZIP 自身的链接只用于工作区下载，无须在解压目录内再次寻找本包。
'''
    entries['START_HERE.md'] = start.encode()
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                    board_source_unchanged=True, manufacturing_release=False,
                    files={name: dict(sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))
                           for name, data in entries.items()})
    entries['MANIFEST.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    for name in entries:
        assert not name.lower().endswith(('.gbr', '.drl', '.gbrjob', '.gko'))
        assert 'MORI_RULE_PROBE_NOT_A_DESIGN_' not in name
    temporary = OUTPUT.with_suffix('.zip.tmp')
    with zipfile.ZipFile(temporary, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in entries.items():
            z.writestr(name, data)
    with zipfile.ZipFile(temporary) as z:
        assert z.testzip() is None
        assert len(z.namelist()) == len(set(z.namelist()))
        for name, item in manifest['files'].items():
            assert hashlib.sha256(z.read(name)).hexdigest() == item['sha256']
    temporary.replace(OUTPUT)
    for board in verification['source_inputs'].values():
        for path, wanted in board.items():
            assert digest(ROOT / path) == wanted
    result = dict(path=str(OUTPUT.relative_to(ROOT)), sha256=digest(OUTPUT), bytes=OUTPUT.stat().st_size,
                  entries=len(entries), CRC='PASS', every_manifest_hash='PASS',
                  manufacturing_files_included=False, current_native_sources_unchanged=True)
    (REVIEW / 'package_result.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
