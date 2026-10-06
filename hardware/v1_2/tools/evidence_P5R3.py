"""Read-only evidence of the accepted P5R3 copper; no hardware measurements."""
from review_P5R3 import *
from all_trace_review_P5R3 import extract,picture,NODE,SHARP
import csv,xml.etree.ElementTree as ET,re
def pins(b,ref):
 f=next(f for f in b.GetFootprints()if f.GetReference()==ref)
 return {p.GetNumber():p.GetNetname()for p in f.Pads()if p.GetNumber()and p.GetNumber()!='MP'}
def ground(b,ref):
 f=next(f for f in b.GetFootprints()if f.GetReference()==ref)
 p=next(p for p in f.Pads()if p.GetNetname()=='/GND');links=[];regions=[]
 anchors=[v for v in b.GetTracks()if isinstance(v,k.PCB_VIA)and v.GetNetname()=='/GND']+[p for f in b.GetFootprints()for p in f.Pads()if p.GetNetname()=='/GND'and p.GetAttribute()==k.PAD_ATTRIB_PTH]
 for z in b.Zones():
  if z.GetIsRuleArea()or z.GetNetname()!='/GND'or z.GetLayer()!=F:continue
  poly=z.GetFilledPolysList(F)
  for i in range(poly.OutlineCount()):
   sh=poly.Outline(i)
   if not p.GetEffectiveShape(F).Collide(sh,mm(.001)):continue
   regions.append({'zone':z.GetZoneName(),'polygon':i})
   for a in anchors:
    if not a.GetEffectiveShape(F).Collide(sh,mm(.001)):continue
    inner=[]
    for iz in b.Zones():
     if iz.GetIsRuleArea()or iz.GetNetname()!='/GND'or iz.GetLayer()not in[k.In1_Cu,k.In2_Cu]:continue
     ip=iz.GetFilledPolysList(iz.GetLayer())
     for ix in range(ip.OutlineCount()):
      if a.GetEffectiveShape(iz.GetLayer()).Collide(ip.Outline(ix),mm(.001)):inner.append({'layer':b.GetLayerName(iz.GetLayer()),'zone':iz.GetZoneName(),'polygon':ix})
    links.append({'xy_mm':xy(a.GetPosition()),'straight_distance_mm':math.dist(xy(p.GetPosition()),xy(a.GetPosition())),'uuid':a.m_Uuid.AsString(),'inner_GND_regions':inner})
 links=sorted(links,key=lambda v:v['straight_distance_mm'])
 return {'pad':ref+'.'+p.GetNumber(),'pad_xy_mm':xy(p.GetPosition()),'F_Cu_regions':regions,'nearest_actual_F_Cu_anchors':links[:4],
         'distance_meaning':'straight distance to a via/PTH on the same filled top copper polygon, NOT solved HF return length'}
results={};changes=[]
for kind in KINDS:
 n,d,p,r=paths(kind);old=k.LoadBoard(str(source(kind)[2]));new=k.LoadBoard(str(p))
 before=json.loads((r/'before_inventory.json').read_text());after=json.loads((r/'after_inventory.json').read_text())
 for typ in ['tracks','vias']:
  a={v['uuid']:v for v in before[typ]};b={v['uuid']:v for v in after[typ]}
  clean=lambda v:{key:x for key,x in v.items()if key!='flags'}
  for uid in sorted(set(a)|set(b)):
   if uid in a and uid in b and clean(a[uid])==clean(b[uid]):continue
   changes.append({'board':n,'type':typ,'uuid':uid,'action':'added'if uid not in a else'removed'if uid not in b else'changed','before':clean(a[uid])if uid in a else None,'after':clean(b[uid])if uid in b else None})
 paste={}
 for label,bb in [('before',old),('after',new)]:
  ds=bb.GetDesignSettings();ap=[]
  for f in bb.GetFootprints():
   for q in f.Pads():
    if not(q.IsOnLayer(k.F_Paste)or q.IsOnLayer(k.B_Paste)):continue
    sz=xy(q.GetSize());mg=xy(q.GetSolderPasteMargin(k.F_Paste if q.IsOnLayer(k.F_Paste)else k.B_Paste));ap.append({'ref':f.GetReference(),'pin':q.GetNumber(),'copper_size_mm':sz,'effective_margin_xy_mm':mg,'aperture_bbox_mm':[sz[0]+2*mg[0],sz[1]+2*mg[1]]})
  paste[label]={'global_margin_mm':k.ToMM(ds.m_SolderPasteMargin),'global_ratio':ds.m_SolderPasteMarginRatio,'mask_expansion_mm':k.ToMM(ds.m_SolderMaskExpansion),'apertures':ap}
 results[kind]={'source_sha256':sha(source(kind)[2]),'pcb_sha256':sha(p),'paste':paste}
 if kind=='power':
  gg={}
  for label,bb in [('before',old),('after',new)]:
   gg[label]={ref:ground(bb,ref)for ref in ['C61','C71','C60','C70','C66','C76','R61','R71','U60','U70']}
  dump(r/'ground_returns_evidence.json',{'pcb_sha256':sha(p),'saved_native_fills_used':True,'measurements':'NOT_TESTED','pads':gg})
  areas=lambda bb:{z.GetZoneName():{'layer':bb.GetLayerName(z.GetLayer()),'bbox_mm':[k.ToMM(v)for v in [z.Outline().BBox().GetX(),z.Outline().BBox().GetY(),z.Outline().BBox().GetRight(),z.Outline().BBox().GetBottom()]],'no_tracks':z.GetDoNotAllowTracks(),'no_vias':z.GetDoNotAllowVias()}for z in bb.Zones()if z.GetIsRuleArea()}
  a,b=areas(old),areas(new);assert set(a)==set(b)
  dump(r/'rule_area_changes.json',{key:{'before':a[key],'after':b[key]}for key in a if a[key]!=b[key]})
 dump(r/'paste_apertures.json',paste)
dump(O/'reports/copper_changes.json',changes)
with(O/'copper_changes.csv').open('w',encoding='utf-8-sig',newline='')as f:
 w=csv.DictWriter(f,['board','type','uuid','action','before','after']);w.writeheader()
 for row in changes:w.writerow({key:json.dumps(v,ensure_ascii=False)if isinstance(v,dict)else v for key,v in row.items()})
motion=k.LoadBoard(str(paths('motion')[2]));power=k.LoadBoard(str(paths('power')[2]));pairs=[]
aliases={'/S288_BUS':'/W_BUS','/HEAD_BUS':'/H_BUS','/BAT_ADC_IN':'/BAT_ADC','/WHEEL_ADC_IN':'/WHEEL_ADC','/CURRENT_ADC_IN':'/CURRENT_ADC'}
for a,b in [('J1','J17'),('J2','J13'),('J3','J14'),('J7','J10')]:
 ma,pa=pins(motion,a),pins(power,b);assert set(ma)==set(pa)
 for num,mn in ma.items():
  pn=pa[num];ok=aliases.get(mn,mn)==pn or ('unconnected-'in mn and'unconnected-'in pn)
  pairs.append({'motion':a+'.'+num,'motion_net':mn,'power':b+'.'+num,'power_net':pn,'status':'PASS'if ok else'FAIL'})
assert all(x['status']=='PASS'for x in pairs),pairs
dump(O/'reports/interface_pairs.json',{'pairs':pairs,'view':'Pin NUMBER mapping only; mating cable view may be mirrored. Cable assembly NOT_TESTED.'})
dump(O/'reports/evidence.json',results)
print('copper changes',len(changes),'interface pairs',len(pairs),flush=True)
