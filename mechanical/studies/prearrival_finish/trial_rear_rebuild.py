"""Reconstruct the same documented rear shell without obsolete seam-hole booleans."""
import sys,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parents[2]/'mechanical/scripts'))
from common import *
from validate import Solid
from export import topology
from interface_completion import axial,repair_quantized_triangles
from monocoque_structure import source_build

load_collections();assembled();bpy.context.view_layer.update()
o=bpy.data.objects[PREFIX+'Head_Rear'];old=Solid(o).m;b=source_build()
outer=b.sphere('repair_outer',(0,0,D['head_z']),D['head_radius']);mother=Solid(outer).m;bpy.data.objects.remove(outer,do_unlink=True)
inner=b.sphere('repair_inner',(0,0,D['head_z']),D['head_radius']-P['shell_thickness_mm']);cavity=Solid(inner).m;bpy.data.objects.remove(inner,do_unlink=True)
m=mother-cavity
bottom=D['head_z']+P['head_lower_opening_z_from_center_mm'];gap=P['seam_gap_mm']/2
m=m^manifold.Manifold.cube([500,250-gap,500-bottom]).translate([-250,-250,bottom])
q=P['interface_completion']['head_seam']
for sign in [-1,1]:
    center=np.array([sign*q['abs_x_mm'],0,D['head_z']+q['z_from_head_mm']])
    m=m+(axial(q['lug_radius_mm'],q['rear_lug_depth_mm'],center+[0,q['rear_lug_y_mm'],0],[0,1,0])^mother)
    m=m-axial(q['rear_clearance_radius_mm'],30,center+[0,-10,0],[0,1,0])
    m=m-axial(q['rear_head_recess_radius_mm'],45,center+[0,-35,0],[0,1,0])
mq=P['microphone_acoustics']
for sign in [-1,1]:
    # Match the original 24-sided acoustic opening, including its phase.
    cutter=b.cyl('repair_mic',(sign*mq['shell_port_abs_x_mm'],mq['shell_port_y_mm'],D['head_z']+mq['shell_port_z_from_head_mm']),mq['shell_port_radius_mm'],mq['shell_port_cut_length_mm'],'Y',24)
    m=m-Solid(cutter).m;bpy.data.objects.remove(cutter,do_unlink=True)
m=m.simplify(.00005)
d=m.to_mesh64();v=np.asarray(d.vert_properties[:,:3],dtype=np.float32).astype(float);f=np.array(d.tri_verts,dtype=np.int64)
v,f,ops,bad=repair_quantized_triangles(v,f)
u,inv=np.unique(v,axis=0,return_inverse=True);wf=inv[f]
top=topology(u,wf)
mm=manifold.Manifold(manifold.Mesh64(np.array(v,dtype=np.float64,order='C'),np.array(f,dtype=np.uint64,order='C')))
regions=manifold.Manifold()
for sign in [-1,1]:
    for x,z in [(q['old_abs_x_mm'],q['old_z_from_head_mm']),(q['abs_x_mm'],q['z_from_head_mm'])]:
        regions+=axial(q['lug_radius_mm']+.02,90,[sign*x,-10,D['head_z']+z],[0,1,0])
removed=old-mm;added=mm-old
report=dict(topology=top,kernel_status=str(mm.status()),operations=ops,
            removed_mm3=removed.volume(),added_mm3=added.volume(),
            outside_seam_regions_mm3=(removed-regions).volume()+(added-regions).volume(),
            removed_bounds=list(removed.bounding_box()),added_bounds=list(added.bounding_box()))
(HERE/'rear_rebuild.json').write_text(json.dumps(report,indent=2)+'\n')
np.savez_compressed(HERE/'rear_rebuilt.npz',vertices=v,faces=f)
print(json.dumps(report,indent=2),flush=True)
