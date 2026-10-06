"""Rebuild only the current, unpublished C2 trial from immutable C1 copper."""
from candidate import *
def run():
 b=k.LoadBoard(str(SD/(OLD+'.kicad_pcb')));connected(b);fs={f.GetReference():f for f in b.GetFootprints()};changes=[]
 for ref,axis in [('D30',k.FLIP_DIRECTION_LEFT_RIGHT),('F70',k.FLIP_DIRECTION_LEFT_RIGHT),('R50',k.FLIP_DIRECTION_TOP_BOTTOM)]:
  f=fs[ref];before=pads(f);f.Flip(f.GetPosition(),axis);assert before==pads(f)
  for z in b.Zones():
   n=z.GetZoneName()
   if n in ['BODY_'+ref,'NETBODY_'+ref]:z.SetZoneName(n+'_OPPOSITE')
   elif n in ['BODY_'+ref+'_OPPOSITE','NETBODY_'+ref+'_OPPOSITE']:z.SetZoneName(n.removesuffix('_OPPOSITE'))
  changes.append(dict(ref=ref,side='B.Cu',pads_unchanged=True))
 f=fs['JP70'];old=f.GetPosition();angle=k.EDA_ANGLE(-90,k.DEGREES_T)
 for z in b.Zones():
  if z.GetZoneName()in ['BODY_JP70','NETBODY_JP70','BODY_JP70_OPPOSITE','NETBODY_JP70_OPPOSITE']:z.Rotate(old,angle)
 f.SetOrientationDegrees(0);move(b,f,(35,44.5))
 changes.append(dict(ref='JP70',xy_mm=[35,44.5],angle=0))
 move(b,fs['TP71'],(23,35));changes.append(dict(ref='TP71',xy_mm=[23,35]))
 j=json.loads((HERE.parent/'j10_candidate/reports/drc.json').read_text())
 bad={i['uuid']for v in j['violations']if v['type']=='items_not_allowed'for i in v['items']}
 removed=[]
 for t in list(b.GetTracks()):
  if t.m_Uuid.AsString()in bad or t.GetNetname()in ['/BAT_ADC','/WHEEL_ADC','/H_PRE','/H6_IN','/C5_EN']:
   removed.append(dict(uuid=t.m_Uuid.AsString(),net=t.GetNetname()));b.Delete(t)
 # Preserve converter hot loops; only F70's branch connection changes face.
 for t in b.GetTracks():
  if t.GetNetname()=='/C5_VIN' and not isinstance(t,k.PCB_VIA) and xy(t.GetStart())==(30.5,39.455):t.SetLayer(k.B_Cu)
 b.GetTitleBlock().SetRevision('J10-C2 / PROTOTYPE / NOT RELEASED')
 b.GetTitleBlock().SetTitle('J10 side-entry + underside D30/F70/R50 / NOT FOR FABRICATION')
 save(b);dump(R/'changes.json',dict(changes=changes,ripped=removed,formal_boards_changed=False,mechanical_acceptance='BLOCKED',backside_F70_allowance_mm=3.09))
 check('02_placement')
if __name__=='__main__':run()
