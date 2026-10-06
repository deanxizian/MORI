"""Intentional small SMD GND plane junctions and body-IMU ground stitching.
No DRC exclusions; every change must be checked by native DRC afterwards.
"""
from pathlib import Path
import pcbnew as k,json,sys
R=Path(__file__).resolve().parents[1];name=sys.argv[1];p=R/'kicad'/name/(name+'.kicad_pcb');b=k.LoadBoard(str(p));mm=k.FromMM
for f in b.GetFootprints():
 for pad in f.Pads():
  if pad.GetNetname()=='/GND' and pad.GetAttribute()==k.PAD_ATTRIB_SMD:
   pad.SetLocalZoneConnection(k.ZONE_CONNECTION_FULL)
if name=='MORI_imu_P1':
 pos=k.VECTOR2I(mm(10),mm(14))
 if not any(isinstance(t,k.PCB_VIA) and t.GetPosition()==pos for t in b.GetTracks()):
  v=k.PCB_VIA(b);v.SetPosition(pos);v.SetWidth(mm(.6));v.SetDrill(mm(.3));v.SetViaType(k.VIATYPE_THROUGH);v.SetLayerPair(k.F_Cu,k.B_Cu);v.SetNet(b.GetNetsByName()['/GND']);b.Add(v)
for z in b.Zones():z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b);print(name,'explicit GND junctions applied; DRC required')
