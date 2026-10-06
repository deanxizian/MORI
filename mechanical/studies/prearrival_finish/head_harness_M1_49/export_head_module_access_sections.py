"""Actual solid sections and screw-position witnesses for the order review."""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];BASE=HERE/'remaining_routes'
OUT=BASE/'cam_restraints/power_sequence_review';OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import D
from mathutils import Matrix,Vector
ctx=Context();started=time.time();origin=Vector((0,0,D['body_z']))
sf=BASE/'cam_restraints/head_module_sequence_v2/review.json';stage=json.loads(sf.read_text())
for f,h in {**stage['sources'],**stage['inputs']}.items():assert sha(ROOT/f)==h,f
assert stage['status']=='PASS';lift=stage['selected_head_lift_mm']
raised=Matrix.Translation((0,0,14))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(15),4,'X')@Matrix.Translation(-origin)
sections={};parts=['Body_Upper','Yaw_Base','Pitch_Yoke','Head_Front','Head_Rear','Load_Frame','Yaw_Base_1_Screw']
for pose in ['closed','lifted']:
    result={}
    for n in parts:
        m=ctx.ss[n].m
        if pose=='lifted':
            if n in stage['moving_upper_module']:m=m.transform(np.asarray(raised)[:3,:])
            elif n in stage['moving_head_module']:m=m.translate([0,0,lift])
        # The head has a seam at Y=0; use Y=-1 for the lifted overview so the
        # cut shows shell material. The screw close-up stays on its Y=0 axis.
        result[n]=m.rotate([-90,0,0]).slice(1. if pose=='lifted' else 0.).to_polygons()
    sections[pose]=result
rows=[]
for name,sign in [('Yaw_Base_1_Screw',1),('Yaw_Base_-1_Screw',-1)]:
    s=ctx.ss[name];body=ctx.ss['Body_Upper'].m
    for d in [0.,.25,.5,1.,2.,4.,8.]:
        m=s.m.translate([sign*d,0,0]);v=float((m^body).volume())
        rows.append(dict(screw=name,withdrawal_mm=d,actual_solid_intersection_mm3=v,status='FAIL' if abs(v)>1e-6 else 'PASS'))
sections['withdrawn_screw_2mm']={'Yaw_Base_1_Screw':ctx.ss['Yaw_Base_1_Screw'].m.translate([2,0,0]).rotate([-90,0,0]).slice(0).to_polygons()}
ctx.assert_unchanged()
out=OUT/'sections.json';out.write_text(json.dumps(sections,default=lambda a:a.tolist())+'\n')
r=dict(status='PASS',scope='Actual-screw interference witnesses and exact Y=0 solid sections, not assembly qualification',
       sources=ctx.sources,inputs={str(sf.relative_to(ROOT)):sha(sf)},screw_witnesses=rows,
       section_file='sections.json',section_sha256=sha(out),head_lift_mm=lift,section_y_mm={'closed':0,'lifted':-1},
       main_changed=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
       script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'geometry_review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('HEAD_MODULE_ACCESS_SECTIONS_DONE',json.dumps(rows),flush=True)
