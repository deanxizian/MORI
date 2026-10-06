#!/usr/bin/env python3
"""Audit checked P2 CAD, preserve P1, and extract hardware-owned handoff.

Run with KiCad Python after run_layout_P2.py <board> check and export_P2.py.
No changes to PCB, schematic, mechanical contract or firmware interfaces.
"""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
import csv,json,math,hashlib
import pcbnew as k
from verify_functional_schematic import nets,native

H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P2'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
xy=lambda p:[round(k.ToMM(p.x),6),round(k.ToMM(p.y),6)]
checks=[];boards={};handoff={};probes=[]
def check(name,ok,detail):checks.append(dict(name=name,status='PASS' if ok else 'FAIL',detail=detail))

for kind in ['motion','imu','power']:
    name='MORI_'+kind+'_P2';p1=name.replace('_P2','_P1');d=H/'kicad'/name;r=O/'reports'/name
    drc=json.loads((r/'drc.json').read_text());erc=json.loads((r/'erc.json').read_text())
    cmds=json.loads((r/'check_commands.json').read_text())
    check(name+' native CLI exits',all(x['returncode']==0 for x in cmds),[x['returncode'] for x in cmds])
    counts=dict(ERC=sum(len(s['violations']) for s in erc['sheets']),DRC=len(drc['violations']),unconnected=len(drc['unconnected_items']),schematic_parity=len(drc['schematic_parity']))
    check(name+' native checks',not any(counts.values()),counts)
    check(name+' no DRC checks ignored',not drc['ignored_checks'],drc['ignored_checks'])
    before=nets(H/'revisions/netlabels_before_functional_20260922'/p1/'netlist.xml');after=nets(r/'netlist.xml')
    delta=[n for n in before.keys()|after.keys() if before.get(n)!=after.get(n)]
    check(name+' unchanged circuit pin/net membership',not delta,delta)
    original=native(H/'kicad'/p1/(p1+'.kicad_sch'));current=native(d/(name+'.kicad_sch'))
    changes=[];fpchanges=[]
    for ref in original[1].keys()|current[1].keys():
        a=original[1].get(ref,{}).copy();b=current[1].get(ref,{}).copy()
        af=a.pop('footprint',None);bf=b.pop('footprint',None)
        if a!=b:changes.append(ref)
        if af!=bf:fpchanges.append(dict(ref=ref,before=af,after=bf))
    check(name+' same component identities/values/pin UUIDs',not changes,changes)
    p1hashes=json.loads((d/'P1_source_hashes.json').read_text())
    # P2's older clone snapshot predates the user's accepted S2 drawing pass.
    # Use that already-recorded S2 verification for the schematic baseline;
    # retain the original clone snapshot unchanged for the other P1 files.
    s2=json.loads((H/'reports/readability_S2/verification.json').read_text())
    p1hashes[p1+'.kicad_sch']=s2['boards'][p1]['schematic_sha256']
    changed=[f for f,v in p1hashes.items() if sha(H/'kicad'/p1/f)!=v]
    check(name+' P1/S2 source files preserved',not changed,dict(changed=changed,schematic_baseline='reports/readability_S2/verification.json (2026-09-22 06:26 UTC)',other_files_baseline='P1_source_hashes.json'))
    board=k.LoadBoard(str(d/(name+'.kicad_pcb')));fps=list(board.GetFootprints());tracks=[t for t in board.GetTracks() if not isinstance(t,k.PCB_VIA)];vias=[t for t in board.GetTracks() if isinstance(t,k.PCB_VIA)]
    check(name+' through vias / layer pair',all(v.GetViaType()==k.VIATYPE_THROUGH and v.TopLayer()==k.F_Cu and v.BottomLayer()==k.B_Cu for v in vias),len(vias))
    check(name+' source via maximum',len(vias)<=500,len(vias))
    # Independent geometric evidence for routing preferences that KiCad DRC
    # does not express. Do not label these measurements as full conformance.
    offgrid=[xy(v.GetPosition()) for v in vias if any(abs(a/0.0254-round(a/0.0254))*.0254>.000254 for a in xy(v.GetPosition()))]
    ends=defaultdict(list)
    for t in tracks:
        for p in [t.GetStart(),t.GetEnd()]:ends[(t.GetNetCode(),t.GetLayer(),p.x,p.y)].append(t)
    chamfers=[]
    for t in tracks:
        a,b=t.GetStart(),t.GetEnd();dx=abs(a.x-b.x);dy=abs(a.y-b.y)
        if not dx or abs(dx-dy)>5000:continue
        neighbors=[]
        for p in [a,b]:
            others=[q for q in ends[(t.GetNetCode(),t.GetLayer(),p.x,p.y)] if q!=t]
            if len(others)!=1:break
            q=others[0];dd=q.GetStart()-q.GetEnd()
            if dd.x and dd.y:break
            neighbors.append('h' if dd.y==0 else 'v')
        if len(neighbors)==2 and neighbors[0]!=neighbors[1]:chamfers.append(dict(xy=xy(a),setback_mm=round(k.ToMM(dx),6)))
    unusual=[c for c in chamfers if abs(c['setback_mm']-.499999)>.001]
    netlength=defaultdict(float)
    for t in tracks:netlength[(str(t.GetNetname()),round(k.ToMM(t.GetWidth()),6))]+=k.ToMM(t.GetLength())
    connectors=[];holes=[]
    for f in fps:
        ref=f.GetReference()
        if ref.startswith('H'):
            for pad in f.Pads():holes.append(dict(id=ref,xy_mm=xy(pad.GetPosition()),diameter_mm=k.ToMM(pad.GetDrillSize().x),assembly_keepout_radius_mm=2.7,hardware_radius_status='ASSUMED 2.2 mm plus source 0.5 mm; verify actual screw/washer'))
        if ref.startswith('J') or ref=='U100':
            pins=[]
            for pad in f.Pads():
                pin=dict(pin=str(pad.GetNumber()),net=str(pad.GetNetname()),xy_mm=xy(pad.GetPosition()))
                pins.append(pin)
                if pad.GetNumber():probes.append(dict(board=name,reference=ref,pin=str(pad.GetNumber()),net=str(pad.GetNetname()),x_mm=pin['xy_mm'][0],y_mm=pin['xy_mm'][1],component_side='B' if f.IsFlipped() else 'F',dedicated_testpoint=False))
            connectors.append(dict(ref=ref,value=f.GetValue(),position_rotation_mm_deg=xy(f.GetPosition())+[f.GetOrientationDegrees()],side='B' if f.IsFlipped() else 'F',footprint=str(f.GetFPID().GetLibItemName()),pins=pins,mating_height_and_clearance_mm=None,clearance_status='BLOCKED pending selected mating connector, lead exit/bend radius and installation review'))
    data=json.loads((d/'connectivity.json').read_text())
    handoff[name]=dict(outline_xy_mm=data['size'],board_thickness_mm=1.6,outline_status='DESIGN_GENERATED',holes=holes,connectors=connectors,installed_envelope_height_mm=None,mass_g=None,STEP='hardware/v1_2/mechanical/'+name+'_BARE_BOARD.step',STEP_scope='BARE BOARD ONLY; no populated-assembly fit claim')
    paths=[d/(name+ext) for ext in ['.kicad_pro','.kicad_pcb','.kicad_sch','.kicad_dru']]
    hashes={str(p.relative_to(ROOT)):sha(p) for p in paths}
    if (r/'exports.json').exists():check(name+' exports match current PCB',json.loads((r/'exports.json').read_text())['source_pcb_sha256']==sha(d/(name+'.kicad_pcb')),sha(d/(name+'.kicad_pcb')))
    boards[name]=dict(counts=counts,report_date=drc['date'],native_tool=drc['kicad_version'],footprints=len(fps),nets=len(after),tracks=len(tracks),vias=len(vias),outline_mm=data['size'],input_hashes=hashes,footprint_changes=fpchanges,erc_default_ignored_checks=erc['ignored_checks'],supplemental_geometry=dict(R14_chamfers_detected=len(chamfers),R14_detected_not_0p5mm=len(unusual),R14_nonconforming_examples=unusual[:8],R14_status='FAIL' if unusual else 'NOT_TESTED',fanout_grid_probe_all_vias=len(vias),vias_off_0p0254mm_grid=len(offgrid),fanout_grid_status='NOT_TESTED: all-via screening is not fanout classification; no equivalent routing-grid guarantee'),copper_length_by_net_width=[dict(net=n,width_mm=w,total_track_length_mm=round(length,3)) for (n,w),length in sorted(netlength.items())])

source=O/'pcb-rules-source.json';live=Path('/Users/dean/Documents/KiCad/Rules/pcb-rules.json')
check('source rule snapshot unchanged',sha(source)==sha(live),sha(source))
probe=json.loads((O/'reports/rule_probe/verification.json').read_text())
check('native rule negative coupon detects intended violations',probe['status']=='PASS',probe['checks'])
report=dict(revision='V1.2-H0.2-P2',run_utc=datetime.now(timezone.utc).isoformat(),native_cad_status='PASS' if all(c['status']=='PASS' for c in checks) else 'FAIL',full_source_rule_conformance='BLOCKED: see supplemental geometry and README; native DRC zero is not all 47 source rules qualified',physical_tests='NOT_TESTED',manufacturing_release=False,source_rules_sha256=sha(source),boards=boards,checks=checks)
(O/'reports/verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
with (O/'probe_map.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=probes[0].keys());w.writeheader();w.writerows(probes)
mechanical=ROOT/'contracts/mechanical_interfaces.json'
handoff=dict(revision='V1.2-H0.2-P2',mechanical_revision_read=json.loads(mechanical.read_text()).get('revision'),mechanical_sha256=sha(mechanical),coordinates='PCB +X right +Y down; front +Z. Native placement CSV uses KiCad export coordinates; robot transform requires mechanical owner. Handoff is not an edit to the shared mechanical contract.',boards=handoff,power_fit='BLOCKED:80x45 PCB plus >=16 mm capacitor does not fit44x16x10 previous allocation. M1.5 has not integrated the power board; complete populated envelopes/cables remain unknown.',motion_fit='70x35 outline only; WeAct stack and bottom-facing J6/J8 connector approach remain unqualified.',imu_fit='20x16 outline only; mating plug height unresolved. TDK AN000393 recommends at least three mechanical anchors; current two-hole interface is an unresolved mechanical deviation.',electrical_revision='V1.2-H0.2-P1 pin numbers/nets unchanged; P2 revises placement and copper.',physical_dimensions='DESIGN_GENERATED/VENDOR_DOCUMENTED where cited; no MEASURED parts',owned_files_not_modified=['config/geometry.json','contracts/mechanical_interfaces.json','contracts/components.json','contracts/electrical_interfaces.json','contracts/wire.h','contracts/wire.c'])
(H/'handoff/mechanical_P2.json').write_text(json.dumps(handoff,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(dict(native_cad_status=report['native_cad_status'],checks=len(checks),boards={n:dict(counts=v['counts'],tracks=v['tracks'],vias=v['vias'],supplemental_geometry=v['supplemental_geometry']) for n,v in boards.items()}),ensure_ascii=False,indent=2))
if report['native_cad_status']!='PASS':raise SystemExit(1)
