"""Check the L-key against the stored candidate; span is endpoint difference."""
from pathlib import Path
TOOL_SCRIPT=Path(__file__).resolve();TOOL_ROOT=TOOL_SCRIPT.parent
HELPER=TOOL_ROOT/'verify_CAM_anchor_cleaned_installation.py';__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\nmemo = {}',1)[0],str(HELPER),'exec'),globals())
__file__=str(TOOL_SCRIPT)
from interface_completion import axial
mounts=json.loads((PROJECT_DIR/'mechanical/reports/prearrival_geometry.json').read_text())['servo_ears']
upper=next(r for r in mounts if r['id']=='Head_Pitch_Ear_0')
pn=P['assembly_issue_fixes']['pitch_nut']
p=np.array(upper['ear_top_mm'])+[pn['screw_head_height_mm']-.7,0,0];a=np.array([1,0,0])
tool=axial(.87,50,p+a*25,a)+axial(.87,14,p+a*50+[0,7,0],[0,1,0])+manifold.Manifold.sphere(.87,32).translate((p+a*50).tolist())
bench={n:s.m for n,s in solids.items() if n.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_')) and n!='Head_Pitch_Ear_0_Screw'}
angles=list(range(-120,121,2));hits=[]
for angle in angles:
    tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p))
    moving=tool.transform(np.array(tr)[:3,:])
    for n,m in bench.items():
        volume=max(0.,float((moving^m).volume()))
        if volume>.001:hits.append({'angle_deg':angle,'object':n,'intersection_mm3':volume})
longest=0;start=None;best=None
for angle in angles:
    if any(r['angle_deg']==angle for r in hits):start=None;continue
    if start is None:start=angle
    if angle-start>longest:longest=angle-start;best=[start,angle]
report={'status':'PASS' if longest>=60 else 'BLOCKED','scope':'Finite L-key turning samples on stored nominal solids',
        'script_sha256':sha(TOOL_SCRIPT),'helper_sha256':sha(HELPER),
        'source_main_sha256':main_hash,'candidate_blend_sha256':sha(candidate/'candidate.blend'),
        'candidate_yoke_sha256':sha(candidate/'Pitch_Yoke.npz'),
        'checked_angles_deg':angles,'angle_endpoints_deg':best,'sampled_span_deg':longest,
        'hits':hits,'obstacles':sorted(bench),'intersection_threshold_mm3':.001,
        'tool_reference':'PB 210 1.5; long50,short14,radius.87 mm allocation',
        'old_counting_correction':'Earlier 242 deg was sample count times step. 121 samples from -120 to120 span240 deg.',
        'continuous_rotation':'NOT_TESTED','hand_access':'NOT_TESTED','main_applied':False}
(candidate/'tool_replay.json').write_text(json.dumps(report,indent=2)+'\n')
assert sha(main)==main_hash
print('ANCHOR_TOOL',report['status'],longest,len(hits),flush=True)
