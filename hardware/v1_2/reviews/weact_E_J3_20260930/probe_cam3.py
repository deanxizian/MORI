from update_native_P5R7 import *
b=k.LoadBoard(str(HERE/'reports/motion/R9_lower_partial.kicad_pcb'))
for f in b.GetFootprints():
 for q in f.Pads():
  if q.GetNetname()=='/CAM_3V3':print(f.GetReference(),q.GetNumber(),xy(q.GetPosition()))
for t in b.GetTracks():
 if t.GetNetname()=='/CAM_3V3':print(t.m_Uuid.AsString(),'VIA'if isinstance(t,k.PCB_VIA)else b.GetLayerName(t.GetLayer()),xy(t.GetStart()),xy(t.GetEnd()),k.ToMM(t.GetWidth()))
