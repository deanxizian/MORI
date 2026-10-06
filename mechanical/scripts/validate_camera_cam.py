"""Independent M1.48 scope, accepted-solid, wall, motion and tool-path audit."""
import sys,time,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid,rigidtr
from validate_head_cleanup import geometry_record
from export import topology

_baseline=None
def declared_ids():
    q=P.get('camera_cam_completion',{})
    return set(q['changed_existing_ids']) if q.get('enabled') else set()
def npz_solid(path):
    d=np.load(path)
    return manifold.Manifold(manifold.Mesh64(np.array(d['vertices_mm'],copy=True),np.array(d['triangles'],dtype=np.uint64,copy=True)))
def approved(name):
    q=P['camera_cam_completion']
    path=q['camera']['approved_mesh'] if name=='Display_Frame' else q['cam_screws']['approved_mesh_directory']+'/'+name+'.npz'
    return npz_solid(PROJECT/path)
def baseline():
    global _baseline
    if _baseline is None:
        from validate_thin_cleanup import load_reference
        _baseline=load_reference(PROJECT/P['camera_cam_completion']['baseline_blend'])
    return _baseline
def prior_solid(name,current):
    """Undo only the immutable approved M1.48 delta for historical checks."""
    from neck_reference import prior_solid as before_M1_49
    current=before_M1_49(name,current)
    if name not in declared_ids():return current
    a=baseline()[name]['solid'];b=approved(name)
    return (current-(b-a))+(a-b)

def hits(m,targets,exclude=(),tol=.0001):
    b=np.array(m.bounding_box());out=[]
    for n,t in targets.items():
        if n in exclude:continue
        c=np.array(t.bounding_box())
        if np.any(b[3:]<c[:3]) or np.any(c[3:]<b[:3]):continue
        v=max(0.,float((m^t).volume()))
        if v>tol:out.append({'id':n,'intersection_mm3':v})
    return out

def run(ss=None,check=None):
    started=time.time();q=P['camera_cam_completion'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    if ss is None:
        load_collections()
        for c in ['DOCK','COUPONS','KEEP_OUT','DATUMS']:COLS[c].hide_viewport=False
        assembled();bpy.context.view_layer.update()
        ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.get('group') not in ['dock','coupon']}
    now={n:geometry_record(s.o) for n,s in ss.items()};old=baseline();ids=declared_ids();ms={n:s.m for n,s in ss.items()}
    changed=sorted(n for n in set(now)&set(old) if now[n]!=old[n]['record'])
    added=sorted(set(now)-set(old));removed=sorted(set(old)-set(now));fail=[];report={}
    def emit(key,ok,data):
        report[key]={'status':'PASS' if ok else 'FAIL',**data}
        if not ok:fail.append(key)
        print('CAMERA_CAM_CHECK',key,report[key]['status'],flush=True)
    emit('scope',set(changed)==ids|declared_neck_capacity_changes()|declared_cam_entry_changes() and not added and not removed,{'changed':changed,'unchanged_count':len(now)-len(changed),'compared_count':len(now),'added':added,'removed':removed})
    shapes=[]
    for n in sorted(ids):
        a=approved(n);b=ms[n];t=topology(ss[n].v,ss[n].f.tolist())
        delta=max(0,(a-b).volume())+max(0,(b-a).volume())
        ok=delta<.003 and len(b.decompose())==1 and not any(t[k] for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles'])
        shapes.append({'id':n,'status':'PASS' if ok else 'FAIL','candidate_difference_mm3':delta,'topology':t})
    emit('approved_solids',all(r['status']=='PASS' for r in shapes),{'rows':shapes,'comparison_tolerance_mm3':.003,'tolerance_scope':'float32 saved vertices versus approved float64 solid, not manufacturing tolerance'})
    camera=ms['Display_Frame'];shell=ms['Head_Front'];before=old['Display_Frame']['solid']
    gap=float(camera.min_gap(shell,1));overlap=max(0,(camera^shell).volume());extra=max(0,(camera-before).volume())
    source=json.loads((PROJECT/'mechanical/studies/prearrival_finish/camera_top_clearance/construction.json').read_text())
    rc=np.array(source['camera_local_basis_columns']);p=np.array(source['camera_pupil_world_mm']);wall=[]
    for x in [-4.,-2.,0.,2.,4.]:
        for w in [-4.,-3.,-2.,-1.1]:
            start=p+rc@np.array([x,-9.,w]);end=p+rc@np.array([x,-3.,w]);hs=camera.ray_cast(start.tolist(),end.tolist());ds=[]
            for h in hs:
                if not ds or abs(h.distance-ds[-1])>1e-6:ds.append(h.distance)
            thickness=(ds[1]-ds[0])*np.linalg.norm(end-start) if len(ds)>=2 else 0.
            wall.append({'x_mm':x,'w_mm':w,'thickness_mm':float(thickness)})
    emit('camera_clearance',gap>=q['camera']['minimum_nominal_shell_gap_mm'] and overlap<1e-6 and extra<.003 and all(abs(r['thickness_mm']-1.2)<.0001 for r in wall),{'shell_gap_mm':gap,'shell_overlap_mm3':overlap,'added_vs_baseline_mm3':extra,'wall_samples':wall,'unchanged_capture_datums':all(now[n]==old[n]['record'] for n in ['Camera_PCB','Camera_Lens','Head_Front'])})
    historical=json.loads((PROJECT/q['camera']['historical_verification']).read_text());paths=[]
    for row in historical['paths']:
        moving=set(row['moving']);fixed=set(row['fixed']);m=manifold.Manifold.batch_boolean([ms[n] for n in sorted(moving)],manifold.OpType.Add)
        stage=row['stage'];distance=24. if stage=='camera_along_optical_axis' else 70. if stage=='optical_frame_front_entry' else 68.
        direction=np.array([0.,1.,math.tan(math.radians(10.)) if stage=='camera_along_optical_axis' else 0.]);bad=[]
        samples=np.arange(0,distance+.01,.5)
        for d in samples:
            h=hits(m.translate((direction*d).tolist()),{n:ms[n] for n in fixed},tol=1e-5)
            if h:bad.append({'distance_mm':float(d),'hits':h})
        paths.append({'stage':stage,'samples':len(samples),'moving':sorted(moving),'fixed':sorted(fixed),'failures':bad})
    emit('camera_assembly',all(not r['failures'] for r in paths),{'rows':paths,'scope':'Named rigid assembly stages only; full harness still BLOCKED'})
    sk=PROJECT/q['cam_screws']['approved_mesh_directory'];stage=json.loads((sk.parent/'cam_board_last/screen.json').read_text())
    fixed=(set(stage['fixed_objects'])&set(ms))|{'CAM_Mainboard','Onboard_MIC_L','Onboard_MIC_R'}|set(q['cam_screws']['ids'])
    tools=[];srows=[r for r in P['interface_completion']['inserts'] if r.get('screw') in q['cam_screws']['ids']]
    toolhistory=json.loads((sk/'verification.json').read_text())
    for r in srows:
        n=r['screw']
        for kind in ['work_sweep','entry_sweep','arrival_sweep']:
            path=sk/(n+'_'+kind+'.npz');m=npz_solid(path);ex=[n]+([r['id']] if kind=='arrival_sweep' else [])
            h=hits(m,{k:ms[k] for k in fixed},ex)
            tools.append({'screw':n,'kind':kind,'hits':h,'source_sha256':sha(path)})
    emit('CAM_tools',all(not r['hits'] for r in tools),{'checks':tools,'current_stage_parts':sorted(fixed),'deferred_parts':sorted(set(ms)-fixed),'angle_range_deg':[-30,30],'axial_travel_mm':8,'tool':'Wera950PKLS05022040001 1.5mm 90/4.5mm; conservative bend envelope','entry_choices':[{k:r[k] for k in ['id','selected_path']} for r in toolhistory['screw_arrival_paths']],'wire_scope':'No wire or unapproved channel adopted; earlier wire study retained as historical evidence.'})
    motion=[]
    for yaw in range(-60,61,10):
        Y=np.asarray(rigidtr(yaw,0))
        for pitch in range(-20,26,5):
            T=np.asarray(rigidtr(yaw,pitch));bad=[]
            for r in srows:
                n=r['screw'];m=ms[n]
                for k,t in ms.items():
                    if k in [n,r['id']]:continue
                    group=ss[k].group
                    placed=m if group=='pitch' else m.transform((np.linalg.inv(Y)@T)[:3,:4]) if group=='yaw' else m.transform(T[:3,:4])
                    bad.extend({'screw':n,**h} for h in hits(placed,{k:t}))
            motion.append({'yaw_deg':yaw,'pitch_deg':pitch,'hits':bad})
    emit('CAM_motion',all(not r['hits'] for r in motion),{'poses':len(motion),'rows':motion,'scope':'Four changed screws versus all current robot solids; only their own four thread pairs excluded'})
    receipt=json.loads((PROJECT/q['approval_record']).read_text());drift=[n for n,h in receipt['protected_hardware'].items() if sha(PROJECT/n)!=h]
    emit('hardware_read_only',not drift,{'protected_files':len(receipt['protected_hardware']),'changed_files':drift})
    report.update(status='FAIL' if fail else 'PASS',failed=fail,revision=P['revision'],source_blend_sha256=sha(Path(bpy.data.filepath)),baseline_blend_sha256=sha(PROJECT/q['baseline_blend']),script_sha256=sha(Path(__file__)),physical_validation='NOT_TESTED',manufacturing_release=False,elapsed_s=time.time()-started)
    save_json(ROOT/'reports/camera_cam_completion_validation.json',report)
    if check:check('camera_CAM_approved_completion',report['status'],'相机上沿与四枚CAM内六角螺钉：范围、候选、间隙与工具/运动复核',{'report':'camera_cam_completion_validation.json','failed':fail})
    return report

if __name__=='__main__':
    result=run()
    if result['status']!='PASS':raise SystemExit(1)
