"""Read-only native-copper evidence and bounded DC models. No bench results.

Run with KiCad's Python, after saving zone fills and running the native checks.
"""
from review_P5R5 import *
import all_trace_review_P5R2 as atlas
import csv,heapq
atlas.paths,atlas.source,atlas.O,atlas.KINDS=paths,source,O,KINDS
load=lambda p:json.loads(p.read_text())
def csvout(p,rows):
 fields=list(dict.fromkeys(x for r in rows for x in r))
 with p.open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,fields);w.writeheader();w.writerows({key:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list,tuple))else v for key,v in r.items()}for r in rows)
def pad(b,ref,num):return next(p for f in b.GetFootprints()if f.GetReference()==ref for p in f.Pads()if p.GetNumber()==str(num))
def front_only_connected(path,targets):
 """Native adjacency in a disposable in-memory copy, without zones or vias."""
 b=k.LoadBoard(str(path))
 for z in list(b.Zones()):b.Delete(z)
 for t in list(b.GetTracks()):
  if isinstance(t,k.PCB_VIA)or t.GetLayer()!=F:b.Delete(t)
 c=k.CONNECTIVITY_DATA();c.Build(b);seen=set();queue=[pad(b,*targets[0])]
 while queue:
  t=queue.pop();uid=t.m_Uuid.AsString()
  if uid in seen:continue
  seen.add(uid);queue.extend(c.GetConnectedTracks(t));queue.extend(c.GetConnectedPads(t))
 return {f'{r}.{n}':pad(b,r,n).m_Uuid.AsString()in seen for r,n in targets}
def regions(b,point,layer):
 out=[]
 for z in b.Zones():
  if z.GetIsRuleArea()or z.GetLayer()!=layer or z.GetNetname()!='/GND':continue
  ps=z.GetFilledPolysList(layer)
  # Contains evaluates the saved filled polygon, including holes; an outline
  # collision test alone would falsely include the interior of a void.
  out += [f'{z.GetZoneName()}:{i}'for i in range(ps.OutlineCount())if ps.Contains(pt(*point),i)]
 return out
def geometry(b):
 return sorted((t.GetNetname(),b.GetLayerName(t.GetLayer()),tuple(sorted([xy(t.GetStart()),xy(t.GetEnd())])),k.ToMM(t.GetWidth()),k.ToMM(t.GetDrillValue())if isinstance(t,k.PCB_VIA)else None)for t in b.GetTracks())

allrows=[];allvias=[];changes=[];result={}
for kind in KINDS:
 n,d,p,r=paths(kind);a=atlas.extract(kind,'before');z=atlas.extract(kind,'after')
 b=k.LoadBoard(str(p));old=k.LoadBoard(str(source(kind)[2]))
 allrows += [dict(board=n,**t)for t in z['tracks']];allvias += [dict(board=n,**t)for t in z['vias']]
 for typ in ['tracks','vias']:
  aa={v['uuid']:v for v in a[typ]};zz={v['uuid']:v for v in z[typ]};clean=lambda v:{k:x for k,x in v.items()if k!='flags'}
  for uid in set(aa)|set(zz):
   if uid in aa and uid in zz and clean(aa[uid])==clean(zz[uid]):continue
   changes.append(dict(board=n,type=typ,uuid=uid,before=clean(aa[uid])if uid in aa else None,after=clean(zz[uid])if uid in zz else None))
 nn=O/'net_review'/kind;nn.mkdir(parents=True,exist_ok=True)
 for net in sorted({v['net']for v in z['tracks']}):(nn/(net.strip('/').replace('+','PLUS')+'.svg')).write_text(atlas.picture(z,net))
 metrics={}
 for phase,bb in [('before',old),('after',b)]:
  ds=bb.GetDesignSettings();metrics[phase]=dict(global_paste_mm=k.ToMM(ds.m_SolderPasteMargin),paste_ratio=ds.m_SolderPasteMarginRatio,mask_mm=k.ToMM(ds.m_SolderMaskExpansion))
  assert ds.m_SolderPasteMargin==0 and ds.m_SolderPasteMarginRatio==0
 result[kind]=dict(pcb_sha256=sha(p),source_sha256=sha(source(kind)[2]),paste=metrics,copper_geometry_identical=geometry(b)==geometry(old))
 if kind=='motion':assert result[kind]['copper_geometry_identical']
 dump(r/'geometry_evidence.json',result[kind])

pp=paths('power')[2];b=k.LoadBoard(str(pp));old=k.LoadBoard(str(source('power')[2]));g={}
for num,pre in [(60,'M5'),(70,'C5')]:
 row={}
 for phase,src,bb in [('before',source('power')[2],old),('after',pp,b)]:
  caps=[f'C{num}',f'C{num+1}',f'C{num+6}']
  rr=front_only_connected(src,[(f'U{num}',1)]+[(c,2)for c in caps]);vv=front_only_connected(src,[(f'U{num}',3)]+[(c,1)for c in caps])
  regions_by_pad={ref:regions(bb,xy(pad(bb,ref,2 if ref.startswith('C')else 1).GetPosition()),F)for ref in[f'U{num}']+caps}
  row[phase]=dict(explicit_F_ground_connections_without_vias_or_pours=rr,explicit_F_VIN_connections_without_vias_or_pours=vv,
    saved_F_ground_regions=regions_by_pad,
    FB_track_length_mm=sum(k.ToMM(t.GetLength())for t in bb.GetTracks()if not isinstance(t,k.PCB_VIA)and t.GetNetname()=='/'+pre+'_FB'),
    FB_via_count=sum(isinstance(t,k.PCB_VIA)and t.GetNetname()=='/'+pre+'_FB'for t in bb.GetTracks()))
  if phase=='after':assert all(rr.values())and all(vv.values())
 g[f'U{num}']=row

# The two feedback return paths are real GND tracks in locally isolated In1
# corridors. Check their full width and all four via annuli against saved pours.
quiet=[]
for t in b.GetTracks():
 if isinstance(t,k.PCB_VIA)or t.GetLayer()!=k.In1_Cu:continue
 assert t.GetNetname()=='/GND'
 a,z=xy(t.GetStart()),xy(t.GetEnd());length=math.dist(a,z);N=max(1,math.ceil(length/.01));normal=(-(z[1]-a[1])/length,(z[0]-a[0])/length);hits=[]
 for i in range(N+1):
  for off in [-k.ToMM(t.GetWidth())/2,0,k.ToMM(t.GetWidth())/2]:
   q=tuple(a[j]+(z[j]-a[j])*i/N+off*normal[j]for j in range(2))
   if regions(b,q,k.In1_Cu):hits.append(q)
 quiet.append(dict(uuid=t.m_Uuid.AsString(),start=a,end=z,full_width_pour_contact_samples=len(hits)))
 assert not hits,('quiet trace joins plane prematurely',quiet[-1])
vias=[]
for point in [(31.8,29.5),(25.65,23.7),(31.8,43.5),(24.9,37.7)]:
 v=next(t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and math.dist(xy(t.GetPosition()),point)<.0001);touch=[]
 for layer in [F,k.In1_Cu,k.In2_Cu,B]:
  for i in range(65):
   angle=i*math.pi/32;q=(point[0]+k.ToMM(v.GetWidth())/2*math.cos(angle),point[1]+k.ToMM(v.GetWidth())/2*math.sin(angle))
   if regions(b,q,layer):touch.append(b.GetLayerName(layer));break
 vias.append(dict(xy_mm=point,pour_contact_layers=touch));assert not touch
for ref in ['R61','R71']:assert not regions(b,xy(pad(b,ref,2).GetPosition()),F)
body=load(paths('power')[3]/'body_review_final.json')
sw=[r for r in body['body_crossing_inventory']if r['reference']in['U60','U70','L60','L70']and r['net']in['/M5_SW','/C5_SW']]
assert not sw,sw
dump(O/'reports/power/buck_returns.json',dict(pcb_sha256=sha(pp),status='PASS',method='Native F-only connectivity; actual saved filled polygon Contains; quiet track edges sampled <=0.01mm and annuli at 64 angles. Geometry only, not HF inductance or noise simulation.',buck=g,quiet_In1_tracks=quiet,quiet_vias=vias,SW_body_crossings_outside_pads=sw,local_R13_exception=True,physical_validation='NOT_TESTED'))

# Verify retained power arrays using actual via coordinates and barrel sizes.
arrays=load(H/'layout_P5R3/reports/power/parallel_via_model.json')
for row in arrays:
 for p in row['centres_mm']:
  v=next(t for t in b.GetTracks()if isinstance(t,k.PCB_VIA)and t.GetNetname()==row['net']and math.dist(xy(t.GetPosition()),p)<.00001)
  assert abs(k.ToMM(v.GetDrillValue())-row['drill_mm'])<.000001
 row['retained_geometry_status']='PASS'
dump(O/'reports/power/retained_via_arrays.json',dict(pcb_sha256=sha(pp),arrays=arrays,load_sharing_and_temperature='NOT_TESTED'))

# DC sensitivity only. A supplied copper temperature is never a predicted rise.
scenarios=[]
for temp in [20,80]:
 for plate in [.015,.020,.025]:
  rho=1.724e-5*(1+.00393*(temp-20));neck=rho*2.713/(1*.070)
  for current,label in [(3.0,'illustrative_continuous_not_system_rating'),(6.48,'budget_concurrent_peak')]:
   barrel=rho*1.6/(math.pi*.45*plate*4)
   scenarios.append(dict(part='R2.2 neck + BAT_MON 4-barrel bank',temperature_C=temp,plating_um=plate*1000,current_A=current,scenario=label,neck_mOhm=neck*1000,via_bank_mOhm=barrel*1000,total_drop_mV=current*(neck+barrel)*1000,power_mW=current*current*(neck+barrel)*1000))
  for pre,cont,peak in [('M5',.5,.75),('C5',1.5,2.0)]:
   # Two serial 1/.45 SW vias, not parallel. Include a stated ripple envelope.
   one=rho*1.6/(math.pi*.45*plate)
   for current,label in [(cont,'continuous_design_target'),(peak,'peak_design_target'),(peak+.5,'peak_plus_assumed_half_ripple')]:
    scenarios.append(dict(part=pre+' SW two serial barrels',temperature_C=temp,plating_um=plate*1000,current_A=current,scenario=label,via_pair_mOhm=2*one*1000,barrel_drop_mV=current*2*one*1000,barrel_power_mW=current*current*2*one*1000))
dump(O/'reports/power/DC_model.json',dict(status='NOT_TESTED',copper_um_outer=70,barrel_length_mm=1.6,neck_width_mm=1,neck_length_mm=2.713,source_current_targets='schematic_S3/README.md and schematic_S3/reports/logic5v_calculations.json',assumptions='Uniform current sharing, finished-drill thin-wall approximation, temperatures and 15/20/25um plating are inputs, not measurements. Ripple +0.5A is an explicit stress assumption. No inferred allowed temperature rise; PCB maker must confirm plating.',excludes='Contact, fuse, spreading resistance, AC loss/inductance, regulator IC and inductor heating, plane constrictions. Does not qualify 3A output.',scenarios=scenarios))

# Full four-board numbered pin mappings, including intentional net aliases.
motion=k.LoadBoard(str(paths('motion')[2]));power=b
fixed=lambda kind:k.LoadBoard(str(H/'kicad'/f'MORI_{kind}_P5R4'/f'MORI_{kind}_P5R4.kicad_pcb'))
imu,rear=fixed('imu'),fixed('rear');pairs=[]
aliases={'/S288_BUS':'/W_BUS','/HEAD_BUS':'/H_BUS','/BAT_ADC_IN':'/BAT_ADC','/WHEEL_ADC_IN':'/WHEEL_ADC','/CURRENT_ADC_IN':'/CURRENT_ADC'}
def pair(ab,an,ar,ap,zb,zn,zr,zp,expected=None):
 a,z=pad(ab,ar,ap).GetNetname(),pad(zb,zr,zp).GetNetname()
 good=(a,z)==expected if expected else aliases.get(a,a)==z or('unconnected-'in a and'unconnected-'in z)
 assert good,(an,ar,ap,a,zn,zr,zp,z)
 pairs.append(dict(source=f'{an} {ar}.{ap}',source_net=a,destination=f'{zn} {zr}.{zp}',destination_net=z,status='PASS'))
for a,z,count in [('J1','J17',2),('J2','J13',2),('J3','J14',3),('J7','J10',8)]:
 for i in range(1,count+1):pair(motion,'motion P5R5',a,i,power,'power P5R5',z,i)
for i,(a,z)in enumerate([('+3V3','+3V3'),('GND','GND'),('SCK','IMU_SCK'),('MOSI','IMU_MOSI'),('MISO','IMU_MISO'),('CS_N','IMU_CS'),('DRDY','IMU_DRDY'),('GND','GND')],1):pair(imu,'imu P5R4','J1',i,motion,'motion P5R5','J4',i,('/'+a,'/'+z))
for rp,bb,name,jp,np in [(1,power,'power P5R5','J19',1),(2,power,'power P5R5','J19',2),(3,motion,'motion P5R5','J8',1),(4,motion,'motion P5R5','J8',2)]:pair(rear,'rear P5R4','J3',rp,bb,name,jp,np)
pair(rear,'rear P5R4','J2',5,power,'power P5R5','J16',1,('/VBUS_RAW','/VBUS_CHARGE'))
dump(O/'reports/interface_pairs.json',dict(pairs=pairs,raw_VBUS_sense='J2.5 raw sense source current limiting ABSENT/BLOCKED; external charger unselected. Never bridge rear J2.1 and J2.5.',cable_assembly='NOT_TESTED'))
csvout(O/'all_segments.csv',allrows);csvout(O/'all_vias.csv',allvias);csvout(O/'copper_changes.csv',changes)
dump(O/'reports/evidence.json',result)
print('Read-only copper, four-board interfaces and DC sensitivity evidence written.')
