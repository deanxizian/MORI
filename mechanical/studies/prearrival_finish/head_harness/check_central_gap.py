"""Bounded central-annulus capacity check, not a harness route or dynamic test."""
from pathlib import Path
import sys,json,hashlib,math,itertools,csv
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[3]
sys.path.insert(0,str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid
from interface_completion import axial
load_collections()
for n in ['DATUMS','KEEP_OUT','DOCK','COUPONS']:COLS[n].hide_viewport=False
assembled();bpy.context.view_layer.update()
source=Path(bpy.data.filepath);before=hashlib.sha256(source.read_bytes()).hexdigest()
ss={n:Solid(bpy.data.objects[PREFIX+n]) for n in ['Yaw_Reaction_Link','Pitch_Yoke']}
csv_path=PROJECT/'hardware/v1_2/prearrival_20261002/harness_detail.csv'
wire_rows={r['线束']:r for r in csv.DictReader(csv_path.open(encoding='utf-8-sig'))}
# Upstream head-power/servo lead sample is Alpha5855. This is a dimensional
# screen only, NOT adoption, dynamic qualification, or a relaxed bend radius.
OD=float(wire_rows['P_J9']['绝缘外径最大mm'])
assert OD==float(wire_rows['P_J18']['绝缘外径最大mm'])
gap=.3;center_r=6.8;z0,z1=150.,182.;segments=96
rows=[]
for angle in range(0,360,30):
    xy=np.array([center_r*math.cos(math.radians(angle)),center_r*math.sin(math.radians(angle))])
    for label,radius in [('bare_sample',OD/2),('sample_plus_project_gap',OD/2+gap)]:
        # Circumscribed polygon contains the nominal circular cross-section.
        m=axial(radius/math.cos(math.pi/segments),z1-z0,[*xy,(z0+z1)/2],[0,0,1],segments=segments)
        hits=[]
        for name,s in ss.items():
            volume=max(0.,(m^s.m).volume())
            if volume>1e-5:hits.append(dict(object=name,volume_mm3=volume))
        rows.append(dict(azimuth_deg=angle,center_xy_mm=xy.tolist(),probe=label,
            radius_mm=radius,z_mm=[z0,z1],hits=hits,status='FAIL' if hits else 'PASS'))
nominal=all(r['status']=='PASS' for r in rows if r['probe']=='bare_sample')
gapfit=all(r['status']=='PASS' for r in rows if r['probe']=='sample_plus_project_gap')
out=dict(revision=P['revision'],source_blend_sha256=before,status='FAIL' if not gapfit else 'PASS',
    scope='One straight single-wire sample within the central annular gap at mechanical zero only',
    source='Alpha5855 max OD from received A2 harness_detail.csv; not selected for production',
    source_csv_sha256=hashlib.sha256(csv_path.read_bytes()).hexdigest(),
    wire_sample_OD_max_mm=OD,required_project_gap_per_side_mm=gap,
    source_stem_radius_mm=P['belly_relayout']['reaction_stem_radius_mm'],
    source_upper_passage_radius_mm=P['belly_relayout']['reaction_stem_clearance_radius_mm'],
    maximum_nominal_OD_with_project_gap_mm=P['belly_relayout']['reaction_stem_clearance_radius_mm']-P['belly_relayout']['reaction_stem_radius_mm']-2*gap,
    bare_sample_overlap_screen='PASS' if nominal else 'FAIL',sample_plus_gap_screen='PASS' if gapfit else 'FAIL',
    cases=rows,main_geometry_changed=False,
    limits=['This is a nominal gap screen, not a selected wire or a validated cable route.',
        'No finite bend, moving cable, tolerance stack, electrical capacity, anchor or dynamic-fatigue qualification.',
        'Only two enclosing joint solids and one32mm straight segment were tested; other approaches remain unassessed.',
        'Failure here does not prove an outer-neck route is impossible.',
        'The0.3mm per-side gap is an explicit project allocation, not a manufacturer requirement.'])
(HERE/'central_gap_check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('CENTRAL_GAP_CHECK',out['status'],'bare',out['bare_sample_overlap_screen'],'gap',out['sample_plus_gap_screen'],'max OD',out['maximum_nominal_OD_with_project_gap_mm'],flush=True)
