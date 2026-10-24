"""USB boot and J5 exit capacity on saved M1.56; no cable/model adoption."""
import sys,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common import *
from validate import Solid
from native_electronics import solid_from
from validate_off_shelf_modules import raw_solid

bpy.context.window.scene=bpy.data.scenes['MORI_V1_Assembly'];load_collections()
for c in COLS.values():c.hide_viewport=False
assembled();bpy.context.view_layer.update()
ss={o.name.removeprefix(PREFIX):Solid(o).m for o in parts() if o.get('group') not in ('dock','coupon')}
core=bpy.data.objects[PREFIX+'MCU_Motion'];fallbacks=[];vv=np.array([list(core.matrix_world@v.co) for v in core.data.vertices])
ff=[list(p.vertices) for p in core.data.polygons];usb=None
ss.pop('MCU_Motion')
for row in json.loads(core['component_reference_index']):
    lo,hi=row['vertices'];a,b=row['faces'];m=solid_from(vv[lo:hi],np.array(ff[a:b])-lo,row['reference'],fallbacks)
    if row['reference']=='VENDOR_163':usb=np.array(m.bounding_box())
    else:ss['MCU_Motion/'+row['reference']]=m
assert usb is not None
review=ROOT/'studies/off_shelf_modules_20261013/controller_center/connector_review'
plugdata=json.loads((review/'plug_reservation_meshes.json').read_text())
for n,row in plugdata.items():ss['Plug/'+n]=raw_solid(row)
bb={n:np.array(m.bounding_box()) for n,m in ss.items()}
def hits(m,targets):
    b=np.array(m.bounding_box());rows=[]
    for n in targets:
        a=bb[n]
        if np.any(b[3:]<a[:3]) or np.any(a[3:]<b[:3]):continue
        vol=float((m^ss[n]).volume())
        if vol>.001:rows.append(dict(part=n,volume_mm3=vol))
    return rows
def box(size,center):return manifold.Manifold.cube(size,True).translate(center)
mouth=usb[4];cx=(usb[0]+usb[3])/2;cz=(usb[2]+usb[5])/2
front={'Body_Front','Speaker','Speaker_Gasket','Frame_Insert_0','Frame_Insert_1'}|{n for n in ss if n.startswith(('Speaker_Screw_','Speaker_Insert_'))}
fixtures=set(ss)-front
boots={};results=[]
for width,height,length in [(10.,4.5,16.),(12.,6.,20.),(14.,8.,24.)]:
    name=f'{width:g}x{height:g}x{length:g}';boot=box([width,length,height],[cx,mouth+length/2,cz]);boots[name]=boot
    bad=[]
    for travel in range(0,101,5):
        h=hits(boot.translate([0,travel,0]),fixtures)
        if h:bad.append(dict(front_travel_mm=travel,hits=h))
    results.append(dict(boot_mm=[width,height,length],status='FAIL' if bad else 'PASS',positions=21,hits=bad))

# Reflect the previously checked full four-wire envelope about the J5 axis.
# Original is left R6/stem1/run12; reflection gives the same right-hand bend.
left=raw_solid(json.loads((review/'cam_exit_reservation_mesh.json').read_text()))
j5bb=bb['Plug/Carrier_J5'];axis=(j5bb[0]+j5bb[3])/2
right=left.mirror([1,0,0]).translate([2*axis,0,0])
exits=[]
for name,m in [('left_R6_stem1',left),('right_R6_stem1',right)]:
    overlaps=[dict(USB_boot_mm=k,overlap_mm3=float((m^boot).volume())) for k,boot in boots.items()]
    exits.append(dict(route=name,boot_intersections=overlaps,
        status='PASS' if all(r['overlap_mm3']<.001 for r in overlaps) else 'FAIL',
        other_fixture_check='Existing independent candidate ribbon clearance remains local only; complete new routing not adopted'))
result=dict(revision=P['revision'],source_blend_sha256=hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest(),
    USB_mouth_Y_mm=float(mouth),USB_center_XZ_mm=[float(cx),float(cz)],USB_direction='+Y/front',
    source='Exact current WeAct vendor solid163 defines receptacle outer mouth; only that mating receptacle excluded',
    boot_tests=results,J5_wire_exit=exits,removed_for_service=sorted(front),source_fallbacks=fallbacks,
    boot_evidence='ASSUMED whole overmould envelopes, no selected USB cable or mating metal shell',
    scope='Capacity screening only. Complete front shell plus attached speaker removed. Real cable strain relief, engagement, handle/hand, bends and electrical role NOT_TESTED.',
    printed_geometry_changed=False,formal_harness_adoption=False)
save_json(ROOT/'reports/off_shelf_usb_capacity.json',result)
print('USB_CAPACITY',[(r['boot_mm'],r['status']) for r in results],exits,flush=True)
