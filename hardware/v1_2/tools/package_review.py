#!/usr/bin/env python3
"""Validate current artifact links/hashes and package a local PROTOTYPE review copy.
This does not publish, order, export Gerber or authorize fabrication.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re
import zipfile
from urllib.parse import unquote

ROOT=Path(__file__).resolve().parents[3]
H=ROOT/'hardware/v1_2'
REPORT=H/'reports/deliverables_manifest.json'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    cad=json.loads((H/'reports/cad_validation.json').read_text())
    if cad['status']!='PASS':raise SystemExit('REFUSED: latest CAD verification failed')
    for name,board in cad['boards'].items():
        for path,digest in board['input_hashes'].items():
            if sha(ROOT/path)!=digest:raise SystemExit('REFUSED: stale CAD result '+path)
    layout_report=H/'reports/functional_schematic/verification.json'
    if layout_report.exists():
        layout=json.loads(layout_report.read_text())
        if layout['status']!='PASS' or layout['cad_report_sha256']!=sha(H/'reports/cad_validation.json'):
            raise SystemExit('REFUSED: missing/failed/stale functional schematic comparison')
    migration=json.loads((H/'reports/migration_validation.json').read_text())
    if migration['status']!='PASS':raise SystemExit('REFUSED: contract validation failed')
    # Preserve historical sources. Validate the current review documents, not
    # links inside unmodified vendor/revision archives.
    docs=[H/'README.md',H/'handoff.md',H/'test_plan.md',H/'power_states.md',H/'tools/REPRODUCE.md',
          H/'reviews/engineering_review.md',H/'reviews/closure_accountability.md',H/'reviews/functional_schematic.md',
          H/'procurement/淘宝询价模板.md',H/'reports/calculation_summary.md',H/'licenses/README.md']
    missing=[];count=0
    for doc in docs:
        for url in re.findall(r'\]\(([^\n]+?)\)',doc.read_text()):
            url=url.strip().strip('<>')
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',url) or url.startswith('#'):continue
            target=(doc.parent/unquote(url.split('#')[0])).resolve()
            count+=1
            if not target.exists():missing.append(dict(document=str(doc.relative_to(ROOT)),target=url))
    if missing:raise SystemExit('Broken current document links: '+json.dumps(missing,ensure_ascii=False))
    exclude_dirs={'__pycache__','revisions','sources','releases'}
    files=[p for p in H.rglob('*') if p.is_file() and p!=REPORT and not exclude_dirs.intersection(p.relative_to(H).parts)
           and not p.is_relative_to(H/'reports/functional_schematic/qa')
           and p.suffix not in ['.pyc','.kicad_prl','.zip','.lck'] and not p.name.endswith('.svg.png')]
    extra=['AGENTS.md','MORI_SPEC_V1_2.md','config/project_baseline.json','config/geometry.json',
           'contracts/components.json','contracts/electrical_interfaces.json','contracts/mechanical_interfaces.json',
           'hardware/bom.csv','hardware/pinmap.csv','hardware/harness.csv','hardware/wiring.csv',
           'mechanical/reports/mass_budget.json','reports/decisions/ADR-HW-V1_2-001.md','reports/decisions/ADR-HW-V1_2-002.md',
           'hardware/v1_2/sources/index.json']
    layout_evidence=[p for p in (H/'revisions/netlabels_before_functional_20260922').rglob('*') if p.is_file()]
    files=sorted(set(files+[ROOT/x for x in extra]+layout_evidence))
    result=dict(revision=cad['revision'],run_utc=datetime.now(timezone.utc).isoformat(),
                local_document_links='PASS',checked_links=count,host_contract_checks=len(migration['checks']),cad_checks=len(cad['checks']),
                physical_tests='NOT_TESTED',manufacturing_release=False,
                scope='Local review subset, not full repository. No vendor PDF/source archives, toolchains, Gerber, drill or manufacturing outputs. Reproduction of vendor-code audit requires original workspace sources.',
                files=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p)) for p in files])
    REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    out=H/'releases';out.mkdir(exist_ok=True)
    archive=out/'MORI_V1.2-H0.2-P1_PROTOTYPE_REVIEW.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in files+[REPORT]:z.write(p,str(p.relative_to(ROOT)))
        z.writestr('START_HERE.txt','MORI V1.2-H0.2-P1 PROTOTYPE REVIEW ONLY\nOpen hardware/v1_2/README.md.\nNot a fabrication package. Battery/USB-C charging, domestic prices and populated mechanical fit are not qualified. No physical tests performed. Full vendor archives and runtimes stay in the original workspace.\n')
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for item in result['files']:
            assert hashlib.sha256(z.read(item['path'])).hexdigest()==item['sha256']
    (out/'review_package.json').write_text(json.dumps(dict(path=str(archive.relative_to(ROOT)),sha256=sha(archive),bytes=archive.stat().st_size,member_hash_check='PASS',manufacturing_package=False),indent=2)+'\n')
    print(f'{len(files)} review files; {count} current links PASS; {archive.stat().st_size} byte ZIP checked')


if __name__=='__main__':main()
