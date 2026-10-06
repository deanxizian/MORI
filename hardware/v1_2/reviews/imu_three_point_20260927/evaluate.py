#!/usr/bin/env python3
"""Read-only native-geometry review of the 20x21 IMU proposal.

Run using KiCad's bundled Python. Writes only this review directory.
No SaveBoard, new PCB, mechanical edit, or manufacturing export.
"""
import collections
import datetime
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

import pcbnew as k
import wx
APP = wx.App(False)

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
SOURCE = ROOT / 'hardware/v1_2/kicad/MORI_imu_P5R4'
PCB = SOURCE / 'MORI_imu_P5R4.kicad_pcb'
PROPOSAL = ROOT / 'mechanical/studies/prearrival_preparation/imu_mount_proposal.json'
HANDOFF = ROOT / 'hardware/v1_2/handoff/mechanical_P5R6.json'
TRANSFORM = ROOT / 'mechanical/reports/imu_mount_transform.json'
MECH = ROOT / 'mechanical/reports/native_electronics_geometry.json'
MATED = ROOT / 'mechanical/studies/prearrival_preparation/mated_connector_review.json'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text())
def dump(name, obj): (OUT / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
def mm(x): return k.FromMM(x)
def pt(x, y): return k.VECTOR2I(mm(x), mm(y))
def xy(p): return [round(k.ToMM(p.x), 6), round(k.ToMM(p.y), 6)]
def rid(item): return item.m_Uuid.AsString()
def line_points(chain): return [xy(chain.CPoint(i)) for i in range(chain.PointCount())]
def polygons(ps):
    return [{'outer': line_points(ps.Outline(i)),
             'holes': [line_points(ps.Hole(i, j)) for j in range(ps.HoleCount(i))]}
            for i in range(ps.OutlineCount())]
def poly_area(pp):
    def ring(a): return abs(sum(x*y2-x2*y for (x,y),(x2,y2) in zip(a,a[1:]+a[:1])))/2
    return sum(ring(p['outer'])-sum(ring(h) for h in p['holes']) for p in pp)

def distance_to_shape(shape, center):
    """Native filled-copper collision, rounded upward within 0.00005 mm."""
    p = pt(*center)
    if shape.Collide(k.SHAPE_CIRCLE(p, 0), 0): return 0.0
    lo, hi = 0, mm(100)
    if not shape.Collide(k.SHAPE_CIRCLE(p, hi), 0): return None
    while hi-lo > 50:
        mid = (lo+hi)//2
        if shape.Collide(k.SHAPE_CIRCLE(p, mid), 0): hi=mid
        else: lo=mid
    return k.ToMM(hi)

def bounding_graphics(f, layer):
    points=[]
    for item in f.GraphicalItems():
        if item.GetLayer()!=layer or not isinstance(item,k.PCB_SHAPE): continue
        bb=item.GetBoundingBox()
        points += [xy(bb.GetOrigin()),xy(bb.GetEnd())]
    if not points:return None
    return [min(x[0] for x in points),min(x[1] for x in points),
            max(x[0] for x in points),max(x[1] for x in points)]

def rectangle_distance(p, box):
    dx=max(box[0]-p[0],0,p[0]-box[2]);dy=max(box[1]-p[1],0,p[1]-box[3])
    return math.hypot(dx,dy)

def segment_distance(p,a,b):
    ab=[b[i]-a[i] for i in (0,1)]
    t=max(0,min(1,sum((p[i]-a[i])*ab[i] for i in (0,1))/sum(x*x for x in ab)))
    return math.dist(p,[a[i]+t*ab[i] for i in (0,1)])

protected=[p for p in SOURCE.rglob('*') if p.is_file() and p.suffix not in ['.kicad_prl','.lck']]
protected += [PROPOSAL,HANDOFF,TRANSFORM,MECH,MATED,
              ROOT/'mechanical/scripts/native_electronics.py',
              ROOT/'mechanical/scripts/prepare_populated_pcbs.py',
              ROOT/'hardware/v1_2/sources/parts/TDK_AN000393_v2p4.pdf',
              ROOT/'config/geometry.json',
              ROOT/'contracts/components.json',ROOT/'contracts/electrical_interfaces.json',
              ROOT/'contracts/mechanical_interfaces.json']
before={str(p.relative_to(ROOT)):sha(p) for p in protected}
proposal=read(PROPOSAL);hand=read(HANDOFF)['boards']['MORI_imu_P5R4']
assert sha(PCB)==hand['pcb_sha256']
b=k.LoadBoard(str(PCB));f={x.GetReference():x for x in b.GetFootprints()}
assert b.GetCopperLayerCount()==2
assert proposal['existing_footprint_translation_in_new_PCB_coordinates_mm']==[0,5]
assert proposal['proposed_outline_mm']==[20,21]
assert proposal['proposed_holes_xy_mm']==[[2.5,17.5],[17.5,17.5],[10,2.5]]
old_h3=[10,-2.5]; radius=proposal['proposed_copper_component_keepout_diameter_mm']/2

tracks=[];pads=[];placements=[]
for item in b.GetTracks():
    tracks.append({'uuid':rid(item),'kind':'via' if isinstance(item,k.PCB_VIA) else 'track',
       'net':item.GetNetname(),'layer':b.GetLayerName(item.GetLayer()),
       'start_mm':xy(item.GetStart()),'end_mm':xy(item.GetEnd()),
       'width_mm':k.ToMM(item.GetWidth(k.F_Cu) if isinstance(item,k.PCB_VIA) else item.GetWidth()),
       'H3_center_to_copper_mm':distance_to_shape(item.GetEffectiveShape(item.GetLayer()),old_h3)})
for ref,fp in sorted(f.items()):
    p=xy(fp.GetPosition())
    placements.append({'ref':ref,'old_xy_mm':p,'proposed_xy_mm':[p[0],p[1]+5],
       'rotation_deg':fp.GetOrientationDegrees(),'layer':b.GetLayerName(fp.GetLayer()),
       'fab_graphics_bounds_with_line_width_mm':bounding_graphics(fp,k.F_Fab),
       'courtyard_bounds_with_line_width_mm':bounding_graphics(fp,k.F_CrtYd)})
    for pad in fp.Pads():
        is_copper=pad.GetAttribute()!=k.PAD_ATTRIB_NPTH
        pads.append({'ref':ref,'number':pad.GetNumber(),'net':pad.GetNetname(),
            'position_mm':xy(pad.GetPosition()),'size_mm':xy(pad.GetSize()),
            'drill_mm':xy(pad.GetDrillSize()),'rotation_deg':pad.GetOrientationDegrees(),
            'shape':str(pad.GetShape()),'copper':is_copper,
            'H3_center_to_copper_mm':distance_to_shape(pad.GetEffectiveShape(k.F_Cu),old_h3) if is_copper else None})

# Virtual keepout subtraction from SAVED filled copper only; no board mutation/save.
# Circumscribed 256-gon encloses a true radius3.3mm circle (max radial excess<0.00025mm).
cut=k.SHAPE_POLY_SET();cut.NewOutline();N=256;rr=radius/math.cos(math.pi/N)
for i in range(N):
    a=2*math.pi*i/N;cut.Append(mm(old_h3[0]+rr*math.cos(a)),mm(old_h3[1]+rr*math.sin(a)))
zones=[]
for z in b.Zones():
    if z.GetIsRuleArea(): continue
    original=z.GetFilledPolysList(z.GetLayer());after=k.SHAPE_POLY_SET(original)
    old_shapes=polygons(original);after.BooleanSubtract(cut);new_shapes=polygons(after)
    anchors=[]
    for fp in b.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname()!=z.GetNetname() or pad.GetAttribute()==k.PAD_ATTRIB_NPTH:continue
            sh=pad.GetEffectiveShape(z.GetLayer())
            aa=original.Collide(sh,0);zz=after.Collide(sh,0)
            if aa:anchors.append({'pad':fp.GetReference()+'.'+pad.GetNumber(),'before':aa,'after':zz})
    zones.append({'name':z.GetZoneName(),'layer':b.GetLayerName(z.GetLayer()),
         'H3_center_to_filled_copper_mm':distance_to_shape(original,old_h3),
         'keepout_overlap_depth_mm':max(0,radius-distance_to_shape(original,old_h3)),
         'region_count_before':original.OutlineCount(),'region_count_after_virtual_cut':after.OutlineCount(),
         'removed_filled_area_mm2':poly_area(old_shapes)-poly_area(new_shapes),
         'ground_pad_contacts':anchors,'saved_polygons':old_shapes,'virtually_cut_polygons':new_shapes})

hole_checks=[]
for ref in ['H1','H2']:
    p=xy(f[ref].GetPosition());dist=[]
    for t in b.GetTracks():dist.append({'kind':'track_or_via','net':t.GetNetname(),'uuid':rid(t),'center_distance_mm':distance_to_shape(t.GetEffectiveShape(t.GetLayer()),p)})
    for fp in b.GetFootprints():
        if fp.GetReference().startswith('H'):continue
        for pad in fp.Pads():dist.append({'kind':'pad','ref':fp.GetReference(),'number':pad.GetNumber(),'center_distance_mm':distance_to_shape(pad.GetEffectiveShape(k.F_Cu),p)})
    for z in b.Zones():
        if not z.GetIsRuleArea():dist.append({'kind':'filled_zone','name':z.GetZoneName(),'center_distance_mm':distance_to_shape(z.GetFilledPolysList(z.GetLayer()),p)})
    nearest=min(dist,key=lambda x:x['center_distance_mm'])
    hole_checks.append({'ref':ref,'existing_drill_mm':xy(next(iter(f[ref].Pads())).GetDrillSize()),
        'nearest_copper':nearest,'gap_if_2p4mm_drill_mm':nearest['center_distance_mm']-1.2,
        'note':'Copper geometric clearance only; does not confirm fastener fit or strength'})

transform=read(TRANSFORM);R=transform['native_to_assembly_rotation'];old_t=transform['native_to_assembly_translation_mm'];new_t=proposal['new_board_origin_world_mm']
def world(p,t):
    cad=[p[0],-p[1],0]
    return [sum(R[i][j]*cad[j] for j in range(3))+t[i] for i in range(3)]
max_err=0
for row in placements:
    a=world(row['old_xy_mm'],old_t);z=world(row['proposed_xy_mm'],new_t)
    row['old_world_CAD_datum_mm']=a;row['proposed_world_CAD_datum_mm']=z
    row['world_delta_mm']=[z[i]-a[i] for i in range(3)]
    max_err=max(max_err,math.dist(a,z))
assert max_err<0.001

u=next(r for r in hand['placements'] if r['reference']=='U1')
body=[u['fab_projection_mm'][0],u['fab_projection_mm'][1]+5,u['fab_projection_mm'][2],u['fab_projection_mm'][3]+5]
uc=[u['xy_mm'][0],u['xy_mm'][1]+5];holes=proposal['proposed_holes_xy_mm']
stress={'sensor_center_proposed_mm':uc,'sensor_body_proposed_mm':body,
  'sensor_to_anchors':[{'hole':i+1,'center_to_center_mm':math.dist(uc,p),'body_edge_to_anchor_center_mm':rectangle_distance(p,body),'body_edge_to_hole_edge_at_2p4mm_mm':rectangle_distance(p,body)-1.2} for i,p in enumerate(holes)],
  'sensor_center_to_anchor_segments_mm':[segment_distance(uc,holes[a],holes[c]) for a,c in [(0,1),(1,2),(2,0)]],
  'sensor_body_to_H1_H2_line_mm':holes[0][1]-body[3],
  'sensor_between_H1_H2_line_and_H3':True,
  'actual_stress_modal_and_bias_testing':'NOT_TESTED',
  'three_point_support_is_not_a_qualification':True}
d=2.5;r=radius
cap=r*r*math.acos(d/r)-d*math.sqrt(r*r-d*d)
support={'proposed_hole_to_rear_edge_ligament_mm':d-1.2,
  'third_support_radius_mm':r,'support_overhang_past_rear_edge_mm':r-d,
  'support_annulus_area_full_mm2':math.pi*(r*r-1.2**2),
  'support_annulus_area_on_board_mm2':math.pi*(r*r-1.2**2)-cap,
  'bearing_area_retained_fraction':(math.pi*(r*r-1.2**2)-cap)/(math.pi*(r*r-1.2**2)),
  'note':'Planar circle/rectangle geometry only; no load, screw torque or strength certification'}
nearest_tracks=min(tracks,key=lambda t:t['H3_center_to_copper_mm'])
nearest_pad=min((p for p in pads if p['copper']),key=lambda p:p['H3_center_to_copper_mm'])
j=next(p for p in hand['placements'] if p['reference']=='J1')
jb=j['fab_projection_mm'];jgap=rectangle_distance(old_h3,jb)-radius
courtyard=next(p for p in placements if p['ref']=='J1')['courtyard_bounds_with_line_width_mm']
mated=next(p for p in read(MATED)['rows'] if p['board']=='imu' and p['ref']=='J1')
mb=mated['bounds_mm'];axis=proposal['third_boss_axis_world_mm'][:2]
mated_gap=rectangle_distance(axis,[mb[0],mb[1],mb[3],mb[4]])-radius
result={'revision':'IMU_THREE_POINT_REVIEW_20260927','scope':'Read-only native PCB evaluation; no candidate PCB saved',
 'baseline':'MORI_imu_P5R4 received in P5R6','baseline_pcb_sha256':sha(PCB),'proposal_source_sha256':sha(PROPOSAL),
 'kicad_version':k.GetBuildVersion(),'python':sys.version,'proposal':proposal,
 'geometry_recommendation':'20x21mm proposal is conditionally adoptable; implement third-hole keepout and full-object translation in a later approved revision',
 'status':'BLOCKED','status_scope':'Native revised board release and physical qualification are not performed in this review',
 'native_edges':[{'start':xy(e.GetStart()),'end':xy(e.GetEnd())} for e in b.GetDrawings() if e.GetLayer()==k.Edge_Cuts],
 'placements':placements,'tracks_and_vias':tracks,'pads':pads,'zones':zones,
 'H3_clearance_summary':{'nearest_track_or_via':nearest_tracks,'nearest_pad':nearest_pad,
      'J1_Fab_to_keepout_gap_mm':jgap,'J1_courtyard_to_keepout_gap_mm':rectangle_distance(old_h3,courtyard)-radius,
      'existing_mated_PHR8_bounding_box_source':str(MATED.relative_to(ROOT)),
      'existing_mated_PHR8_to_3p3mm_support_projection_gap_mm':mated_gap,
      'new_fastener_full_tool_path':'NOT_TESTED',
      'required_local_change':'Trim both F.Cu/B.Cu ground pours; do not waive GND from proposed keepout'},
 'existing_holes_if_enlarged':hole_checks,'support_geometry':support,'stress_geometry':stress,
 'transform':{'native_plot_2D_to_STEP':'[x,y] -> [x,-y]','STEP_to_body_rotation':R,
    'old_translation_mm':old_t,'new_translation_mm':new_t,'max_existing_placement_world_delta_mm':max_err,
    'formula':'world = R_step_to_body * [x_native, -y_native, z_STEP] + t',
    'native_to_assembly_rotation_field_actually_applies_to_STEP_coordinates':True,
    'mechanical_config_followup':{
       'path':'config/geometry.json#/native_electronics/boards/imu/board_center_xy_mm',
       'current':[-25,-40],'required_if_centroid_based_import_retained':[-25,-42.5],
       'reason':'Existing board_transform recenters from new outline centroid. Leaving -40 moves all retained parts +2.5mm in world Y.',
       'owner':'mechanical; proposal only, not applied',
       'keep_substrate_reference_z_mm':108.355,
       'keep_rotation_xyz_deg':[180,0,0]},
    'sensor_rotation_and_physical_position':'UNCHANGED to <0.001mm numerical tolerance; not calibration'},
 'physical_tests':'NOT_TESTED','candidate_ERC_DRC':'NOT_TESTED','manufacturing_release':False}

native=OUT/'native_baseline';native.mkdir(exist_ok=True)
commands=[]
for sub,args,input_file in [('drc',['pcb','drc','--format','json','--severity-all','--all-track-errors','--schematic-parity','--refill-zones','--exit-code-violations'],PCB),
                           ('erc',['sch','erc','--format','json','--severity-all','--exit-code-violations'],SOURCE/'MORI_imu_P5R4.kicad_sch')]:
    argv=[CLI,*args,'-o',str(native/(sub+'.json')),str(input_file)]
    cp=subprocess.run(argv,capture_output=True,text=True)
    report=read(native/(sub+'.json'))
    commands.append({'argv':argv,'returncode':cp.returncode,'stdout':cp.stdout,'stderr':cp.stderr})
    result['baseline_'+sub]={'status':'PASS' if cp.returncode==0 else 'FAIL','report':'native_baseline/'+sub+'.json',
      'violations':len(report.get('violations',[])),'unconnected':len(report.get('unconnected_items',[])),
      'schematic_parity':len(report.get('schematic_parity',[]))}

after={str(p.relative_to(ROOT)):sha(p) for p in protected}
changed=[p for p in before if before[p]!=after[p]]
assert not changed,changed
dump('evaluation.json',result)
dump('commands_and_sources.json',{'created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'script_command':[sys.executable,str(Path(__file__).resolve())],'kicad_version':k.GetBuildVersion(),
 'native_commands':commands,'source_sha256_before':before,'source_sha256_after':after,
 'source_integrity':'PASS','changed_protected_files':changed,
 'development_note':'Initial script attempt stopped before output at PCB_VIA.GetWidth() without a layer. Fixed to GetWidth(F_Cu); final run completed. No board files were saved in either attempt.'})
print(json.dumps({'output':str(OUT),'nearest_track_mm':nearest_tracks['H3_center_to_copper_mm'],
 'nearest_pad_mm':nearest_pad['H3_center_to_copper_mm'],'J1_keepout_gap_mm':jgap,
 'zones':[{q:v[q] for q in ['name','keepout_overlap_depth_mm','region_count_before','region_count_after_virtual_cut','removed_filled_area_mm2']} for v in zones],
 'support':support,'stress':stress,'max_world_error_mm':max_err,'baseline_drc':result['baseline_drc'],
 'baseline_erc':result['baseline_erc'],'source_integrity':'PASS'},ensure_ascii=False,indent=2))
