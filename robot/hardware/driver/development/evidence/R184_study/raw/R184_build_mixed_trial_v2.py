"""Independent R184-only builder for an explicitly grouped mixed body guard.

No production helper or native source is edited. Preserve all zone UUIDs and
restriction settings. The original fixed via apertures stay in board coordinates.
Geometry expectations are rounded to KiCad's integer-nanometre representation,
not accepted by a widened area tolerance. Adoption requires independent review.
"""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
import build_trial as native
from copper_geometry import *
from zone_expansion import zone_settings
from shapely.affinity import rotate,translate
from shapely.geometry import Polygon

b=Path('robot/.state/c3-completion/trials')
original=native.move_body_guards
records=[]

def quantize(g):
    return unary_union([Polygon([(round(x,6),round(y,6)) for x,y in p.exterior.coords],
        [[(round(x,6),round(y,6)) for x,y in h.coords] for h in p.interiors]) for p in parts(g)])

def grouped(owned,delta,reconstruct,rotation=0,origin=None,rotate_fixed=False,repartition=False):
    names={z.GetZoneName() for z in owned}
    expected={'BODY_D1602_0'}|{'BODY_D1602_'+str(i) for i in range(1,5)}|{'BODY_D1602_0_VIA_'+str(i) for i in range(4)}
    if names!=expected:
        return original(owned,delta,reconstruct,rotation,origin,rotate_fixed,repartition)
    assert reconstruct and rotate_fixed and repartition
    assert origin==[34.35,17.15] and abs(rotation-45)<1e-8 and all(abs(a-b)<1e-8 for a,b in zip(delta,[2.65,-1.775]))
    before={uid(z):polyset(z.Outline()) for z in owned}
    settings={uid(z):zone_settings(z.GetBoard(),z) for z in owned}
    old_tracks=unary_union([before[uid(z)] for z in owned if z.GetDoNotAllowTracks()])
    old_vias=unary_union([before[uid(z)] for z in owned if z.GetDoNotAllowVias()])
    fixed=old_tracks.difference(old_vias)
    def transformed(g):return quantize(translate(rotate(g,-rotation,origin=origin),xoff=delta[0],yoff=delta[1]))
    body=next(z for z in owned if z.GetZoneName()=='BODY_D1602_0')
    via_only=[z for z in owned if '_VIA_' in z.GetZoneName()]
    assert not body.GetDoNotAllowVias() and body.GetDoNotAllowTracks()
    assert all(z.GetDoNotAllowVias() and not z.GetDoNotAllowTracks() for z in via_only)
    comparable=[{k:v for k,v in settings[uid(z)].items() if k!='GetZoneName'} for z in via_only]
    assert all(s==comparable[0] for s in comparable)
    target=quantize(transformed(before[uid(body)]).difference(fixed))
    regions={uid(z):quantize(transformed(before[uid(z)]).difference(fixed)) for z in via_only}
    replacement=native.repartition_via_guards(regions,target)
    for z in owned:
        native.set_outline(z,quantize(replacement[uid(z)]) if z in via_only else transformed(before[uid(z)]))
    track_target=unary_union([transformed(before[uid(z)]) for z in owned if z.GetDoNotAllowTracks()])
    via_target=quantize(track_target.difference(fixed))
    actual_tracks=unary_union([polyset(z.Outline()) for z in owned if z.GetDoNotAllowTracks()])
    actual_vias=unary_union([polyset(z.Outline()) for z in owned if z.GetDoNotAllowVias()])
    assert actual_tracks.symmetric_difference(track_target).area<1e-7
    assert actual_vias.symmetric_difference(via_target).area<1e-7
    assert all(zone_settings(z.GetBoard(),z)==settings[uid(z)] for z in owned)
    row=dict(method=__doc__,fixed_aperture_area_mm2=fixed.area,
             track_union_error_mm2=actual_tracks.symmetric_difference(track_target).area,
             via_union_error_mm2=actual_vias.symmetric_difference(via_target).area,
             guards={uid(z):dict(name=z.GetZoneName(),settings=settings[uid(z)],expected_wkb_hex=polyset(z.Outline()).wkb_hex) for z in owned})
    records.append(row)
    return {k:v for k,v in row.items() if k!='guards'}

native.move_body_guards=grouped
source,destination,plan=sys.argv[1:4]
assert json.loads(Path(plan).read_text())['revision']=='R184C'
native.build(source,destination,plan)
(b/'R184C-mixed-guard-build.json').write_text(json.dumps(records,indent=2)+'\n')
