"""Publish P5 layout metadata without reselecting parts or changing firmware."""
import json,csv,copy,hashlib
from pathlib import Path
H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P5';REV='V1.2-H0.5-P5';BAK=H/'revisions/before_P5_contracts';BAK.mkdir(parents=True,exist_ok=True)
load=lambda p:json.loads(p.read_text())
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def csvout(p,rows):
 keys=list(dict.fromkeys(k for row in rows for k in row))
 with p.open('w',newline='',encoding='utf-8-sig')as f:
  w=csv.DictWriter(f,keys);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False)if isinstance(v,(dict,list))else v for k,v in row.items()}for row in rows)
def rename(v):
 if isinstance(v,str):
  for kind in ['motion','imu','power','rear']:v=v.replace('MORI_'+kind+'_P4','MORI_'+kind+'_P5')
  return v
 if isinstance(v,list):return[rename(x)for x in v]
 if isinstance(v,dict):return{k:rename(x)for k,x in v.items()}
 return v
v=load(O/'reports/verification.json');assert all(x['status']=='PASS'for x in v['native_checks'].values())
for filename in ['components.json','electrical_interfaces.json']:
 source=ROOT/'contracts'/filename
 if not(BAK/filename).exists():(BAK/filename).write_bytes(source.read_bytes())
c=load(ROOT/'contracts/components.json');e=load(ROOT/'contracts/electrical_interfaces.json')
oldpins=copy.deepcopy(e['pinmap']);mechhash=hashlib.sha256((ROOT/'contracts/mechanical_interfaces.json').read_bytes()).hexdigest()
style=dict(revision='P5',status='NOT_TESTED',native_rule_check='PASS',foreign_body_track_screen='PASS',foreign_body_track_candidates=0,inner_signal_tracks=0,visual_review='Completed native top/bottom view review, corridor simplification and documented local exceptions; user visual acceptance pending',full_source_rule_equivalence='NOT_TESTED',exceptions='hardware/v1_2/layout_P5/reports/body_escape_exceptions.json',report='hardware/v1_2/layout_P5/routing_acceptance.md',physical_tests='NOT_TESTED')
e.setdefault('historical_pcb_projects',{}).update({k:v for k,v in e['pcb_projects'].items()if not k.endswith('_P5')});e['pcb_projects']={};handoff=load(H/'handoff/mechanical_P5.json')
for kind in ['motion','imu','power','rear']:
 name='MORI_'+kind+'_P5';b=handoff['boards'][name]
 e['pcb_projects'][name]=dict(path='hardware/v1_2/kicad/'+name,dimensions_mm=b['outline_mm'],board_thickness_mm=1.6,layers=b['copper_layers'],nominal_copper_um=b['nominal_copper_um'],status='PROTOTYPE',native_checks=v['native_checks'][kind],fabrication_release=False,physical_tests='NOT_TESTED')
e.update(revision=REV,status='PROTOTYPE_ROUTED_UNVALIDATED',hardware_schematic_revision=REV,gpio_change=False,engineering_review='hardware/v1_2/layout_P5/README.md',mechanical_handoff='hardware/v1_2/handoff/mechanical_P5.json',layout_validation='hardware/v1_2/layout_P5/reports/verification.json',schematic_validation='hardware/v1_2/layout_P5/reports/verification.json',pcb_routing_style_review=style,connector_pinmap='hardware/v1_2/layout_P5/connector_pinmap.csv',pcb_revision_relationship=dict(existing='P5',synchronized=True,reason='Zero inherited routing copper; new placement and route. Circuit/pin maps unchanged. Power ground stack now4 layers. P4 preserved.'))
e['active_schematics']={k:f'hardware/v1_2/kicad/MORI_{k}_P5/MORI_{k}_P5.kicad_sch'for k in ['motion','imu','power','rear']}
e['pinmap']=rename(e['pinmap']);e['harness']=rename(e['harness'])
for row in e['pinmap']+e['harness']:row['revision']=REV
for key in ['charging','route']:e[key]=rename(e[key])
e['charging']['rear_pinmap']='hardware/v1_2/layout_P5/connector_pinmap.csv'
c.update(revision=REV,date='2026-09-23',status='PROTOTYPE_ROUTED_UNVALIDATED',pcb_routing_style_review=style,engineering_revision_note='P5 complete new placement/routing; P4 parts and nets retained. Power4-layer GND stack. Full native checks0; procurement, physical tests and complete source-rule equivalence are not released.',assembly_cross_reference='hardware/v1_2/layout_P5/assembly_parts_with_mpn.csv')
for row in c['components']:
 for key in ['schematic_references','purpose','full_model']:
  if key in row:row[key]=rename(row[key])
 if row.get('board_revision')=='P4':row['board_revision']='P5'
 if row['id']=='carrier_pcb':
  row.update(full_model='MORI_motion_P5 + MORI_imu_P5 + MORI_power_P5 + MORI_rear_P5',board_revision='P5',specification='motion70x35 four-layer; power80x55 four-layer70/35/35/70um nominal; IMU20x16 and rear24x25 two-layer; all1.6mm; supplier stack-up and quote pending')
  row['notes']='P5原型四板。电源由2层升级4层以保证公共地回流；旧打样额度不是新叠层报价。完整插合尺寸与物理验证仍未完成。'
c['layout_cross_task_open_items']=[dict(item='speaker_selection',status='BLOCKED',reason='Mechanical M1.20/M1.21 records Fusheng FS4545DB0450-H25-R01; existing hardware acoustic BOM has not been synchronized or repriced in this layout-only task. No speaker geometry or amplifier qualification is asserted here.')]
def gpio(rows):return sorted(tuple(str(r.get(x,''))for x in ['domain','net','mcu_pin','peripheral','direction'])for r in rows)
assert gpio(oldpins)==gpio(e['pinmap']);assert mechhash==hashlib.sha256((ROOT/'contracts/mechanical_interfaces.json').read_bytes()).hexdigest()
dump(ROOT/'contracts/components.json',c);dump(ROOT/'contracts/electrical_interfaces.json',e)
csvout(ROOT/'hardware/pinmap.csv',e['pinmap']);csvout(H/'interfaces'/('pinmap_'+REV+'.csv'),e['pinmap'])
csvout(ROOT/'hardware/harness.csv',e['harness']);csvout(H/'interfaces'/('harness_'+REV+'.csv'),e['harness']);dump(O/'harness.json',e['harness'])
old=list(csv.DictReader((H/'layout_P4/assembly_parts_with_mpn.csv').open(encoding='utf-8-sig')));actual={}
for kind in ['motion','imu','power','rear']:
 for row in load(H/'kicad'/f'MORI_{kind}_P5/connectivity.json')['components']:actual[f'MORI_{kind}_P5',row['ref']]=row
for row in old:
 row['board']=rename(row['board']);row['footprint']=actual[row['board'],row['ref']]['footprint']
csvout(O/'assembly_parts_with_mpn.csv',old)
csvout(H/'assembly_parts.csv',[dict(revision=REV,**r)for r in old])
rows=[]
for row in c['components']:
 q=dict(revision=REV,**row);q['subtotal_cny']=None if row.get('unit_price_cny')is None else row['unit_price_cny']*row['quantity'];q['price_status']='NOT_APPLICABLE'if row['quantity']==0 else'UNCONFIRMED'if row.get('unit_price_cny')is None else'PRIOR_RECORDED_QUOTE_RECHECK_REQUIRED';rows.append(q)
for p in [H/'bom.csv',H/f'bom_{REV}.csv',ROOT/'hardware/bom.csv']:csvout(p,rows)
dump(O/'reports/contract_publication.json',dict(revision=REV,MCU_pin_assignments_changed=False,mechanical_owned_files_modified=False,parts_reselected=False,layout_only=True,price_or_stock_reverified=False,new_power_stack_quote='BLOCKED',physical_tests='NOT_TESTED'))
print('P5 contracts/pinmap/harness published; GPIO unchanged; quotes unconfirmed')
