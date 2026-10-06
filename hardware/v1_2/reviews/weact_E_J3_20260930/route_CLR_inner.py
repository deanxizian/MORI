"""Short, explicitly reviewed In2 CLR bridge around E; In1 stays GND-only."""
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
from body_keepouts_P3R1 import rectangle
name,d,p=paths('motion');OUT=HERE/'reports/motion'
b=k.LoadBoard(str(OUT/'polished_CLR_source.kicad_pcb'))
oldname,oldd,oldp=paths('motion','P5R6');old=k.LoadBoard(str(oldp));orig={t.m_Uuid.AsString()for t in old.GetTracks()}
for t in list(b.GetTracks()):
    if t.GetNetname()=='/CLR_N' and t.m_Uuid.AsString()not in orig:
        if isinstance(t,k.PCB_VIA)or t.GetLayer()==k.F_Cu:b.Delete(t)
        elif xy(t.GetEnd())==(30,19.35):t.SetEnd(pt(30,19.276))
track(b,'/CLR_N',[(30,19.276),(31.496,17.78)],.2,k.B_Cu)
inner=[(31.496,17.78),(32.12,17.78),(33.2,16.7),(33.2,16.25),(44,16.25)]
front=[(44,16.25),(47.5,16.25),(48,16.75),(48,27.9),(48.2,28.1),(48.5,28.1)]
track(b,'/CLR_N',inner,.2,k.In2_Cu);track(b,'/CLR_N',front,.2,k.F_Cu)
for x,y in [(31.496,17.78),(44,16.25)]:via(b,'/CLR_N',x,y,vd=.8,dr=.3,grid=False)
z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(k.In2_Cu);z.SetZoneName('P5R7_E_SOCKET_In2.Cu')
z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
z.Outline().BooleanAdd(rectangle([33.66,17.76,38.74,28.42]));b.Add(z)
# Keep a nearby interplane return at the bridge exit. The original start-side
# moved ground stitch at (32.1,18.6) already ties both GND planes.
guard=Guard(b,'/GND');candidate=None
for q in [(44,17.4),(43.5,17.4),(44,15.1),(44.5,17.4),(43,17.4)]:
    if guard.via_clear(q,.8):candidate=q;break
assert candidate,'No unambiguous GND return-stitch location'
via(b,'/GND',*candidate,vd=.8,dr=.3,grid=False)
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(d/(name+'.kicad_pro')).write_text((oldd/(oldname+'.kicad_pro')).read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
dump(OUT/'CLR_inner_review.json',{'net':'/CLR_N','layer':'In2.Cu','width_mm':.2,'points_mm':inner,
 'length_mm':sum(__import__('math').dist(a,z)for a,z in zip(inner,inner[1:])),
 'reason':'Avoid socket-body crossings, densely constrained outer-layer bridges and long repeated-via detours. Only a local low-rate interlock signal uses In2; In1 remains uninterrupted GND reference.',
 'return_stitch_start_mm':[32.1,18.6],'added_return_stitch_exit_mm':candidate,
 'plane_limit':'In2 is now GND pour plus one short CLR signal, not an exclusively solid GND plane. Review B-side signal return intersections; no EMC or physical qualification claim.',
 'E_projection_keepout_on_inner':True,'manufacturing_release':False})
checks('motion','inner_clr')
