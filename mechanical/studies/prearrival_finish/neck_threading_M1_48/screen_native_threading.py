"""Native M1.48 repeat of a local witness and four explicit terminal paths.

Bounded local diagnostic only: no root/whole wire/hand motion is inferred from
a bare-terminal test. No initializer from prior route studies is executed.
"""
from pathlib import Path
import hashlib
import json
import math
import sys

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[3]
sys.path.insert(0, str(PROJECT/'mechanical/scripts'))
from common import *
from validate import Solid

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
source = Path(bpy.data.filepath).resolve()
assert source == PROJECT/'mechanical/mori_v1_2.blend'
before = sha(source)
audit = json.loads((HERE/'source_audit.json').read_text())
assert before == audit['source_main_sha256']
load_collections(); assembled(); bpy.context.view_layer.update()
ss = {o.name.removeprefix(PREFIX):Solid(o) for o in parts()
      if o.type=='MESH' and o.get('group') not in ['dock','coupon']}
A8 = HERE.parent/'harness_A8'
stock = A8/('cam_wire_forming/lifted_end2/contact_refined_forming/'
            'root_seating/body_supply/complete_head/bridge_wire_stock')
old_screen_path = stock/'bridge_then_shell_over_wires/screen.json'
old_screen = json.loads(old_screen_path.read_text())
old_wires_path = stock/'bridge_then_shell_over_wires/temporary_wires.npz'
old_wires = np.load(old_wires_path)
native = ss['Yaw_Base'].m
raw = np.load(A8/'terminal_threading/cleaned/Yaw_Base.npz')
candidate = manifold.Manifold(manifold.Mesh64(raw['vertices_mm'],raw['triangles'].astype(np.uint64)))
ez = np.array([0.,0.,1.])

def overlap(m, target):
    x = m^target
    v = max(0.,float(x.volume()))
    return dict(intersection_mm3=v, bounds_mm=list(x.bounding_box()) if v>1e-8 else None)

# Repeat the exact historical padded-terminal shape only for reproducibility.
witnesses=[]
for pin in range(1,5):
    end=old_wires[f'pin{pin}'][-1]
    er=np.r_[end[:2],0.];er/=np.linalg.norm(er)
    tr=np.column_stack([er,np.cross(ez,er),ez,end+ez*2.05])
    historical = manifold.Manifold.cube([1.,1.8,4.1],center=True).minkowski_sum(
        manifold.Manifold.sphere(.31,48)).transform(tr)
    if pin==4:
        t=historical.translate([0,0,-224.])
        witnesses.append(dict(pin=pin,bridge_lift_mm=224.,
            native=overlap(t,native),cleaned_J2_candidate=overlap(t,candidate)))

# A straight tail is not an insertion proof. Compare the lower circular bend
# itself against both solids at fine points, including solid containment.
packing_path = A8/'body_prefix_v2/packing.json'
selected = json.loads(packing_path.read_text())['selected']
targets = {'native_bridge':native,'cleaned_J2_candidate':candidate,
           'native_bearing':ss['Yaw_Bearing'].m}
point_rows=[];terminal_rows=[];saved={}
terminal_size=np.array([1.,1.8,4.1])
# Project gap + 0.01 mm numerical allowance. Axis-aligned box expansion is
# a conservative superset of an isotropic 0.31 mm expansion.
pad=.31
terminal0=manifold.Manifold.cube(terminal_size.tolist(),center=True)
terminal_padded=manifold.Manifold.cube((terminal_size+2*pad).tolist(),center=True)
for selection in selected:
    pin=selection['pin'];a=math.radians(selection['azimuth_deg'])
    er=np.array([math.cos(a),math.sin(a),0.]);et=np.cross(ez,er)
    thetas=np.linspace(0,math.pi/2,361)
    centers=[]
    for theta in thetas:
        p=er*(14.8-8*math.sin(theta))+ez*(139+8*(1-math.cos(theta)))
        centers.append(p)
    centers=np.array(centers);saved[f'pin{pin}_wire_bend']=centers
    for label,m in targets.items():
        actual=[];padded=[]
        for i,p in enumerate(centers):
            tiny=manifold.Manifold.sphere(.005,12).translate(p.tolist())
            if (tiny^m).volume()>tiny.volume()/2:
                actual.append(dict(theta_deg=float(np.degrees(thetas[i])),point_mm=p.tolist()))
                break
        # Min distance between points and solid is used only for a failure
        # witness; zero intersection at samples is not continuous clearance.
        point_rows.append(dict(pin=pin,target=label,center_inside=actual[0] if actual else None,
                               status='FAIL' if actual else 'NOT_TESTED',
                               scope='Centre-in-solid witness; no clearance PASS from sampling'))

    transforms=[]
    # Horizontal inward arrival; R8 upward bend; then straight emergence.
    for r in np.linspace(25.,14.8,52):
        p=er*r+ez*139.; t=-er;n=ez
        # n x et = t, giving a right-handed local frame.
        transforms.append(('radial_arrival',float(r),np.column_stack([n,et,t,p+t*2.05])))
    for theta in np.linspace(0,math.pi/2,181)[1:]:
        p=er*(14.8-8*math.sin(theta))+ez*(139+8*(1-math.cos(theta)))
        t=-er*math.cos(theta)+ez*math.sin(theta)
        n=er*math.sin(theta)+ez*math.cos(theta)
        transforms.append(('lower_R8_bend',float(np.degrees(theta)),np.column_stack([n,et,t,p+t*2.05])))
    for z in np.linspace(147.,174.,109)[1:]:
        p=er*6.8+ez*z
        transforms.append(('vertical_emergence',float(z),np.column_stack([er,et,ez,p+ez*2.05])))
    saved[f'pin{pin}_terminal_transforms']=np.asarray([t for _,_,t in transforms])
    for label,m in targets.items():
        first_actual=None;first_padded=None
        for step,(stage,value,tr) in enumerate(transforms):
            if first_actual is None:
                hit=overlap(terminal0.transform(tr),m)
                if hit['intersection_mm3']>1e-6:
                    first_actual=dict(step=step,stage=stage,parameter=value,**hit)
            if first_padded is None:
                hit=overlap(terminal_padded.transform(tr),m)
                if hit['intersection_mm3']>1e-6:
                    first_padded=dict(step=step,stage=stage,parameter=value,**hit)
            if first_actual and first_padded:break
        terminal_rows.append(dict(pin=pin,target=label,samples=len(transforms),
            status='FAIL' if first_actual or first_padded else 'NOT_TESTED',
            first_nominal_overlap=first_actual,first_padded_overlap=first_padded,
            scope='Discrete bare-terminal local test; no continuous/full-wire/hands qualification'))
        print('NATIVE_TERMINAL',pin,label,terminal_rows[-1]['status'],flush=True)

np.savez_compressed(HERE/'native_threading_paths.npz',**saved)
report=dict(status='BLOCKED',scope='Native lower-neck local diagnostics',
    revision=P['revision'],source_main_sha256=before,script_sha256=sha(__file__),
    source_audit_sha256=sha(HERE/'source_audit.json'),
    sources={str(p.relative_to(PROJECT)):sha(p) for p in [old_screen_path,old_wires_path,packing_path]},
    historical_witness_repeat=witnesses,wire_center_checks=point_rows,terminal_path_checks=terminal_rows,
    terminal_dimensions_mm=terminal_size.tolist(),terminal_evidence='ASSUMED requested space; not manufacturer crimp geometry',
    wire_OD_mm=.6604,project_surface_gap_mm=.3,terminal_padding_mm=pad,
    lower_arc_radius_mm=8.,lower_arc_exit_radius_mm=6.8,
    actual_native_bore_role='Central 3.6 mm hole is horn-locking driver access; no permanent wire allocation adopted.',
    main_model_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    limitations=['These are finite paths, not proof that all unchanged-part assembly orders fail.',
                 'No actual terminal selection or supplier cut length is released.',
                 'An unchanged original-model route must be independently verified; the old cut-channel route is not native geometry.'])
assert sha(source)==before
report['main_unchanged']=True
(HERE/'native_threading_screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('NATIVE_WITNESS',witnesses,flush=True)
