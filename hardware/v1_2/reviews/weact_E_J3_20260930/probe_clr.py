from update_native_P5R7 import *
b=k.LoadBoard(str(HERE/'reports/motion/socket_escape_v5_partial.kicad_pcb'))
for t in b.GetTracks():
 if t.GetNetname()=='/CLR_N'and t.GetLayer()==k.B_Cu:print(t.m_Uuid.AsString(),xy(t.GetStart()),xy(t.GetEnd()),'VIA'if isinstance(t,k.PCB_VIA)else'')
