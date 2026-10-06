"""Final local placement/route refinement, from an immutable routing checkpoint."""
from update_native_P5R7 import *
from geometry_guard_P5 import Guard
OUT=HERE/'reports/motion'
name,d,p=paths('motion')
checkpoint=OUT/'routed_before_polish.kicad_pcb'
if not checkpoint.exists():checkpoint.write_bytes(p.read_bytes())
b=k.LoadBoard(str(checkpoint))
original=k.LoadBoard(str(paths('motion','P5R6')[2]))
orig={t.m_Uuid.AsString():t for t in original.GetTracks()}
# Compare a rotated horizontal resistor with the failed vertical translation.
# It opens two upper corridors without crossing the original charge/head/ADC routes.
r=next(f for f in b.GetFootprints()if f.GetReference()=='R19')
oldpos=r.GetPosition();angle=k.EDA_ANGLE(90,k.DEGREES_T)
for z in b.Zones():
    if z.GetZoneName() in [prefix+'R19'+suffix for prefix in ['BODY_','NETBODY_','VIA_BODY_']for suffix in ['','_OPPOSITE']]:
        z.Rotate(oldpos,angle);z.Move(pt(-1,2))
r.Rotate(oldpos,angle);r.Move(pt(-1,2))
assert xy(r.GetPosition())==(32,16.5) and r.GetOrientationDegrees()==0
for t in list(b.GetTracks()):
    if t.GetNetname()in ['/ARM_FEEDBACK','/ARM_Q'] and t.m_Uuid.AsString()not in orig:b.Delete(t)
for uid in ['2ebd696d-2250-4fbc-b686-d601755a8b02','cde4911c-37c6-4e68-be4a-882d3b163c08']:
    if not any(t.m_Uuid.AsString()==uid for t in b.GetTracks()):b.Add(orig[uid].Duplicate())
track(b,'/ARM_Q',[(31.175,15.138399),(31.175,16.5)],.2,k.B_Cu)
track(b,'/ARM_FEEDBACK',[(32.825,16.5),(32.825,27.605),(30.23,30.2)],.2,k.B_Cu)

# Replace the local CLR branch, removing its now-redundant original via.
clr_old={'758d22c4-c090-4b53-a70f-7da39f31646f','f8e94817-cd34-462b-a659-d9a9e661b56c',
 '23d8f828-c1ef-4f5b-bea0-f430e2154d5c','e1454b8e-a68c-48c6-b61e-54cab55e04d1','59de2d0a-79c8-46b0-93a3-e3fd26fdf267'}
for t in list(b.GetTracks()):
    if t.GetNetname()=='/CLR_N' and (t.m_Uuid.AsString()not in orig or t.m_Uuid.AsString()in clr_old):b.Delete(t)
new_routes=[
 ('/CLR_N',k.B_Cu,[(27,15.85),(29.25,15.85),(29.7,16.3),(30,16.6),(30,19.35)]),
 ('/CLR_N',k.F_Cu,[(29.7,16.3),(30.07,15.93),(47.5,15.93),(48,16.43),(48,27.6),(48.5,28.1)])]
for net,l,points in new_routes:track(b,net,points,.2,l)
via(b,'/CLR_N',29.7,16.3,vd=.8,dr=.3,grid=False)

# Center the SCK via on the resistor escape, removing the 0.025mm pad-centre jog.
for t in list(b.GetTracks()):
    if t.GetNetname()=='/IMU_SCK' and t.m_Uuid.AsString()not in orig:
        if isinstance(t,k.PCB_VIA) and xy(t.GetPosition())==(27.3,25.7):t.SetPosition(pt(27.325,25.7))
        elif not isinstance(t,k.PCB_VIA) and t.GetLayer()==k.B_Cu and max(xy(t.GetStart())[0],xy(t.GetEnd())[0])<28:b.Delete(t)
        elif not isinstance(t,k.PCB_VIA) and t.GetLayer()==k.F_Cu:
            for get,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
                q=xy(get())
                if q==(27.3,25.7):setter(pt(27.325,25.7))
                elif q==(28.6,24.4):setter(pt(28.625,24.4))
track(b,'/IMU_SCK',[(27.325,27),(27.325,25.7)],.2,k.B_Cu)

# Move one MOSI via 0.1mm diagonally, so the tiny final kink becomes a straight run.
for t in list(b.GetTracks()):
    if t.GetNetname()!='/IMU_MOSI' or t.m_Uuid.AsString()in orig:continue
    if isinstance(t,k.PCB_VIA):
        if xy(t.GetPosition())==(34,29.4):t.SetPosition(pt(34.1,29.3))
        continue
    a,z=xy(t.GetStart()),xy(t.GetEnd())
    if t.GetLayer()==k.F_Cu and set([a,z])=={(33.9,29.3),(34,29.4)}:b.Delete(t);continue
    for get,setter in [(t.GetStart,t.SetStart),(t.GetEnd,t.SetEnd)]:
        q=xy(get())
        if q in [(34,29.4),(33.9,29.3)]:setter(pt(34.1,29.3))

# Reconnect the existing R13/J4 CS T-junction as one continuous horizontal run.
for t in b.GetTracks():
    if t.GetNetname()=='/IMU_CS' and not isinstance(t,k.PCB_VIA) and t.m_Uuid.AsString()not in orig:
        if xy(t.GetEnd())==(45.5,21.336):t.SetEnd(pt(45.719999,21.336))
        elif xy(t.GetStart())==(45.5,21.336):t.SetStart(pt(45.719999,21.336))

# Loading a checkpoint without a matching project uses KiCad default severities.
# Restore the complete source project settings, then load/refill with that project.
oldname,oldd,_=paths('motion','P5R6')
pro=oldd/(oldname+'.kicad_pro')
(d/(name+'.kicad_pro')).write_text(pro.read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
k.SaveBoard(str(p),b)
# SaveBoard may write settings attached to a checkpoint; restore once more.
(d/(name+'.kicad_pro')).write_text(pro.read_text().replace(oldname,name).replace('V1.2-H0.5-P5R6','V1.2-H0.5-P5R7'))
b=k.LoadBoard(str(p));b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
dump(OUT/'placement_refinement.json',{
 'reference':'R19','before':{'xy_mm':[33,16],'rotation_deg':-90},'after':{'xy_mm':[32,16.5],'rotation_deg':0},
 'reason':'Compared vertical translation and horizontal orientation. Rotated position opens E socket corridors while retaining original HEAD_BUS, CHG_N, WHEEL_ADC_IN and C1 decoupling geometry.',
 'R19_numbered_functions_unchanged':True,'no_other_component_pose_change':True,
 'ground_and_signal_via_changes':'See native before/after copper inventory; no capacitor-return or power trace moved.'})
checks('motion','polished')
