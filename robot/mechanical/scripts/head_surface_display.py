"""Display normals for planar head prints; never changes vertices or topology."""
from common import *


def planar_directions(name):
    axes=[Vector((1,0,0)),Vector((0,1,0)),Vector((0,0,1))]
    h=P['head_print_cleanup']
    if name=='Pitch_Cradle' and h.get('cradle_rear_profile')=='folded_u':
        run=h['cradle_outer_half_width_mm']-h['cradle_fold_rear_abs_x_mm']
        rise=h['cradle_side_rear_y_mm']-h['cradle_rear_y_mm']
        axes += [Vector((rise,run,0)).normalized(),Vector((rise,-run,0)).normalized()]
    if name=='Pitch_Yoke':
        run=h['floor_upper_half_width_mm']-h['floor_lower_half_width_mm']
        rise=h['yoke_floor_z_from_head_mm'][1]-h['yoke_floor_z_from_head_mm'][0]
        axes += [Vector((rise,0,run)).normalized(),Vector((rise,0,-run)).normalized()]
    if name=='Display_Frame':
        tr=Matrix.Rotation(math.radians(P['layout_cleanup']['display_mount_pitch_deg']),3,'X')
        axes += [tr@Vector((0,1,0)),tr@Vector((0,0,1))]
    return axes


def planar_faces(o):
    s=P['head_surface_display'];directions=planar_directions(o.name.removeprefix(PREFIX))
    normal_transform=o.matrix_world.to_3x3().inverted().transposed()
    threshold=math.cos(math.radians(s['planar_alignment_tolerance_deg']))
    return [max(abs((normal_transform@p.normal).normalized().dot(n)) for n in directions)>=threshold
            for p in o.data.polygons]


def apply_head_surface_display():
    s=P.get('head_surface_display',{})
    if not s.get('enabled'):return
    rows=[]
    for name in s['target_part_ids']:
        o=bpy.data.objects[PREFIX+name];me=o.data;me.update();is_planar=planar_faces(o)
        edge_faces=[[] for _ in me.edges]
        for p,flat in zip(me.polygons,is_planar):
            p.use_smooth=not flat
            for k in p.loop_indices:edge_faces[me.loops[k].edge_index].append(p.index)
        angle=math.radians(s['sharp_edge_angle_deg'])
        flat_angle=math.radians(s['planar_alignment_tolerance_deg'])
        for e,fs in zip(me.edges,edge_faces):
            if len(fs)!=2:continue
            a,b=fs;difference=me.polygons[a].normal.angle(me.polygons[b].normal,0)
            if difference>angle or ((is_planar[a] or is_planar[b]) and difference>flat_angle):
                e.use_edge_sharp=True
        me.update()
        # Blender's corner-normal computation can drift on very thin Boolean
        # triangles even when the face is flat. Store the geometric face normal
        # explicitly, preserving the computed smooth normals on curved regions.
        normals=[n.vector[:] for n in me.corner_normals]
        for p,flat in zip(me.polygons,is_planar):
            if flat:
                for k in p.loop_indices:normals[k]=p.normal[:]
        me.normals_split_custom_set(normals);me.update()
        o['surface_display_revision']=s['revision']
        o['surface_display_policy']='Designed planes have explicit face normals; curved walls retain smooth corner normals with sharp boundary edges. No physical geometry changed.'
        rows.append({'id':name,'planar_faces':sum(is_planar),'smooth_curved_faces':sum(p.use_smooth for p in me.polygons),
                     'sharp_edges':sum(e.use_edge_sharp for e in me.edges),
                     'has_custom_normals':me.has_custom_normals,'geometry_operation':'NONE'})
    save_json(ROOT/'reports/head_surface_display.json',{'revision':P['revision'],'status':'GENERATED_PENDING_VALIDATION','parts':rows})
    print('HEAD_SURFACE_DISPLAY_COMPLETE',flush=True)
