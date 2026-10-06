"""Reserve deliberate J10 signal corridors before completing endpoint routes.

Up-going signals use F.Cu; down-going signals B.Cu, in monotonic order.
Only copper is changed. All pad/part/outline interfaces stay fixed.
"""
from route import *
NETS=['/ARM_Q','/FAULT_N','/CHG_N','/BAT_ADC','/WHEEL_ADC','/CURRENT_ADC']

def run():
    b=load();(R/'09_before_bus_corridor.kicad_pcb').write_bytes(PCB.read_bytes())
    oldids=[]
    for t in list(b.GetTracks()):
        if t.GetNetname()in NETS:oldids.append(t.m_Uuid.AsString());b.Delete(t)
    routes=[
        ('/FAULT_N',F,[(44.5,31),(46.,31),(46.25,30.75),(46.25,22.9),(45.5,22.15),(45.5,21.9)]),
        ('/BAT_ADC',F,[(44.5,35),(46.,35),(46.7,34.3),(46.7,24.0)]),
        ('/WHEEL_ADC',F,[(44.5,37),(46.,37),(47.2,35.8),(47.2,28.8),(47.7,28.3),(48.25,28.3)]),
        ('/ARM_Q',B,[(44.5,29),(46.,29),(47.3,30.3),(47.3,43.7),(48.,44.4)]),
        ('/CHG_N',B,[(44.5,33),(46.,33),(46.85,33.85),(46.85,43.5),(46.3,44.05),(44.,44.05)]),
        ('/CURRENT_ADC',B,[(44.5,39),(46.,39),(46.4,39.4),(46.4,42.9),(45.95,43.35),(42.,43.35)]),
    ]
    for net,l,pts in routes:guarded(b,net,pts,.2,l)
    for net,x,y in [('/FAULT_N',45.5,21.9),('/WHEEL_ADC',48.25,28.3),('/CHG_N',44.,44.05),('/CURRENT_ADC',42.,43.35)]:
        assert Guard(b,net).via_clear((x,y),.6),(net,'via obstructed')
        via(b,net,x,y,vd=.6,dr=.3,grid=False)
    # Reuse unchanged, previously reviewed remote source geometry. The new
    # connector neighbourhood is deliberately excluded. Native guards and final
    # DRC recheck every accepted element against the candidate.
    sp=ROOT/'hardware/v1_2/kicad/MORI_power_P5R6/MORI_power_P5R6.kicad_pcb'
    src=k.LoadBoard(str(sp)); restored=[]; rejected=[]
    for t in src.GetTracks():
        net=t.GetNetname()
        if net not in NETS:continue
        a,z=xy(t.GetStart()),xy(t.GetEnd())
        if max(a[0],z[0])>=37 and min(a[0],z[0])<=48 and max(a[1],z[1])>=24 and min(a[1],z[1])<=45:continue
        g=Guard(b,net)
        good=g.via_clear(a,k.ToMM(t.GetWidth(F)))if isinstance(t,k.PCB_VIA)else g.line_clear(a,z,t.GetLayer(),k.ToMM(t.GetWidth()))
        if good:
            clone=t.Duplicate();clone.SetParent(b);clone.SetNet(b.GetNetsByName()[net]);b.Add(clone);restored.append(t.m_Uuid.AsString())
        else:rejected.append(t.m_Uuid.AsString())
    save(b);dump(R/'10_bus_corridor_changes.json',{'ripped':oldids,'corridors':[{'net':n,'layer':b.GetLayerName(l),'points':p}for n,l,p in routes],'restored_formal_remote_copper':restored,'rejected_formal_copper':rejected,'source_sha256':sha(sp)})
    snapshot('10_corridors')
if __name__=='__main__':run()
