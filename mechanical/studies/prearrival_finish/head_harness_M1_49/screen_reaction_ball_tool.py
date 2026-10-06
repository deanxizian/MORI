"""Finite articulation screen using a documented 1.5mm ball-end L-key.

An M2 socket-cap conversion is NOT adopted. Engagement and allowed angle/torque
remain unknown; only a conservative tool envelope is tested against solids.
"""
from pathlib import Path
import json,math,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3]
BASE=HERE/'remaining_routes';REST=BASE/'cam_restraints';OUT=REST/'reaction_ball_tool'
sys.path.insert(0,str(ROOT/'mechanical/scripts'))
from harness_context import Context,np,sha
from common import manifold
from interface_completion import axial
ctx=Context();started=time.time();read=lambda p:json.loads(p.read_text())
source=OUT/'source.json';spec=read(source);assert sha(OUT/spec['source_file'])==spec['source_sha256']
stagefile=REST/'inner_head_lowering/review.json';stage=read(stagefile)
for f,h in {**stage['sources'],**stage['inputs']}.items():assert sha(ROOT/f)==h,f
absent=set(stage['rows'][1]['not_yet_installed'])|{'Body_Lower'}|{n for n in ctx.ss if n.startswith(('Frame_Screw_','Shell_Screw_'))}
inputs=[source,OUT/spec['source_file'],stagefile,ROOT/'mechanical/scripts/interface_completion.py']
fixed={n:s.m for n,s in ctx.ss.items() if n not in absent}
for n,p in [('Yaw_Base',BASE/'c6_left_slot_entry/Yaw_Base_candidate.npz'),
            ('Pitch_Yoke',REST/'sliding_guide_v4/Pitch_Yoke_candidate.npz'),
            ('Pitch_Cradle',REST/'return_clamp_v3/Pitch_Cradle_candidate.npz'),
            ('connector_band',REST/'return_clamp_v3/band.npz'),('connector_head',REST/'return_clamp_v3/head.npz')]:
    inputs.append(p);a=np.load(p);fixed[n]=manifold.Manifold(manifold.Mesh64(a['vertices_mm'],a['triangles'].astype(np.uint64)))
fixed.update({n:t['m'] for n,t in ctx.targets.items() if n.startswith(('Plug_','fixed_wire_'))})
boxes={n:np.asarray(t.bounding_box()) for n,t in fixed.items()}
def failure(m,defer=()):
    bb=np.asarray(m.bounding_box())
    for n,t in fixed.items():
        if n in defer:continue
        tb=boxes[n]
        if np.any(bb[3:]+.3<tb[:3]) or np.any(tb[3:]+.3<bb[:3]):continue
        v=float((m^t).volume());gap=0. if abs(v)>1e-6 else float(m.min_gap(t,.301))
        if abs(v)>1e-6 or gap<.3:return dict(target=n,overlap_mm3=v,gap_mm_capped=gap)
    return None
def verts(m):return np.asarray(m.to_mesh64().vert_properties[:,:3])
# The catalogue gives a total width of2mm. Use radius1.01 rather than deriving
# only the regular-hex circumradius; ball and elbow profiles are not exact CAD.
rad=1.01;tip=np.array([0.,10.2,142.5]);rows=[];clear=[];saved={}
for defer in [(),('Plug_power_J3',)]:
 for tilt in np.arange(0,25.01,2.5):
  for azimuth in (range(0,360,5) if tilt else [0]):
    t=math.radians(float(tilt));a=math.radians(azimuth)
    d=np.array([math.sin(t)*math.cos(a),math.cos(t),math.sin(t)*math.sin(a)])
    # A240mm coaxial cylinder contains the full 90mm long shaft throughout
    # the150mm linear entry. This is exact for this circular shaft allocation.
    shaft=axial(rad,240.,tip+d*120.,d);hit=failure(shaft,defer)
    record=dict(deferred=list(defer),tilt_deg=float(tilt),azimuth_deg=azimuth,status='BLOCKED',failure=hit)
    if not hit:
        base=np.cross(d,np.array([0.,0.,1.]));base/=np.linalg.norm(base);other=np.cross(d,base)
        elbow=tip+d*90.;passes=[]
        for roll in range(0,360,10):
            angle=math.radians(roll);b=base*math.cos(angle)+other*math.sin(angle)
            arm=axial(rad,14.,elbow+b*7.,b);bend=manifold.Manifold.sphere(rad*math.sqrt(3),24).translate(elbow.tolist())
            hh=None
            for part in [arm,bend]:
                v=verts(part);sweep=manifold.Manifold.hull_points(np.vstack([v,v+d*150.]))
                hh=failure(sweep,defer)
                if hh:break
            if hh:record['failure']=hh;break
            passes.append(roll)
        record.update(roll_samples_passed=len(passes),status='PASS' if len(passes)==36 else 'BLOCKED')
        if record['status']=='PASS':
            clear.append(record);print('BALL_TOOL_CLEAR',record,flush=True)
            if len(clear)==1:
                for label,m in [('shaft',axial(rad,90.,tip+d*45.,d)),('arm',arm),('elbow',bend)]:
                    mesh=m.to_mesh64();saved[label+'_vertices']=mesh.vert_properties[:,:3];saved[label+'_triangles']=mesh.tri_verts
    rows.append(record)
 print('BALL_TOOL_STAGE',defer,'clear',len(clear),'rows',len(rows),flush=True)
ctx.assert_unchanged()
if saved:np.savez_compressed(OUT/'tool.npz',**saved)
r=dict(status='PASS' if clear else 'BLOCKED',scope='Finite tool-direction/roll screen and conservative straight entry sweeps; no engagement or fastening qualification',
    sources=ctx.sources,inputs={str(p.relative_to(ROOT)):sha(p) for p in inputs},tool=spec,
    assumed_tip_mm=tip.tolist(),tool_envelope_radius_mm=rad,entry_travel_mm=150,tilt_range_deg=[0,25],
    allowed_manufacturer_articulation_angle=None,clear=clear,rows=rows,absent=sorted(absent),
    continuous_rotation='NOT_TESTED',matching_screw_recess='BLOCKED',tightening_torque='NOT_TESTED',
    main_changed=False,approved=False,C6_main_applied=False,full_harness='BLOCKED',Yaw_Reaction_Link_present=True,
    script_sha256=sha(Path(__file__)),elapsed_s=time.time()-started)
(OUT/'review.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n')
print('REACTION_BALL_TOOL_DONE',r['status'],len(clear),r['elapsed_s'],flush=True)
