"""Inspect unadopted 11-conductor cut surfaces, preserving native geometry.

Radial material tests describe sampled geometry only, not a strength limit.
The ray crossing method follows yaw_service_M1_48/check_sections.py; no earlier
study initializer or alternative geometry is executed.
"""
from pathlib import Path
import sys,json,math
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(HERE.parent/'outer_harness_M1_48'))
from native_context import Context,sha,np,manifold
from common import P
ctx=Context();layers={};components={}
four_line='--four-line' in sys.argv
source_dir=HERE.parent/'yaw_service_M1_48' if four_line else HERE
suffix='_four_line' if four_line else ''
paths={n:source_dir/(('refined_'+n if four_line else n+'_trial')+'.npz') for n in ['Yaw_Base','Pitch_Yoke']}
for name in ['Yaw_Base','Pitch_Yoke']:
    path=paths[name];d=np.load(path)
    m=manifold.Manifold(manifold.Mesh64(d['vertices_mm'],d['triangles'].astype(np.uint64)))
    layers[name]=m;layers[name+'_native']=ctx.ss[name].m
    layers[name+'_removed']=ctx.ss[name].m-m
    components[name]=[dict(volume_mm3=float(c.volume()),bounds_mm=list(c.bounding_box()),
        triangles=int(c.num_tri())) for c in m.decompose()]
for name in ['Yaw_Reaction_Link','Yaw_Reaction_Retainer_Screw','Yaw_Reaction_Retainer_Nut','Yaw_Bearing','Yaw_Anti_Lift_Keeper']:
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
    values=sorted(values)
    return None if len(values)%2 else list(zip(values[::2],values[1::2]))

socket=[];lost_examples=[]
for z in [139.71,140.,141.,142.5,144.,145.,146.,147.]:
    polys={n:[np.asarray(p) for p in layers[n].slice(z).to_polygons()] for n in ['Yaw_Base_native','Yaw_Base']}
    losses=[];valid=0;changed=0;largest=0.;min_backing=1e6;minimum=None
    for deg in np.arange(.125,360,.5):
        theta=math.radians(deg);nominal_r=min(6.2,4.7/math.cos(theta)) if math.cos(theta)>0 else 6.2
        source=ray_bands(polys['Yaw_Base_native'],theta);trial=ray_bands(polys['Yaw_Base'],theta)
        # Only count original wall rays that begin at the D socket. Existing
        # screw/nut access gaps are excluded and separately visible in sections.
        orig=[] if source is None else [(a,b) for a,b in source if abs(a-nominal_r)<.035 and b>a+.05]
        if len(orig)!=1:continue
        valid+=1
        kept=[] if trial is None else [(a,b) for a,b in trial if abs(a-orig[0][0])<.01 and b>a+.01]
        if not kept:
            losses.append(float(deg))
            if len(lost_examples)<30:lost_examples.append(dict(z_mm=z,angle_deg=float(deg),original_bands=source,candidate_bands=trial))
            continue
        width=kept[0][1]-kept[0][0]
        if width<min_backing:min_backing=width;minimum=dict(z_mm=z,angle_deg=float(deg),backing_mm=width)
        reduction=orig[0][1]-kept[0][1]
        if reduction>.01:changed+=1;largest=max(largest,reduction)
    socket.append(dict(z_mm=z,original_contact_rays=valid,lost_contact_rays=len(losses),
        lost_contact_angles_deg=losses,thinned_contact_rays=changed,maximum_backing_loss_mm=largest,
        minimum_retained_backing=minimum))

journal_r=P['head_axial_retention']['bearing']['trial_journal_d_mm']/2
bearing=ctx.ss['Yaw_Bearing'];zs=np.linspace(bearing.lo[2]+.5,bearing.hi[2]-.25,17);walls={}
for name in ['Pitch_Yoke_native','Pitch_Yoke']:
    rows=[];missing=[]
    for z in zs:
        polygons=[np.asarray(p) for p in layers[name].slice(float(z)).to_polygons()]
        for degrees in np.arange(.125,360,.5):
            bands=ray_bands(polygons,math.radians(degrees))
            material=[] if bands is None else [(a,min(b,journal_r)) for a,b in bands if a<journal_r and b>journal_r-.02]
            if len(material)!=1:missing.append(dict(z_mm=float(z),angle_deg=float(degrees),bands=bands));continue
            a,b=material[0];rows.append(dict(z_mm=float(z),angle_deg=float(degrees),thickness_mm=b-a))
    walls[name]=dict(sampled_rays=len(zs)*720,valid_rays=len(rows),missing=missing,
        minimum=min(rows,key=lambda r:r['thickness_mm']))

sections={}
for z in [139.71,140.,141.,142.5,144.,146.,147.,152.5,165.,188.]:
    sections['Z'+str(z)]={n:[p.tolist() for p in m.slice(z).to_polygons()] for n,m in layers.items()}
for degrees in [0,45,135,180]:
    angle=math.radians(degrees)
    tr=np.array([[math.cos(angle),math.sin(angle),0.,0.],[0.,0.,1.,0.],[-math.sin(angle),math.cos(angle),0.,0.]])
    sections['radial'+str(degrees)]={n:[p.tolist() for p in m.transform(tr).slice(0).to_polygons()] for n,m in layers.items()}
ctx.assert_unchanged()
(HERE/('sections'+suffix+'.json')).write_text(json.dumps(sections,ensure_ascii=False)+'\n')
out=dict(status='BLOCKED',scope='Sampled channel-host support sections; candidate not adopted',
    source_main_sha256=ctx.source_hash,script_sha256=sha(__file__),
    variant='previous_four_line' if four_line else 'new_eleven_line',
    candidate_sources={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in paths.items()},
    components=components,socket_contact=socket,lost_contact_examples=lost_examples,journal_walls=walls,
    sections_sha256=sha(HERE/('sections'+suffix+'.json')),
    support_review='BLOCKED' if any(r['lost_contact_rays'] for r in socket) else 'NOT_TESTED',
    no_new_strength_threshold=True,all_part_minimum_wall='NOT_TESTED',strength='NOT_TESTED',main_applied=False)
(HERE/('section_checks'+suffix+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('HOST_SECTIONS',json.dumps(dict(components=components,
    socket=[{k:v for k,v in r.items() if k!='lost_contact_angles_deg'} for r in socket],
    journal={n:r['minimum'] for n,r in walls.items()})),flush=True)
