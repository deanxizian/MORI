"""Conservative path resistance scenarios from native copper, not ampacity."""
from candidate import *
b=load();ts={t.m_Uuid.AsString():t for t in b.GetTracks()};j=json.loads((R/'load_path_audit.json').read_text());rows=[]
for r in j['rows']:
 if not ((r['net']=='/BAT_MON'and r['destination']in ['J4.2','F70.1'])or r['net']in ['/H6_IN','/H_PRE','/C5_VIN']):continue
 track_sum=0;length=0;via_specs=[];widths=[]
 for uid in r['route_uuids']:
  t=ts.get(uid)
  if not t:continue
  if isinstance(t,k.PCB_VIA):via_specs.append(k.ToMM(t.GetDrillValue()));continue
  L=math.dist(xy(t.GetStart()),xy(t.GetEnd()));w=k.ToMM(t.GetWidth());length+=L;widths.append(w)
  track_sum+=1.724e-8*(L/1000)/((w/1000)*70e-6)
 scenarios=[]
 for temp in [20,80]:
  factor=1+.00393*(temp-20)
  for plating in [15,20,25]:
   # Final barrel hole diameter and uniform plating, not a manufacturing spec.
   vr=sum(1.724e-8*.0016/(math.pi*(d/1000)*(plating*1e-6))for d in via_specs)
   resistance=(track_sum+vr)*factor
   scenarios.append({'assumed_copper_temperature_C':temp,'assumed_via_plating_um':plating,'estimated_path_ohm':resistance,'loads':[{'scenario_current_A':i,'drop_V':i*resistance,'copper_loss_W':i*i*resistance}for i in [1,2,3.5]]})
 rows.append({'net':r['net'],'source':r['source'],'destination':r['destination'],'status':r['status'],'path_min_track_mm':min(widths),'track_length_sum_mm':length,'via_drills_mm':via_specs,'scenarios':scenarios})
dump(R/'power_path_estimates.json',{'pcb_sha256':sha(PCB),'outer_copper_nominal_um':70,'board_thickness_mm':1.6,'rho20_ohm_m':1.724e-8,'copper_alpha_per_C':.00393,'physical_status':'NOT_TESTED','method':'Sum full lengths of a native-shape connected load path. Ignores parallel plane benefits, contacts, shunt/semiconductor/inductor resistance. Includes full via barrel length; 15/20/25 um are scenarios, not verified plating. 20/80 C are calculation inputs, NOT predicted or measured temperatures. 1/2/3.5 A are test scenarios, NOT permissible continuous currents.','rows':rows})
print([(r['net'],r['destination'],round(r['track_length_sum_mm'],2),r['path_min_track_mm'])for r in rows])
