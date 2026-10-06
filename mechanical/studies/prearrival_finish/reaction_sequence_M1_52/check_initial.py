"""Current native bench sequence diagnosis; no candidate geometry or main edits.

First isolate the collar/yoke dependency. A free bench manipulation cannot
qualify the still-unselected SCS0009 horn, spline or fastener stack.
"""
from pathlib import Path
import sys, json, time
OUT=Path(__file__).resolve().parent
PROJECT=OUT.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from harness_context import Context, np, sha
from common import P, manifold
from interface_completion import axial

ctx=Context();started=time.time();assert P['revision']=='V1.2-M1.52'
names=['Pitch_Yoke','Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut',
       'Yaw_Horn','Yaw_Lock_Screw','Yaw_Servo','Yaw_Output']
solids={n:ctx.ss[n].m for n in names}
metadata={n:dict(bounds_mm=list(m.bounding_box()),group=ctx.ss[n].group,
                 data_status=ctx.ss[n].o.get('data_status'),model_fidelity=ctx.ss[n].o.get('model_fidelity'),
                 interface_status=ctx.ss[n].o.get('interface_status')) for n,m in solids.items()}

def intersect(a,b):
    return max(0.,float((a^b).volume()))

def sampled_path(parts,targets,axis,travel=100,step=.25):
    first=None;count=0;min_gap=100.;witness=None
    for distance in np.arange(0,travel+step/2,step):
        delta=np.asarray(axis)*distance;count+=1
        for n,m in parts.items():
            posed=m.translate(delta.tolist())
            for target,t in targets.items():
                volume=intersect(posed,t)
                if volume>1e-6:
                    first=dict(moving=n,target=target,travel_mm=float(distance),overlap_mm3=volume);break
                gap=float(posed.min_gap(t,5))
                if gap<min_gap:min_gap=gap;witness=dict(moving=n,target=target,travel_mm=float(distance))
            if first:break
        if first:break
    return dict(status='BLOCKED' if first else 'PASS',axis=list(axis),travel_mm=travel,
                sample_step_mm=step,checked_samples=count,first_collision=first,
                minimum_sampled_gap_mm=min_gap,minimum_gap_witness=witness)

# Both directions are considered. Earlier studies only tried removal above the
# yoke; a useful current sequence may require preassembly from below instead.
rows=[]
groups={'bare_link':['Yaw_Reaction_Link'],
        'link_with_clamp_fasteners':['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut'],
        'link_with_horn':['Yaw_Reaction_Link','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Clamp_Nut','Yaw_Horn','Yaw_Lock_Screw']}
for label,members in groups.items():
    for direction in [-1,1]:
        r=sampled_path({n:solids[n] for n in members},{'Pitch_Yoke':solids['Pitch_Yoke']},[0,0,direction])
        rows.append(dict(case=label,**r));print('BENCH_COLLAR',label,direction,r['status'],r['first_collision'],flush=True)

# On a fully detached link the seats themselves must allow their hardware in.
# The mating screw/nut partner is deferred in this local entry check.
fasteners=[]
for name,axis in [('Yaw_Reaction_Clamp_Nut',[0,-1,0]),('Yaw_Reaction_Clamp_Screw',[0,1,0])]:
    r=sampled_path({name:solids[name]},{'Yaw_Reaction_Link':solids['Yaw_Reaction_Link']},axis,travel=40)
    fasteners.append(dict(part=name,**r));print('BARE_CLAMP_FASTENER',name,r['status'],r['first_collision'],flush=True)

# Source-derived reference slices expose the actual throat and collar. These
# are section data, not a replacement or a manufactured design drawing.
sections={}
for n in ['Pitch_Yoke','Yaw_Reaction_Link','Yaw_Horn']:
    sections[n]=[p.tolist() for p in solids[n].transform([[0,1,0,0],[0,0,1,0],[1,0,0,0]]).slice(0).to_polygons()]
ctx.assert_unchanged()
report=dict(revision=P['revision'],source_blend_sha256=ctx.source_hash,sources=ctx.sources,
            scope='Current isolated-yoke bench manipulations only; no final horn interface or whole assembly qualification',
            status='PASS',metadata=metadata,vertical_paths=rows,detached_clamp_fasteners=fasteners,
            full_reaction_preassembly='BLOCKED',full_harness='BLOCKED',physical_fit='NOT_TESTED',
            main_changed=False,C6_applied=False,sections_plane='X=0, displayed as Y/Z',sections=sections,
            script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'initial.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
for n,m in solids.items():
    a=m.to_mesh64();np.savez_compressed(OUT/(n+'.npz'),vertices_mm=a.vert_properties[:,:3],triangles=a.tri_verts)
print('CURRENT_BENCH_DIAGNOSIS_DONE',report['elapsed_s'],flush=True)
