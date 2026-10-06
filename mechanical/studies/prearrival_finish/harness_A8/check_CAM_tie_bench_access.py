"""Explicit bench approach volumes for a formed tie allocation.

Neither a rigid preformed ring nor a cutter box is a flexible-tie assembly
simulation. Keep failed approaches and report precise scope.
"""
from pathlib import Path
BENCH_SCRIPT = Path(__file__).resolve()
BENCH_A8 = BENCH_SCRIPT.parent
BENCH_HELPER = BENCH_A8/'screen_CAM_tie_installation.py'
__file__ = str(BENCH_HELPER)
exec(compile(BENCH_HELPER.read_text().split('\n# Orienting',1)[0], str(BENCH_HELPER),'exec'), globals())
__file__ = str(BENCH_SCRIPT)
BENCH_OUT = BENCH_A8/'cam_tie_install'

bench_ids = {n for n in ss if n.startswith(('Pitch_Yoke','Pitch_Servo','Pitch_Output','Pitch_Bearing','Head_Pitch_Ear_'))}
bench = {n: s.m for n,s in ss.items() if n in bench_ids}
bench['Pitch_Yoke'] = TIE_HOST
band, points, length = ribbon(-6.5, TIE_HEAD_FRONT)
tie = band + TIE_HEAD

def clashes(m, targets):
    rows=[]
    for n, target in targets.items():
        if not overlap_boxes(m,target,.001): continue
        volume=max(0.,float((m^target).volume()))
        if volume > .001: rows.append({'object':n,'volume_mm3':volume})
    return rows

def gap_record(m, targets, cap=5.):
    best={'gap_mm':cap,'object':None,'search_cap_mm':cap}
    for n,target in targets.items():
        if not overlap_boxes(m,target,cap):continue
        d=float(m.min_gap(target,cap))
        if d<best['gap_mm']:best={'gap_mm':d,'object':n,'search_cap_mm':cap}
    return best

# Direct underside insertion of an already closed ring: no claim that this
# describes the flexible wrapping operation. If blocked, the ring must not be
# advertised as a simple slide-on fit.
slide_hits=[]
bare_slide_hits=[]
for dz in np.linspace(-12,0,121):
    for hit in clashes(tie.translate([0,0,float(dz)]),bench):
        slide_hits.append({'translation_z_mm':float(dz),**hit})
    for hit in clashes(tie.translate([0,0,float(dz)]),{'Pitch_Yoke':TIE_HOST}):
        bare_slide_hits.append({'translation_z_mm':float(dz),**hit})

# Conservative free-tail working corridor. The drawing provides flat length,
# not a preformed tail or latch channel. X includes +/-0.5mm trial channel
# offset plus a bent-tip allowance; this is not a supplier tolerance.
tail_corridor=box([TIE_CAVITY_X-3.,TIE_HEAD_FRONT,TIE_Z-1.35],
                  [TIE_CAVITY_X+3.,TIE_HEAD_FRONT+110.,TIE_Z+1.35])
tail_hits=clashes(tail_corridor,bench)

# Cutter 79 22 125 nominal catalogue dimensions: head A11/B10/D6.5,
# full tool 125x60x19mm. The allocated head includes opening allowance;
# handle and hinge shape are boxes, not vendor CAD or measured tooling.
# Tool long axis +Z; flush face approaches from +Y. Swept boxes include all
# translations 0..60mm in +Z, a continuous straight approach of this allocation.
front=TIE_HEAD_FRONT+.25
tip=TIE_Z-TIE_WIDTH/2
cutter_head=box([TIE_CAVITY_X-6.5,front,tip],
                [TIE_CAVITY_X+6.5,front+7.5,tip+10.])
cutter_body=box([TIE_CAVITY_X-31.,front,tip+10.],
                [TIE_CAVITY_X+31.,front+20.,tip+125.])
cutter=cutter_head+cutter_body
swept=box([TIE_CAVITY_X-6.5,front,tip],
          [TIE_CAVITY_X+6.5,front+7.5,tip+70.])+box(
          [TIE_CAVITY_X-31.,front,tip+10.],
          [TIE_CAVITY_X+31.,front+20.,tip+185.])
tool_hits=clashes(swept,bench|{'tie_head_allocation':TIE_HEAD,'formed_band':band})

# Loose upper leads stand behind the cutter before the pitch frame and CAM
# are fitted. These are local staging columns, not a complete cable route.
local_leads={}
for slot,x in enumerate(xx):
    local_leads[f'local_loose_lead_{slot}']=manifold.Manifold.cylinder(
        45.,(.6604/2+.001)/math.cos(math.pi/64),circular_segments=64).translate([float(x),-1.5,229.9])
lead_hits=clashes(swept,local_leads)

# Reuse the checked bare-servo route, now including the actual nonempty tie
# allocation and four local staged wires. This is an incremental obstacle
# check, not a replacement for the existing 209-part installation replay.
servo_path=[[0.,0.,0.],[6.,0.,0.],[6.,6.5,0.],[35.,6.5,0.],[35.,6.5,65.]]
servo_targets={'tie_head_allocation':TIE_HEAD,'formed_band':band}|local_leads
servo_hits=[];servo_samples=0;servo_clearances=[]
for segment,(p,q) in enumerate(zip(servo_path,servo_path[1:])):
    p,q=np.array(p),np.array(q)
    count=int(np.ceil(np.linalg.norm(q-p)/.1));nearest={'gap_mm':5.,'object':None}
    for j in range(count+1):
        delta=p+(q-p)*j/count
        if segment==0 or j:servo_samples+=1
        for name in ['Pitch_Servo','Pitch_Output']:
            moved=ss[name].m.translate(delta.tolist())
            for hit in clashes(moved,servo_targets):
                servo_hits.append({'moving':name,'translation_mm':delta.tolist(),**hit})
            gap=gap_record(moved,servo_targets)
            if gap['gap_mm']<nearest['gap_mm']:
                nearest=gap|{'moving':name,'translation_mm':delta.tolist()}
    step=float(np.linalg.norm(q-p)/count)
    servo_clearances.append({'segment':segment,**nearest,'step_mm':step,
       'continuous_gap_lower_bound_mm':max(0.,nearest['gap_mm']-step/2)})

# Record whether this same tool allocation conflicts with the final prescribed
# pitch-loop geometry. A collision is a real sequence constraint for this
# allocation, not proof that every cutter/tool orientation is impossible.
loop_hits=[]
arrays=np.load(BENCH_A8/'cam_fan_in/short_tail_v2/curves.npz')
mesh=swept.to_mesh64()
tree=BVHTree.FromPolygons(mesh.vert_properties[:,:3],mesh.tri_verts.tolist(),all_triangles=True)
for slot in range(4):
    curve=arrays[f'candidate0_slot{slot}_pitch0']
    for pt in curve:
        if not np.all(pt >= np.array(swept.bounding_box())[:3]-.331):continue
        if not np.all(pt <= np.array(swept.bounding_box())[3:]+.331):continue
        ball=manifold.Manifold.sphere(.331,16).translate(pt.tolist())
        if (ball ^ swept).volume()>1e-5:
            loop_hits.append({'slot':slot,'point_mm':pt.tolist()});break

for name,m in [('oriented_head',TIE_HEAD),('oriented_band',band),
               ('tail_corridor',tail_corridor),('cutter_allocation',cutter),('cutter_swept',swept)]:
    cache(BENCH_OUT/(name+'.npz'),m)
report={
 'status':'PASS' if not tool_hits and not lead_hits and not tail_hits else 'BLOCKED',
 'scope':'Tail and cutter working volumes on detached pitch-yoke bench assembly only',
 'source_main_sha256':source_hash,'script_sha256':sha(BENCH_SCRIPT),
 'candidate_sha256':sha(BENCH_A8/'cam_anchors/candidate_v3/cleaned/candidate.blend'),
 'bench_obstacle_ids':sorted(bench),
 'not_yet_fitted':['Yaw servo and its fasteners','Pitch cradle, display frame and CAM board','Head shells','Final upper service-loop shape'],
 'closed_ring_slide_from_below':{'status':'BLOCKED' if slide_hits else 'PASS','samples':121,'translation_mm':[[0,0,-12],[0,0,0]],'hits':slide_hits},
 'closed_ring_before_servo':{'status':'BLOCKED' if bare_slide_hits else 'PASS','samples':121,'hits':bare_slide_hits,'scope':'Rigid ring versus bare candidate Pitch_Yoke only; not threading, tightening or flexibility'},
 'servo_with_preplaced_tie':{'status':'BLOCKED' if servo_hits else 'PASS','checked_samples':servo_samples,'hits':servo_hits,'removal_waypoints_mm':servo_path,'segment_clearances':servo_clearances,'scope':'Incremental nonempty tie and four local staged-wire obstacles only; actual loose-tail shape and final tightening not checked'},
 'tail_corridor':{'status':'BLOCKED' if tail_hits else 'PASS','hits':tail_hits,'bounds_mm':list(tail_corridor.bounding_box()),'clearance':gap_record(tail_corridor,bench),'dimensions_evidence':'ASSUMED work allocation, not a bend/latch qualification'},
 'cutter_approach':{'status':'BLOCKED' if tool_hits or lead_hits else 'PASS','hits':tool_hits,'local_lead_hits':lead_hits,'clearance_to_bench':gap_record(swept,bench),'clearance_to_local_leads':gap_record(swept,local_leads),'continuous_translation_mm':60.,'tool_outline_evidence':'ASSUMED conservative boxes based on documented dimensions','cutting_force_and_hand_access':'NOT_TESTED'},
 'same_tool_with_final_pitch_loops':{'status':'BLOCKED' if loop_hits else 'NOT_TESTED','hits':loop_hits,'scope':'Intersection samples only; no continuous all-clear claim'},
 'tie_threading_and_tightening':'NOT_TESTED','all_anchors':'NOT_TESTED','full_harness_installation':'NOT_TESTED',
 'wire_insulation_and_pullout':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED'}
(BENCH_OUT/'bench_access.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('TIE_BENCH',report['status'],'slide_hits',len(slide_hits),'bare_slide_hits',len(bare_slide_hits),'servo_hits',len(servo_hits),'tail_hits',tail_hits,'tool_hits',tool_hits,'lead_hits',lead_hits,'final_loop_hits',loop_hits,flush=True)
