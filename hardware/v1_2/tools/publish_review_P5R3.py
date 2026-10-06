"""Gate and package the accepted external-review corrections, hardware only.
Use --publish to update current hardware references. No orders/manufacturing.
"""
from review_P5R3 import *
import csv,copy,re
from datetime import datetime,timezone
REV='V1.2-H0.5-P5R3';OLD='V1.2-H0.5-P5R2'
def load(p):return json.loads(p.read_text())
def update(v):
 if isinstance(v,str):
  if v==OLD:return REV
  for kind in KINDS:v=v.replace('MORI_'+kind+'_P5R2','MORI_'+kind+'_P5R3')
  return v
 if isinstance(v,list):return [update(x)for x in v]
 if isinstance(v,dict):return {update(key):update(x)for key,x in v.items()}
 return v
def csvout(p,rows):
 keys=list(dict.fromkeys(key for row in rows for key in row))
 with p.open('w',encoding='utf-8-sig',newline='')as f:
  w=csv.DictWriter(f,keys);w.writeheader()
  for row in rows:w.writerow({key:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list))else v for key,v in row.items()})
native={};deltas={};segments=[];vias=[];sources=load(O/'sources.json')
for kind in KINDS:
 name,d,p,r=paths(kind);drc=load(r/'drc.json');erc=load(r/'erc.json');delta=load(r/'delta.json');body=load(r/'body_review_final.json')
 assert not drc['violations']and not drc['unconnected_items']and not drc['schematic_parity']and not drc['ignored_checks']
 assert not any(s['violations']for s in erc['sheets'])
 assert sha(source(kind)[2])==sources[kind]['sha256']
 for cmd in load(r/'check_commands.json'):
  assert cmd['returncode']==0
  for file,h in cmd['input_sha256'].items():assert sha(ROOT/file)==h,('stale check',file)
 assert delta['output_pcb_sha256']==body['source_sha256']==sha(p)
 assert all(delta[x]for x in ['pad_net_footprint_map_identical','edge_geometry_identical','holes_connectors_and_module_poses_identical','copper_layers_unchanged'])
 assert not delta['changed_placements']and not delta['drc_exclusions']and not delta['inner_signal_tracks']
 assert not any(x['classification']=='FAIL_FOREIGN_NET'for x in body['body_crossing_inventory'])
 native[kind]={'board':name,'status':'PASS','ERC':0,'DRC':0,'unconnected':0,'parity':0,'source_sha256':sha(p),'tool':drc['kicad_version'],'report':str((r/'drc.json').relative_to(ROOT))};deltas[kind]=delta
 inv=load(r/'after_inventory.json');assert inv['sha256']==sha(p)
 segments +=[{'board':name,**t,'physical_status':'NOT_TESTED'}for t in inv['tracks']]
 vias +=[{'board':name,**v,'physical_status':'NOT_TESTED'}for v in inv['vias']]
 (d/'README.md').write_text(f'# {name}\n\n{REV} / PROTOTYPE / 实物 NOT_TESTED。审查修正版，原理/器件/针脚/摆位/外形不变。\n\n实际 ERC/DRC/未连接/原理图差异均0。关键改动、保留项与限制见 [P5R3审查记录](../../layout_P5R3/README.md)。没有制造释放。\n')
 data=load(d/'connectivity.json');data.update(revision=REV,layout_revision='P5R3',circuit_revision='V1.2-H0.5-P5');dump(d/'connectivity.json',data)
csvout(O/'all_segments.csv',segments);csvout(O/'all_vias.csv',vias)
rules=ROOT.parent/'KiCad/Rules/pcb-rules.json';expected='5d49d0134ca8c32acc41736591db9e839c347a40a2baa061d32c9ce64a7c25b0';assert sha(rules)==expected
(O/'pcb-rules-source.json').write_bytes(rules.read_bytes())
summary={'revision':REV,'scope':'External P5R2 review corrections; power copper, rear CC2 via entry and restored DRC checks, and all-four-board paste defaults. Not a full new component/firmware design.',
         'native_checks':native,'source_projects_preserved':True,'rules_source':{'path':str(rules),'sha256':expected,'total':47,'enabled':44,'full_equivalence':'NOT_TESTED','documented_Paste_override':'global +0.05 mm changed to 0 mm/0 percent; mask unchanged'},
         'deltas':deltas,'all_placements_unchanged':True,'schematic_topology_and_pinmap_unchanged':True,
         'interface_pairs':'reports/interface_pairs.json','copper_changes':'copper_changes.csv','parallel_via_topology':'reports/power/parallel_topology_test.json',
         'foreign_body_crossing_candidates':0,'style_limitations':'Inherited P5R2 local R14/USB shell/module-underlay exceptions remain. Not a strict all-preferences PASS.',
         'bench_tests':'NOT_TESTED','current_rating_thermal_EMC':'NOT_TESTED','manufacturing_release':False,'mechanical_fit':'BLOCKED'}
dump(O/'reports/verification.json',summary)
oldhandoff=load(H/'handoff/mechanical_P5R2.json');handoff=copy.deepcopy(oldhandoff)
handoff.update(revision=REV,generated_utc=datetime.now(timezone.utc).isoformat(),mechanical_revision_read=load(ROOT/'contracts/mechanical_interfaces.json').get('revision'),mechanical_source_sha256=sha(ROOT/'contracts/mechanical_interfaces.json'),change_scope='All outlines, holes, footprints, component positions/rotations and connector pin mappings unchanged from P5R2. Only power copper/local copper areas, rear CC2 entry/check configuration, paste defaults and power schematic dimension note changed. No mechanical fit qualification.')
handoff['boards']={}
for kind in KINDS:
 name,d,p,r=paths(kind);board=update(copy.deepcopy(oldhandoff['boards'][source(kind)[0]]));board['pcb_sha256']=sha(p);board['native_project']=str((d/(name+'.kicad_pro')).relative_to(ROOT));handoff['boards'][name]=board
dump(H/'handoff/mechanical_P5R3.json',handoff)
for file in ['placements.csv','connector_pinmap.csv','assembly_parts_with_mpn.csv']:
 with(H/'layout_P5R2'/file).open(encoding='utf-8-sig',newline='')as f:rows=[update(r)for r in csv.DictReader(f)]
 csvout(O/file,rows)
dump(O/'harness.json',update(load(H/'layout_P5R2/harness.json')))
if '--publish'in sys.argv:
 backup=H/'revisions/before_P5R3_contracts'
 files=['contracts/components.json','contracts/electrical_interfaces.json','hardware/pinmap.csv','hardware/harness.csv','hardware/bom.csv','hardware/v1_2/bom.csv','hardware/v1_2/assembly_parts.csv','hardware/README.md','hardware/v1_2/README.md']
 for file in files:
  p=ROOT/file;dest=backup/file
  if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
 cpath=ROOT/'contracts/components.json';epath=ROOT/'contracts/electrical_interfaces.json';c=load(cpath);e=load(epath)
 assert c['revision']in[OLD,REV]and e['revision']in[OLD,REV]
 c['revision']=REV;e['revision']=REV;c['components']=update(c['components']);c['assembly_cross_reference']='hardware/v1_2/layout_P5R3/assembly_parts_with_mpn.csv'
 for item in c['components']:
  if isinstance(item.get('board_revision'),str):item['board_revision']=item['board_revision'].replace('P5R2','P5R3')
 e['pcb_projects']=update(e['pcb_projects']);e['active_schematics']=update(e['active_schematics'])
 for kind in KINDS:
  name=paths(kind)[0];project=e['pcb_projects'][name];project.update(native_checks=native[kind],circuit_revision='V1.2-H0.5-P5',prototype_status='PROTOTYPE_NOT_BENCH_VALIDATED')
  if 'source_sha256'in project:project['source_sha256']=native[kind]['source_sha256']
 e.update(hardware_schematic_revision='V1.2-H0.5-P5',gpio_change=False,pcb_revision_relationship='P5R3 corrects power sense/ground/layer transitions and all-board paste defaults. Circuit, GPIO, components and mechanical interfaces unchanged from P5R2.',mechanical_handoff='hardware/v1_2/handoff/mechanical_P5R3.json',connector_pinmap='hardware/v1_2/layout_P5R3/connector_pinmap.csv',layout_validation='hardware/v1_2/layout_P5R3/reports/verification.json')
 for contract in [c,e]:
  contract['layout_P5R3_external_review']=summary;contract['pcb_routing_style_review']['status']='NOT_TESTED';contract['pcb_routing_style_review']['P5R3_external_review']='hardware/v1_2/layout_P5R3/reports/verification.json'
 dump(cpath,c);dump(epath,e)
 for file in files[2:7]:
  p=ROOT/file
  with p.open(encoding='utf-8-sig',newline='')as f:rd=csv.DictReader(f);fields=rd.fieldnames;rows=[{key:update(value)for key,value in row.items()}for row in rd]
  with p.open('w',encoding='utf-8-sig',newline='')as f:w=csv.DictWriter(f,fields);w.writeheader();w.writerows(rows)
 for src,dst in [('hardware/pinmap.csv','interfaces/pinmap_'+REV+'.csv'),('hardware/harness.csv','interfaces/harness_'+REV+'.csv'),('hardware/v1_2/bom.csv','bom_'+REV+'.csv')]: (H/dst).write_bytes((ROOT/src).read_bytes())
 dump(O/'reports/publication.json',{'revision':REV,'published':True,'hardware_only':True,'manufacturing_release':False,'source_projects_preserved':True,'utc':datetime.now(timezone.utc).isoformat()})
print('P5R3 checks PASS; published=', '--publish'in sys.argv)
