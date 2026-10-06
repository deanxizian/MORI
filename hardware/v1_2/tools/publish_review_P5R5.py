"""Gate P5R5 motion/power; --publish updates hardware references only. Rear/IMU P5R4 and historical projects are immutable. No fabrication/order action."""
from review_P5R5 import *
from layout_P5 import rect, box
import csv, copy, xml.etree.ElementTree as ET
from datetime import datetime, timezone

REV = 'V1.2-H0.5-P5R5'
OLD = 'V1.2-H0.5-P5R4'
load = lambda p: json.loads(p.read_text())

def update(v):
    if isinstance(v, str):
        if v == OLD: return REV
        for kind in KINDS:
            v = v.replace('MORI_'+kind+'_P5R3', 'MORI_'+kind+'_P5R5')
        return v
    if isinstance(v, list): return [update(x) for x in v]
    if isinstance(v, dict): return {update(key): update(x) for key, x in v.items()}
    return v

def csvread(p):
    with p.open(encoding='utf-8-sig', newline='') as f: return list(csv.DictReader(f))

def csvout(p, rows):
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with p.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, keys); w.writeheader()
        w.writerows({key: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list, tuple)) else v for key, v in row.items()} for row in rows)

def pad_map(b):
    return sorted((f.GetReference(), p.GetNumber(), p.GetNetname(),
                   tuple(sorted(xy(p.GetSize()))), tuple(sorted(xy(p.GetDrillSize()))),
                   int(p.GetShape()), int(p.GetAttribute()))
                  for f in b.GetFootprints() for p in f.Pads())

def topology(p):
    root = ET.parse(p).getroot()
    return sorted((n.attrib['name'], tuple(sorted((x.attrib['ref'], x.attrib['pin']) for x in n.findall('node')))) for n in root.findall('nets/net'))

sources = load(O/'sources.json'); native = {}; invariants = {}; deltas = {}
for unchanged in ['rear','imu']:
    for cmd in load(H/'layout_P5R4/reports'/unchanged/'check_commands.json'):
        for file,h in cmd['input_sha256'].items():assert sha(ROOT/file)==h,('changed P5R4 input',file)
for kind in KINDS:
    name, d, p, r = paths(kind); oldname, olddir, oldpcb = source(kind)
    drc, erc = load(r/'drc.json'), load(r/'erc.json')
    assert not any(drc[x] for x in ['violations', 'unconnected_items', 'schematic_parity', 'ignored_checks'])
    assert not erc['ignored_checks'] and not any(s['violations'] for s in erc['sheets'])
    for cmd in load(r/'check_commands.json'):
        assert cmd['returncode'] == 0
        for file, h in cmd['input_sha256'].items(): assert sha(ROOT/file) == h, ('stale check', file)
    # Both previous checked source projects and their libraries are immutable.
    for cmd in load(H/'layout_P5R3/reports'/kind/'check_commands.json'):
        for file, h in cmd['input_sha256'].items(): assert sha(ROOT/file) == h, ('changed historical source', file)
    assert sha(oldpcb) == sources[kind]['sha256']
    delta, body = load(r/'delta.json'), load(r/'body_review_final.json')
    assert delta['output_pcb_sha256'] == body['source_sha256'] == load(r/'after_inventory.json')['sha256'] == sha(p)
    assert load(r/'review_exports.json')['source_pcb_sha256'] == sha(p)
    assert load(r/'geometry_evidence.json')['pcb_sha256'] == sha(p)
    assert all(delta[x] for x in ['edge_geometry_identical','holes_connectors_and_module_poses_identical','copper_layers_unchanged'])
    assert not delta['drc_exclusions']
    if kind=='motion': assert not delta['inner_signal_tracks']
    else:
        inner_board=k.LoadBoard(str(p))
        assert all(t.GetNetname()=='/GND' for t in inner_board.GetTracks() if not isinstance(t,k.PCB_VIA) and t.GetLayer() not in [F,B])
    assert not any(t['classification'] == 'FAIL_FOREIGN_NET' for t in body['body_crossing_inventory'])
    newb, oldb = k.LoadBoard(str(p)), k.LoadBoard(str(oldpcb))
    inv = {'pad_nets_sizes_drills_identical': pad_map(newb) == pad_map(oldb),
           'schematic_net_topology_identical': topology(r/'netlist.xml') == topology(H/'layout_P5R3/reports'/kind/'netlist.xml'),
           'custom_DRC_rule_file_unchanged': sha(d/(name+'.kicad_dru')) == sha(olddir/(oldname+'.kicad_dru'))}
    assert inv['pad_nets_sizes_drills_identical'] and inv['schematic_net_topology_identical'],(kind,inv)
    if kind=='motion': assert inv['custom_DRC_rule_file_unchanged']
    else:
        import difflib
        diff=list(difflib.unified_diff((olddir/(oldname+'.kicad_dru')).read_text().splitlines(),(d/(name+'.kicad_dru')).read_text().splitlines()))
        changed=[x for x in diff if x[:1] in ['+','-'] and not x.startswith(('+++','---'))]
        assert len(changed)==2 and all('R13 In1.Cu' in x for x in changed),changed
        dump(r/'scoped_rule_change.json',dict(diff=diff,reason='Two isolated GND feedback returns only; source R13 deviation explicitly documented. Other native rules unchanged.'))
        assert load(r/'buck_returns.json')['status']=='PASS'
        assert load(r/'load_path_audit.json')['status']=='PASS'
    invariants[kind], deltas[kind] = inv, delta
    native[kind] = dict(board=name, status='PASS', ERC=0, DRC=0, unconnected=0, parity=0,
                       ignored_ERC_checks=[], ignored_DRC_checks=[], source_sha256=sha(p),
                       tool=drc['kicad_version'], report=str((r/'drc.json').relative_to(ROOT)))

rules = ROOT.parent/'KiCad/Rules/pcb-rules.json'
assert sha(rules) == '5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0'
(O/'pcb-rules-source.json').write_bytes(rules.read_bytes())
summary = dict(revision=REV, scope='Power buck-cell layout and motion/power printed markings; rear/IMU retain P5R4',
    native_checks=native, source_projects_preserved=True,circuit_revision='V1.2-H0.5-P5',invariants=invariants,deltas=deltas,
    rules_source=dict(path=str(rules),sha256=sha(rules),total=47,enabled=44,full_equivalence='NOT_TESTED'),
    foreign_body_crossing_candidates=0,
    R13_local_exception='Power In1: two /GND-only quiet feedback return corridors. Exact rule diff and full-width saved-pour isolation evidence provided.',
    R14_local_exceptions=[q for q in load(O/'reports/power/R14_corner_review.json')['corner_review'] if q['status']=='FAIL'],
    style_limits='Own-pad/connector escapes and raised U100 projection itemized. Explicit R13 deviation and two R14 exceptions; zero DRC is not complete source-rule/style equivalence.',
    interface_pairs='reports/interface_pairs.json',bench_tests='NOT_TESTED',manufacturing_release=False,mechanical_fit='BLOCKED',
    unresolved=['Copper plating, thermal and permitted continuous currents await supplier confirmation and bench data',
                'External PD/3S charger remains unselected; rear J2.5 RAW source-side current limiting absent/BLOCKED',
                'Rear/IMU P5R4 module/TVS coordination and stencil supplier confirmation remain open'])
dump(O/'reports/verification.json', summary)

oldhandoff = load(H/'handoff/mechanical_P5R4.json')
handoff = copy.deepcopy(oldhandoff)
handoff.update(revision=REV, generated_utc=datetime.now(timezone.utc).isoformat(),
    mechanical_revision_read=load(ROOT/'contracts/mechanical_interfaces.json').get('revision'),
    mechanical_source_sha256=sha(ROOT/'contracts/mechanical_interfaces.json'),
    change_scope='Power U60/U70 and local buck passives moved; outlines, holes, connectors unchanged. Motion copper unchanged; rear/IMU P5R4 unchanged. No full populated/mated fit qualification.')
handoff['boards'] = {}
for oldname, oldboard in oldhandoff['boards'].items():
    board = update(copy.deepcopy(oldboard)); name = update(oldname)
    if oldname not in [source(t)[0] for t in KINDS]:
        handoff['boards'][name] = board
        continue
    kind = 'motion' if 'motion' in name else 'power'; _, d, p, r = paths(kind)
    b = k.LoadBoard(str(p)); fps = {f.GetReference(): f for f in b.GetFootprints()}
    board.update(pcb_sha256=sha(p),native_project=str((d/(name+'.kicad_pro')).relative_to(ROOT)),placements=[])
    for ref, f in sorted(fps.items()):
        board['placements'].append(dict(board=name,reference=ref,xy_mm=xy(f.GetPosition()),
            rotation_deg=f.GetOrientationDegrees(),side='B' if f.IsFlipped() else 'F',footprint=f.GetFPIDAsString(),
            fab_projection_mm=rect(f),native_body_and_pad_bounds_mm=box(f),vendor_full_height_mm=None,physical_tests='NOT_TESTED'))
    for cn in board['connectors']:
        ref=cn.get('ref',cn.get('reference')); f=fps[ref]
        cn.update(footprint=f.GetFPIDAsString(),native_body_and_pad_bounds_mm=box(f))
        cn['pins']=[dict(revision=REV,board=name,reference=ref,pin=q.GetNumber(),net=q.GetNetname(),xy_mm=xy(q.GetPosition()),
                         component_side='B' if f.IsFlipped() else 'F',view='Native component-side pad number; mating cable view is mirrored',status='NOT_TESTED')
                    for q in f.Pads() if q.GetNumber() and q.GetNumber()!='MP']
    # Historical STEP is bare board only and cannot depict moved components.
    board['bare_STEP_note']='Historical bare board reused only because outlines/holes are unchanged; no P5R5 populated STEP or mated-fit claim.'
    handoff['boards'][name]=board
dump(H/'handoff/mechanical_P5R5.json',handoff)
csvout(O/'placements.csv',[p for b in handoff['boards'].values() for p in b['placements']])
csvout(O/'connector_pinmap.csv',[p for b in handoff['boards'].values() for c in b['connectors'] for p in c['pins']])
assembly=update(csvread(H/'layout_P5R4/assembly_parts_with_mpn.csv'))
for kind in KINDS:
    name,d,p,r=paths(kind); assembly_board=k.LoadBoard(str(p))
    fps={f.GetReference():f.GetFPIDAsString() for f in assembly_board.GetFootprints()}
    for row in assembly:
        if row['board']==name and row['ref'] in fps: row['footprint']=fps[row['ref']]
csvout(O/'assembly_parts_with_mpn.csv',assembly)
dump(O/'harness.json',update(load(H/'layout_P5R4/harness.json')))

if '--publish' in sys.argv:
    files=['contracts/components.json','contracts/electrical_interfaces.json','hardware/pinmap.csv','hardware/harness.csv',
           'hardware/bom.csv','hardware/v1_2/bom.csv','hardware/v1_2/assembly_parts.csv','hardware/README.md','hardware/v1_2/README.md']
    for file in files:
        p=ROOT/file; dest=H/'revisions/before_P5R5_contracts'/file
        if not dest.exists(): dest.parent.mkdir(parents=True,exist_ok=True); dest.write_bytes(p.read_bytes())
    c,e=load(ROOT/files[0]),load(ROOT/files[1])
    assert c['revision'] in [OLD,REV] and e['revision'] in [OLD,REV]
    c['revision']=e['revision']=REV; c['components']=update(c['components'])
    for comp in c['components']:
        if comp['id']=='carrier_pcb': comp['board_revision']='motion/power:P5R5; imu/rear:P5R4'
        if comp['id']=='usb_charge':
            comp['user_selection_confirmation']={'date':'2026-09-24','answer':'仍未选定','status':'BLOCKED'}
    c['assembly_cross_reference']='hardware/v1_2/layout_P5R5/assembly_parts_with_mpn.csv'
    e['pcb_projects']=update(e['pcb_projects']); e['active_schematics']=update(e['active_schematics'])
    for kind in KINDS:
        name=paths(kind)[0];e['pcb_projects'][name].update(native_checks=native[kind],circuit_revision='V1.2-H0.5-P5',prototype_status='PROTOTYPE_NOT_BENCH_VALIDATED')
    e.update(hardware_schematic_revision='V1.2-H0.5-P5',gpio_change=False,
             pcb_revision_relationship='Motion/power P5R5 buck/marking review; rear/IMU retain P5R4. Motion copper, electrical nets and pin assignments unchanged.',
             mechanical_handoff='hardware/v1_2/handoff/mechanical_P5R5.json',connector_pinmap='hardware/v1_2/layout_P5R5/connector_pinmap.csv',
             layout_validation='hardware/v1_2/layout_P5R5/reports/verification.json')
    for contract in [c,e]:
        contract['layout_P5R5_motion_power_review']=summary
        contract['pcb_routing_style_review']['status']='NOT_TESTED'
        contract['pcb_routing_style_review']['P5R5_motion_power_review']='hardware/v1_2/layout_P5R5/reports/verification.json'
    dump(ROOT/files[0],c); dump(ROOT/files[1],e)
    for file in files[2:6]:
        rows=update(csvread(ROOT/file))
        for row in rows:
            if row.get('id')=='carrier_pcb':row['board_revision']='motion/power:P5R5; imu/rear:P5R4'
        csvout(ROOT/file,rows)
    csvout(H/'assembly_parts.csv',[dict(revision=REV,**r) for r in assembly])
    for src,dst in [('hardware/pinmap.csv','interfaces/pinmap_'+REV+'.csv'),('hardware/harness.csv','interfaces/harness_'+REV+'.csv'),('hardware/v1_2/bom.csv','bom_'+REV+'.csv')]:
        (H/dst).write_bytes((ROOT/src).read_bytes())
    dump(O/'reports/publication.json',dict(revision=REV,published=True,hardware_only=True,manufacturing_release=False,utc=datetime.now(timezone.utc).isoformat()))
print('P5R5 native gates PASS; hardware references published =', '--publish' in sys.argv)
