"""Package reviewable native projects and evidence; never manufacturing data."""
from pathlib import Path
import json,hashlib,zipfile,ast,re

ROOT=Path(__file__).resolve().parents[3]; H=ROOT/'hardware/v1_2'; O=H/'layout_P5R4'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
files=set()
def add(p):
    assert p.is_file(),p
    assert p.suffix not in ['.gbr','.drl','.zip','.ses','.dsn']
    files.add(p)
for kind in ['rear','imu']:
    n=f'MORI_{kind}_P5R4'; d=H/'kicad'/n;r=O/'reports'/kind
    for command in load(r/'check_commands.json'):
        assert command['returncode']==0
        for f,h in command['input_sha256'].items(): assert sha(ROOT/f)==h,('stale',f)
    assert load(r/'review_exports.json')['source_pcb_sha256']==sha(d/(n+'.kicad_pcb'))
# Four currently referenced boards plus two R3 and two R2 comparison sources.
for n in ['MORI_rear_P5R4','MORI_imu_P5R4','MORI_motion_P5R3','MORI_power_P5R3','MORI_rear_P5R3','MORI_imu_P5R3','MORI_rear_P5R2','MORI_imu_P5R2']:
    for p in (H/'kicad'/n).rglob('*'):
        if p.is_file() and p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_sym','.kicad_mod','.json','.csv','.md'] or p.is_file()and p.name in ['fp-lib-table','sym-lib-table']:
            add(p)
for p in O.iterdir():
    if p.is_file() and p.suffix in ['.md','.html','.json','.csv']:add(p)
for folder in ['previews','net_review','sources']:
    for p in (O/folder).rglob('*'):
        if p.is_file():add(p)
final_reports={'drc.json','erc.json','check_commands.json','check_0.log','check_1.log','check_2.log','netlist.xml',
               'before_inventory.json','after_inventory.json','before_all_segments.csv','after_all_segments.csv',
               'delta.json','body_review_final.json','R14_corner_review.json','geometry_evidence.json','stencil_design.json',
               'CC2_flowthrough.json','ground_return_regions.json','input_DC_model.json','review_exports.json',
               'project_before_explicit_ERC.json'}
for kind in ['rear','imu']:
    for p in (O/'reports'/kind).iterdir():
        if p.name in final_reports:add(p)
for p in (O/'reports').iterdir():
    if p.is_file() and p.suffix=='.json' and p.name not in ['package_manifest.json','package_integrity.json']:add(p)
for f in ['components.json','electrical_interfaces.json','mechanical_interfaces.json']:add(ROOT/'contracts'/f)
for f in ['README.md','handoff/mechanical_P5R4.json','handoff/mechanical_P5R3.json',
          'interfaces/pinmap_V1.2-H0.5-P5R4.csv','interfaces/harness_V1.2-H0.5-P5R4.csv',
          'bom_V1.2-H0.5-P5R4.csv','sources/parts/TDK_AN000393_v2p4.pdf','sources/parts/TDK_ICM42688P_DS000347_v1p9.pdf']:add(H/f)
for f in ['README.md','pinmap.csv','harness.csv']:add(ROOT/'hardware'/f)
for f in ['AGENTS.md','MORI_SPEC_V1_2.md']:
    if (ROOT/f).exists():add(ROOT/f)
for f in ['review.md','fix_list.md','metrics.json','input_sha256.json','intake.json']:
    add(H/'reviews/P5R2_rear_imu_external_20260924'/f)
# Prior check records are needed for source-hash gating, not rerun claims.
for kind in ['rear','imu','motion','power']:
    for f in ['check_commands.json','netlist.xml','drc.json','erc.json']:
        add(H/'layout_P5R3/reports'/kind/f)
for f in ['README.md','review_disposition.md','placements.csv','assembly_parts_with_mpn.csv','harness.json']:
    add(H/'layout_P5R3'/f)

# Bundle locally imported helpers for the documented checking commands.
todo=['check_review_P5R4.py','evidence_P5R4.py','export_P5R4.py','publish_review_P5R4.py','report_P5R4.py','package_review_P5R4.py',
      'check_review_P5R3.py','corner_review_P5.py','audit_body_P5.py','audit_load_paths_P5.py']
seen=set()
while todo:
    name=todo.pop()
    if name in seen:continue
    seen.add(name);p=H/'tools'/name
    if not p.exists():continue
    add(p);t=p.read_text();tree=ast.parse(t)
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):todo +=[v.name.split('.')[0]+'.py'for v in node.names]
        if isinstance(node,ast.ImportFrom)and node.module:todo.append(node.module.split('.')[0]+'.py')
    todo +=re.findall(r"['\"]([A-Za-z0-9_]+\.py)['\"]",t)

manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
mp=O/'reports/package_manifest.json';mp.write_text(json.dumps({'revision':'V1.2-H0.5-P5R4','files':manifest,'manufacturing_release':False},ensure_ascii=False,indent=2)+'\n')
files.add(mp)
archive=H/'MORI_Rear_IMU_P5R4_Reviewed_Projects.zip'
readme='''MORI rear / IMU P5R4 — PROTOTYPE / physical tests NOT_TESTED

Open hardware/v1_2/layout_P5R4/index.html for before/after views.
Native current projects: rear and imu P5R4; motion and power P5R3.
R2/R3 comparison projects are historical, not the current rear/IMU artwork.
See review_disposition.md, test_plan.md and reports/verification.json.
External PD/3S module remains unselected. J2.5 raw VBUS sense has NO source-side
current limit yet: short-fault protection and module coordination are BLOCKED.
The 100um IMU stencil is a proposal awaiting assembly-supplier confirmation.
No Gerber, stencil-order data, procurement or fabrication release is included.

Libraries are project-local. KiCad 10.0.6 was used. Existing shell command logs
contain the original workspace paths and SHA-256 of each checked input.
Native DRC/ERC can be rerun directly with KiCad on the extracted projects.
Python helpers require KiCad's pcbnew Python; image export additionally uses
Node/sharp at the recorded local runtime path. Publish/source gates target the
original MORI workspace and the sibling KiCad rules repository; do not run
--publish against an unrelated checkout. The original rules snapshot is included.
contracts/mechanical_interfaces.json is a read-only snapshot, never modified
by this task. Historical bare STEP references do not describe populated P5R4.
Trial/failing edit transactions are excluded; final reports retain any explicit
style exceptions. See reports/package_manifest.json for artifact hashes.
'''
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=8)as z:
    z.writestr('START_HERE.txt',readme)
    for p in sorted(files):z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive)as z:
    assert z.testzip()is None
    for name,h in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==h,name
    assert not any(n.lower().endswith(('.gbr','.drl','.ses','.dsn'))for n in z.namelist())
report={'archive':str(archive.relative_to(ROOT)),'sha256':sha(archive),'bytes':archive.stat().st_size,
        'manifest_files':len(manifest),'zip_crc':'PASS','sha256_comparison':'PASS','manufacturing_release':False}
(O/'reports/package_integrity.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
