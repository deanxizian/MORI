from candidate import *
b=load();g=Guard(b,'/GND');p=(41.825,22);choices=[]
for vd,dr in [(.6,.3),(.5,.25)]:
 for x in [42.7+i*.1 for i in range(8)]:
  for y in [21.5+i*.1 for i in range(8)]:
   q=(round(x,3),round(y,3))
   if not g.via_clear(q,vd):continue
   for line in simple(p,q)+[[p,(q[0],p[1]),q]]:
    if all(g.line_clear(a,z,F,.2)for a,z in zip(line,line[1:])):choices.append((math.dist(p,q)+(.2 if vd<.6 else 0),vd,dr,line));break
assert choices
_,vd,dr,line=min(choices);print('R51 ground',vd,dr,line)
track(b,'/GND',line,.2,F);via(b,'/GND',*line[-1],vd,dr,grid=False)
# Remove the exploratory stitch; the native copper graph identified R51 instead.
for t in list(b.GetTracks()):
 if isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),(41.4,44.8))<.001:b.Delete(t)
 for_unused=0
# Clip only the seven test-point circle segments intersected by exposed lands.
r=json.loads((R/'24_local_drc.json').read_text());ids={x['uuid']for v in r['violations']if v['type']=='silk_over_copper'for x in v['items']};clipped=[]
for f in b.GetFootprints():
 for s in list(f.GraphicalItems()):
  if s.m_Uuid.AsString()in ids:
   assert f.GetReference()in ['TP61','TP71'] and s.GetLayer()==k.F_SilkS
   clipped.append({'reference':f.GetReference(),'uuid':s.m_Uuid.AsString()});f.Remove(s)
for t in b.GetTracks():
 if isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),line[-1])<.001:
  t.SetFrontTentingMode(k.TENTING_MODE_TENTED);t.SetBackTentingMode(k.TENTING_MODE_TENTED)
save(b);dump(R/'26_ground_silk_changes.json',{'R51_ground_path':line,'via_diameter':vd,'via_drill':dr,'clipped_silkscreen_segments':clipped})
check('26_copper');snapshot('26_copper')
