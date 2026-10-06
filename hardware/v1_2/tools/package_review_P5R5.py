"""Bundle final native projects and traceable review evidence, not fabrication data."""
from pathlib import Path
import json,hashlib,zipfile,ast,re
ROOT=Path(__file__).resolve().parents[3];H=ROOT/'hardware/v1_2';O=H/'layout_P5R5'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
files=set()
def add(p):
 assert p.is_file(),p
 assert p.suffix not in ['.gbr','.drl','.zip','.ses','.dsn'];files.add(p)
for kind,rev in [('motion','P5R5'),('power','P5R5'),('imu','P5R4'),('rear','P5R4')]:
 for cmd in load(H/f'layout_{rev}/reports/{kind}/check_commands.json'):
  assert cmd['returncode']==0
  for p,h in cmd['input_sha256'].items():assert sha(ROOT/p)==h,('stale checked input',p)
for name in ['MORI_motion_P5R5','MORI_power_P5R5','MORI_imu_P5R4','MORI_rear_P5R4','MORI_motion_P5R3','MORI_power_P5R3']:
 for p in(H/'kicad'/name).rglob('*'):
  if p.is_file()and(p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_sym','.kicad_mod','.json','.csv','.md']or p.name in ['fp-lib-table','sym-lib-table']):add(p)
for p in O.iterdir():
 if p.is_file()and p.suffix in ['.md','.html','.json','.csv']:add(p)
for folder in ['previews','net_review','sources']:
 for p in(O/folder).rglob('*'):
  if p.is_file():add(p)
final={'drc.json','erc.json','check_commands.json','check_0.log','check_1.log','check_2.log','netlist.xml','before_inventory.json','after_inventory.json','before_all_segments.csv','after_all_segments.csv','delta.json','body_review_final.json','R14_corner_review.json','geometry_evidence.json','review_exports.json','buck_returns.json','DC_model.json','retained_via_arrays.json','scoped_rule_change.json','load_path_audit.json','schematic_T_junctions.json','silkscreen_labels.json'}
for kind in ['motion','power']:
 for p in(O/'reports'/kind).iterdir():
  if p.name in final:add(p)
for p in(O/'reports').iterdir():
 if p.is_file()and p.suffix=='.json'and p.name not in['package_manifest.json','package_integrity.json']:add(p)
for p in(H/'reviews/P5R3_external_20260924').rglob('*'):
 if p.is_file()and p.suffix in ['.md','.html','.json','.txt','.png','.svg']:add(p)
for file in ['components.json','electrical_interfaces.json','mechanical_interfaces.json']:add(ROOT/'contracts'/file)
assert sha(ROOT/'contracts/mechanical_interfaces.json')==load(H/'handoff/mechanical_P5R5.json')['mechanical_source_sha256']
for file in ['README.md','handoff/mechanical_P5R5.json','handoff/mechanical_P5R4.json','interfaces/pinmap_V1.2-H0.5-P5R5.csv','interfaces/harness_V1.2-H0.5-P5R5.csv','bom_V1.2-H0.5-P5R5.csv','sources/parts/TI_TPS54302_RevC.pdf','schematic_S3/README.md','schematic_S3/reports/logic5v_calculations.json']:add(H/file)
for file in ['README.md','pinmap.csv','harness.csv']:add(ROOT/'hardware'/file)
for file in ['AGENTS.md','MORI_SPEC_V1_2.md']:add(ROOT/file)
for kind in ['motion','power']:
 for file in ['check_commands.json','netlist.xml','drc.json','erc.json']:add(H/'layout_P5R3/reports'/kind/file)
add(H/'layout_P5R3/reports/power/parallel_via_model.json')
for file in ['README.md','review_disposition.md','via_budget.md']:add(H/'layout_P5R3'/file)
for file in ['README.md','review_disposition.md','test_plan.md','assembly_parts_with_mpn.csv','harness.json','firmware_handoff.md']:add(H/'layout_P5R4'/file)
for kind in ['rear','imu']:
 for file in ['check_commands.json','netlist.xml','drc.json','erc.json']:add(H/'layout_P5R4/reports'/kind/file)
todo=['check_review_P5R5.py','evidence_P5R5.py','export_P5R5.py','publish_review_P5R5.py','report_P5R5.py','package_review_P5R5.py','corner_review_P5R5.py','check_review_P5R3.py','corner_review_P5.py','audit_body_P5.py','audit_load_paths_P5.py'];seen=set()
while todo:
 name=todo.pop()
 if name in seen:continue
 seen.add(name);p=H/'tools'/name
 if not p.exists():continue
 add(p);source=p.read_text();tree=ast.parse(source)
 for node in ast.walk(tree):
  if isinstance(node,ast.Import):todo +=[v.name.split('.')[0]+'.py'for v in node.names]
  if isinstance(node,ast.ImportFrom)and node.module:todo.append(node.module.split('.')[0]+'.py')
 todo += re.findall(r"['\"]([A-Za-z0-9_]+\.py)['\"]",source)
manifest={str(p.relative_to(ROOT)):sha(p)for p in sorted(files)}
mp=O/'reports/package_manifest.json';mp.write_text(json.dumps(dict(revision='V1.2-H0.5-P5R5',files=manifest,manufacturing_release=False),ensure_ascii=False,indent=2)+'\n');files.add(mp)
archive=H/'MORI_Motion_Power_P5R5_Reviewed_Projects.zip'
start='''MORI motion/power P5R5 - PROTOTYPE / physical tests NOT_TESTED

Open hardware/v1_2/layout_P5R5/index.html for the current review.
Current projects: motion/power P5R5; rear/IMU P5R4.
The included motion/power P5R3 projects are comparison sources only.
Local native footprint/symbol libraries are included. KiCad 10.0.6 was used.
No Gerber, drill, stencil manufacturing files or purchase orders are included.

Read review_disposition.md and reports/verification.json. Two quiet GND
returns use In1 as an explicitly scoped source-R13 exception. Two M5_EN
corners retain a strict 0.5mm-bevel exception. Zero native DRC is not a
claim of complete style equivalence, thermal/EMC qualification or physical fit.
External PD/3S module selection and rear RAW sense source limiting remain open.

Rerun KiCad DRC/ERC directly against the extracted native projects.
Python helpers need KiCad pcbnew; exports also use recorded Node/sharp paths.
Saved logs contain the original workspace paths and input hashes.
Do not run stage editing tools as a final-board generator. Native files are
authoritative. --publish is for the original hardware workspace only.
Mechanical contract is a read-only snapshot, not a new populated-fit release.
Manufacturing release is false. See package_manifest.json for SHA-256 hashes.
'''
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=8)as z:
 z.writestr('START_HERE.txt',start)
 for p in sorted(files):z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive)as z:
 assert z.testzip()is None
 for p,h in manifest.items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
 assert not any(p.lower().endswith(('.gbr','.drl','.dsn','.ses'))for p in z.namelist())
result=dict(archive=str(archive.relative_to(ROOT)),sha256=sha(archive),bytes=archive.stat().st_size,manifest_files=len(manifest),zip_crc='PASS',sha256_comparison='PASS',manufacturing_release=False)
(O/'reports/package_integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
