"""Explicit independent GND relocation prototype, not production acceptance.

Retains every via UUID/net/padstack; only declared GND positions and exact
declared straight return tracks may change. Never mutates the source project.
Native DRC, source connectivity, power widths and reference audit follow.
"""
import hashlib,json,math,shutil,sys,uuid
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
def snap(board,t):
    return dict(net=t.GetNetname(),layer=board.GetLayerName(t.GetLayer()),width_mm=t.GetWidth()/1e6,
                start_mm=list(xy(t.GetStart())),end_mm=list(xy(t.GetEnd())))
def build(source,dest,planfile):
    source,dest=Path(source),Path(dest);plan=json.loads(Path(planfile).read_text())
    assert set(plan)=={'revision','board_sha256','move_ground_vias','delete_copper','deleted_copper_expected','routes','rationale'}
    path=source/'MORI_Interface_C3.kicad_pcb';source_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    assert source_hash==plan['board_sha256'];assert not dest.exists()
    board=pcb.LoadBoard(str(path));items={uid(t):t for t in board.GetTracks()}
    old_vias={u:via_snapshot(board,t) for u,t in items.items() if isinstance(t,pcb.PCB_VIA)}
    moves=plan['move_ground_vias'];moveids=[s['uuid'] for s in moves]
    assert moves and len(moveids)==len(set(moveids))
    for s in moves:
        v=items[s['uuid']];p=s['position_mm']
        assert isinstance(v,pcb.PCB_VIA) and v.GetNetname()=='GND' and not v.IsLocked()
        assert via_snapshot(board,v)==s['source_expected'] and s['reason'].strip()
        assert len(p)==2 and all(type(x) in (int,float) and math.isfinite(x) for x in p)
        assert p!=s['source_expected']['position_mm']
    deletes=plan['delete_copper'];assert len(deletes)==len(set(deletes)) and set(deletes)==set(plan['deleted_copper_expected'])
    assert not set(deletes)&set(moveids)
    for u in deletes:
        t=items[u]
        assert type(t).__name__=='PCB_TRACK' and t.GetNetname()=='GND' and not t.IsLocked()
        assert snap(board,t)==plan['deleted_copper_expected'][u]
    for r in plan['routes']:
        assert r['net']=='GND' and r['layer'] in ['F.Cu','B.Cu'] and r['width_mm']>=.2
        assert len(r['points_mm'])>=2 and all(len(p)==2 and all(type(x) in (int,float) and math.isfinite(x) for x in p) for p in r['points_mm'])
    shutil.copytree(source,dest,ignore=shutil.ignore_patterns('*.kicad_prl','*.lck'))
    for u in deletes: board.Remove(items[u])
    for s in moves:items[s['uuid']].SetPosition(pcb.VECTOR2I(*(pcb.FromMM(x) for x in s['position_mm'])))
    net=next(n for n in board.GetNetInfo().NetsByNetcode().values() if n.GetNetname()=='GND')
    added=[]
    for i,r in enumerate(plan['routes']):
        for j,(a,b) in enumerate(zip(r['points_mm'],r['points_mm'][1:])):
            assert a!=b
            t=pcb.PCB_TRACK(board);t.SetNet(net);t.SetLayer(board.GetLayerID(r['layer']));t.SetWidth(pcb.FromMM(r['width_mm']))
            t.SetStart(pcb.VECTOR2I(*(pcb.FromMM(x) for x in a)));t.SetEnd(pcb.VECTOR2I(*(pcb.FromMM(x) for x in b)))
            t.SetUuid(pcb.KIID(str(uuid.uuid5(uuid.NAMESPACE_URL,plan['revision']+'/ground-route/'+str(i)+'/'+str(j)))))
            board.Add(t);added.append(uid(t))
    board.GetTitleBlock().SetRevision('C3_'+plan['revision']+'_PROTOTYPE')
    target=dest/path.name;pcb.SaveBoard(str(target),board);saved=pcb.LoadBoard(str(target))
    expected={u:dict(v) for u,v in old_vias.items()}
    for s in moves:expected[s['uuid']]['position_mm']=s['position_mm']
    actual={uid(t):via_snapshot(saved,t) for t in saved.GetTracks() if isinstance(t,pcb.PCB_VIA)}
    assert actual==expected
    saved_tracks={uid(t):t for t in saved.GetTracks()}
    assert set(saved_tracks)==(set(items)-set(deletes))|set(added)
    for u,t in items.items():
        if u not in deletes and not isinstance(t,pcb.PCB_VIA): assert snap(saved,saved_tracks[u])==snap(board,t)
    for u in added: assert snap(saved,saved_tracks[u])==snap(board,next(t for t in board.GetTracks() if uid(t)==u))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==source_hash
    result=dict(source_sha256=source_hash,board_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
                via_count=len(actual),GND_via_count=sum(s['net']=='GND' for s in actual.values()),
                moved_via_uuids=moveids,removed_track_uuids=deletes,added_track_uuids=added,
                exact_via_and_track_readback='PASS',adopted=False)
    (dest.parent/(plan['revision']+'-ground-build.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result),flush=True)
if __name__=='__main__':build(*sys.argv[1:])
