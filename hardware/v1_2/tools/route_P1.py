#!/usr/bin/env python3
"""Reproducible DSN / SES native workflow; P1 is not manufacturing released."""
from pathlib import Path
import pcbnew as k
import json,sys
R=Path(__file__).resolve().parents[1]
name,action=sys.argv[1:3];D=R/'kicad'/name;pcb=D/(name+'.kicad_pcb')
b=k.LoadBoard(str(pcb));d=json.loads((D/'connectivity.json').read_text());p=json.loads((D/(name+'.kicad_pro')).read_text());mm=k.FromMM
nc=k.NETCLASS('Default');nc.SetClearance(mm(.15));nc.SetTrackWidth(mm(.20));nc.SetViaDiameter(mm(.6));nc.SetViaDrill(mm(.3))
ns=b.GetDesignSettings().m_NetSettings;ns.SetNetclass('Default',nc)
cl=[dict(name='Default',clearance=.15,track_width=.2,via_diameter=.6,via_drill=.3)]
patterns=[]
for netname,net in b.GetNetsByName().items():net.SetNetClass(nc)
for label,width in [('LogicPower',.25),('MainPower',1.0)]:
 c=k.NETCLASS(label);c.SetClearance(mm(.15 if label=='LogicPower' else .2));c.SetTrackWidth(mm(width));c.SetViaDiameter(mm(1.2 if width>1 else .6));c.SetViaDrill(mm(.6 if width>1 else .3));ns.SetNetclass(label,c)
 cl.append(dict(name=label,clearance=.15 if label=='LogicPower' else .2,track_width=width,via_diameter=1.2 if width>1 else .6,via_drill=.6 if width>1 else .3))
 for n in d.get('power_nets' if label=='LogicPower' else 'high_current_nets',[]):
  net=b.GetNetsByName()['/'+n];net.SetNetClass(c);ns.SetNetclassPatternAssignment('/'+n,label);patterns.append(dict(netclass=label,pattern='/'+n))
p['net_settings']['classes']=cl;p['net_settings']['netclass_patterns']=patterns;(D/(name+'.kicad_pro')).write_text(json.dumps(p,indent=2)+'\n');ns.RecomputeEffectiveNetclasses()
if action=='prepare':
 assert len(b.GetTracks())==0
 k.SaveBoard(str(pcb),b);assert k.ExportSpecctraDSN(b,str(D/(name+'.dsn')))
 print(name,'DSN exported')
elif action=='import':
 assert k.ImportSpecctraSES(b,str(D/(name+'.ses')))
 k.SaveBoard(str(pcb),b);print(name,len(b.GetTracks()),'tracks/vias imported')
elif action=='zones':
 assert len(b.Zones())==0
 w,h=d['size']
 for layer in [k.F_Cu,k.B_Cu]:
  z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.GetNetsByName()['/GND']);z.SetLocalClearance(mm(.2));z.SetThermalReliefGap(mm(.25));z.SetThermalReliefSpokeWidth(mm(.25));z.SetPadConnection(k.ZONE_CONNECTION_THERMAL)
  z.SetMinThickness(mm(.15));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS);poly=z.Outline();poly.NewOutline()
  for x,y in [(0,0),(w,0),(w,h),(0,h)]:poly.Append(mm(x),mm(y))
  b.Add(z)
 k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(pcb),b);print(name,'GND planes filled')
else:raise SystemExit('prepare|import|zones required')
