"""Bundle checked native projects and final evidence, excluding trial/fabrication files."""
from pathlib import Path
import json,hashlib,zipfile,ast,re,posixpath,csv
ROOT=Path(__file__).resolve().parents[3];H=ROOT/'hardware/v1_2';O=H/'layout_P5R6'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
load=lambda p:json.loads(p.read_text())
files=set()
def add(p):
    assert p.is_file(),p
    assert p.suffix not in ['.gbr','.drl','.zip','.ses','.dsn'];files.add(p)
# Native checked inputs and source hashes still govern release into this review archive.
for kind in ['motion','power','rear','imu']:
    for cmd in load(O/'reports'/kind/'check_commands.json'):
        assert cmd['returncode']==0
        for p,h in cmd['input_sha256'].items():assert sha(ROOT/p)==h,('stale input',p)
for name in ['MORI_motion_P5R6','MORI_power_P5R6','MORI_rear_P5R6','MORI_imu_P5R4','MORI_motion_P5R5','MORI_power_P5R5','MORI_rear_P5R4']:
    for p in (H/'kicad'/name).rglob('*'):
        if p.is_file() and (p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro','.kicad_dru','.kicad_sym','.kicad_mod','.json','.csv','.md'] or p.name in ['fp-lib-table','sym-lib-table']):add(p)
for p in O.iterdir():
    if p.is_file() and p.suffix in ['.md','.html','.json','.csv']:add(p)
for folder in ['previews','net_review','sources']:
    for p in (O/folder).rglob('*'):
        if p.is_file():add(p)
final={'drc.json','erc.json','check_commands.json','check_0.log','check_1.log','check_2.log','netlist.xml','before_inventory.json','after_inventory.json','before_all_segments.csv','after_all_segments.csv','delta.json','body_review_final.json','R14_corner_review.json','geometry_evidence.json','review_exports.json','buck_returns.json','DC_model.json','retained_via_arrays.json','load_path_audit.json','silkscreen_labels.json','bootstrap_and_SW_banks.json','diode_final_native_evidence.json','diode_land_pattern.json','BAT54H_package.png','BAT54H_land_detail.png','EN_smooth_geometry.json'}
for kind in ['motion','power','rear','imu']:
    for p in (O/'reports'/kind).iterdir():
        if p.name in final:add(p)
for p in (O/'reports').iterdir():
    if p.is_file() and p.suffix in ['.json','.log'] and p.name not in ['package_manifest.json','package_integrity.json']:add(p)
for f in ['components.json','electrical_interfaces.json','mechanical_interfaces.json']:add(ROOT/'contracts'/f)
assert sha(ROOT/'contracts/mechanical_interfaces.json')==load(H/'handoff/mechanical_P5R6.json')['mechanical_source_sha256']
for f in ['README.md','bom.csv','assembly_parts.csv','handoff/mechanical_P5R6.json','handoff/mechanical_P5R5.json','interfaces/pinmap_V1.2-H0.5-P5R6.csv','interfaces/harness_V1.2-H0.5-P5R6.csv','bom_V1.2-H0.5-P5R6.csv','schematic_S3/README.md','schematic_S3/reports/logic5v_calculations.json','layout_P5R3/reports/power/parallel_via_model.json','sources/connectors_P4/SOFNG_MS202V.pdf']:add(H/f)
for f in ['README.md','pinmap.csv','harness.csv','bom.csv']:add(ROOT/'hardware'/f)
for f in ['AGENTS.md','MORI_SPEC_V1_2.md']:add(ROOT/f)
for rev,kinds in [('P5R5',['motion','power']),('P5R4',['rear','imu'])]:
    for f in ['README.md','test_plan.md','review_disposition.md']:
        add(H/f'layout_{rev}'/f)
    for kind in kinds:
        for f in ['check_commands.json','netlist.xml','drc.json','erc.json','body_review_final.json','R14_corner_review.json']:add(H/f'layout_{rev}/reports/{kind}'/f)
review=H/'reviews/fourboards_P5R5_P5R4_external_20260925'
for f in ['assessment.md','intake.json','native_audit.json','vendor_sources.json','external/MORI_FourBoards_P5R5_P5R4_Fix_List.md','external/MORI_FourBoards_P5R5_P5R4_Review.md']:add(review/f)
# Only local Python dependencies; no attachment scripts are executed or installed.
todo=['review_P5R6.py','check_review_P5R6.py','evidence_P5R6.py','local_evidence_P5R6.py','export_P5R6.py','publish_review_P5R6.py','report_P5R6.py','package_review_P5R6.py','corner_review_P5R6.py','motion_diodes_P5R6.py','power_local_P5R6.py','labels_P5R6.py','en_cleanup_P5R6.py','metadata_P5R6.py','check_review_P5R3.py','audit_body_P5.py','audit_load_paths_P5.py'];seen=set()
while todo:
    name=todo.pop()
    if name in seen:continue
    seen.add(name);p=H/'tools'/name
    if not p.exists():continue
    add(p);s=p.read_text();tree=ast.parse(s)
    for node in ast.walk(tree):
        if isinstance(node,ast.Import):todo += [v.name.split('.')[0]+'.py' for v in node.names]
        if isinstance(node,ast.ImportFrom) and node.module:todo.append(node.module.split('.')[0]+'.py')
    todo += re.findall(r"['\"]([A-Za-z0-9_]+\.py)['\"]",s)
# Current entry links, including the native libraries, must exist inside archive.
manifest={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
for link in re.findall(r'(?:href|src)="([^"]+)"',(O/'index.html').read_text()):
    if not link.startswith(('http','#')):
        rel=posixpath.normpath('hardware/v1_2/layout_P5R6/'+link);assert rel in manifest,('package link',rel)
# Prices, quantities and ordered models remain unchanged except prototype set revision names.
backup=H/'revisions/before_P5R6_contracts'
def rows(p):
    with p.open(encoding='utf-8-sig') as f:return {r['id']:r for r in csv.DictReader(f)}
a,z=rows(backup/'hardware/v1_2/bom.csv'),rows(H/'bom.csv')
assert set(a)==set(z)
for id in a:
    for key in ['quantity','unit_price_cny','currency','quote_date','stock_quantity','price_status']:
        assert a[id].get(key)==z[id].get(key),(id,key)
    if id!='carrier_pcb':assert a[id]['full_model']==z[id]['full_model']
mp=O/'reports/package_manifest.json';mp.write_text(json.dumps({'revision':'V1.2-H0.5-P5R6','files':manifest,'manufacturing_release':False},ensure_ascii=False,indent=2)+'\n');files.add(mp)
archive=H/'MORI_FourBoards_P5R6_Reviewed_Projects.zip'
start='''MORI P5R6 reviewed native projects / PROTOTYPE / NOT_TESTED

Open hardware/v1_2/layout_P5R6/index.html for comparisons and evidence.
CURRENT: motion, power, rear P5R6; IMU P5R4.
COMPARISON ONLY: motion/power P5R5 and rear P5R4.

All four current boards were checked with KiCad 10.0.6: ERC/DRC/opens/parity
zero, no ignored checks. Native projects and local symbol/footprint libraries
are included. Standard KiCad libraries/models require a matching installation.
No Gerber, drill, stencil manufacturing files or purchase order is included.

See README.md and review_disposition.md for intentional land changes, retained
R13/R14 exceptions, unknown switch lever direction and unselected PD/3S charger.
RAW source protection, process/thermal/EMC and complete physical fit remain open.
The included mechanical contract is a read-only snapshot, not a fit release.

Rerun native ERC/DRC against the extracted native projects.
Python audit scripts require KiCad pcbnew. Export scripts record Node/sharp paths.
Stage editing scripts are historical operations, NOT an idempotent final-board
build. Do not rerun init/power_local/motion_diodes/en_cleanup on finished boards.
--publish is only for the original hardware-owned workspace.
Logs retain original absolute paths and checked input hashes.
Some inherited historical README links refer to the larger original project.
Current P5R6 index links are verified as included in this archive.

The SHA-256 manifest covers every supplied source/evidence file except itself
and this introductory file. Manufacturing release remains false.
'''
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=8) as z:
    z.writestr('START_HERE.txt',start)
    for p in sorted(files):z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    for path,h in manifest.items():assert hashlib.sha256(z.read(path)).hexdigest()==h,path
    assert not any(p.lower().endswith(('.gbr','.drl','.dsn','.ses')) for p in z.namelist())
result={'archive':str(archive.relative_to(ROOT)),'sha256':sha(archive),'bytes':archive.stat().st_size,'manifest_files':len(manifest),'zip_crc':'PASS','sha256_comparison':'PASS','current_index_links':'PASS','BOM_prices_quantities_MPNs_unchanged':'PASS','manufacturing_release':False}
(O/'reports/package_integrity.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
