"""Align the two existing trial hex nuts with their existing hex pockets.

This corrects an assembly orientation, not fastener selection or horn fit.
Every dimension, bolt axis and printed surface remains unchanged.
"""
from common import *
from validate import Solid


def apply_reaction_nut_alignment():
    q=P.get('reaction_nut_alignment', {})
    if not q.get('enabled'):
        return
    assembled();bpy.context.view_layer.update()
    rows=[]
    for name, host in q['nut_hosts'].items():
        o=bpy.data.objects[PREFIX+name]
        assert o.get('mori_owner')==OWNER
        before=Solid(o);center=Vector((before.lo+before.hi)/2)
        rotation=(Matrix.Translation(center)
                  @Matrix.Rotation(math.radians(q['rotation_y_deg']),4,'Y')
                  @Matrix.Translation(-center))
        prior=float((before.m^Solid(bpy.data.objects[PREFIX+host]).m).volume())
        # Bake the rigid rotation into this owned mesh. Object origin, parent,
        # and assembled-position metadata remain stable for scene controls.
        o.data.transform(o.matrix_world.inverted()@rotation@o.matrix_world)
        o.data.update();SOLIDS.pop(o.name,None)
        o['nut_pocket_alignment']='M1.52: same trial hex nut rotated 30deg about its unchanged Y bolt axis.'
        o['interface_status']='Trial fastener envelope; hex orientation corrected only. Supplier, thread/engagement, horn interface and physical fit remain unreleased.'
        after=Solid(o)
        overlap=float((after.m^Solid(bpy.data.objects[PREFIX+host]).m).volume())
        assert abs(overlap)<1e-6,(name,overlap)
        rows.append(dict(nut=name,host=host,center_mm=list(center),rotation_y_deg=q['rotation_y_deg'],
                         previous_overlap_mm3=prior,corrected_overlap_mm3=overlap,
                         dimension_change=False,fastener_selection='BLOCKED'))
    save_json(ROOT/'reports/reaction_nut_alignment_geometry.json',dict(
        revision=P['revision'],rows=rows,printed_geometry_changed=False,
        physical_fit='NOT_TESTED',horn_interface='BLOCKED',manufacturing_release=False))
    print('REACTION_NUT_ALIGNMENT',rows,flush=True)
