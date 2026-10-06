"""Publish evidence and a blocking interface note only; leave all CAD intact."""
from pathlib import Path
import copy, datetime, hashlib, json

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[4]
H=ROOT/'hardware/v1_2'
REV='V1.2-H0.5-P5R7'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,value):
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
def rel(p):return str(p.relative_to(ROOT))

base=H/'handoff/mechanical_P5R7.json'
inspection=json.loads((HERE/'step_inspection.json').read_text())
published=json.loads((HERE.parent/'verification.json').read_text())
protected={p:sha(ROOT/p)for p in published['native_inputs']}
for p,digest in published['native_inputs'].items():assert protected[p]==digest, p
handoff=json.loads(base.read_text())
for name,b in handoff['boards'].items():
    p=ROOT/b['native_project'];pcb=p.with_suffix('.kicad_pcb')
    assert sha(pcb)==b['pcb_sha256']
    protected[rel(pcb)]=sha(pcb)
protected[rel(base)]=sha(base)
protected[inspection['source']]=sha(ROOT/inspection['source'])
assert protected[inspection['source']]==inspection['source_sha256']
for name in ['hardware/pinmap.csv','contracts/mechanical_interfaces.json','config/geometry.json']:
    protected[name]=sha(ROOT/name)

received=[]
for name in ['service.json','followthrough.json']:
    source=ROOT/'mechanical/studies/prearrival_closure/p5r7_receipt'/name
    dest=HERE/'received_mechanical'/name
    dest.parent.mkdir(exist_ok=True)
    if dest.exists():assert dest.read_bytes()==source.read_bytes()
    else:dest.write_bytes(source.read_bytes())
    received.append({'path':rel(source),'snapshot':rel(dest),'sha256':sha(source),
        'scope':'Incoming mechanical screening evidence, not a physical measurement or manufacturer specification'})

note={'id':'P5R7-E-PIN-FIT-A1','date':'2026-10-01','status':'BLOCKED',
    'report':rel(HERE/'README.md'),'reproducible_model_audit':rel(HERE/'step_inspection.json'),
    'supplier_questionnaire':rel(HERE/'supplier_questionnaire.md'),
    'native_revision':REV,'native_CAD_changed':False,
    'confirmed_scope':'Original vendor STEP uses diameter0.812mm E holes and nominal0.64mm square original bent pins; original source shapes already intersect.',
    'candidate':'61300821121','candidate_procurement_approved':False,
    'weact_finished_hole_diameter_mm':None,'weact_finished_hole_tolerance_mm':None,
    'original_supplied_header_mpn':None,'manufacturer_matched_straight_header_mpn':None,
    'catalogue_candidate_pin_square_mm':.64,'catalogue_candidate_pin_square_tolerance_mm':.15,
    'catalogue_candidate_recommended_hole_diameter_mm':1.10,'catalogue_candidate_recommended_hole_tolerance_mm':.15,
    'source_STEP_model_hole_diameter_mm':.812,
    'source_STEP_original_E_pin_overlap_mm3':sum(r['original_pin_PCB_overlap_mm3']for r in inspection['E_pin_rows']),
    'source_STEP_original_E_pin_section_mm':[.64,.64],
    'source_STEP_claim_limit':'Model-internal inconsistency established. No manufacturer statement establishing why it differs from production, or authorizing physical fit.',
    'action':'Retain as blocked catalogue candidate; do not resize pins, drill the purchased core, waive collision, or select a thinner substitute solely from the STEP.',
    'required_inputs':['WeAct current V1.1/SKU finished plated E hole diameter, minimum and tolerance','Actual supplied bent-pin MPN, solder-tail shape/dimensions/tolerances after plating','Manufacturer-approved straight-header MPN/drawing and underside installation option','If needle changes, documented female contact compatibility, depth, retention and stack'],
    'physical_tests':'NOT_TESTED','purchase_order_sent':False,'supplier_message_sent':False}
addendum={'revision':REV,'addendum_id':note['id'],'date':'2026-10-01',
    'base_handoff':rel(base),'base_handoff_sha256':sha(base),
    'base_handoff_preserved':True,'scope':'Issue7 E pin/core-hole qualification only; J3 and all native sources unchanged',
    'weact_E_pin_fit':note,'approved_orientation_preserved':{'component_side':'UP','male_pin_direction':'DOWN'},
    'pin_coordinate_audit_68':'PASS; position/pin-number scope only','full_mated_fit':'BLOCKED',
    'mechanical_feedback_sources':received,'mechanical_main_replaced_by_hardware':False,
    'new_stack_dimension_frozen':False,'manufacturing_release':False,'physical_tests':'NOT_TESTED',
    'native_source_manifest':published['native_inputs']}
target=H/'handoff/mechanical_P5R7_E_pin_fit_A1.json'
dump(target,addendum)

before={}
for filename in ['components.json','electrical_interfaces.json']:
    p=ROOT/'contracts'/filename;before[filename]=sha(p)
    snap=HERE/'contracts_before_addendum'/filename;snap.parent.mkdir(exist_ok=True)
    if not snap.exists():snap.write_bytes(p.read_bytes())
    data=json.loads(p.read_text());assert data['revision']==REV
    data['P5R7_E_pin_fit_addendum']=dict(note,handoff=rel(target))
    if filename=='components.json':
        row=next(x for x in data['components']if x['id']=='p4_motion_module_sockets')
        row['mating_compatibility_status']='BLOCKED'
        row['E_pin_fit_evidence']=rel(HERE/'README.md')
        missing='WeAct E finished plated-hole specification and actual supplied/matched straight-header MPN; source STEP is internally inconsistent'
        if missing not in row['missing']:row['missing'].append(missing)
        warning=' P5R7-E-PIN-FIT-A1: original vendor bent-pin STEP also intersects its PCB holes; this is not evidence of real mating. E straight-header compatibility remains BLOCKED pending manufacturer data.'
        if warning not in row['notes']:row['notes']+=warning
    else:
        data['mechanical_handoff_addenda']=list(dict.fromkeys(data.get('mechanical_handoff_addenda',[])+[rel(target)]))
    assert sha(p)==before[filename], 'Concurrent contract edit: '+filename
    tmp=p.with_name(p.name+'.EpinA1.tmp');dump(tmp,data);tmp.replace(p)

# Add navigational notices without rewriting the previously received handoff.
notices={
    H/'README.md':'**2026-10-01 插合增补：**原厂 STEP 自带 E 弯针也与模型孔边相交。实物孔规格未知，61300821121 与 WeAct 的兼容性为 **BLOCKED**；[证据与厂家确认清单](reviews/weact_E_J3_20260930/E_pin_hole_addendum_20261001/README.md)。P5R7 原生工程未改。',
    HERE.parent/'README.md':'**2026-10-01 后续插合核对：**原厂 STEP 的 E 孔与自带弯针也存在相交，实际成品孔和匹配直针仍待厂家确认。候选兼容性 **BLOCKED**；[查看增补 A1](E_pin_hole_addendum_20261001/README.md)。本文原生检查结论不代表插合通过。',
    H/'wiring_P5R7/README.md':'**E 插合待核：**正确针号/方向保持，但直针与 WeAct 成品孔的兼容性尚未确认；[增补 A1](../reviews/weact_E_J3_20260930/E_pin_hole_addendum_20261001/README.md)。不得强压、扩孔或缩针。'}
for p,notice in notices.items():
    body=p.read_text()
    if notice not in body:
        line,rest=body.split('\n',1);p.write_text(line+'\n\n'+notice+'\n'+rest)

unchanged=[]
for path,digest in protected.items():
    now=sha(ROOT/path);assert now==digest, 'Protected CAD/mechanical source changed: '+path
    unchanged.append({'path':path,'sha256':digest,'status':'PASS'})
source_files=[ROOT/inspection['source'],ROOT/'hardware/v1_2/sources/weact_f4/WeAct-STM32F4_64PIN-CoreBoard_V11 Board Shape 外形.pdf',
    ROOT/'hardware/v1_2/sources/weact_f4/WeAct-STM32F4_64PIN-CoreBoard_V11 SchDoc.pdf']
manifest={'date':'2026-10-01','status':'PASS','scope':'Evidence publication and unchanged-source checks only; physical compatibility BLOCKED',
    'sources':[{'path':rel(p),'sha256':sha(p),'data_basis':'VENDOR_DOCUMENTED_GEOMETRY_NOT_MEASURED'}for p in source_files],
    'web_sources':json.loads((HERE/'web_source_manifest.json').read_text()),
    'mechanical_feedback':received,'protected_files_checked':unchanged,
    'contract_before_sha256':before,'contract_after_sha256':{n:sha(ROOT/'contracts'/n)for n in before},
    'handoff_addendum':rel(target),'handoff_addendum_sha256':sha(target),
    'native_ERC_DRC':'Existing P5R7 reports remain applicable to unchanged CAD; not rerun for evidence-only note',
    'no_mechanical_CAD_write':True,'physical_tests':'NOT_TESTED'}
dump(HERE/'evidence_manifest.json',manifest)
print(json.dumps({'publication':'PASS','protected_files':len(unchanged),'E_pin_fit':'BLOCKED','original_handoff_unchanged':sha(base)==protected[rel(base)]}))
