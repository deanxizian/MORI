from update_native_P5R7 import *
from geometry_guard_P5 import Guard,obstacles
b=k.LoadBoard(str(HERE/'reports/motion/R9_lower_partial.kicad_pcb'))
for t in b.GetTracks():
 if t.IsOnLayer(k.F_Cu) and any(38<x<59 and 14.8<y<15.2 for x,y in[xy(t.GetStart()),xy(t.GetEnd())]):print(t.GetNetname(),t.m_Uuid.AsString(),'VIA'if isinstance(t,k.PCB_VIA)else'F',xy(t.GetStart()),xy(t.GetEnd()))
for x in range(28,61):
 q=(x,15.45);o=obstacles(b,'/BAT_ADC_IN',q,k.F_Cu)
 if o:print(q,o)
print('via59,15.35',obstacles(b,'/BAT_ADC_IN',(59,15.35),k.F_Cu,.8,True),obstacles(b,'/BAT_ADC_IN',(59,15.35),k.B_Cu,.8,True))
