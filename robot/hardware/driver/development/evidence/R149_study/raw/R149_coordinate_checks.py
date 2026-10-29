"""Native save/reload and rejected-plan checks for exact coordinate conversion; no electrical qualification."""
import contextlib,copy,hashlib,io,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from build_trial import build
b=Path('robot/.state/c3-completion/trials');out=b/'R149-coordinate-checks';out.mkdir(exist_ok=False);src=out/'source';src.mkdir()
board=pcb.BOARD();nets={}
for name in ['GND','SIG_A','SIG_B']:
    n=pcb.NETINFO_ITEM(board,name);board.Add(n);nets[name]=n
ids=[]
for name,pos in [('SIG_A',(10,10)),('SIG_B',(20,20)),('GND',(5,5))]:
    v=pcb.PCB_VIA(board);v.SetPosition(pcb.VECTOR2I(pos[0]*1000000,pos[1]*1000000));v.SetLayerPair(pcb.F_Cu,pcb.B_Cu);v.SetViaType(pcb.VIATYPE_THROUGH);v.SetWidth(500000);v.SetDrill(300000);v.SetNet(nets[name]);board.Add(v);ids.append(uid(v))
path=src/'MORI_Interface_C3.kicad_pcb';pcb.SaveBoard(str(path),board);c=Copper(path)
base=dict(revision='R149-coordinate-roundtrip',board_sha256=c.sha,
    move_vias=[dict(uuid=ids[0],source_expected=via_snapshot(c.board,c.by_id[ids[0]]),position_mm=[32.3,14.0],reason='Exact-coordinate native roundtrip fixture')],
    reassign_vias=[dict(uuid=ids[1],source_expected=via_snapshot(c.board,c.by_id[ids[1]]),position_mm=[32.3,17.8],net='SIG_A')],
    vias=[dict(net='SIG_B',position_mm=[32.3,9.7],diameter_mm=.5,drill_mm=.3)],
    routes=[dict(net='SIG_A',layer='F.Cu',width_mm=.2,points_mm=[[32.3,14.0],[32.3,17.8]])])
plan=out/'positive.json';plan.write_text(json.dumps(base,indent=2)+'\n')
with contextlib.redirect_stdout(io.StringIO()):build(src,out/'positive',plan)
d=Copper(out/'positive/MORI_Interface_C3.kicad_pcb')
assert list(xy(d.by_id[ids[0]].GetPosition()))==[32.3,14.0]
assert list(xy(d.by_id[ids[1]].GetPosition()))==[32.3,17.8]
assert d.by_id[ids[1]].GetNetname()=='SIG_A'
assert any(list(xy(v.GetPosition()))==[32.3,9.7] for v in d.vias)
assert all(t.GetStart().x==32300000 and t.GetEnd().x==32300000 for t in d.segments)
cases=[]
def case(name,mutate,message):
    p=copy.deepcopy(base);mutate(p);p['revision']='R149-'+name;cases.append((name,p,message))
case('wrong-source-hash',lambda p:p.update(board_sha256='0'*64),'Plan source PCB hash does not match')
case('missing-source-hash',lambda p:p.pop('board_sha256'),'Via movement requires an exact source board hash')
case('wrong-source-drill',lambda p:p['move_vias'][0]['source_expected'].update(drill_mm=.25),'Moved non-ground via snapshot mismatch')
case('missing-reason',lambda p:p['move_vias'][0].pop('reason'),'Via move requires a distinct finite position')
case('nonfinite-position',lambda p:p['move_vias'][0].update(position_mm=[float('nan'),14]),'Via move requires a distinct finite position')
case('unchanged-position',lambda p:p['move_vias'][0].update(position_mm=[10,10]),'Via move requires a distinct finite position')
case('duplicate-move',lambda p:p['move_vias'].append(copy.deepcopy(p['move_vias'][0])),'Duplicate or conflicting via move')
case('ground-move',lambda p:p['move_vias'][0].update(uuid=ids[2],source_expected=via_snapshot(c.board,c.by_id[ids[2]])),'Moved non-ground via snapshot mismatch')
rows=[dict(case='native-exact-coordinate-roundtrip',status='PASS',legacy_FromMM_32_3=pcb.FromMM(32.3),actual_track_x_iu=32300000)]
for name,p,message in cases:
    q=out/(name+'.json');q.write_text(json.dumps(p,indent=2)+'\n')
    try:
        with contextlib.redirect_stdout(io.StringIO()):build(src,out/name,q)
    except ValueError as e:rows.append(dict(case=name,status='PASS' if str(e).startswith(message) else 'FAIL',exception=str(e)))
    else:rows.append(dict(case=name,status='FAIL',exception=None))
assert hashlib.sha256(path.read_bytes()).hexdigest()==c.sha
result=dict(scope=__doc__,status='PASS' if all(x['status']=='PASS' for x in rows) else 'FAIL',source_sha256=c.sha,source_unchanged=True,results=rows)
(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result));assert result['status']=='PASS'
