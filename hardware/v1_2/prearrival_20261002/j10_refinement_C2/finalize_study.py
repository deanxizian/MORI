"""Freeze a reviewable, explicitly unfinished placement candidate.

The failed routing experiments are archived, not accepted. Mechanics must
receive the same original-position D30/F70 candidate it actually screened.
No manufacturing export, no exclusions, no changes to formal projects.
"""
from candidate import *
import prepare_routes
def run():
 history=HERE/'rejected_routing_trials';history.mkdir(exist_ok=True)
 rejected=history/'04_manual_not_accepted.kicad_pcb'
 if not rejected.exists():rejected.write_bytes(PCB.read_bytes())
 prepare_routes.run()
 b=load();fs={f.GetReference():f for f in b.GetFootprints()}
 # Reference hole0.7+0.1 in the catalogue is not the more specific PTH
 # recommendation for glass epoxy from JST's official PH FAQ.
 oldid=str(fs['J10'].GetFPID().GetLibNickname())+':'+str(fs['J10'].GetFPID().GetLibItemName())
 newlib='JST_PH_S8B-PH-K_1x08_P2.00mm_Horizontal__C2_land1p50_finished0p90'
 j=fs['J10'];j.SetFPID(k.LIB_ID('Connector_JST',newlib))
 before=[(p.GetNumber(),xy(p.GetPosition()),p.GetNetname())for p in j.Pads()]
 for p in j.Pads():p.SetSize(pt(1.5,1.5));p.SetDrillSize(pt(.9,.9))
 assert before==[(p.GetNumber(),xy(p.GetPosition()),p.GetNetname())for p in j.Pads()]
 # Store the actual larger land in the local library; inverse-transform the
 # embedded footprint back to its unplaced library orientation.
 local=k.FootprintLoad(str(D/'footprints/Connector_JST.pretty'),oldid.split(':',1)[1])
 local.SetFPID(k.LIB_ID('Connector_JST',newlib))
 for p in local.Pads():p.SetSize(pt(1.5,1.5));p.SetDrillSize(pt(.9,.9))
 k.FootprintSave(str(D/'footprints/Connector_JST.pretty'),local)
 for file in [D/(NAME+'.kicad_sch'),D/'MORI.kicad_sym',D/'assembly_bom.csv',D/'connectivity.json']:
  file.write_text(file.read_text().replace(oldid,'Connector_JST:'+newlib))
 for z in list(b.Zones()):
  if z.GetZoneName()in ['BODY_J10','NETBODY_J10','BODY_J10_OPPOSITE','NETBODY_J10_OPPOSITE']:b.Delete(z)
 rr=rect(j);full=rectangle(rr);body=rectangle(rr)
 for p in j.Pads():
  bb=p.GetBoundingBox();x1,y1,x2,y2=[k.ToMM(v)for v in [bb.GetX(),bb.GetY(),bb.GetRight(),bb.GetBottom()]]
  body.BooleanSubtract(rectangle([x1-.005,y1-.005,rr[2]+1,y2+.005]))
 body.Simplify()
 for layer in [k.F_Cu,k.B_Cu]:
  suffix=''if layer==k.F_Cu else'_OPPOSITE'
  for prefix,shape,forbid in [('NETBODY_',full,False),('BODY_',body,True)]:
   z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetZoneName(prefix+'J10'+suffix)
   z.SetDoNotAllowTracks(forbid);z.SetDoNotAllowVias(forbid);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(False)
   z.Outline().BooleanAdd(shape);b.Add(z)
 # Retain only valid, unaffected copper; leave the replacement wiring open
 # instead of keeping the failed experimental crossovers or claiming closure.
 affected={'/BAT_ADC','/WHEEL_ADC','/H_PRE','/H6_IN','/C5_EN','/ARM_Q','/FAULT_N','/CHG_N','/CURRENT_ADC'}
 cuts=[]
 for tr in list(b.GetTracks()):
  if tr.GetNetname()in affected:cuts.append(dict(uuid=tr.m_Uuid.AsString(),net=tr.GetNetname()));b.Delete(tr)
 b.GetTitleBlock().SetTitle('J10 C2 PLACEMENT STUDY / AFFECTED NETS UNROUTED / NO FABRICATION')
 b.GetTitleBlock().SetRevision('C2-A3 / BLOCKED')
 save(b);dump(R/'05_intentionally_unrouted_nets.json',dict(nets=sorted(affected),removed=cuts))
 # Clearance checks on the larger connector lands/new component faces.
 report=check('05_placement_unrouted')
 # Remove only copper reported invalid, never alter a rule or exclusion.
 b=load();bad={i['uuid']for row in report['violations']if row['severity']=='error'and row['type']not in ['starved_thermal','track_angle']for i in row['items']}
 removed=[]
 for tr in list(b.GetTracks()):
  if tr.m_Uuid.AsString()in bad:removed.append(dict(uuid=tr.m_Uuid.AsString(),net=tr.GetNetname()));b.Delete(tr)
 save(b);dump(R/'06_invalid_copper_removed.json',removed)
 report=check('FINAL_PLACEMENT_ONLY')
 args=[CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(R/'FINAL_erc.json'),str(D/(NAME+'.kicad_sch'))]
 cp=subprocess.run(args,capture_output=True,text=True)
 dump(R/'FINAL_erc_command.json',dict(argv=args,returncode=cp.returncode,stdout=cp.stdout,stderr=cp.stderr))
 # Correct copied C1 README: this candidate no longer has the old hole size.
 (D/'README.md').write_text('''# J10 C2：仅供摆放/接口复核，相关网络未布通

PROTOTYPE / BLOCKED / NO FABRICATION。不是已完成的新版PCB。

J10保持编号孔中心及网络，改JST PH侧出；按JST官方针对玻纤镀通孔的PH建议，候选成品孔0.90mm、铜盘1.50mm（孔成品公差要求+0/−0.05mm，须板厂确认）。D30、F70、R50移背面；JP70旋转/平移，TP71移到(23,35)。正式P5R6和已交接A2未修改。

存在未布通网络及真实DRC问题，详见../reports/FINAL_PLACEMENT_ONLY_drc.json。失败的走线试验未采用，留在../rejected_routing_trials。未导出Gerber、钻孔或制造装配文件。

本候选的摆放、线束出线高度/操作空间、端子成品孔公差和背面热设计尚未全部闭合。请看../README.md，不以原生工程存在或ERC通过作为定板依据。
''')
 print('FINAL',len(report['violations']),len(report['unconnected_items']),'ERC',cp.returncode,flush=True)
if __name__=='__main__':run()
