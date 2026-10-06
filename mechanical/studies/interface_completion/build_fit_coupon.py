"""Independent PA12 interface coupon derived from current insert dimensions.

This auxiliary sample does not alter the robot or replace its current prints.
All spacings are trial-test layout dimensions, not purchased hardware evidence.
"""
import sys,json,math,hashlib,struct
from pathlib import Path
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parents[1]/'scripts'))
from common import *
from export import topology,read_stl
q=P['interface_completion'];out=HERE/'coupons';out.mkdir(exist_ok=True)
families={r['sku']:r for r in q['inserts']};pitch=10.;rows=[];m=manifold.Manifold.cube([60,40,8])
for j,sku in enumerate(sorted(families)):
 r=families[sku]
 for i,delta in enumerate([-.2,-.1,0,.1,.2]):
  x=5+pitch*i;y=8+12*j;d=r['pilot_mm']+delta;depth=r['length_mm']+1.2
  m-=manifold.Manifold.cylinder(depth+.01,d/2,d/2,96).translate([x,y,8-depth])
  rows.append({'test':'insert','sku':sku,'xy_mm':[x,y],'pilot_diameter_mm':d,'blind_depth_mm':depth,'insert_length_mm':r['length_mm']})
for j,(thread,af,depth,through) in enumerate([('M2',4.,1.8,2.2),('M3',5.5,2.6,3.3)]):
 for i,extra in enumerate([.1,.2,.3]):
  x=5+(i+3*j)*pitch;y=32;a=af+extra
  m-=manifold.Manifold.cylinder(depth+.01,a/math.sqrt(3),a/math.sqrt(3),6).translate([x,y,8-depth])
  m-=manifold.Manifold.cylinder(9,through/2,through/2,64).translate([x,y,-.5])
  rows.append({'test':'nut','thread':thread,'xy_mm':[x,y],'pocket_AF_mm':a,'pocket_depth_mm':depth,'through_diameter_mm':through})
# One unique corner notch identifies the paper-map origin; no structural use.
m-=manifold.Manifold.cube([2,2,9]).translate([-.01,-.01,-.5]);d=m.to_mesh64();v=np.asarray(d.vert_properties[:,:3]);f=np.asarray(d.tri_verts)
t=topology(v,f);assert not any(t[k] for k in ['degenerate_triangles','nonmanifold_edges','boundary_edges','inconsistent_edges'])
scene=bpy.data.scenes.new('MORI_Interface_Coupon');scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=.001
me=bpy.data.meshes.new('MORI_V1__InterfaceCouponMesh');me.from_pydata(v.tolist(),[],f.tolist());me.update();o=bpy.data.objects.new('MORI_V1__InterfaceCoupon',me);scene.collection.objects.link(o)
for k,val in {'mori_owner':OWNER,'category':'PRINTABLE','data_status':'ASSUMED','role':'coupon','material':'PA12 / same supplier process as robot','not_a_robot_part':True}.items():o[k]=val
bpy.context.window.scene=scene;bpy.context.view_layer.update()
bpy.ops.wm.save_as_mainfile(filepath=str(out/'interface_coupon.blend'))
stl=out/'interface_coupon.stl'
with stl.open('wb') as stream:
 stream.write(b'MORI PA12 auxiliary insert/nut coupon, millimetres'.ljust(80,b' '));stream.write(struct.pack('<I',len(f)))
 for face in f:
  a,b,c=v[face];n=np.cross(b-a,c-a);n/=np.linalg.norm(n);stream.write(struct.pack('<12fH',*n,*a,*b,*c,0))
rv,rf,rn=read_stl(stl);rt=topology(rv,rf,rn);ra=np.asarray(rv);size=(ra.max(0)-ra.min(0)).tolist()
assert np.allclose(size,[60,40,8],rtol=0,atol=.00001)
assert not any(rt[k] for k in ['degenerate_triangles','nonmanifold_edges','boundary_edges','inconsistent_edges','inconsistent_stl_normals'])
assert abs(rt['signed_volume_mm3']-t['signed_volume_mm3'])<.01
record={'source_revision':P['revision'],'geometry_source_sha256':hashlib.sha256((PROJECT/'config/geometry.json').read_bytes()).hexdigest(),'source_insert_catalogue':q['insert_source'],'status':'PASS','scope':'One closed auxiliary coupon and16 labelled trial interfaces, mm. STL readback checks scale, manifold topology, normals and volume. NOT a robot-part release; actual PA12 installation, pullout, nut retention and torque NOT_TESTED. Nut pockets are trial variants, not adopted assembly interfaces.','size_mm':[60,40,8],'rows':rows,'topology':t,'stl_readback':{'size_mm':size,'topology':rt},'stl_sha256':hashlib.sha256(stl.read_bytes()).hexdigest(),'robot_part_delta':0}
(out/'manifest.json').write_text(json.dumps(record,ensure_ascii=False,indent=2))
svg=['<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="720"><rect width="1040" height="720" fill="#f8fafb"/><g font-family="Arial"><text x="40" y="40" font-size="24">PA12 insert / nut coupon: 60 x 40 x 8 mm</text><rect x="40" y="90" width="900" height="600" fill="#d4e0e4" stroke="#294452"/>']
for r in rows:
 x,y=r['xy_mm'];label=f'{r["pilot_diameter_mm"]:.2f}' if r['test']=='insert' else f'{r["thread"]} AF{r["pocket_AF_mm"]:.1f}'
 radius=(r['pilot_diameter_mm']/2 if r['test']=='insert' else r['pocket_AF_mm']/math.sqrt(3))*15
 svg.append(f'<circle cx="{40+x*15}" cy="{690-y*15}" r="{radius}" fill="white" stroke="#294452"/><text x="{40+x*15}" y="{690-y*15+radius+24}" text-anchor="middle" font-size="16">{label}</text>')
svg.append('<text x="825" y="580" font-size="18">M2 insert</text><text x="825" y="400" font-size="18">M3 insert</text><rect x="40" y="660" width="30" height="30" fill="#f8fafb"/></g></svg>');(out/'map.svg').write_text(''.join(svg))
print('INTERFACE_COUPON',record['status'],len(rows),t,flush=True)
