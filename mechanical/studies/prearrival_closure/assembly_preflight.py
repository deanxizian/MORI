"""Current-source staged fasteners, bare-print insert tooling and rigid plugs.

No source .blend, PCB, or print is modified. Tool requirements are explicit
envelopes, not an assertion that a particular hot-insert tool was purchased.
"""
import sys,json,hashlib,math,collections
from pathlib import Path
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid,rigidtr
from interface_completion import axial
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o) for o in parts() if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
names=set(ss);source=PROJECT/'mechanical/mori_v1_2.blend';sourcehash=hashlib.sha256(source.read_bytes()).hexdigest()
def hits(shape,targets,exclude=(),tolerance=.02):
    bb=np.array(shape.bounding_box());out=[]
    for n in targets:
        if n in exclude or n not in ss:continue
        s=ss[n]
        if np.any(bb[3:]<s.lo) or np.any(s.hi<bb[:3]):continue
        v=max(0,(shape^s.m).volume())
        if v>tolerance:out.append(dict(part=n,overlap_mm3=v))
    return out

# Selected hardware tool access, reevaluated against FINAL geometry.
# Use the established bench set rather than pretending every tool enters the
# closed robot. Selection of stages is recorded per screw and can be audited.
past=PROJECT/'mechanical/studies/interface_completion'
old={r['id']:r for r in json.loads((past/'fastener_current.json').read_text())}
stages={r['id']:r for r in json.loads((past/'bench_sequence_checks.json').read_text())['fasteners']}
lcd_axes={r['id']:r for r in json.loads((PROJECT/'mechanical/reports/readiness_geometry.json').read_text())['LCD']}
deferred={'Yaw_Lock_Screw','Pitch_Lock_Screw','Yaw_Reaction_Clamp_Screw','Yaw_Reaction_Retainer_Screw'}
inserts=P['interface_completion']['inserts'];updated={r['screw']:r for r in inserts if r.get('screw_length_mm')}
fasteners=[]
for n,f in old.items():
    if n not in ss:continue
    if n in deferred:
        fasteners.append(dict(id=n,status='BLOCKED',reason='Matching horn/shaft/locking vendor interface unresolved; do not qualify placeholder.'));continue
    a=-np.array(lcd_axes[n]['axis']) if n in lcd_axes else np.array(f['extracted_axis_outward']);a/=np.linalg.norm(a)
    # The extreme plane along known screw axis is the actual head top, avoiding
    # stale nominal lengths after approved catalogue replacements.
    s=ss[n];c=(s.lo+s.hi)/2;v=s.v@a;face=c+a*(max(v)-c@a)
    if n in lcd_axes:face=np.array(lcd_axes[n]['head_bearing_mm'])+a*P['readiness_completion']['lcd']['head_height_mm']
    bench=set(stages[n]['included_parts'])&names if n in stages else set()
    if not bench:
        fasteners.append(dict(id=n,status='BLOCKED',reason='Missing declared bench stage.'));continue
    trials=[]
    if n in ['Head_Pitch_Ear_0_Screw','Head_Pitch_Ear_1_Screw']:
        p=face-a*.7
        shape=axial(.87,50,p+a*25,a)+axial(.87,14,p+a*50+[0,7,0],[0,1,0])+manifold.Manifold.sphere(.87,32).translate((p+a*50).tolist())
        fixture={x for x in names if x.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_'))}-{n}
        hits_by_angle=[]
        for angle in range(-120,121,2):
            tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p))
            hh=hits(shape.transform(np.array(tr)[:3,:]),fixture)
            if hh:hits_by_angle.append(dict(angle_deg=angle,hits=hh))
        blocked_angles={r['angle_deg'] for r in hits_by_angle};longest=run=0
        for angle in range(-120,121,2):
            run=run+2 if angle not in blocked_angles else 0;longest=max(longest,run)
        longest=max(0,longest-2) # N samples span (N-1) intervals.
        fasteners.append(dict(id=n,status='PASS' if longest>=60 else 'FAIL',tool='PB210.1,5',stage='Detached yoke, pitch servo before yaw servo',clear_sampled_span_deg=longest,hits_by_angle=hits_by_angle,source_blend_sha256=sourcehash,head_top_mm=face.tolist(),axis=a.tolist(),tool_dimensions_mm=[1.5,50,14],sweep_step_deg=2));continue
    # PH1 exact catalogue blade for GB823; larger envelope for M3 and unspecified
    # original drive/hub heads. This is geometric access, drive recess fit is
    # separately retained as a source/physical qualification.
    choices=[('Wiha42415_PH1',2,60,9,100),('Wiha42416_PH1',2,80,9,100)]
    if any(t in n for t in ['Frame_Screw','Shell_Screw']):choices=[('PB190.2-100/6',3,100,17.5,105)]
    if n.startswith(('Wheel_Cap','Wheel_End')):choices=[('2.5AF_Lkey_70x20_envelope_requirement',1.45,70,0,0)]
    if n.startswith('Yaw_Base'):choices=[('2AF_Lkey_70x20_envelope_requirement',1.16,70,0,0)]
    for tool,rad,ln,gr,gl in choices:
        pieces=[('shaft',axial(rad,ln,face+a*(.04+ln/2),a))]
        if gl:pieces.append(('handle',axial(gr,gl,face+a*(.04+ln+gl/2),a)))
        hs=[]
        for label,m in pieces:
            hs.extend(dict(tool_piece=label,**r) for r in hits(m,bench,{n}))
        if 'Lkey' in tool:
            ref=np.array([0.,0,1.]) if abs(a[2])<.8 else np.array([0.,1,0])
            u=np.cross(a,ref);u/=np.linalg.norm(u);v=np.cross(a,u)
            # Complete transverse leg at the outer end; sampled every5deg.
            for theta in range(0,360,5):
                b=u*math.cos(math.radians(theta))+v*math.sin(math.radians(theta))
                arm=axial(rad,20,face+a*(70-rad)+b*10,b)
                hs.extend(dict(tool_piece='Lkey_arm',rotation_deg=theta,**r) for r in hits(arm,bench,{n}))
        trials.append(dict(tool=tool,hits=hs,shaft_radius_mm=rad,shaft_length_mm=ln,handle_radius_mm=gr,handle_length_mm=gl))
    fasteners.append(dict(id=n,status='PASS' if any(not t['hits'] for t in trials) else 'FAIL',stage=stages[n]['stage'],included_parts=sorted(bench),trials=trials,head_top_mm=face.tolist(),axis=a.tolist()))

# Heat-insert installation happens on the isolated print BEFORE assemblies.
# A supplier-specific tip is not selected: record the maximum envelope checked.
insert_rows=[]
for r in inserts:
    e=np.array(r['entry_mm']);a=np.array(r['outward']);host=r['host'];trials=[]
    for neck_r in [1.5,2.0]:
        sh=[('neck',axial(neck_r,10,e+a*5.04,a)),('barrel',axial(3.5,35,e+a*27.54,a)),('grip',axial(12,80,e+a*85.04,a))]
        hs=[]
        for label,m in sh:hs.extend(dict(tool_piece=label,**h) for h in hits(m,[host]))
        trials.append(dict(neck_diameter_mm=2*neck_r,neck_length_mm=10,barrel_mm=[7,35],grip_mm=[24,80],hits=hs))
    insert_rows.append(dict(id=r['id'],host=host,status='PASS' if any(not t['hits'] for t in trials) else 'FAIL',stage='Bare print held independently on bench; opposite support fixture separate',trials=trials,limits='ASSUMED tooling envelope requirement; tip end must match insert bore/annulus. Temperature, pressure, installation force and rear fixture need coupon/process validation.'))

# Current received P5R6 nominal plugs; compare the actual inventory hash before
# reusing manufacturer-derived housing objects.
prior=PROJECT/'mechanical/studies/prearrival_preparation'
mr=json.loads((prior/'mated_connector_review.json').read_text())
inv=PROJECT/'mechanical/sources/populated_P5/inventory.json'
assert mr['sources']['inventory']==hashlib.sha256(inv.read_bytes()).hexdigest(),'Received PCB inventory changed; rebuild mates instead of reusing stale plugs.'
with bpy.data.libraries.load(str(prior/'mated_connector_review.blend'),link=False) as (src,dst):dst.objects=[n for n in src.objects if n.startswith(PREFIX+'PREARRIVAL_Plug_')]
for o in dst.objects:
    if o:bpy.context.scene.collection.objects.link(o)
bpy.context.view_layer.update()
plugs={o.name.removeprefix(PREFIX+'PREARRIVAL_Plug_'):Solid(o) for o in dst.objects if o}
bench_body={n for n in names if ss[n].group=='body' and not n.startswith(('Body_','Battery','Yaw_','Speaker','Rear_Interface','USB_','Power_Switch','Shell_','Frame_','Wheel_Bearing'))}
bench_body.add('Body_IMU')
bench_rear={n for n in names if n.startswith(('Body_Upper','Speaker','Rear_Interface','USB_','Power_Switch','Frame_Insert','Shell_Insert'))}
plug_rows=[]
for r in mr['rows']:
    key=r['board']+'_'+r['ref'];p=plugs[key];a=np.array(r['axis']);owner=P['native_electronics']['boards'][r['board']]['object']
    fixture=bench_rear if r['board']=='rear' else bench_body
    ph=[]
    for d in np.arange(0,12.01,.5):
        ph.extend(dict(travel_mm=float(d),**h) for h in hits(p.m.translate((a*d).tolist()),fixture,{owner}))
    static=hits(p.m,names,{owner})
    native=[h for h in r['overlap_candidates'] if h['target'].startswith(owner+'/')]
    issue7=r['board']=='rear' and r['ref']=='J3'
    plug_rows.append(dict(board=r['board'],ref=r['ref'],mating=r['mating'],center_mm=r['center_mm'],axis=r['axis'],status='PASS' if not ph and not native and not static and not issue7 else 'BLOCKED',bench_path_status='PASS' if not ph and not native else 'FAIL',pending_issue7=issue7,issue7_note='Known interference with the proposed8.5mm WeAct socket stack; received M1.43 does not yet contain that candidate.' if issue7 else '',static_hits=static,native_other_component_hits=native,path_hits=ph,fixture=sorted(fixture),stage='Bare upper shell with rear interface and speaker' if r['board']=='rear' else 'Fastened electronics/frame subassembly before bridge, battery and shells',travel_mm=12,step_mm=.5))

out=dict(revision=P['revision'],source_blend_sha256=sourcehash,fasteners=fasteners,insert_installation=insert_rows,plugs=plug_rows,counts={'fasteners':dict(collections.Counter(r['status'] for r in fasteners)),'inserts':dict(collections.Counter(r['status'] for r in insert_rows)),'plugs':dict(collections.Counter(r['status'] for r in plug_rows))},status='FAIL' if any(r['status']=='FAIL' for r in fasteners+insert_rows) else 'BLOCKED',limits=['Declared staged tools only; hand gripping/heat and lead forces need real trial','L-key rows use explicit required tool envelopes, including72 transverse-arm poses; purchased tool length must match','P5R7 sources remain owned by hardware and unreceived','Rigid insertion volumes do not certify flexible wires or electrical pin assignment'])
(HERE/'assembly_preflight.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print('ASSEMBLY_PREFLIGHT',json.dumps(out['counts']),flush=True)
print('FASTENER_FAIL',[(r['id'],r.get('trials',[])[-1]['hits']) for r in fasteners if r['status']=='FAIL'],flush=True)
print('INSERT_FAIL',[(r['id'],r['trials'][0]['hits']) for r in insert_rows if r['status']=='FAIL'],flush=True)
print('PLUG_FAIL',[(r['board'],r['ref'],r['static_hits'],r['path_hits'][:2]) for r in plug_rows if r['status']!='PASS'],flush=True)
