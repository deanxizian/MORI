"""Native-vs-trial journal wall samples and exact mesh section extraction."""
from pathlib import Path
import sys,json,math
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,sha,np,manifold
from common import P
ctx=Context();layers={};topology={}

def mesh_stats(v,f):
    directed=np.vstack([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
    edges=np.sort(directed,axis=1)
    _,counts=np.unique(edges,axis=0,return_counts=True)
    area=np.linalg.norm(np.cross(v[f[:,1]]-v[f[:,0]],v[f[:,2]]-v[f[:,0]]),axis=1)/2
    return dict(vertices=len(v),triangles=len(f),non_two_face_edges=int(np.count_nonzero(counts!=2)),
                zero_area_faces=int(np.count_nonzero(area==0)),minimum_triangle_area_mm2=float(area.min()))

for name in ['Yaw_Base','Pitch_Yoke']:
    path=HERE/f'refined_{name}.npz';d=np.load(path)
    m=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
    topology[name]=dict(**mesh_stats(d['vertices_mm'],d['triangles']),components=len(m.decompose()),kernel=str(m.status()))
    layers[name]=m;layers[name+'_native']=ctx.ss[name].m
    layers[name+'_removed']=ctx.ss[name].m-m
for name in ['Yaw_Reaction_Link','Yaw_Bearing','Yaw_Anti_Lift_Keeper']:
    layers[name]=ctx.ss[name].m

def ray_bands(polygons,angle):
    e=np.array([math.cos(angle),math.sin(angle)])
    cross=lambda a,b:a[...,0]*b[...,1]-a[...,1]*b[...,0]
    values=[]
    for a in polygons:
        edge=np.roll(a,-1,axis=0)-a;den=cross(e,edge);valid=np.abs(den)>1e-12
        u=np.zeros(len(a));r=np.zeros(len(a))
        u[valid]=cross(a[valid],e)/den[valid];r[valid]=cross(a[valid],edge[valid])/den[valid]
        values.extend(r[valid&(u>=-1e-9)&(u<1-1e-9)&(r>0)].tolist())
    # Preserve crossing multiplicity. Collapsing a nearly coincident entry/exit
    # into one rounded value corrupts even/odd parity and creates missing rays.
    values=sorted(values)
    return None if len(values)%2 else list(zip(values[::2],values[1::2]))

journal_r=P['head_axial_retention']['bearing']['trial_journal_d_mm']/2
bearing=ctx.ss['Yaw_Bearing'];zs=np.linspace(bearing.lo[2]+.5,bearing.hi[2]-.25,17)
walls={}
for name in ['Pitch_Yoke_native','Pitch_Yoke']:
    rows=[];missing=[]
    for z in zs:
        polygons=[np.asarray(p) for p in layers[name].slice(float(z)).to_polygons()]
        for degrees in np.arange(.125,360,.5):
            bands=ray_bands(polygons,math.radians(degrees))
            material=[] if bands is None else [(a,min(b,journal_r)) for a,b in bands if a<journal_r and b>journal_r-.02]
            if len(material)!=1:
                missing.append(dict(z_mm=float(z),angle_deg=float(degrees),bands=bands));continue
            a,b=material[0];rows.append(dict(z_mm=float(z),angle_deg=float(degrees),inner_radius_mm=a,outer_radius_mm=b,thickness_mm=b-a))
    walls[name]=dict(sampled_rays=len(zs)*720,valid_rays=len(rows),missing=missing,
                     minimum=min(rows,key=lambda r:r['thickness_mm']))
sections={}
angle=math.pi/4
tr=np.array([[math.cos(angle),math.sin(angle),0.,0.],[0.,0.,1.,0.],[-math.sin(angle),math.cos(angle),0.,0.]])
sections['radial45']={n:[p.tolist() for p in m.transform(tr).slice(0).to_polygons()] for n,m in layers.items()}
for z in [141.,152.5,188.]:
    sections['Z'+str(z)]={n:[p.tolist() for p in m.slice(z).to_polygons()] for n,m in layers.items()}
ctx.assert_unchanged()
out=dict(status='PASS' if all(not r['missing'] for r in walls.values()) else 'BLOCKED',
         scope='Section extraction and finite journal-wall samples only; no strength certification',
         source_main_sha256=ctx.source_hash,script_sha256=sha(__file__),topology=topology,walls=walls,
         sources={n:sha(HERE/f'refined_{n}.npz') for n in ['Yaw_Base','Pitch_Yoke']},
         wall_scope='17 journal planes x 720 rays, excluding the bottom entry chamfer',
         all_part_minimum_wall='NOT_TESTED',strength='NOT_TESTED',main_applied=False)
(HERE/'sections.json').write_text(json.dumps(sections,ensure_ascii=False)+'\n')
out['sections_sha256']=sha(HERE/'sections.json')
(HERE/'section_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('SECTION_CHECK',out['status'],topology,{n:r['minimum'] for n,r in walls.items()},flush=True)
