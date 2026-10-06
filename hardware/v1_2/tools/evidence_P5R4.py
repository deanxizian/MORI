"""Reproducible geometric/DC/stencil evidence. No physical-test claims."""
from review_P5R4 import *
import all_trace_review_P5R2 as atlas
import heapq,csv,xml.etree.ElementTree as ET
atlas.paths,atlas.source,atlas.O,atlas.KINDS=paths,source,O,KINDS

def pin(b,ref,num):
 return next(p for f in b.GetFootprints() if f.GetReference()==ref for p in f.Pads() if p.GetNumber()==str(num))
def network(b,net):
 """Explicit tracks/vias only. No fictitious straight line through a pour."""
 g=collections.defaultdict(list)
 def node(p,l):return (*[round(x,4)for x in p],int(l))
 for t in b.GetTracks():
  if t.GetNetname()!=net:continue
  if isinstance(t,k.PCB_VIA):
   a,z=node(xy(t.GetPosition()),F),node(xy(t.GetPosition()),B)
   data={'kind':'via','uuid':t.m_Uuid.AsString(),'length_mm':0,'drill_mm':k.ToMM(t.GetDrillValue())}
  else:
   a,z=node(xy(t.GetStart()),t.GetLayer()),node(xy(t.GetEnd()),t.GetLayer())
   data={'kind':'track','uuid':t.m_Uuid.AsString(),'length_mm':k.ToMM(t.GetLength()),'width_mm':k.ToMM(t.GetWidth())}
  g[a].append((z,data));g[z].append((a,data))
 return g,node
def path(b,net,aa,zz):
 g,node=network(b,net);start=node(aa[0],aa[1]);end=node(zz[0],zz[1]);q=[(0,start,[])];seen=set()
 while q:
  cost,v,pp=heapq.heappop(q)
  if v in seen:continue
  seen.add(v)
  if v==end:return {'explicit_length_mm':cost,'edges':pp}
  for w,item in g[v]:
   if w not in seen:heapq.heappush(q,(cost+item['length_mm'],w,pp+[item]))
 return None
def ground_regions(b,point):
 """Actual saved native F/B polygons and their PTH/via anchors."""
 out=[]
 for z in b.Zones():
  if z.GetIsRuleArea() or z.GetNetname()!='/GND':continue
  l=z.GetLayer();ps=z.GetFilledPolysList(l)
  for ix in range(ps.OutlineCount()):
   sh=ps.Outline(ix)
   if not sh.Collide(pt(*point),mm(.01)):continue
   anchors=[]
   for f in b.GetFootprints():
    for p in f.Pads():
     if p.GetNetname()=='/GND' and p.GetAttribute()==k.PAD_ATTRIB_PTH and p.GetEffectiveShape(l).Collide(sh,mm(.001)):
      anchors.append(f.GetReference()+'.'+p.GetNumber())
   out.append({'layer':b.GetLayerName(l),'zone':z.GetZoneName(),'polygon':ix,'PTH_ground_anchors':anchors})
 return out

result={};rows=[];vias=[]
for kind in KINDS:
 n,d,p,r=paths(kind);before=atlas.extract(kind,'before');after=atlas.extract(kind,'after')
 rows += [{'board':n,**t}for t in after['tracks']];vias += [{'board':n,**t}for t in after['vias']]
 b=k.LoadBoard(str(p));old=k.LoadBoard(str(source(kind)[2]));rr={}
 for phase,bb in [('P5R3',old),('P5R4',b)]:
  rr[phase]={'total_trace_length_mm':sum(k.ToMM(t.GetLength())for t in bb.GetTracks()if not isinstance(t,k.PCB_VIA))}
  if kind=='imu':
   rr[phase]['VDD8_to_C1_supply_explicit']=path(bb,'/+3V3',(xy(pin(bb,'U1',8).GetPosition()),F),(xy(pin(bb,'C1',1).GetPosition()),F))
   rr[phase]['C1_ground_to_GND6_explicit']=path(bb,'/GND',(xy(pin(bb,'C1',2).GetPosition()),F),(xy(pin(bb,'U1',6).GetPosition()),F))
  else:
   # The old main route begins within F1.2 rather than its exact centre.
   supply_start=(4.6,.95) if phase=='P5R3' else (4.099999,1.95)
   rr[phase]['fused_main_path']=path(bb,'/VBUS_FUSED',(supply_start,B),((19,15.7),B))
   rr[phase]['D1_branch_path']=path(bb,'/VBUS_FUSED',(((17.32,15.7) if phase=='P5R3' else (6.096,16.1036)),B),(xy(pin(bb,'D1',1).GetPosition()),B))
   # Previous D1 trace starts/ends inside the pad; diagnose as None if a
   # centreline graph alone cannot reach it. No invented comparison metric.
  rr[phase]['mask_mm']=k.ToMM(bb.GetDesignSettings().m_SolderMaskExpansion)
 result[kind]={'pcb_sha256':sha(p),'metrics':rr}
 # Diagnostic per-net views are explicitly separate from native previews.
 nn=O/'net_review'/kind;nn.mkdir(parents=True,exist_ok=True)
 for net in sorted({t['net']for t in after['tracks']}):
  (nn/(net.strip('/').replace('+','PLUS')+'.svg')).write_text(atlas.picture(after,net))
 dump(r/'geometry_evidence.json',result[kind])

imu=k.LoadBoard(str(paths('imu')[2]));rear=k.LoadBoard(str(paths('rear')[2]))
f=next(f for f in imu.GetFootprints()if f.GetReference()=='U1');ap=[]
for p in f.Pads():
 margin=p.GetSolderPasteMargin(F if False else k.F_Paste)
 L,W=k.ToMM(p.GetSize().x+2*margin.x),k.ToMM(p.GetSize().y+2*margin.y)
 ap.append({'pin':p.GetNumber(),'Cu_mm':xy(p.GetSize()),'effective_paste_mm':[L,W],'linear_ratio':.9,'rectangle_area_ratio_to_land':.81,'aspect_ratio_at_100um':min(L,W)/.1,'release_area_ratio_rect_at_100um':L*W/(2*(L+W)*.1),'maximum_stencil_um_at_rect_AR_0p66':1000*L*W/(2*(L+W)*.66)})
 assert min(L,W)/.1>=1.5 and L*W/(2*(L+W)*.1)>=.66
dump(O/'reports/imu/stencil_design.json',{'source':'TDK AN-000393 v2.4 pages 7-8; reviewed local vendor PDF','interpretation':'90 percent of both linear land dimensions, explicitly an engineering interpretation of the generic 90 percent recommendation','KiCad_ratio_override':-.05,'KiCad_per_edge_semantics_verified_from_effective_margin':True,'nominal_stencil_um':100,'thickness_status':'PROPOSED_NOT_ORDERED','manufacturing_release':False,'supplier_confirmation':'BLOCKED','rectangular_release_area_ratio_is_conservative_for_rounded_aperture':True,'copper_and_mask_unchanged':True,'pads':ap})

# CC2 actual same-net bypass test: the outgoing via must not touch any
# incoming copper. DRC cannot certify this topology condition.
p=pin(rear,'D3',1);px,py=xy(p.GetPosition());incoming=[];outgoing=[]
for t in rear.GetTracks():
 if t.GetNetname()!='/CC2' or isinstance(t,k.PCB_VIA) or t.GetLayer()!=B:continue
 (incoming if max(xy(t.GetStart())[1],xy(t.GetEnd())[1])<=py+.0001 else outgoing).append(t)
tv=[v for v in rear.GetTracks()if isinstance(v,k.PCB_VIA)and v.GetNetname()=='/CC2'];assert len(tv)==1
vp=xy(tv[0].GetPosition());gaps=[atlas.segment_distance(vp,xy(t.GetStart()),xy(t.GetEnd()))-k.ToMM(tv[0].GetWidth())/2-k.ToMM(t.GetWidth())/2 for t in incoming]
assert min(gaps)>.19,(vp,gaps)
touches_outside=[]
for a in incoming:
 for z in outgoing:
  aa,az=xy(a.GetStart()),xy(a.GetEnd());N=max(1,math.ceil(math.dist(aa,az)/.01))
  for i in range(N+1):
   v=(aa[0]+(az[0]-aa[0])*i/N,aa[1]+(az[1]-aa[1])*i/N)
   if atlas.segment_distance(v,xy(z.GetStart()),xy(z.GetEnd()))<k.ToMM(a.GetWidth()+z.GetWidth())/2-.001 and not p.GetEffectiveShape(B).Collide(pt(*v),0):touches_outside.append(v)
assert not touches_outside
dump(O/'reports/rear/CC2_flowthrough.json',{'status':'PASS','method':'Native copper coordinates; incoming-to-output-via clearance and incoming/outgoing overlap only inside D3.1 land','D3_signal_pad_mm':[px,py],'output_via_mm':vp,'minimum_via_to_incoming_copper_gap_mm':min(gaps),'overlap_outside_TVS_pad':touches_outside,'ESD_waveform_test':'NOT_TESTED'})
dump(O/'reports/rear/ground_return_regions.json',{'source_pcb_sha256':sha(paths('rear')[2]),'D2_via':{'xy':[8,10],'distance_to_GND_pad_mm':math.dist((8,10),xy(pin(rear,'D2',2).GetPosition())),'regions':ground_regions(rear,(8,10))},'D3_via':{'xy':[15.95,10.7],'distance_to_GND_pad_mm':math.dist((15.95,10.7),xy(pin(rear,'D3',2).GetPosition())),'regions':ground_regions(rear,(15.95,10.7))},'distance_is_not_HF_impedance':True})

main=result['rear']['metrics']['P5R4']['fused_main_path'];assert main
dc=[]
for temp in [20,70]:
 for plate in [.015,.020,.025]:
  rho=1.724e-5*(1+.00393*(temp-20));rt=rv=0
  for edge in main['edges']:
   if edge['kind']=='track':rt+=rho*edge['length_mm']/(edge['width_mm']*.035)
   else:rv+=rho*1.6/(math.pi*edge['drill_mm']*plate)
  dc.append({'assumed_Cu_temperature_C':temp,'assumed_outer_copper_um':35,'assumed_barrel_plating_um':plate*1000,'input_current_A':1,'trace_mOhm':rt*1000,'via_mOhm':rv*1000,'total_mV_at_1A':(rt+rv)*1000,'I2R_mW_at_1A':(rt+rv)*1000})
dump(O/'reports/rear/input_DC_model.json',{'status':'NOT_TESTED','main_path_mm':main['explicit_length_mm'],'assumptions':'35um external copper, 1.6mm length barrel, finished drill approximation; actual foil/plating require fab confirmation. F1, USB, PH contact, wire and return-plane resistance excluded. Copper temperature is a scenario input, not a thermal prediction.','scenarios':dc,'conclusion':'DC trace/barrel model only; 1A continuous/ESD/temperature qualification remains NOT_TESTED'})

# Board-to-board pin NUMBER mappings, not connector visual left/right.
current=lambda kind:k.LoadBoard(str(H/'kicad'/f'MORI_{kind}_P5R3'/f'MORI_{kind}_P5R3.kicad_pcb'))
motion,power=current('motion'),current('power');pairs=[]
expected=[('+3V3','+3V3'),('GND','GND'),('SCK','IMU_SCK'),('MOSI','IMU_MOSI'),('MISO','IMU_MISO'),('CS_N','IMU_CS'),('DRDY','IMU_DRDY'),('GND','GND')]
for i,(a,z)in enumerate(expected,1):
 aa,zz=pin(imu,'J1',i).GetNetname().strip('/'),pin(motion,'J4',i).GetNetname().strip('/')
 assert (aa,zz)==(a,z),(i,aa,zz)
 pairs.append({'from':f'imu J1.{i}','from_net':aa,'to':f'motion J4.{i}','to_net':zz,'status':'PASS'})
for rp,bb,jp,np in [(1,power,'J19',1),(2,power,'J19',2),(3,motion,'J8',1),(4,motion,'J8',2)]:
 aa,zz=pin(rear,'J3',rp).GetNetname(),pin(bb,jp,np).GetNetname();assert aa==zz,(rp,aa,zz)
 pairs.append({'from':f'rear J3.{rp}','from_net':aa,'to':f'{"power"if bb==power else "motion"} {jp}.{np}','to_net':zz,'status':'PASS'})
dump(O/'reports/interface_pairs.json',{'pairs':pairs,'raw_sense':{'rear':'J2.5 VBUS_RAW','power':'J16.1 VBUS_CHARGE -> R55 47k -> Q50 base; R56 100k shunt','source_current_limit':'ABSENT / BLOCKED until external charger and harness boundary frozen','do_not_bridge':'rear J2.1 and J2.5 must never be tied together'},'harness_assembly':'NOT_TESTED'})

def csvout(p,rr):
 keys=list(dict.fromkeys(key for r in rr for key in r))
 with p.open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(list,dict))else v for k,v in r.items()}for r in rr)
csvout(O/'all_segments.csv',rows);csvout(O/'all_vias.csv',vias)
dump(O/'reports/evidence.json',result)
print('geometry, native input DC model, effective paste and CC2 flow-through evidence written',flush=True)
