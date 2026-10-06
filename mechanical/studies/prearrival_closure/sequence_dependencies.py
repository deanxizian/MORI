"""Check assembly ordering across subassemblies, not only isolated operations."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
exec(compile((HERE/'rigid_assembly_paths.py').read_text().split('# Parts are handled')[0],str(HERE/'rigid_assembly_paths.py'),'exec'))
from interface_completion import axial
upper=with_inserts({'Body_Upper'})|select('Speaker','Rear_Interface','USB_Receptacle','Power_Switch','Frame_Screw')
check('fixed_bridge_after_upper_shell',with_inserts({'Yaw_Base'}),core|drive|upper,[0,0,1],90,.5)
check('yoke_after_upper_shell',yoke,core|drive|upper|{'Yaw_Base','Yaw_Bearing'},[0,0,1],90,.5)
ft=json.loads((HERE/'assembly_preflight.json').read_text())
tools=[]
for r in ft['fasteners']:
    if not r['id'].startswith('Yaw_Base'):continue
    p=np.array(r['head_top_mm']);a=np.array(r['axis']);rad=1.16
    shapes=[axial(rad,70,p+a*35.04,a)]
    ref=np.array([0.,0,1.]);u=np.cross(a,ref);u/=np.linalg.norm(u);v=np.cross(a,u)
    for angle in range(0,360,5):
        t=math.radians(angle);b=u*math.cos(t)+v*math.sin(t)
        shapes.append(axial(rad,20,p+a*(70-rad)+b*10,b))
    hits=[]
    for i,m in enumerate(shapes):
        bb=np.array(m.bounding_box())
        for n in sorted(upper):
            s=ss[n]
            if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
            volume=max(0,(m^s.m).volume())
            if volume>.02:hits.append(dict(part=n,volume_mm3=volume,tool_piece=i))
    tools.append(dict(id=r['id'],status='FAIL' if hits else 'PASS',additional_fixture=sorted(upper),hits=hits))
out=dict(source_blend_sha256=hashlib.sha256((PROJECT/'mechanical/mori_v1_2.blend').read_bytes()).hexdigest(),paths=results,tools=tools,status='PASS' if all(r['status']=='PASS' for r in results+tools) else 'BLOCKED')
(HERE/'sequence_dependencies.json').write_text(json.dumps(out,indent=2)+'\n')
# Try the existing shell path both with the bridge fixed and as a loose
# subassembly carried inside the upper shell. Do not silently omit it.
prior=json.loads((PROJECT/'mechanical/reports/assembly_issue_validation.json').read_text())['body_service']['upper_shell']
b=prior['path'];origin=Vector((0,0,D['body_z']))
def pose(a,y,z):return Matrix.Translation((0,y,z))@Matrix.Translation(origin)@Matrix.Rotation(math.radians(a),4,'X')@Matrix.Translation(-origin)
poses=[pose(b['tilt_x_deg']*u,0,b['initial_lift_mm']*u) for u in np.linspace(0,1,61)]
poses += [pose(b['tilt_x_deg'],y,b['initial_lift_mm']) for y in np.linspace(0,-b['rear_translation_mm'],57)[1:]]
poses += [pose(b['tilt_x_deg'],-b['rear_translation_mm'],z) for z in np.arange(b['initial_lift_mm']+.5,b['final_lift_mm']+.01,.5)]
def posecheck(label,moving,fixed):
    bad=[];count=0
    for j,tr in enumerate(poses):
        count+=1
        for n in moving:
            m=ss[n].m.transform(np.array(tr)[:3,:]);bb=np.array(m.bounding_box())
            for k in fixed:
                t=ss[k]
                if np.any(bb[3:]<t.lo) or np.any(t.hi<bb[:3]):continue
                volume=max(0,(m^t.m).volume())
                if volume>.05:bad.append(dict(pose=j,moving=n,fixed=k,volume_mm3=volume))
            if len(bad)>30:break
        if len(bad)>30:break
    r=dict(id=label,status='PASS' if not bad else 'FAIL',samples=count,moving=sorted(moving),fixture=sorted(fixed),hits=bad)
    print('ORDER',label,r['status'],bad[:2],flush=True);return r
out['order_alternatives']=[posecheck('upper_shell_around_fixed_bridge',prior['moving'],{'Yaw_Base'})]
carried=set(prior['moving'])|{'Yaw_Base'}|select('Yaw_Base_','Yaw_Bearing')
carried-=select('Yaw_Base_-1_Screw','Yaw_Base_1_Screw')
out['order_alternatives'].append(posecheck('shell_carrying_loose_bridge',carried,core|drive))
out['order_alternatives'].append(posecheck('upper_shell_without_speaker_around_fixed_bridge',[n for n in prior['moving'] if not n.startswith('Speaker')],{'Yaw_Base'}))
check('bridge_into_detached_shell_from_below',with_inserts({'Yaw_Base'})|select('Yaw_Base_-1_Nut','Yaw_Base_1_Nut'),upper-select('Frame_Screw'),[0,0,-1],150,1)
out['short_leg_tool_alternatives']=[]
fixture=core|drive|upper|{'Yaw_Base','Yaw_Bearing'}|select('Yaw_Base_')
for r in ft['fasteners']:
    if not r['id'].startswith('Yaw_Base'):continue
    p=np.array(r['head_top_mm']);a=np.array(r['axis']);rad=1.16
    for short in [16,20,24]:
        clear=[];bad=[]
        for angle in range(0,360,2):
            t=math.radians(angle);v=np.array([0.,math.sin(t),-math.cos(t)])
            # Short leg engages 0.7mm into the hex, long leg points down.
            m=axial(rad,short,p+a*(short/2-.7),a)+axial(rad,70,p+a*(short-.7)+v*35,v)
            bb=np.array(m.bounding_box());hits=[]
            for k in fixture-{r['id']}:
                s=ss[k]
                if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
                volume=max(0,(m^s.m).volume())
                if volume>.02:hits.append(dict(part=k,volume_mm3=volume))
            if hits:bad.append(dict(angle_deg=angle,hits=hits))
            else:clear.append(angle)
        run=best=0;cs=set(clear)
        for angle in list(range(0,360,2))*2:
            run=run+1 if angle in cs else 0;best=max(run,best)
        span=min(360,max(0,(best-1)*2))
        out['short_leg_tool_alternatives'].append(dict(id=r['id'],short_leg_mm=short,long_leg_mm=70,clear_span_deg=span,clear_angles=clear,status='PASS' if span>=60 else 'FAIL',blocked=bad))
        print('SHORT_TOOL',r['id'],short,span,flush=True)
    sign=int(a[0]);check('bridge_screw_from_open_bottom_'+r['id'],{r['id']},fixture-{r['id']},a,33,.5,waypoints=[[0,0,0],[sign*8,0,0],[sign*8,0,-25]])
out['paths']=results
speaker_moving=select('Speaker','Speaker_Gasket')-select('Speaker_Insert','Speaker_Screw')
speaker_fixture=core|drive|upper|{'Yaw_Base','Yaw_Bearing'}
speaker_fixture-=speaker_moving|select('Speaker_Screw','Frame_Screw')
for y in [0,-3,-5,-8,-10]:
    check('speaker_after_shell_y'+str(y),speaker_moving,speaker_fixture,[0,0,-1],100,1,waypoints=[[0,0,0],[0,y,0],[0,y,-100]])
out['speaker_tool_access']=[]
for r in ft['fasteners']:
    if not r['id'].startswith('Speaker'):continue
    p=np.array(r['head_top_mm']);a=np.array(r['axis']);hits=[]
    for label,m in [('shaft',axial(2,60,p+a*30.04,a)),('handle',axial(9,100,p+a*110.04,a))]:
        bb=np.array(m.bounding_box())
        for k in speaker_fixture-{r['id']}:
            s=ss[k]
            if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
            volume=max(0,(m^s.m).volume())
            if volume>.02:hits.append(dict(part=k,volume_mm3=volume,piece=label))
    out['speaker_tool_access'].append(dict(id=r['id'],status='PASS' if not hits else 'FAIL',hits=hits))
    print('SPEAKER_TOOL',r['id'],hits[:3],flush=True)
out['status']='BLOCKED' # A complete, mutually compatible sequence must be selected.
(HERE/'sequence_dependencies.json').write_text(json.dumps(out,indent=2)+'\n')
print('SEQUENCE',out['status'],[(r['id'],r['status']) for r in tools],flush=True)
