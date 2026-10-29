"""Read-only actual new supply-path width, connectivity and nominal mounted-face geometry."""
import ast
import hashlib
import json
import sys
from pathlib import Path
from shapely.geometry import box
from shapely.ops import polygonize
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups

b=Path('robot/.state/c3-completion/trials')
revision=sys.argv[1]
out=b/(revision+'-inspection.json')
assert not out.exists()
a=Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c=Copper(b/revision/'MORI_Interface_C3.kicad_pcb')
assert a.sha=='7a74c8cf57681740216e47ab2f1b7f52af83a652cb6379c83d8dde4cb9353bd9'
node=next(n for n in ast.parse((b/'R138_joint_search.py').read_text()).body if isinstance(n,ast.FunctionDef) and n.name=='fab')
exec(compile(ast.Module(body=[node],type_ignores=[]),'fab_helper','exec'))
new=[t for t in c.segments if uid(t) not in a.by_id]
pads={c.pad_name(q):q for q in c.pads}
rows=[]
for width in [0,.2,.3,.4,.48,.5,.6]:
    pairs=c.connected_pairs('/HEAD_6V_RAW',width)
    rows.append({'width_mm':width, **{label:tuple(sorted([uid(pads['C909.1']),uid(pads[target])])) in pairs
                 for label,target in [('C909_to_C911','C911.1'),('C909_to_L901','L901.2'),('C909_to_U1201','U1201.5')]}})
tracks=[]
for t in new:
    layer=c.board.GetLayerName(t.GetLayer())
    own=unary_union([s for (u,ly),s in c.shapes.items() if ly==layer and isinstance(c.by_id[u],pcb.PAD) and c.by_id[u].GetNetname()==t.GetNetname()])
    outside=c.shapes[uid(t),layer].difference(own)
    hits=[]
    for f in c.footprints:
        area=outside.intersection(fab(f)).area
        if area>1e-6:
            hits.append({'reference':f.GetReference(),'mounted_layer':c.board.GetLayerName(f.GetLayer()),
                         'same_face':f.GetLayer()==t.GetLayer(),'outside_pad_nominal_projection_mm2':area})
    tracks.append({'uuid':uid(t),'net':t.GetNetname(),'layer':layer,'width_mm':t.GetWidth()/1e6,
                   'start_mm':xy(t.GetStart()),'end_mm':xy(t.GetEnd()),
                   'length_mm':LineString([xy(t.GetStart()),xy(t.GetEnd())]).length,'body_projections':hits})
refs=sorted({h['reference'] for r in tracks for h in r['body_projections']}|{'C909','C911'})
fps={f.GetReference():f for f in c.footprints}
data={'scope':__doc__,'source_sha256':a.sha,'candidate_sha256':c.sha,
      'counts':{'segments':len(c.segments),'vias':len(c.vias),'footprints':len(c.footprints),'new_segments':len(new)},
      'new_supply_width_checks':rows,
      'HEAD_6V_RAW_groups':[g['pads'] for g in groups(c,'/HEAD_6V_RAW')],
      'HEAD_VM_groups':[g['pads'] for g in groups(c,'/HEAD_VM')],
      'new_tracks':tracks,
      'same_face_nominal_body_hit_count':sum(h['same_face'] for r in tracks for h in r['body_projections']),
      'new_vias':[{'uuid':uid(v),**via_snapshot(c.board,v),'native_contact_layers':via_contact_layers(c.board,v)} for v in c.vias if uid(v) not in a.by_id],
      'projected_components':{r:{'value':fps[r].GetValue(),'layer':c.board.GetLayerName(fps[r].GetLayer()),
                                 'position_mm':xy(fps[r].GetPosition()),'angle_deg':fps[r].GetOrientationDegrees()} for r in refs},
      'limits':['New connectivity is screened as well as preservation of old pairs.',
                'Copper erosion and native connectivity do not qualify plated-barrel current, ripple, ESR/ESL or temperature.',
                'Nominal Fab/fallback bodies are not manufacturer maxima or measured envelopes.'],
      'physical':'NOT_TESTED','manufacturing_release':False}
out.write_text(json.dumps(data,indent=2)+'\n')
assert hashlib.sha256(Path(a.path).read_bytes()).hexdigest()==a.sha
print(json.dumps({k:data[k] for k in ['candidate_sha256','counts','new_supply_width_checks','HEAD_6V_RAW_groups','same_face_nominal_body_hit_count','new_vias']}),flush=True)
