#!/usr/bin/env python3
"""Publish hardware-only, routed P5R2 review artifacts after actual native checks.

Keeps all old PCB revisions, vendor facts, pins, mechanics and firmware intact.
This does not qualify thermals, manufacturing, procurement or physical fit.
"""
import pcbnew as k
import json,csv,copy,re,html,math,collections,sys
from datetime import datetime,timezone
from all_trace_review_P5R2 import paths,source,KINDS,H,ROOT,O,sha,xy,pt,mm
from layout_P5 import rect,box
REV='V1.2-H0.5-P5R2';OLD='V1.2-H0.5-P5R1'
def load(p):return json.loads(p.read_text())
def dump(p,j):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n')
def csvout(p,rows):
 keys=list(dict.fromkeys(key for row in rows for key in row))
 with p.open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,keys);w.writeheader();w.writerows({key:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list))else v for key,v in row.items()}for row in rows)
def update(v):
 if isinstance(v,str):
  if v==OLD:return REV
  for kind in KINDS:
   v=re.sub(r'MORI_'+kind+r'_P5(?:R1)?(?![A-Za-z0-9])','MORI_'+kind+'_P5R2',v)
  return v
 if isinstance(v,list):return [update(x)for x in v]
 if isinstance(v,dict):return {update(key):update(x)for key,x in v.items()}
 return v
notes={
 'motion':{'/BAT_ADC':'R14/C9 到主控改为一条直通竖线及一次转角，去掉 S 形绕线。','/CAM_3V3':'R9 下移0.25mm让出通道，消除上下反复0.1mm偏移；保留通道间一次0.2032mm单向过渡。继续下移R9会压到另一面 HEAD_BUS 本体投影，试验已回退。','/CAM_RX':'R9 下移0.25mm，焊盘和原走线保持真实铜面连接；网络不变。','/CAM_RX_BUF':'R9 下移0.25mm，焊盘和原走线保持真实铜面连接；网络不变。','/IMU_CS':'R13 转90度并移位；去掉绕上拉电阻的屋顶形绕路，以直通干线和垂直支线连接。','/S288_OE_REQ_N':'去掉靠 R3 的错位重叠，形成连续的主控/过孔/上拉连接。','/+5V_MOTION':'0.5mm 供电线保留，J1至U100的连续路径无串联换层过孔；峰值0.75A为设计场景。'},
 'imu':{'/MISO':'R1 移位并旋转，缩短局部折返；保留连接器到过孔的既有走廊。','/MISO_IC':'R1 转为水平，向 U1.1 外侧短接，未穿传感器中心。','/+3V3':'重新连接 C1/C2/C3 外侧供电；U1.8 保留0.2mm局部倒角，严格0.499999mm setback未满足，另列例外。','/GND':'U1.9/U1.11 两处短接地转角保留；精确0.499999mm倒角 FAIL。扩大倒角或改为斜接会破坏密脚净空/相邻分支角度。不是全部R14通过。'},
 'power':{'/CHG_N':'删除约13mm错位重叠；连接器/状态管到过孔采用一条水平通道，末端短斜段只用于固定过孔落点。','/H_SENSE':'去掉下方V形小抖动，合并为单一水平走廊；传感支路双面并行部分保留，未改变网络。','/H_GATE':'重新对齐Q30/R31外侧竖向走廊，消除小横移及其端部折返。','/W_BRAKE_GATE':'R24.2连接处转角铜宽与焊盘搭接；按中心线筛查会误列自由弯。严格0.5mm倒角试验使R24.2断开，已回退。','/W_REF':'U21.1/2同网端子和U20两支路的真实分支连接，筛查的折返点位于端子落点；不是悬空折返。','/W_SENSE':'R21.2处分向R22和过孔，两条线在同一端子汇接；不是无用支路。','/+5V_MOTION':'C63/C64输出电容支路在焊盘汇接；0.8mm负载路线保留，0.2mm反馈/测试支路不承担主负载。','/C5_VIN':'C70/C76/U70输入端供电树，宽线交汇位于电容焊盘；保留局部小引脚收口以维持输入回路。','/H_VM':'Q30多引脚宽铜汇流，C30/J9/J12负载分支与细采样支路分别检查；最宽完整J9路径仍含0.8mm段。','/W_VM':'Q10输出/J7/J8负载和细采样支路分开校核；J8最宽完整路径仍含0.8mm段，不能称全程1.5mm。','/PACK_FUSED':'2mm负载主干与R90/D90细偏置分支；两个不同宽度的重叠是电气汇接。换层载流能力未台架验证。','/BAT_MON':'2mm配电干线、0.8mm两路5V输入及细监测分支分开核对；线宽突变有分支用途。'},
 'rear':{'/VBUS_RAW':'USB的0.5mm引脚收口与主充电路径；到J2.5的0.2mm路径是检测支路，不能接充电负载。','/VBUS_FUSED':'去掉重复铜段；0.6mm主线、两次换层。1A是既有设计输入场景，温升/插座接触待实测。','/CC1':'保留开关左侧及下沿路径；尝试右侧短路会冲突VBUS/CC2或器件另一面投影，已回退。CC为配置/检测信号，不是差分数据对。','/CC2':'USB至ESD器件局部短接，再从开关右侧到J2。','/GND':'铜区连接、屏蔽壳局部实连与缝合过孔；USB1.SH保留既有R25非热焊盘例外，ESD/焊接未实测。'}}
native={};boards={};netrows=[];segrows=[];virows=[];candrows=[];bodyrows=[];placementrows=[];pinrows=[];deltas={};native_inputs={}
oldhandoff=load(H/'handoff/mechanical_P5R1.json');sources=load(O/'sources.json')
for kind in KINDS:
 name,d,p,r=paths(kind);b=k.LoadBoard(str(p));inv=load(r/'after_inventory.json');before=load(r/'before_inventory.json');delta=load(r/'delta.json');deltas[kind]=delta
 drc=load(r/'drc.json');erc=load(r/'erc.json');checks=load(r/'check_commands.json');body=load(r/'body_review_final.json');widths=load(r/'width_review.json')
 assert inv['sha256']==body['source_sha256']==delta['output_pcb_sha256']==widths['pcb_sha256']==sha(p)
 assert sha(ROOT/sources[kind]['source'])==sources[kind]['sha256']
 for log in checks:
  assert not log['returncode']
  for file,h in log['input_sha256'].items():assert sha(ROOT/file)==h,(kind,file,'stale check')
 co={'ERC':sum(len(s['violations'])for s in erc['sheets']),'DRC':len(drc['violations']),'unconnected':len(drc['unconnected_items']),'parity':len(drc['schematic_parity'])};assert not any(co.values()),co
 assert all(delta[x]for x in ['pad_net_footprint_map_identical','edge_geometry_identical','holes_connectors_and_module_poses_identical','copper_layers_unchanged'])and not delta['drc_exclusions']and not delta['inner_signal_tracks']
 assert not any(t['classification']=='FAIL_FOREIGN_NET'for t in body['body_crossing_inventory'])
 native[kind]={'board':name,**co,'status':'PASS','source_sha256':sha(p),'tool':drc['kicad_version'],'report':str((r/'drc.json').relative_to(ROOT))}
 netindex=load(r/'after_atlas_index.json')['nets'];segments={t['uuid']:t for t in inv['tracks']};candidates={c['id']:c for c in inv['candidates']}
 bodies=collections.defaultdict(list)
 for q in body['body_crossing_inventory']:
  bodyrows.append({'board':name,**q});bodies[q['track_uuid']].append(q)
 for net in netindex:
  nn=net['net'];ts=[t for t in inv['tracks']if t['net']==nn];bs=[t for t in before['tracks']if t['net']==nn]
  note=notes[kind].get(nn,'已沿逐网图核对端点、走廊、换层、分支和本体投影；原生检查及几何筛查提示另附。未作示波器/实物性能验证。')
  netrows.append({'board':name,'kind':kind,'net':nn,'segments_before':len(bs),'segments_after':len(ts),'length_before_mm':round(sum(t['length']for t in bs),4),'length_after_mm':round(sum(t['length']for t in ts),4),'widths_mm':sorted({t['width']for t in ts}),'visual_review_performed':True,'notes':note,'image_before':net['svg'].replace('/after/','/before/'),'image_after':net['svg'],'physical_status':'NOT_TESTED','strict_all_style_rules':'NOT_TESTED'})
 for t in inv['tracks']:
  segrows.append({'board':name,**t,'body_records':[{'ref':q['reference'],'classification':q['classification']}for q in bodies[t['uuid']]],'review_basis':'原生双面图＋逐网络追踪；筛查编号可复核；电气性能NOT_TESTED','net_note':notes[kind].get(t['net'],''),'native_DRC':'PASS'})
 for v in inv['vias']:virows.append({'board':name,**v,'native_DRC':'PASS','plating_and_thermal':'NOT_TESTED'})
 nativepads=[q for f in b.GetFootprints()for q in f.Pads()]
 for c in inv['candidates']:
  maxw=max(segments[u]['width']for u in c['uuids']);pos=pt(*c['xy']);landing=[]
  for q in nativepads:
   if q.GetNetname()==c['net']and q.IsOnLayer(b.GetLayerID(c['layer']))and q.GetEffectiveShape(b.GetLayerID(c['layer'])).Collide(pos,mm(maxw/2+.001)):landing.append(q.GetParentFootprint().GetReference()+'.'+q.GetNumber())
  viahit=[v['uuid']for v in inv['vias']if v['net']==c['net']and math.dist(v['xy'],c['xy'])<=v['diameter']/2+maxw/2+.001]
  explanation=notes[kind].get(c['net'],'')
  if landing or viahit:classification='焊盘/过孔落点附近的几何提示；见实铜与逐网图'
  elif c['type']=='OFFSET_ENDPOINTS':classification='同网线段中心端点偏移；实体铜已连通，端点不等于断线'
  elif c['type']=='SHORT_SEGMENT':classification='局部短线段；已连同相邻长线/分支查看，不按长度自动判违规'
  elif c['type']=='NON_45':classification='直接斜线或落点收口；角度非45已保留在清单，非全规则通过声明'
  else:classification='已按网络复核的汇接；具体原因见网络说明'
  candrows.append({'board':name,**c,'near_same_net_pads':landing,'near_same_net_vias':viahit,'disposition':classification,'net_review':explanation,'automatic_style_PASS':False})
 oldkey=source(kind)[0];board=update(copy.deepcopy(oldhandoff['boards'][oldkey]));board['pcb_sha256']=sha(p);board['native_project']=str((d/(name+'.kicad_pro')).relative_to(ROOT));board['placements']=[]
 board['bare_STEP']=oldhandoff['boards'][oldkey]['bare_STEP'];board['bare_STEP_note']='Reuses historical bare board only: Edge.Cuts and all holes unchanged. This is not a populated or mated assembly.'
 conn={x.get('ref',x.get('reference')):x for x in board['connectors']}
 comps=load(d/'connectivity.json');cc={x['ref']:x for x in comps['components']}
 for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
  ref=f.GetReference();pos=xy(f.GetPosition());angle=f.GetOrientationDegrees();side='B'if f.IsFlipped()else'F'
  row={'board':name,'reference':ref,'xy_mm':pos,'rotation_deg':angle,'side':side,'footprint':f.GetFPIDAsString(),'fab_projection_mm':rect(f),'native_body_and_pad_bounds_mm':box(f),'vendor_full_height_mm':None,'physical_tests':'NOT_TESTED'};board['placements'].append(row);placementrows.append(row)
  if ref in cc:cc[ref].update(placed_at=[*pos,angle],side=side)
  if ref not in conn:continue
  cn=conn[ref];cn.update(xy_mm=pos,rotation_deg=angle,side=side,footprint=f.GetFPIDAsString(),native_body_and_pad_bounds_mm=box(f));cn['pins']=[]
  for pad in f.Pads():
   if not pad.GetNumber()or pad.GetNumber()=='MP':continue
   pin={'revision':REV,'board':name,'reference':ref,'pin':pad.GetNumber(),'net':pad.GetNetname(),'xy_mm':xy(pad.GetPosition()),'component_side':side,'view':'Native component-side pad number; mating cable view is mirrored','status':'NOT_TESTED'};cn['pins'].append(pin);pinrows.append(pin)
 comps.update(revision=REV,layout_revision='P5R2',circuit_revision='V1.2-H0.5-P5');dump(d/'connectivity.json',comps);boards[name]=board
 (d/'README.md').write_text(f'# {name}\n\nPROTOTYPE / 实物 NOT_TESTED。P5R2逐网复查版；电路、器件型号和针脚不变。\n\n当前ERC/DRC/未连接/一致性均0，完整报告与局部例外见 ../../layout_P5R2/README.md。本目录没有制造释放。\n')
csvout(O/'all_segments_review.csv',segrows);csvout(O/'all_vias_review.csv',virows);csvout(O/'net_review.csv',netrows);csvout(O/'screening_disposition.csv',candrows);csvout(O/'placements.csv',placementrows);csvout(O/'connector_pinmap.csv',pinrows)
with (H/'layout_P5R1/assembly_parts_with_mpn.csv').open(encoding='utf-8-sig',newline='')as f:
 csvout(O/'assembly_parts_with_mpn.csv',[update(row)for row in csv.DictReader(f)])
dump(O/'harness.json',update(load(H/'layout_P5R1/harness.json')))
dump(O/'reports/body_escape_inventory.json',bodyrows);dump(O/'reports/net_review.json',netrows)
rules=ROOT.parent/'KiCad/Rules/pcb-rules.json';assert sha(rules)=='5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0';(O/'pcb-rules-source.json').write_bytes(rules.read_bytes())
summary={'revision':REV,'scope':'All four custom PCBs; per-net visual review, every segment/via inventory, transactional routing corrections, native checks and supply-width review. Circuit unchanged.','native_checks':native,'source_projects_preserved':True,'rules_source':{'path':str(rules),'sha256':sha(rules),'enabled':44,'total':47,'full_equivalence':'NOT_TESTED'},'reviewed_nets':len(netrows),'source_segments':sum(x['before']['tracks']for x in deltas.values()),'final_segments':len(segrows),'final_vias':len(virows),'deltas':deltas,'foreign_body_crossing_candidates':0,'body_escape_inventory':'reports/body_escape_inventory.json','strict_no_under_component_routing':'NOT_TESTED','R14_local_exceptions':['IMU U1.9/U1.11: two short GND free corners do not meet exact 0.499999 mm setback; geometric FAIL retained explicitly','IMU U1.8: 0.2 mm local bevel for dense LGA escape, not exact 0.499999 mm source setback','Power W_BRAKE_GATE near R24.2: copper-width pad landing; centreline-only corner screening is not a complete pad-attachment classifier'],'user_visual_acceptance':'NOT_TESTED','current_capacity_and_temperature':'NOT_TESTED','manufacturing_release':False,'mechanical_fit':'BLOCKED','physical_tests':'NOT_TESTED'}
dump(O/'reports/verification.json',summary)
mech=ROOT/'contracts/mechanical_interfaces.json';handoff={'revision':REV,'generated_utc':datetime.now(timezone.utc).isoformat(),'mechanical_revision_read':load(mech).get('revision'),'mechanical_source_sha256':sha(mech),'coordinates':oldhandoff['coordinates'],'boards':boards,'power_height_allocation_mm':oldhandoff['power_height_allocation_mm'],'change_scope':'Outlines, holes, connector and purchased-module poses unchanged. Motion R9/R13 and IMU R1 placement changed; all copper reviewed. Full mated envelope and thermal tests remain unqualified.','full_mated_fit':'BLOCKED','physical_tests':'NOT_TESTED','owned_files_not_modified':['config/geometry.json','contracts/mechanical_interfaces.json','mechanical/','firmware/']};dump(H/'handoff/mechanical_P5R2.json',handoff)
if '--publish' in sys.argv:
 cpath=ROOT/'contracts/components.json';epath=ROOT/'contracts/electrical_interfaces.json';c=load(cpath);e=load(epath);assert c['revision']in[OLD,REV]and e['revision']in[OLD,REV]
 backup=H/'revisions/before_P5R2_contracts'
 files=['contracts/components.json','contracts/electrical_interfaces.json','hardware/pinmap.csv','hardware/harness.csv','hardware/bom.csv','hardware/v1_2/bom.csv','hardware/v1_2/assembly_parts.csv']
 for file in files:
  p=ROOT/file;dest=backup/file
  if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
 # Only current hardware references change. Historical validation reports,
 # source indexes and their hashes must remain attached to their old files.
 c['revision']=REV;e['revision']=REV
 c['components']=update(c['components'])
 c['assembly_cross_reference']='hardware/v1_2/layout_P5R2/assembly_parts_with_mpn.csv'
 e['pcb_projects']=update(e['pcb_projects']);e['active_schematics']=update(e['active_schematics'])
 for kind in KINDS:
  name=paths(kind)[0];project=e['pcb_projects'][name];project['native_checks']=native[kind];project['circuit_revision']='V1.2-H0.5-P5';project['prototype_status']='PROTOTYPE_NOT_BENCH_VALIDATED'
  if 'source_sha256'in project:project['source_sha256']=native[kind]['source_sha256']
 e['hardware_schematic_revision']='V1.2-H0.5-P5';e['gpio_change']=False;e['pcb_revision_relationship']='All four boards P5R2 are routing-only corrections; circuit/PIN/GPIO unchanged from P5. See full per-net review and local exceptions.';e['mechanical_handoff']='hardware/v1_2/handoff/mechanical_P5R2.json';e['connector_pinmap']='hardware/v1_2/layout_P5R2/connector_pinmap.csv';e['layout_validation']='hardware/v1_2/layout_P5R2/reports/verification.json'
 for contract in [c,e]:
  contract['layout_P5R2_all_trace_review']=summary;contract['pcb_routing_style_review']['status']='NOT_TESTED';contract['pcb_routing_style_review']['P5R2_all_trace_review']='hardware/v1_2/layout_P5R2/reports/verification.json'
 for component in c['components']:
  if component.get('board_revision')in['P5','P5R1']:component['board_revision']='P5R2'
  elif component.get('board_revision')=='motion:P5R1; imu/power/rear:P5':component['board_revision']='motion/imu/power/rear:P5R2'
 dump(cpath,c);dump(epath,e)
 for file in files[2:]:
  p=ROOT/file
  with p.open(encoding='utf-8-sig',newline='')as f:rd=csv.DictReader(f);fields=rd.fieldnames;rows=[{key:update(value)for key,value in row.items()}for row in rd]
  with p.open('w',encoding='utf-8-sig',newline='')as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 for src,dst in [('hardware/pinmap.csv','interfaces/pinmap_'+REV+'.csv'),('hardware/harness.csv','interfaces/harness_'+REV+'.csv'),('hardware/v1_2/bom.csv','bom_'+REV+'.csv')]: (H/dst).write_bytes((ROOT/src).read_bytes())
 dump(O/'reports/publication.json',{'revision':REV,'published':True,'hardware_only':True,'manufacturing_release':False,'source_projects_preserved':True,'generated_utc':datetime.now(timezone.utc).isoformat()})
print(json.dumps({'native':native,'nets':len(netrows),'segments':len(segrows),'vias':len(virows),'publication':'--publish'in sys.argv},ensure_ascii=False))
