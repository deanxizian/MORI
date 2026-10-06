"""Check both conditional CAM end families against all four earlier UART paths."""
from pathlib import Path
import json,hashlib,math,itertools
import numpy as np
from mathutils import Vector,Matrix
from mathutils.kdtree import KDTree
HERE=Path(__file__).resolve().parent;OUT=HERE/'cam_pitch_port';ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads((OUT/'departure_screen.json').read_text())
paths=np.load(OUT/'departure_curves.npz');body=np.load(HERE/'body_prefix_v2/body_to_yaw_curves.npz')
meta=json.loads((HERE/'body_prefix_v2/body_to_yaw_motion.json').read_text())
assert d['source_curves_sha256']==sha(OUT/'departure_curves.npz')
assert meta['curves_sha256']==sha(HERE/'body_prefix_v2/body_to_yaw_curves.npz')
P=json.loads((ROOT/'config/geometry.json').read_text());head_z=222.
# Read the actual head datum from the shared project derivation.
import sys
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from common import D
head_z=D['head_z']
def samples(points,step):
    p=np.vstack([np.linspace(a,b,max(1,math.ceil(np.linalg.norm(b-a)/step))+1)[:-1] for a,b in zip(points,points[1:])]+[points[-1:]])
    return p,float(np.linalg.norm(np.diff(p,axis=0),axis=1).max())
rows=[];limits=[]
for family in d['selected']:
    name=family['direction'];minimum=math.inf;worst=None
    head_samples=[samples(paths[f'{name}_slot{i}'],.02) for i in range(4)]
    for yaw in d['head_pose_set']['yaw_deg']:
        cache=[]
        for pin in range(1,5):
            points,step=samples(body[f'pin{pin}_yaw{yaw}'],.02);tree=KDTree(len(points))
            for j,p in enumerate(points):tree.insert(Vector(p),j)
            tree.balance();err=next(r['curve_error_bound_mm'] for r in meta['rows'] if r['pin']==pin and r['yaw_deg']==yaw)
            cache.append((pin,tree,step,err))
        for pitch in d['head_pose_set']['pitch_deg']:
            c=Vector([0,0,head_z]);tr=np.array(Matrix.Translation(c)@Matrix.Rotation(math.radians(yaw),4,'Z')@Matrix.Rotation(math.radians(pitch),4,'X')@Matrix.Translation(-c))
            for i,(p,hs) in enumerate(head_samples):
                pts=p@tr[:3,:3].T+tr[:3,3]
                for pin,tree,bs,err in cache:
                    distance=min(float(tree.find(Vector(q))[2]) for q in pts)
                    gap=distance-(hs+bs)/2-err-family['curve_error_bounds_mm'][i]-.6604-1e-4
                    row={'family':name,'yaw_deg':yaw,'pitch_deg':pitch,'head_slot_index':i,'body_pin':pin,
                         'status':'PASS' if gap>=.3 else 'BLOCKED','surface_gap_bound_mm':gap}
                    rows.append(row)
                    if gap<minimum:minimum=gap;worst=row
    limits.append({'family':name,'status':'PASS' if minimum>=.3 else 'BLOCKED','minimum_surface_gap_bound_mm':minimum,'worst':worst})
    print('CAM_END_COEXISTENCE',name,minimum,flush=True)
result={'status':'PASS' if all(r['status']=='PASS' for r in limits) else 'BLOCKED',
    'scope':'Conditional pitch-fixed CAM ends versus four existing body/yaw UART segments across130 finite poses; connecting service loop still absent',
    'source_script_sha256':sha(Path(__file__)),'source_main_sha256':sha(ROOT/'mechanical/mori_v1_2.blend'),
    'source_departure_sha256':sha(OUT/'departure_screen.json'),'source_head_curves_sha256':sha(OUT/'departure_curves.npz'),
    'source_body_curves_sha256':sha(HERE/'body_prefix_v2/body_to_yaw_curves.npz'),'source_body_motion_sha256':sha(HERE/'body_prefix_v2/body_to_yaw_motion.json'),
    'head_pivot_z_mm':head_z,'pair_count':len(rows),'families':limits,'rows':rows,
    'method':'Nearest dense chord samples, subtract both sample halfsteps and both analytic chord-error bounds plus0.0001mm allowance',
    'minimum_surface_gap_required_mm':.3,'physical_pin_numbering':'BLOCKED','main_applied':False,
    'whole_harness':'BLOCKED','manufacturing_release':False}
(OUT/'coexistence_screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('CAM_END_COEXISTENCE_DONE',result['status'],len(rows),flush=True)
