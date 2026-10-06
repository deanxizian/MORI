"""Integrate the trial grip bed and add a conservative catalogue tie envelope.

This writes an independent candidate only. The cable tie's installed form is
an assumption; catalogue dimensions do not certify grip or wire pullout.
"""
from pathlib import Path
CLAMP_SCRIPT=Path(__file__).resolve();CLAMP_ROOT=CLAMP_SCRIPT.parent
CLAMP_HELPER=CLAMP_ROOT/'screen_CAM_anchor_support.py';__file__=str(CLAMP_HELPER)
exec(compile(CLAMP_HELPER.read_text().split('\nhost=ss[',1)[0],str(CLAMP_HELPER),'exec'),globals())
__file__=str(CLAMP_SCRIPT)
OUT=CLAMP_ROOT/'cam_anchors/candidate_v3';OUT.mkdir(parents=True,exist_ok=True)
from interface_completion import replace_owned,axial
from validate_head_cleanup import geometry_record
before={n:geometry_record(s.o) for n,s in ss.items()}
host=ss['Pitch_Yoke'].m
xc0=float(xx.min()-1.2);xc1=float(xx.max()+1.2)
def rr(lo,hi,r):
    x0,y0=lo;x1,y1=hi;points=[]
    for cx,cy,start in [(x1-r,y1-r,0),(x0+r,y1-r,90),(x0+r,y0+r,180),(x1-r,y0+r,270)]:
        for a in np.linspace(start,start+90,33):
            a=math.radians(float(a));points.append([cx+r*math.cos(a),cy+r*math.sin(a)])
    return manifold.CrossSection([points])

# Small functional corner radii support a bent tie; they are not decoration.
bed=rr([xc0,-4.5],[xc1,-1.75],.6).extrude(3.).translate([0,0,230.6])
grooves=manifold.Manifold.batch_boolean([manifold.Manifold.cylinder(6.,.35,circular_segments=64).translate([float(x),-1.5,230.]) for x in xx],manifold.OpType.Add)
bed=bed-grooves
beam=box([-35.,-7.,233.4],[xc1,-2.5,236.4])
addition=beam+bed;combined=host+addition
support_check={'source':source_fit(addition),'wires':wire_fit(addition),
    'host_root_overlap_mm3':float((addition^host).volume()),
    'combined_components':len([m for m in combined.decompose() if abs(m.volume())>1e-7])}

# A flat installed band reference, not a detailed tooth or latch reconstruction.
# The upper dimensions enclose both official regional T18R drawings.
inner=rr([xc0,-4.5],[xc1,-1.16],.6)
outer=rr([xc0-1.3,-5.8],[xc1+1.3,.14],1.9)
band=(outer-inner).extrude(2.7).translate([0,0,230.65])
head=box([xc1+1.3,-5.5,229.35],[xc1+6.6,-.2,234.65])
tie=band+head
tie_check={'source':source_fit(tie),'wires':wire_fit(tie),
    'host_intersection_mm3':max(0.,float((tie^host).volume())),
    'support_intersection_mm3':max(0.,float((tie^addition).volume())),
    'support_minimum_gap_mm':float(tie.min_gap(addition,1.)),
    'scope':'Conservative2.7mm band width,1.3mm thickness and5.3mm head cube; installed form assumed'}

# Recheck the existing pitch-servo straight insertion because the support is
# integral with its carrier. Remove only the same stated bench prerequisites.
insertion=[]
for dx in np.arange(0,35.001,.5):
    for name in ['Pitch_Servo','Pitch_Output']:
        moving=ss[name].m.translate([float(dx),0,0])
        volume=max(0.,float((moving^addition).volume()))
        if volume>1e-5:insertion.append({'dx_mm':float(dx),'part':name,'intersection_mm3':volume})

# Preserve the documented upper screw's short-L-key operating arc.
mounts=json.loads((PROJECT/'mechanical/reports/prearrival_geometry.json').read_text())['servo_ears']
upper=next(r for r in mounts if r['id']=='Head_Pitch_Ear_0')
pn=P['assembly_issue_fixes']['pitch_nut']
p=np.array(upper['ear_top_mm'])+[pn['screw_head_height_mm']-.7,0,0];a=np.array([1,0,0])
tool=axial(.87,50,p+a*25,a)+axial(.87,14,p+a*50+[0,7,0],[0,1,0])+manifold.Manifold.sphere(.87,32).translate((p+a*50).tolist())
tool_hits=[]
bench={n:s for n,s in ss.items() if n.startswith(('Pitch_Yoke','Pitch_Bearing','Pitch_Servo','Head_Pitch_')) and n!='Head_Pitch_Ear_0_Screw'}
for angle in range(-120,121,2):
    tr=Matrix.Translation(Vector(p))@Matrix.Rotation(math.radians(angle),4,'X')@Matrix.Translation(-Vector(p));moving=tool.transform(np.array(tr)[:3,:])
    for n,s in bench.items():
        m=combined if n=='Pitch_Yoke' else s.m
        volume=max(0.,float((moving^m).volume()))
        if volume>.02:tool_hits.append({'angle_deg':angle,'object':n,'intersection_mm3':volume})
longest=run=0
for angle in range(-120,121,2):
    run=run+2 if not any(r['angle_deg']==angle for r in tool_hits) else 0;longest=max(longest,run)

for name,m in [('Pitch_Yoke',combined),('addition',addition),('tie_band',band),('tie_head_allocation',head)]:cache(OUT/(name+'.npz'),m)
replace_owned('Pitch_Yoke',combined)
for name,m in [('Band',band),('HeadEnvelope',head)]:
    mesh=m.to_mesh64();data=bpy.data.meshes.new('A8_CAM_Tie_'+name)
    data.from_pydata(mesh.vert_properties[:,:3].tolist(),[],mesh.tri_verts.tolist());data.update()
    obj=bpy.data.objects.new('A8_CAM_Tie_'+name,data);bpy.context.scene.collection.objects.link(obj)
    obj['study_owner']='A8_CAM_ANCHOR';obj['part_class']='PLACEHOLDER';obj['data_status']='ASSUMED';obj['group']='yaw'
    obj['scope']='Catalogue-bounded installed tie allocation; not final procurement CAD'
    data.materials.append(material('A8_CAM_Tie_amber',(.95,.48,.06),roughness=.7))
after={n:geometry_record(s.o) for n,s in ss.items()}
changed=sorted(n for n in before if before[n]!=after[n]);assert changed==['Pitch_Yoke']
bpy.context.scene['independent_unapproved_study']='A8 yaw-side CAM grip bed; no main adoption'
bpy.context.scene['main_model_not_updated']=True
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'candidate.blend'))
ok=(support_check['source']['status']==support_check['wires']['status']==tie_check['source']['status']==tie_check['wires']['status']=='PASS'
    and support_check['host_root_overlap_mm3']>5 and support_check['combined_components']==1 and tie_check['host_intersection_mm3']<1e-6 and tie_check['support_intersection_mm3']<1e-6)
result={'status':'PASS' if ok else 'BLOCKED','scope':'Local integral support and catalogue-bounded tie fit only',
    'source_main_sha256':source_hash,'source_script_sha256':sha(CLAMP_SCRIPT),'source_helper_sha256':sha(CLAMP_HELPER),
    'source_dimension_receipt_sha256':sha(CLAMP_ROOT/'cam_anchors/sources/web_dimensions.json'),
    'source_J3M_sha256':sha(CLAMP_ROOT/'assembly_feed_v3/open_mouth/cleaned/candidate.blend'),
    'support_check':support_check,'tie_check':tie_check,
    'pitch_servo_straight_insertion':{'status':'PASS' if not insertion else 'BLOCKED','hits':insertion,'travel_mm':35,'step_mm':.5},
    'upper_pitch_tool':{'status':'PASS' if longest>=60 else 'BLOCKED','longest_clear_sampled_span_deg':longest,'hits':tool_hits},
    'added_print_parts':0,'added_screws':0,'proposed_ties':1,'beam_bounds_mm':list(beam.bounding_box()),'changed_prints_relative_J3M':changed,
    'new_print_volume_mm3':float((combined-host).volume()),'new_bed_bounds_mm':list(bed.bounding_box()),
    'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.suffix in ['.npz','.blend']},
    'retention_pullout':'NOT_TESTED','complete_installation':'NOT_TESTED','all_harness_anchors':'NOT_TESTED',
    'strength':'NOT_TESTED','manufacturing_release':False,'whole_harness':'BLOCKED','main_applied':False}
(OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CLAMP_CANDIDATE',result['status'],'source',support_check,'tie',tie_check,'servo_insertion_hits',len(insertion),'tool_arc',longest,flush=True)
