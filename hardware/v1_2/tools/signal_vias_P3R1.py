"""Set small-current signal vias to 0.6/0.3 mm within inherited rule limits.

This opens routing channels between 1.25 mm connector fanout rows. Existing
load-carrying vias, grounds and buck switching/Kelvin paths are preserved.
0.15 mm nominal annulus; actual fabrication tolerances remain a release gate.
"""
import sys,json
import pcbnew as k
from layout_P3R1 import paths,xy,mm
kind=sys.argv[1];_,_,p,r=paths(kind);b=k.LoadBoard(str(p));log=[]
rules=json.loads((p.parent/(p.stem+'.kicad_pro')).read_text())['board']['design_settings']['rules']
diameter=max(.6,rules['min_via_diameter'],.3+2*rules['min_via_annular_width'])
protected={'/GND','/M5_FB','/C5_FB','/M5_SW','/C5_SW','/M5_BOOT','/C5_BOOT','/KELVIN_P','/KELVIN_N',
 '/BAT_MON','/BAT_REV','/BAT_IN','/W9','/W_PRE','/W_VM','/H6','/H_PRE','/H_VM','/M5_VIN','/C5_VIN','/+5V_MOTION','/+5V_CAM','/W_DUMP','/H_DUMP'}
for t in b.GetTracks():
 if not isinstance(t,k.PCB_VIA) or t.GetNetname() in protected:continue
 old=k.ToMM(t.GetWidth(k.F_Cu))
 if old>.801 or abs(old-diameter)<.001 or k.ToMM(t.GetDrill())>.3:continue
 log.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname(),xy_mm=xy(t.GetPosition()),before_mm=old,after_mm=diameter,drill_mm=k.ToMM(t.GetDrill())))
 t.SetWidth(mm(diameter))
k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)
(r/'signal_via_geometry.json').write_text(json.dumps(log,indent=2)+'\n');print(kind,'signal vias adjusted',len(log),flush=True)
