"""Wire-only alternative: free a front corridor for CAM pin1, no print edits."""
from pathlib import Path
import sys,json,time,itertools
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
sys.path.insert(0,str(HERE.parent/'harness_A8/body_prefix_v2'))
from harness_context import Context,np,sha
from route_family import family,rotate
from body_curve_geometry import make
from curve_clearance import prepared,pair,self_clear
from common import P
from validate import rigidtr
ctx=Context();started=time.time();read=lambda n:json.loads((HERE/n).read_text())
old=read('body_layered_four_screen.json');proof=read('current_source_verification.json')
assert proof['status']=='PASS'
for p,h in proof['sources'].items():assert sha(PROJECT/p)==h,p
for p,h in proof['inputs'].items():assert sha(HERE/p)==h,p
old_curves=np.load(HERE/'body_layered_four_candidates.npz')
pool=read('body_layered_screen.json');assert sha(HERE/'body_layered_screen.json')==old['inputs']['body_layered_screen.json']
original=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in original.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
base=family(z0=138,dip=.37,samples=7201);err=max(r['chord_error_mm'] for r in base)
angles=[11,22,33,125,144,163,0,49,135,153,42]
neck={f'wire{i}_y{r["yaw_deg"]}':rotate(r['points'],angles[i]) for i in range(11) for r in base}
hits=[];checks=0
for i in [1,2,10]:
    for yaw in range(-60,61,10):
        p=neck[f'wire{i}_y{yaw}']
        for group,t in targets.items():
            ctx.targets=t
            for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                issue=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=err,radius=P['neck_harness_capacity']['wire_allocations'][i]['OD_mm']/2)
                checks+=1
                if issue:hits.append(dict(slot=i,yaw=yaw,pitch=pitch,group=group,**issue));break
            if hits:break
        if hits:break
    if hits:break
ctx.targets=original
print('FRONT_NECK_SOLIDS',len(hits),checks,flush=True)
pair_rows=[];obstacles={};changed_rows=[];selected=None;full={};self_rows=[]
if not hits:
    # Every local wire pair is recalculated because the new phase changes the
    # relative position of three curves; no geometric spacing is inferred.
    for yaw in range(-60,61,10):
        items=[prepared(neck[f'wire{i}_y{yaw}'],s['OD_mm']/2,err) for i,s in enumerate(P['neck_harness_capacity']['wire_allocations'])]
        for i,j in itertools.combinations(range(11),2):
            pair_rows.append(dict(yaw=yaw,a=i,b=j,**pair(items[i],items[j])))
        for i in range(11):
            if i==10:continue
            row=next((r for r in old['selected'] if r['slot']==i),None)
            if row:
                assert row['pin']!=1
                obstacles[i,yaw]=prepared(old_curves[f'pin{row["pin"]}_y{yaw}'],.3302,max(err,row['chord_error_mm']))
            else:obstacles[i,yaw]=items[i]
    print('FRONT_NECK_PACK',sum(r['status']!='PASS' for r in pair_rows),flush=True)
if not hits and all(r['status']=='PASS' for r in pair_rows):
    unique={}
    for rows in pool['pools'].values():
        for row in rows:
            if row['pin']==1:
                key=tuple(row[k] for k in ['entry_deg','exit_deg','family','planar_radius_mm','lead_mm'])
                unique[key]=row
    # Try original selected geometries first, then every available finite family.
    options=sorted(unique.values(),key=lambda r:(r['slot']!=10,r['length_mm']))
    for oldrow in options:
        row=dict(oldrow,body_entry_angle_deg=42,slot=10)
        q=make(row,42,ctx.port_pins['motion_J5']['pins']['1'])
        if q is None:continue
        p,n,L,error=q
        issue=ctx.clear(p[:n],chord_error=error,ignore=['Plug_motion_J5']) or ctx.clear(p[n-1:],chord_error=error)
        result=dict(parameters={k:row[k] for k in ['entry_deg','exit_deg','family','planar_radius_mm','lead_mm']},status='BLOCKED',hit=issue)
        if issue:changed_rows.append(result);continue
        a=prepared(p,.3302,error);wire_hits=[]
        for (slot,yaw),b in obstacles.items():
            r=pair(a,b)
            if r['status']!='PASS':wire_hits.append(dict(slot=slot,yaw=yaw,**r));break
        if wire_hits:result['wire_hits']=wire_hits;changed_rows.append(result);continue
        # Fixed body candidate must also clear all current moving solids.
        for group,t in targets.items():
            ctx.targets=t
            for yaw in ([0] if group=='body' else range(-60,61,10)):
                for pitch in (range(-20,26,5) if group=='pitch' else [0]):
                    tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
                    for section,pts in [('stem',p[:n]),('tail',p[n-1:])]:
                        issue=ctx.clear(pts@tr[:3,:3].T+tr[:3,3],chord_error=error,ignore=['Plug_motion_J5'] if section=='stem' else [])
                        checks+=1
                        if issue:break
                    if issue:break
                if issue:break
            if issue:break
        ctx.targets=original
        if issue:result['motion_hit']=issue;changed_rows.append(result);continue
        own=[];temp={}
        for yaw in range(-60,61,10):
            curve=np.vstack([p,neck[f'wire10_y{yaw}'][1:]])
            r=self_clear(prepared(curve,.3302,max(err,error)))
            own.append(dict(yaw=yaw,**r));temp[f'pin1_y{yaw}']=curve
            if r['status']!='PASS':break
        if any(r['status']!='PASS' for r in own):result['self_hits']=own;changed_rows.append(result);continue
        selected=dict(row,length_mm=L,chord_error_mm=error,id='pin1_front42',plane_z_mm=float(ctx.port_pins['motion_J5']['pins']['1'][2]+row['lead_mm']+7))
        full=temp;self_rows=own;result['status']='PASS';changed_rows.append(result);break
ctx.targets=original;ctx.assert_unchanged()
np.savez_compressed(HERE/'front_neck_candidates.npz',**neck)
if selected:
    full.update({k:old_curves[k] for k in old_curves.files if not k.startswith('pin1_')})
    np.savez_compressed(HERE/'front_body_candidates.npz',**full)
status='PASS' if selected else 'BLOCKED'
report=dict(status=status,source_blend_sha256=ctx.source_hash,sources=ctx.sources,
    angles_deg=angles,neck_hits=hits,neck_pair_checks=pair_rows,body_trials=changed_rows,
    selected=selected,self_checks=self_rows,checks=checks,
    selected_other_body_rows=[r for r in old['selected'] if r['pin']!=1],
    local_length_mm=base[0]['length_mm'],local_chord_error_mm=err,
    minimum_local_sampled_bend_mm=min(r['minimum_sampled_bend_mm'] for r in base),
    curve_files={p.name:sha(p) for p in [HERE/'front_neck_candidates.npz']+([HERE/'front_body_candidates.npz'] if selected else [])},
    script_sha256=sha(Path(__file__)),inputs={n:sha(HERE/n) for n in ['current_source_verification.json','body_layered_screen.json','body_layered_four_screen.json','body_layered_four_candidates.npz','body_curve_geometry.py','curve_clearance.py','route_family.py']},
    scope='Wire-only revised local phases and pin1 body route; no upper fan or full harness closure',
    full_harness='BLOCKED',main_changed=False,anchors='NOT_TESTED',wired_assembly='NOT_TESTED',elapsed_s=time.time()-started)
(HERE/'front_route_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('FRONT_ROUTES_DONE',status,'bodytrials',len(changed_rows),'checks',checks,flush=True)
