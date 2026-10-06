"""Remove stale live wheel snapshots; keep geometry.json authoritative.

No geometry, vendor dimensions, electrical file or hardware selection changes.
Preserve the previous interface contract and model for the following rebuild audit.
"""
from pathlib import Path
import json, hashlib, shutil, datetime
HERE=Path(__file__).resolve().parent;M=HERE.parents[1];P=M.parent
OUT=HERE/'interface_sync';OUT.mkdir(exist_ok=True)
contract=P/'contracts/mechanical_interfaces.json';geometry=P/'config/geometry.json'
g=json.loads(geometry.read_text());c=json.loads(contract.read_text())
assert g['revision']=='V1.2-M1.46'
baseline=OUT/'before';baseline.mkdir(exist_ok=True)
for src,name in [(contract,'mechanical_interfaces.json'),(geometry,'geometry.json'),(M/'mori_v1_2.blend','mori_v1_2.blend')]:
    dst=baseline/name
    if not dst.exists():shutil.copy2(src,dst)
for name in ['build_manifest.json','delivery_consistency.json','rebuild_check.json']:
    dst=baseline/name
    if not dst.exists():shutil.copy2(M/'reports'/name,dst)
old=json.loads((baseline/'mechanical_interfaces.json').read_text())
# Numeric geometry is no longer duplicated as a misleading current snapshot.
c['wheel_mounting']['current_design']={
    'geometry_source':'config/geometry.json#/wheel_interface',
    'geometry_revision':g['revision'],
    'final_overrides':[
        'config/geometry.json#/drive_print_cleanup',
        'config/geometry.json#/drive_edge_cleanup',
        'config/geometry.json#/interface_completion',
        'config/geometry.json#/assembly_issue_fixes/drive_nuts',
        'config/geometry.json#/assembly_issue_fixes/wheel_bearing',
        'config/geometry.json#/assembly_issue_fixes/body_seam'],
    'final_geometry_evidence':['mechanical/reports/wheel_interface_design.json','mechanical/reports/wheel_interface_validation.json','mechanical/reports/assembly_issue_validation.json'],
    'superseded_snapshot':'mechanical/studies/prearrival_finish/interface_sync/before/mechanical_interfaces.json#/wheel_mounting/current_design',
    'note':'Resolve current shared parameters and later overrides. The old M1.14 numeric snapshot is historical and must not drive manufacturing.'}
c['wheel_mounting']['axial_retention']='Integral shaft shoulder -> first bearing inner ring -> 4.5mm metal spacer -> second inner ring -> 10mm metal spacer -> hub -> M3 washer/axial screw. Current inner-bearing centre is absX38.5mm and shaft shoulder ends at absX36.0mm; source config/geometry.json#/wheel_interface and assembly_issue_fixes/wheel_bearing. Physical fits, preload and screw specification remain unqualified.'
c['wheel_mounting']['case_retention']='Opposed horizontal servo cases in shared cage, common cap and compliant pads. Distinguish the four current M3 cap bolts from the four M2 drive-retention screws/nuts with side entries. Use current config/geometry.json and the generated fastener schedule; no assumed servo body thread depth. Clamp creep/torque reaction and actual cable exit remain unqualified.'
c['wheel_mounting'].pop('shell_seam_mount_abs_y_mm',None)
c['wheel_mounting']['shell_seam_geometry_source']='config/geometry.json#/assembly_issue_fixes/body_seam; paired current XY axes are (±22, ±71)mm. Former absY54mm sites are retired.'
c['interface_completion']['WeAct_socket_receipt']='P5R7 adopted in M1.45: WeAct component side UP, individual male headers DOWN, nominal face gap11.04mm. Original STEP E pin/hole contradiction and actual insertion/contact remain BLOCKED. See P5R7_adoption and hardware formal A1 addendum.'
c['interface_completion']['remaining_nominal_design_issues']=[
    'Current list: mechanical/studies/prearrival_finish/work_status.json',
    'Reaction-link initial assembly and tool path unresolved; full transmission awaits SCS0009 matching horn evidence',
    'Three isolated thin-feature candidates not yet approved/applied',
    'Complete harness, unselected purchased items and continuous-drive budget not closed']
c['interface_completion']['closed_by_M1_43']='The previously listed drive-nut entries, inner-bearing lips, upper-pitch nut roof, camera mast cavity and body-shell path were addressed by approved assembly_issue_fixes. See current validation reports; no physical qualification.'
c['revision']=g['revision']
c['current_geometry_revision']=g['revision']
c['current_authority']={
    'geometry':'config/geometry.json',
    'nominal_dimensions':'Read current parameter blocks plus enabled later overrides; do not use old revision narratives as dimensions.',
    'historical_fields':['structure_revision','appearance_revision','mechanical_selection_M1_10','custom_pcb_capacity_feedback'],
    'historical_fields_note':'Retained for traceability; these refer to the revision where those decisions were introduced, not the complete current assembly.',
    'current_status':'mechanical/studies/prearrival_finish/work_status.json',
    'tyres':'105x18mm design requirement only; supplier, free bead diameter, retention and mass unresolved. contracts/components.json tyres remains read-only REQUIRED_UNSELECTED.',
    'scope':'Documentation synchronization only; geometry and hardware sources unchanged.'}
assert c['components']==old['components']
assert c['vendor_geometry_sources']==old['vendor_geometry_sources']
for ref in [c['wheel_mounting']['current_design']['geometry_source']]+c['wheel_mounting']['current_design']['final_overrides']:
    value=g
    for key in ref.split('#/')[1].split('/'):value=value[key]
contract.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
changes=[]
def walk(a,b,path=''):
    if isinstance(a,dict) and isinstance(b,dict):
        for k in sorted(set(a)|set(b)):walk(a.get(k),b.get(k),path+'/'+k)
    elif a!=b:changes.append(dict(path=path,before=a,after=b))
walk(old,c)
out=dict(revision=g['revision'],created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
    status='BLOCKED',status_scope='Awaiting rebuild equivalence',main_geometry_changed=False,hardware_files_changed=False,
    before_contract_sha256=hashlib.sha256((baseline/'mechanical_interfaces.json').read_bytes()).hexdigest(),
    current_contract_sha256=hashlib.sha256(contract.read_bytes()).hexdigest(),
    unchanged_geometry_sha256=hashlib.sha256(geometry.read_bytes()).hexdigest(),
    baseline_blend_sha256=hashlib.sha256((baseline/'mori_v1_2.blend').read_bytes()).hexdigest(),
    changes=changes)
(OUT/'contract_changes.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('INTERFACE_SYNC',len(changes),'documentation fields; unchanged geometry input')
