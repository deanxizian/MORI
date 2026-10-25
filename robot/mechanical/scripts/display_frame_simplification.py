"""M1.41 accepted flush U-shaped Display_Frame connections.

Shared geometry parameters remain the only dimension source. No purchased
part, screw datum, central optical mast or camera mount is relocated.
"""
from common import *
from monocoque_structure import obj
S=P.get('display_frame_simplification',{})

def dimensions():
    h=P['head_print_cleanup'];q=P['readiness_completion']['lcd'];hz=D['head_z']
    rear=q['crossbar_center_y_mm']-q['crossbar_depth_mm']/2+q['crossbar_forward_shift_mm']
    return dict(inner=h['face_return_xy_mm'][0][0],earinner=h['face_return_xy_mm'][1][0],
                outer=h['face_return_xy_mm'][3][0],oldrear=h['face_return_xy_mm'][0][1],
                earback=h['face_return_xy_mm'][2][1],rear=rear,front=rear+q['crossbar_depth_mm'],
                bot=hz+q['original_crossbar_bottom_from_head_mm']-q['lower_crossbar_extension_mm'],
                top=hz+q['crossbar_top_from_head_mm'],join0=hz+h['face_return_z_from_head_mm'][0],
                join1=hz+h['face_return_z_from_head_mm'][1],mast_half=h['face_mast_width_mm']/2)

def block(lo,hi):return manifold.Manifold.cube((np.array(hi)-lo).tolist()).translate(lo)

def cylinder(point,axis,r,length):
    tr=Matrix.Translation(Vector(point))@Vector(axis).to_track_quat('Z','Y').to_matrix().to_4x4()
    return manifold.Manifold.cylinder(length,r,r,96).transform(np.array(tr)[:3,:])

def change_region():
    d=dimensions();e=S['region_tolerance_mm']
    # All changed material is inside this lower connection envelope. The
    # independent validator additionally compares the exact accepted solid.
    return block([-d['outer']-e,d['earback']-e,d['bot']-e],
                 [d['outer']+e,d['front']+e,d['join1']+e])

def simplify_solid(original):
    d=dimensions();q=P['readiness_completion']['lcd'];m=original
    for sign in [-1,1]:
        a,b=sorted([sign*d['inner'],sign*d['earinner']])
        m-=block([a,d['oldrear'],d['join0']],[b,d['rear'],d['join1']+S['return_cut_extra_mm']])
    # Extend only the two ends. Re-unioning the full existing bar would fill
    # its bores and force a second, differently tessellated cylinder cut.
    for sign in [-1,1]:
        a,b=sorted([sign*q['crossbar_width_mm']/2,sign*d['outer']])
        m+=block([a,d['rear'],d['bot']],[b,d['front'],d['top']])
    for sign in [-1,1]:
        a,b=sorted([sign*d['mast_half'],sign*d['earinner']]);e=S['legacy_fragment_cleanup_margin_mm']
        m-=block([a,d['oldrear'],d['top']-e],[b,d['rear'],d['top']+e])
        a,b=sorted([sign*d['earinner'],sign*d['outer']])
        m+=block([a,d['rear'],d['top']],[b,d['front'],d['join1']])
        m+=block([a,d['earback'],d['bot']],[b,d['rear'],d['join0']])
    # Existing source bores/spot faces remain untouched. Use the project's
    # normal Boolean tolerance to remove sub-micron triangle slivers while
    # retaining a closed manifold before Blender/STL float conversion.
    return m.simplify(P['mesh']['boolean_simplify_tolerance_mm'])

def apply_display_frame_simplification():
    if not S.get('enabled'):return
    from validate import Solid
    o=obj('Display_Frame');before=Solid(o).m;after=simplify_solid(before);d=after.to_mesh64()
    inv=o.matrix_world.inverted();me=bpy.data.meshes.new('Display_Frame_M1_41_flush_U')
    me.from_pydata([tuple(inv@Vector(v)) for v in d.vert_properties[:,:3]],[],d.tri_verts.tolist());me.update()
    o.data=me;me.materials.append(MATS['frame']);SOLIDS.pop(o.name,None)
    o['label_zh']='平直U形屏幕连接架 / 前面与底边齐平'
    o['display_frame_revision']=S['revision']
    o['interface_note']='Accepted flush side-ear/front-beam junctions; four side holes, three LCD axes, mast and camera unchanged. All fits and strength remain prototype.'
    o['model_fidelity']='DESIGN_GEOMETRY'
    save_json(ROOT/'reports/display_frame_geometry.json',dict(revision=P['revision'],dimensions_mm=dimensions(),
        before_volume_mm3=before.volume(),after_volume_mm3=after.volume(),changed_existing_ids=['Display_Frame'],
        new_prints=0,new_fasteners=0,source=S['approved_geometry'],central_mast='UNCHANGED',strength='NOT_TESTED'))
    print('DISPLAY_FRAME_FLUSH_COMPLETE',flush=True)
