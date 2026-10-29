"""Build one explicitly declared face-change prototype, never an adopted board.

Uses the existing guarded builder for translations/deletions. The sole additional
operation is native TOP_BOTTOM flip of R1033 and its one intact BODY rule area,
followed by the declared in-plane transform. Full planned-delta support is still
required before any possible adoption; no acceptance rule is relaxed here.
"""
import json,hashlib,sys,subprocess
from shapely.affinity import scale,rotate,translate
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
import build_trial
from copper_geometry import *

base=Path('robot/.state/c3-completion/trials');source=Path('robot/hardware/driver/development/native')
plan=json.loads((base/'R136B-plan.json').read_text());plan['revision']='R137C'
plan['scope']=__doc__
plan['translations']=[{'reference':'R1003','from_mm':[50.5,6.0],'delta_mm':[-29.4,22.6],'rotation_deg':180}]
plan['routes']=[];plan['vias']=[]
plan['face_transforms']=[{'reference':'R1033','from_mm':[50.5,8.25],'from_layer':'B.Cu','to_layer':'F.Cu',
 'from_rotation_deg':180,'flip_direction':'TOP_BOTTOM','position_mm':[7.3,21.4],'rotation_deg':0,
 'expected_pad_positions_mm':{'1':[6.475,21.4],'2':[8.125,21.4]},
 'owned_guard_uuids':['af535114-9de2-48cb-b30d-9f70ae3e3049']}]
c=Copper(source/'MORI_Interface_C3.kicad_pcb')
id_='60c16ff0-1985-5e62-8b16-14517a64d7d7';t=c.by_id[id_]
assert type(t).__name__=='PCB_TRACK' and t.GetNetname()=='/FAULT_N'
plan['delete_copper'].append(id_)
plan['deleted_copper_expected'][id_]={'net':t.GetNetname(),'layer':c.board.GetLayerName(t.GetLayer()),'width_mm':t.GetWidth()/1e6,'start_mm':list(xy(t.GetStart())),'end_mm':list(xy(t.GetEnd()))}
planpath=base/'R137C-plan.json';assert not planpath.exists();planpath.write_text(json.dumps(plan,indent=2)+'\n')
dest=base/'R137C';result=subprocess.run([sys.executable,str(Path(build_trial.__file__)),str(source),str(dest),str(planpath)],text=True,capture_output=True);(base/'R137C-builder-command.json').write_text(json.dumps({'argv':result.args,'returncode':result.returncode,'stdout':result.stdout,'stderr':result.stderr},indent=2)+'\n');assert result.returncode==0
board=pcb.LoadBoard(str(dest/'MORI_Interface_C3.kicad_pcb'));spec=plan['face_transforms'][0]
f=next(f for f in board.GetFootprints() if f.GetReference()==spec['reference'])
assert list(xy(f.GetPosition()))==spec['from_mm'] and board.GetLayerName(f.GetLayer())==spec['from_layer'] and f.GetOrientationDegrees()==spec['from_rotation_deg']
guards=[z for z in board.Zones() if z.GetIsRuleArea() and z.GetZoneName().startswith('BODY_R1033_')]
assert [uid(z) for z in guards]==spec['owned_guard_uuids'] and all(z.GetLayer()==pcb.B_Cu and z.GetDoNotAllowTracks() and z.GetDoNotAllowVias() for z in guards)
origin=pcb.VECTOR2I(pcb.FromMM(spec['from_mm'][0]),pcb.FromMM(spec['from_mm'][1]));f.Flip(origin,pcb.FLIP_DIRECTION_TOP_BOTTOM)
flipped_angle=f.GetOrientationDegrees();f.SetOrientationDegrees(spec['rotation_deg'])
delta=pcb.VECTOR2I(int(round(spec['position_mm'][0]*1e6))-int(round(spec['from_mm'][0]*1e6)),int(round(spec['position_mm'][1]*1e6))-int(round(spec['from_mm'][1]*1e6)));f.Move(delta)
for z in guards:
 z.Flip(origin,pcb.FLIP_DIRECTION_TOP_BOTTOM)
 z.Rotate(origin,pcb.EDA_ANGLE(spec['rotation_deg']-flipped_angle,pcb.DEGREES_T));z.Move(delta)
pcb.SaveBoard(str(dest/'MORI_Interface_C3.kicad_pcb'),board)
saved=pcb.LoadBoard(str(dest/'MORI_Interface_C3.kicad_pcb'));sf=next(x for x in saved.GetFootprints() if x.GetReference()=='R1033')
assert sf.GetLayer()==pcb.F_Cu and sf.GetOrientationDegrees()==0
for q in sf.Pads():assert list(xy(q.GetPosition()))==spec['expected_pad_positions_mm'][q.GetNumber()]
sg=[z for z in saved.Zones() if uid(z) in spec['owned_guard_uuids']]
assert len(sg)==1 and sg[0].GetLayer()==pcb.F_Cu and sg[0].GetDoNotAllowTracks() and sg[0].GetDoNotAllowVias()
assert polyset(sg[0].Outline()).symmetric_difference(polyset(guards[0].Outline())).area<1e-7
oldguard=next(k['shape'] for k in c.keepouts if k['id']==spec['owned_guard_uuids'][0]);expected_guard=translate(rotate(scale(oldguard,xfact=1,yfact=-1,origin=spec['from_mm']),-(spec['rotation_deg']-flipped_angle),origin=spec['from_mm']),xoff=spec['position_mm'][0]-spec['from_mm'][0],yoff=spec['position_mm'][1]-spec['from_mm'][1]);assert expected_guard.symmetric_difference(polyset(sg[0].Outline())).area<1e-7
mf=dest/'edit_manifest.json';changes=json.loads(mf.read_text());changes.append({'kind':'experimental_native_face_transform','scope':'Independent prototype only; no adopted-board or acceptance-rule change',**spec})
mf.write_text(json.dumps(changes,indent=2)+'\n')
assert hashlib.sha256((source/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest()==c.sha
print(json.dumps({'candidate':str(dest),'source_unchanged':True,'candidate_sha256':hashlib.sha256((dest/'MORI_Interface_C3.kicad_pcb').read_bytes()).hexdigest(),'readback_face_and_pads':'PASS','adopted':False}))
