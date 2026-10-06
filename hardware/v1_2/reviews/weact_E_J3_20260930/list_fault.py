from update_native_P5R7 import *
b=k.LoadBoard(str(HERE/'reports/motion/long_socket_screen_source.kicad_pcb'))
for t in b.GetTracks():
 if t.GetNetname()=='/FAULT_N':print(t.m_Uuid.AsString(), 'VIA'if isinstance(t,k.PCB_VIA)else b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()))
