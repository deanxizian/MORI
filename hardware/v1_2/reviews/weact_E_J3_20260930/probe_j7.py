from update_native_P5R7 import *
b=k.LoadBoard(str(HERE/'reports/motion/socket_escape_v4_partial.kicad_pcb'))
for f in b.GetFootprints():
 if f.GetReference() in ['J7','R8','R9']:
  print(f.GetReference(),[(q.GetNumber(),q.GetNetname(),xy(q.GetPosition()))for q in f.Pads()])
for t in b.GetTracks():
 if t.GetNetname()=='/BAT_ADC_IN':print(t.m_Uuid.AsString(),'VIA'if isinstance(t,k.PCB_VIA)else b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()))
