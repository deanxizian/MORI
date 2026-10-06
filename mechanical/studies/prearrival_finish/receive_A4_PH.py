# -*- coding: utf-8 -*-
"""Independent read-only KiCad mechanical-interface receipt for PHC1."""
from pathlib import Path
import json,hashlib,datetime
import pcbnew
PROJECT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
hp=PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A4_PH.json';h=read(hp)
native={};manifests={}
for label in ['formal_source_manifest','candidate_source_manifest']:
    p=PROJECT/h[label];manifest=read(p);bad=[]
    for path,digest in manifest.items():
        if sha(PROJECT/path)!=digest:bad.append(path)
    assert not bad,bad
    manifests[label]=dict(file=h[label],sha256=sha(p),files_verified=len(manifest),mismatches=bad)
    native.update(manifest)
def xy(p):return [p.x,p.y]
def models(fp):
    return [dict(file=str(m.m_Filename),scale=[m.m_Scale.x,m.m_Scale.y,m.m_Scale.z],
        offset=[m.m_Offset.x,m.m_Offset.y,m.m_Offset.z],rotation=[m.m_Rotation.x,m.m_Rotation.y,m.m_Rotation.z]) for m in fp.Models()]
def pads(fp):
    return {p.GetNumber():dict(position=xy(p.GetPosition()),angle=p.GetOrientationDegrees(),shape=int(p.GetShape()),
        size=xy(p.GetSize()),drill=xy(p.GetDrillSize()),net=p.GetNetname(),attribute=int(p.GetAttribute())) for p in fp.Pads()}
def outline(board):
    rows=[]
    for q in board.GetDrawings():
        if q.GetLayer()!=pcbnew.Edge_Cuts:continue
        rows.append(dict(shape=int(q.GetShape()),start=xy(q.GetStart()),end=xy(q.GetEnd()),
            midpoint=xy(q.GetArcMid()) if q.GetShape()==pcbnew.SHAPE_T_ARC else None))
    return sorted(rows,key=lambda r:json.dumps(r,sort_keys=True))
rows=[];total=0
for kind,entry in h['boards'].items():
    formal=next(p for p in h['formal_native_source_manifest'] if 'MORI_'+kind+'_' in p and p.endswith('.kicad_pcb'))
    a=pcbnew.LoadBoard(str(PROJECT/formal));b=pcbnew.LoadBoard(str(PROJECT/entry['board']))
    af={x.GetReference():x for x in a.GetFootprints()};bf={x.GetReference():x for x in b.GetFootprints()}
    assert set(af)==set(bf),(kind,'footprint set')
    changed={x['ref']:x for x in entry['pad_changes']};checks=[];ph=[]
    for ref,old in af.items():
        new=bf[ref];op,np=pads(old),pads(new)
        assert set(op)==set(np),(kind,ref,'pad numbers')
        pose=(xy(old.GetPosition()),old.GetOrientationDegrees(),old.GetLayer())==(xy(new.GetPosition()),new.GetOrientationDegrees(),new.GetLayer())
        mm=models(old)==models(new)
        checks.append(dict(reference=ref,pose_unchanged=pose,model_files_and_transforms_unchanged=mm))
        assert pose and mm,(kind,ref)
        for num,p in op.items():
            q=np[num]
            if ref not in changed:assert p==q,(kind,ref,num,'unowned pad change')
            else:
                spec=changed[ref]
                assert {k:v for k,v in p.items() if k not in ['size','drill']}=={k:v for k,v in q.items() if k not in ['size','drill']}
                hole=round(spec['finished_hole_nominal_mm']*1e6);land=round(spec['copper_land_mm']*1e6)
                assert q['drill']==[hole,hole] and q['size']==[land,land],(kind,ref,num)
                ph.append(dict(reference=ref,pin=num,xy_mm=[v/1e6 for v in p['position']],hole_mm=hole/1e6,land_mm=land/1e6))
    assert outline(a)==outline(b),(kind,'Edge.Cuts')
    reportdir=PROJECT/entry['native_report_directory'];drc=read(reportdir/'initial_drc.json');erc=read(reportdir/'initial_erc.json')
    assert not drc['violations'] and not drc.get('unconnected_items') and not drc.get('schematic_parity')
    assert erc.get('sheets'), (kind,'Missing ERC sheets')
    ercv=sum(len(s.get('violations',[])) for s in erc['sheets'])
    assert ercv==0
    commands=read(reportdir/'initial_commands.json');assert len(commands)==2
    for cmd in commands:
        assert cmd['returncode']==0 and sha(Path(cmd['argv'][-1]))==cmd['input_sha256'], (kind,cmd['argv'])
    rows.append(dict(board=kind,status='PASS',components_checked=len(checks),checks=checks,
        all_component_models_unchanged=True,outline_and_all_mounting_pads_unchanged=True,
        PH_pads_checked=ph,received_DRC_zero=True,received_ERC_zero=True,
        received_CLI_returncodes=[cmd['returncode'] for cmd in commands],received_CLI_input_hashes_match=True,
        reports_sha256={str(p.relative_to(PROJECT)):sha(p) for p in [reportdir/'initial_drc.json',reportdir/'initial_erc.json',reportdir/'initial_commands.json']}))
    total+=len(ph)
assert total==h['total_changed_holes']==69
out=dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',
    scope='Independent native mechanical interface equality and received report integrity, no formal board/model adoption',
    handoff=str(hp.relative_to(PROJECT)),handoff_sha256=sha(hp),manifests=manifests,
    kicad_python_version=pcbnew.Version(),boards=rows,total_PH_pads=total,
    source_main_sha256=sha(PROJECT/'mechanical/mori_v1_2.blend'),formal_boards_replaced=False,
    geometry_changed=False,manufacturing_release=False,
    limits=['Matching model references/transforms do not verify the underlying purchased model dimensions.',
        'Factory finished-hole tolerance/plating/drill registration remains unconfirmed.',
        'This receipt does not adopt or complete A3 J10 side-entry C2 or its harness.',
        'ERC/DRC results are received originals, not duplicated electrical qualification; native interfaces inspected independently.'])
(OUT/'hardware_A4_PH_receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('A4_NATIVE_RECEIPT_PASS',total,'PH holes',[r['components_checked'] for r in rows],out['kicad_python_version'])
