from update_native_P5R7 import *
b=k.LoadBoard(str(HERE/'reports/motion/R9_corridor_partial.kicad_pcb'))
for t in b.GetTracks():
 if t.GetNetname()=='/HEAD_BUS':print(t.m_Uuid.AsString(),'VIA'if isinstance(t,k.PCB_VIA)else b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()))
