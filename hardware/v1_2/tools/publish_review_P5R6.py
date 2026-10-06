"""Gate P5R6 revisions and publish hardware-only references; no manufacturing release."""
from review_P5R6 import *
from layout_P5 import rect,box
from datetime import datetime,timezone
import copy,csv,xml.etree.ElementTree as ET
REV='V1.2-H0.5-P5R6';OLD='V1.2-H0.5-P5R5'
load=lambda p:json.loads(p.read_text())

def update(v):
    if isinstance(v,str):
        if v==OLD:return REV
        for kind in KINDS:v=v.replace(source(kind)[0],paths(kind)[0])
        return v
    if isinstance(v,list):return [update(x) for x in v]
    if isinstance(v,dict):return {update(k):update(x) for k,x in v.items()}
    return v

def diode_fields():
    fp='MORI_Custom:BAT54H_SOD123F_Nexperia_20241008_P5R6'
    return {'board_revision':'P5R6','purpose':'Motion PCB D1/D2/D3 land correction; same BAT54H,115 MPN',
        'specification':'Nexperia BAT54H,115 / SOD123F; 1=K, 2=A; vendor copper/paste p5',
        'interface':fp,'shaft_hole_interface':fp,
        'dimensions_mm':{'package_footprint':fp,'package_body_max_mm':[2.7,1.7,1.2],'terminal_span_max_mm':3.6,'copper_pad_mm':[1.2,1.2],'pad_pitch_mm':2.8,'paste_aperture_mm':[1.1,1.1]},
        'source_date':'2024-10-08','source_urls':['https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf'],
        'source_local_paths':['hardware/v1_2/layout_P5R6/sources/Nexperia_BAT54H_20241008.pdf'],
        'package_evidence_status':'VENDOR_DOCUMENTED','package_read_date':'2026-09-25',
        'package_source_sha256':'3b7856e29d2fbe6713716ba8076f249ea94b5b79210989571cd0e68d6d2c03ff',
        'selection_status':'VENDOR_PACKAGE_AND_LAND_CONFIRMED_QUOTE_ASSEMBLY_PENDING',
        'missing':['Exact domestic price/stock/tax/shipping','Fabricator mask/stencil/assembly qualification'],
        'notes':'Same purchased MPN; native SOD123F copper and paste corrected. Vendor dimensions are documented maxima, not measured. Global procurement/thermal/assembly state unchanged; generic KiCad 3D is not manufacturer CAD.'}

def csvread(p):
    with p.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def csvout(p,rows):
    keys=list(dict.fromkeys(k for row in rows for k in row))
    with p.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list,tuple)) else v for k,v in row.items()} for row in rows)
def padmap(b,skip=()):
    return sorted((f.GetReference(),p.GetNumber(),p.GetNetname(),tuple(sorted(xy(p.GetSize()))),tuple(sorted(xy(p.GetDrillSize()))),int(p.GetShape()),int(p.GetAttribute())) for f in b.GetFootprints() if f.GetReference() not in skip for p in f.Pads())
def nets(b):return sorted((f.GetReference(),p.GetNumber(),p.GetNetname()) for f in b.GetFootprints() for p in f.Pads())
def topology(p):
    root=ET.parse(p).getroot()
    return sorted((n.attrib['name'],tuple(sorted((x.attrib['ref'],x.attrib['pin']) for x in n.findall('node')))) for n in root.findall('nets/net'))
def checked(r):
    for cmd in load(r/'check_commands.json'):
        assert cmd['returncode']==0
        for file,h in cmd['input_sha256'].items():assert sha(ROOT/file)==h,('stale input',file)

native={};invariants={};deltas={};source_records=load(O/'sources.json')
for kind in KINDS+['imu']:
    n,d,p,r=paths(kind);checked(r);drc,erc=load(r/'drc.json'),load(r/'erc.json')
    assert not any(drc[x] for x in ['violations','unconnected_items','schematic_parity','ignored_checks'])
    assert not erc['ignored_checks'] and not any(s['violations'] for s in erc['sheets'])
    native[kind]={'board':n,'status':'PASS','ERC':0,'DRC':0,'unconnected':0,'parity':0,'ignored_ERC_checks':[],'ignored_DRC_checks':[],'source_sha256':sha(p),'tool':drc['kicad_version'],'report':str((r/'drc.json').relative_to(ROOT))}
    if kind=='imu':
        checked(H/'layout_P5R4/reports/imu');continue
    sn,sd,sp=source(kind);sr=H/('layout_P5R4' if kind=='rear' else 'layout_P5R5')/'reports'/kind
    checked(sr);assert sha(sp)==source_records[kind]['sha256']
    delta,body=load(r/'delta.json'),load(r/'body_review_final.json')
    assert delta['output_pcb_sha256']==body['source_sha256']==load(r/'after_inventory.json')['sha256']==sha(p)
    assert load(r/'review_exports.json')['source_pcb_sha256']==load(r/'geometry_evidence.json')['pcb_sha256']==sha(p)
    assert all(delta[x] for x in ['edge_geometry_identical','holes_connectors_and_module_poses_identical','copper_layers_unchanged'])
    assert not delta['drc_exclusions'] and not any(x['classification']=='FAIL_FOREIGN_NET' for x in body['body_crossing_inventory'])
    assert not load(r/'silkscreen_labels.json')['unplaced']
    a,z=k.LoadBoard(str(sp)),k.LoadBoard(str(p));skip=['D1','D2','D3'] if kind=='motion' else []
    inv={'pad_nets_identical':nets(a)==nets(z),'all_other_pad_sizes_drills_identical':padmap(a,skip)==padmap(z,skip),'schematic_net_topology_identical':topology(sr/'netlist.xml')==topology(r/'netlist.xml'),'custom_DRC_rule_file_unchanged':sha(sd/(sn+'.kicad_dru'))==sha(d/(n+'.kicad_dru'))}
    assert all(inv.values()),(kind,inv)
    inv['intentional_land_pattern_change']='D1/D2/D3 Nexperia SOD123F, 1.2mm square copper/2.8mm pitch/1.1mm paste' if skip else None
    if kind in ['motion','rear']:assert load(r/'geometry_evidence.json')['copper_geometry_identical']
    if kind=='power':
        assert load(r/'buck_returns.json')['status']=='PASS'
        assert load(r/'load_path_audit.json')['status']=='PASS'
        assert load(r/'bootstrap_and_SW_banks.json')['pcb_sha256']==sha(p)
        assert not [x for x in load(r/'R14_corner_review.json')['corner_review'] if x['status']=='FAIL']
    if kind=='motion':assert load(r/'diode_final_native_evidence.json')['pcb_sha256']==sha(p)
    invariants[kind],deltas[kind]=inv,delta
rules=ROOT.parent/'KiCad/Rules/pcb-rules.json'
assert sha(rules)=='5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0'
(O/'pcb-rules-source.json').write_bytes(rules.read_bytes())
summary={'revision':REV,'scope':'Motion SOD123F land correction; power bootstrap/SW banks/M5_EN/markings; rear actual markings. IMU remains immutable P5R4.','native_checks':native,'source_projects_preserved':True,'circuit_revision':'V1.2-H0.5-P5','invariants':invariants,'deltas':deltas,'rules_source':{'path':str(rules),'sha256':sha(rules),'total':47,'enabled':44,'full_equivalence':'NOT_TESTED'},'foreign_body_crossing_candidates_in_changed_boards':0,'R13_local_exception':'Existing two isolated power /GND feedback-return paths on In1; unchanged, retained sampled pour-isolation evidence.','R14_power_free_corner_failures':0,'R14_retained_rear_exception':[x for x in load(O/'reports/rear/R14_corner_review.json')['corner_review'] if x['status']=='FAIL'],'IMU_retained_style_exceptions':'P5R4 short GND pad/via escapes; unchanged, see layout_P5R4 review.','style_limits':'Own-pad housing escape and raised U100 module projection are itemized. Native DRC does not certify full source-rule equivalence or all aesthetic preferences.','interface_pairs':'reports/interface_pairs.json','bench_tests':'NOT_TESTED','manufacturing_release':False,'mechanical_fit':'BLOCKED','unresolved':['External PD/3S charger unselected; RAW sense source protection and CC/voltage coordination remain BLOCKED','SW1 lever direction must be measured before assembly; silk records electrical ON contact pairs only','Supplier copper/steel-stencil process, current/temperature/ripple/EMC and complete populated/mated fit NOT_TESTED','6.48A concurrent design budget versus nominal 6.3A fuse still requires load-duration/time-current coordination']}
dump(O/'reports/verification.json',summary)

handoff=copy.deepcopy(load(H/'handoff/mechanical_P5R5.json'));oldboards=handoff['boards'];handoff['boards']={}
handoff.update(revision=REV,generated_utc=datetime.now(timezone.utc).isoformat(),mechanical_revision_read=load(ROOT/'contracts/mechanical_interfaces.json').get('revision'),mechanical_source_sha256=sha(ROOT/'contracts/mechanical_interfaces.json'),change_scope='Only power C62/C72 poses and motion D1/D2/D3 native land/body dimensions changed; other PCB outlines/holes/connectors unchanged. Rear silk only. IMU P5R4 unchanged; no full fit claim.')
for oldname,oldboard in oldboards.items():
    name=update(oldname);board=update(copy.deepcopy(oldboard));kind=next(kd for kd in ['motion','power','rear','imu'] if '_'+kd+'_' in name)
    if kind in KINDS:
        n,d,p,r=paths(kind);b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
        board.update(pcb_sha256=sha(p),native_project=str((d/(n+'.kicad_pro')).relative_to(ROOT)),placements=[])
        for ref,f in sorted(fps.items()):
            h=1.2 if kind=='motion' and ref in ['D1','D2','D3'] else None
            board['placements'].append({'board':name,'reference':ref,'xy_mm':xy(f.GetPosition()),'rotation_deg':f.GetOrientationDegrees(),'side':'B' if f.IsFlipped() else 'F','footprint':f.GetFPIDAsString(),'fab_projection_mm':rect(f),'native_body_and_pad_bounds_mm':box(f),'vendor_full_height_mm':h,'height_source':'Nexperia BAT54H max package height' if h else None,'physical_tests':'NOT_TESTED'})
        for cn in board['connectors']:
            f=fps[cn.get('ref',cn.get('reference'))];ref=f.GetReference();cn.update(footprint=f.GetFPIDAsString(),native_body_and_pad_bounds_mm=box(f))
            cn['pins']=[{'revision':REV,'board':name,'reference':ref,'pin':p.GetNumber(),'net':p.GetNetname(),'xy_mm':xy(p.GetPosition()),'component_side':'B' if f.IsFlipped() else 'F','view':'Native numbered pads; mating cable observation must account for mirror','status':'NOT_TESTED'} for p in f.Pads() if p.GetNumber() and p.GetNumber()!='MP']
        board['bare_STEP_note']='Historical bare board only: unchanged outlines/holes. No P5R6 populated/mated STEP qualification.'
    handoff['boards'][name]=board
dump(H/'handoff/mechanical_P5R6.json',handoff)
csvout(O/'placements.csv',[p for b in handoff['boards'].values() for p in b['placements']])
csvout(O/'connector_pinmap.csv',[p for b in handoff['boards'].values() for c in b['connectors'] for p in c['pins']])
assembly=update(csvread(H/'layout_P5R5/assembly_parts_with_mpn.csv'))
for kind in KINDS:
    n,d,p,r=paths(kind);b=k.LoadBoard(str(p));fps={f.GetReference():f for f in b.GetFootprints()}
    for row in assembly:
        if row['board']==n and row['ref'] in fps:
            row['footprint']=fps[row['ref']].GetFPIDAsString()
            if kind=='power' and row['ref']=='J6':
                row['value']='BAT_MON SERVICE / DNP';assert str(row['quantity'])=='0'
            if kind=='motion' and row['ref'] in ['D1','D2','D3']:row['source']='https://assets.nexperia.com/documents/data-sheet/BAT54H.pdf#page=5'
csvout(O/'assembly_parts_with_mpn.csv',assembly)
dump(O/'harness.json',update(load(H/'layout_P5R5/harness.json')))

if '--publish' in sys.argv:
    files=['contracts/components.json','contracts/electrical_interfaces.json','hardware/pinmap.csv','hardware/harness.csv','hardware/bom.csv','hardware/v1_2/bom.csv','hardware/v1_2/assembly_parts.csv','hardware/README.md','hardware/v1_2/README.md']
    for file in files:
        src=ROOT/file;dst=H/'revisions/before_P5R6_contracts'/file
        if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes(src.read_bytes())
    c,e=load(ROOT/files[0]),load(ROOT/files[1]);assert c['revision'] in [OLD,REV] and e['revision'] in [OLD,REV]
    c['revision']=e['revision']=REV;c['date']='2026-09-25';c['components']=update(c['components'])
    for comp in c['components']:
        if comp['id']=='carrier_pcb':
            comp['board_revision']='motion/power/rear:P5R6; imu:P5R4'
            comp['interface']='Native Edge.Cuts/holes/connectors: hardware/v1_2/handoff/mechanical_P5R6.json'
    for comp in c['components']:
        if comp['id']=='p4_015':comp.update(diode_fields())
    c['local_review_source_index']='hardware/v1_2/layout_P5R6/reports/vendor_sources.json'
    c['assembly_cross_reference']='hardware/v1_2/layout_P5R6/assembly_parts_with_mpn.csv'
    e['pcb_projects']=update(e['pcb_projects']);e['active_schematics']=update(e['active_schematics'])
    for kind in KINDS+['imu']:
        name=paths(kind)[0];e['pcb_projects'][name].update(native_checks=native[kind],circuit_revision='V1.2-H0.5-P5',prototype_status='PROTOTYPE_NOT_BENCH_VALIDATED')
    e.update(hardware_schematic_revision='V1.2-H0.5-P5',gpio_change=False,pcb_revision_relationship=summary['scope'],mechanical_handoff='hardware/v1_2/handoff/mechanical_P5R6.json',connector_pinmap='hardware/v1_2/layout_P5R6/connector_pinmap.csv',layout_validation='hardware/v1_2/layout_P5R6/reports/verification.json',schematic_validation='hardware/v1_2/layout_P5R6/reports/verification.json')
    for contract in [c,e]:
        contract['layout_P5R6_local_review']=summary
        contract['pcb_routing_style_review']['status']='NOT_TESTED'
        contract['pcb_routing_style_review']['P5R6_local_review']='hardware/v1_2/layout_P5R6/reports/verification.json'
    dump(ROOT/files[0],c);dump(ROOT/files[1],e)
    for file in files[2:6]:
        rows=update(csvread(ROOT/file))
        for row in rows:
            if row.get('id')=='carrier_pcb':
                row['board_revision']='motion/power/rear:P5R6; imu:P5R4'
                if 'interface' in row:row['interface']='Native geometry: hardware/v1_2/handoff/mechanical_P5R6.json'
        for row in rows:
            if row.get('id')=='p4_015':row.update(diode_fields())
        csvout(ROOT/file,rows)
    csvout(H/'assembly_parts.csv',[dict(revision=REV,**r) for r in assembly])
    for src,dst in [('hardware/pinmap.csv','interfaces/pinmap_'+REV+'.csv'),('hardware/harness.csv','interfaces/harness_'+REV+'.csv'),('hardware/v1_2/bom.csv','bom_'+REV+'.csv')]:
        (H/dst).write_bytes((ROOT/src).read_bytes())
    dump(O/'reports/publication.json',{'revision':REV,'published':True,'hardware_only':True,'manufacturing_release':False,'utc':datetime.now(timezone.utc).isoformat()})
print('P5R6 native gates PASS; hardware references published =','--publish' in sys.argv)
