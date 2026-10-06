"""Fresh partial-route checks and native-solid illustration of the last conflict."""
from pathlib import Path
import itertools,json,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes/rear_separated_neck';OUT=BASE/'review';OUT.mkdir(exist_ok=True)
OLD=HERE/'remaining_routes/left_tall_balanced'
sys.path.insert(0,str(ROOT/'mechanical/scripts'));sys.path.insert(0,str(HERE))
from harness_context import Context,np,sha
from common import bpy,COLS
from route_family import family
from rear_neck_geometry import build
from curve_clearance import prepared,pair,self_clear
from validate import rigidtr
from render import camera
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
report=read(BASE/'neck_screen.json');nr=read(OLD/'neck_screen.json')
for r in [report,nr]:
    for f,h in {**r['sources'],**r['inputs']}.items():assert sha(ROOT/f)==h,f
assert sha(OLD/'neck_candidates.npz')==nr['curve_sha256']
case=next(r for r in report['results'] if r['power4_extra_radial_dip_mm']==1.1)
assert case['start_z_mm']==171. and case['modified_slots']==[4,5,7,8,9,10]
lane=next(r for r in nr['results'] if r['status']=='PASS');old=np.load(OLD/'neck_candidates.npz')
angles=lane['angles_deg'];turns={int(k):v for k,v in case['nominal_turns_deg'].items()}
rows=family(z0=149.,dip=.6,samples=7201);curves={};length_replay=[];point_replay=[]
error=max(lane['chord_error_mm'],max(r['chord_error_mm'] for r in case['curvature']))
for slot,row in itertools.product(range(11),rows):
    yaw=row['yaw_deg'];original=old[f'z149.0_dip0.6_wire{slot}_y{yaw}'];p=build(row,original,slot,angles,turns)
    curves[slot,yaw]=p
    if slot in turns:
        expected=next(r for r in case['lengths'] if r['slot']==slot and r['yaw']==yaw)['polygon_length_mm']
        delta=abs(float(np.linalg.norm(np.diff(p,axis=0),axis=1).sum())-expected);assert delta<1e-8
        length_replay.append(dict(slot=slot,yaw=yaw,length_delta_mm=delta))
for hit in case['hits']:
    tr=np.linalg.inv(np.asarray(rigidtr(hit['yaw'],0)));p=curves[hit['slot'],hit['yaw']]@tr[:3,:3].T+tr[:3,3]
    delta=float(np.min(np.linalg.norm(p-hit['point_mm'],axis=1)));assert delta<1e-8
    point_replay.append(dict(slot=hit['slot'],yaw=hit['yaw'],point_delta_mm=delta))
native=ctx.targets;groups={n:s.group if s.group in ['yaw','pitch'] else 'body' for n,s in ctx.ss.items()}
targets={g:{n:t for n,t in native.items() if groups.get(n,'body')==g} for g in ['body','yaw','pitch']}
hits=[];checks=0;self_rows=[];pairs=[]
for slot,yaw in itertools.product(range(11),range(-60,61,10)):
    p=curves[slot,yaw];radius=nr['OD_mm'][slot]/2;self_rows.append(dict(slot=slot,yaw=yaw,**self_clear(prepared(p,radius,error))))
    if slot not in turns:continue  # Identical samples to the hash-verified original native proof.
    for group,tg in targets.items():
        ctx.targets=tg
        for pitch in (range(-20,26,5) if group=='pitch' else [0]):
            tr=np.eye(4) if group=='body' else np.linalg.inv(np.asarray(rigidtr(yaw,pitch if group=='pitch' else 0)))
            hit=ctx.clear(p@tr[:3,:3].T+tr[:3,3],chord_error=error,radius=radius);checks+=1
            if hit:hits.append(dict(slot=slot,yaw=yaw,pitch=pitch,group=group,**hit))
for yaw in range(-60,61,10):
    items={s:prepared(curves[s,yaw],nr['OD_mm'][s]/2,error) for s in range(11)}
    for a,b in itertools.combinations(items,2):pairs.append(dict(yaw=yaw,a=a,b=b,**pair(items[a],items[b])))
assert checks==936 and len(pairs)==715 and len(self_rows)==143
other=[r for r in pairs if 5 not in [r['a'],r['b']]];assert len(other)==585
partial=not [h for h in hits if h['slot']!=5] and all(r['status']=='PASS' for r in other) and all(r['status']=='PASS' for r in self_rows if r['slot']!=5)
ctx.targets=native
# Quantify the zero-pose conflict against the actual Pitch_Yoke surface.
s=native['Pitch_Yoke'];p=curves[5,0];d,i=min((float(s['tree'].find_nearest(v)[3]),i) for i,v in enumerate(p.tolist()))
deepest=dict(slot=5,yaw=0,object='Pitch_Yoke',minimum_sampled_center_surface_distance_mm=d,wire_radius_mm=nr['OD_mm'][5]/2,point_mm=p[i].tolist(),
    note='Unsigned sampled distance; a distance smaller than the wire radius establishes local wire-volume overlap at that sample, not a structural strength result.')
arrays={f'wire{s}_y{y}':p for (s,y),p in curves.items()};np.savez_compressed(OUT/'curves.npz',**arrays)
tag='MORI_REAR_OUTLET_DIAG__';new=[]
for slot in range(11):
    p=curves[slot,0];cu=bpy.data.curves.new(tag+str(slot),'CURVE');cu.dimensions='3D';cu.bevel_depth=nr['OD_mm'][slot]/2;cu.bevel_resolution=3;cu.use_fill_caps=True
    sp=cu.splines.new('POLY');sp.points.add(len(p)-1)
    for v,point in zip(sp.points,p):v.co=(*point,1)
    o=bpy.data.objects.new(tag+'slot'+str(slot),cu);bpy.context.scene.collection.objects.link(o)
    o.color=(.95,.05,.04,1) if slot==5 else (.05,.67,.74,1) if slot>=7 else (1.,.55,.07,1)
    o['robot_part']=False;o['category']='PLACEHOLDER';o['data_status']='ASSUMED';o['scope']='Failed route candidate; variable local length and unfinished endpoints';new.append(o)
for c in COLS.values():c.hide_viewport=False;c.hide_render=False
scene=bpy.context.scene;scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='OBJECT';scene.display.shading.light='STUDIO'
scene.display.shading.show_cavity=True;scene.display.shading.cavity_type='BOTH';scene.display.shading.show_shadows=True;scene.display.shading.show_specular_highlight=False
scene.display.shading.background_type='WORLD';scene.world.color=(.86,.88,.90);scene.view_settings.view_transform='Standard';scene.render.film_transparent=False
scene.render.resolution_x=1200;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';images=[]
for name,eye,target,scale in [('rear_outlet_overview',(80,-135,237),(-5,-5,177),82),('rear_outlet_conflict',(-78,-120,248),(-8,-9,195),39)]:
    for o in scene.objects:
        if o.type in ['MESH','CURVE','FONT']:o.hide_render=True
    for n in ['Pitch_Yoke','Yaw_Bearing','Yaw_Servo','Pitch_Servo','CAM_Mainboard']:
        ctx.ss[n].o.hide_render=False;ctx.ss[n].o.color=(.57,.62,.64,1) if n=='Pitch_Yoke' else ctx.ss[n].o.color
    for o in new:o.hide_render=False;o.hide_set(False)
    cam=camera(tag+name,eye,target,scale);cam.data.clip_start=.1;scene.render.filepath=str(OUT/(name+'.png'))
    bpy.ops.render.render(write_still=True);images.append(dict(file=name+'.png',sha256=sha(OUT/(name+'.png'))))
ctx.assert_unchanged();blend=OUT/'MORI_M1_49_rear_outlet_diagnosis.blend';bpy.ops.wm.save_as_mainfile(filepath=str(blend));ctx.assert_unchanged()
inputs=[BASE/'neck_screen.json',OLD/'neck_screen.json',OLD/'neck_candidates.npz',HERE/'rear_neck_geometry.py',HERE/'route_family.py',HERE/'curve_clearance.py']
r=dict(status='PASS' if partial else 'BLOCKED',sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},
    scope='Diagnostic delivery and ten local paths excluding slot5. The full eleven-path set still fails; no full harness or constant-length claim.',
    excluded_slot=5,excluded_function='P_J18_1 / +5V_CAM in the current lower-route slot mapping',
    native_checks=checks,hits=hits,pairs=pairs,self_checks=self_rows,ten_local_pair_count=len(other),ten_local_paths='PASS' if partial else 'BLOCKED',
    length_replay=length_replay,conflict_point_replay=point_replay,deepest_zero_pose=deepest,images=images,blend_sha256=sha(blend),curve_sha256=sha(OUT/'curves.npz'),
    all_eleven_local_paths='BLOCKED',main_changed=False,C6_main_applied=False,full_harness='BLOCKED',constant_length='BLOCKED',anchors='NOT_TESTED',wired_assembly='NOT_TESTED',
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,indent=2)+'\n');print('REAR_OUTLET_DIAG_DONE',r['status'],deepest,flush=True)
