"""Read-only release-document consistency checks, not physical qualification."""
from pathlib import Path
import json,csv,hashlib,collections,re
H=Path(__file__).resolve().parents[1];ROOT=H.parents[1];O=H/'layout_P4';REV='V1.2-H0.4-P4'
load=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
checks=[]
def check(name,condition,detail=None):
 checks.append(dict(check=name,status='PASS' if condition else 'FAIL',detail=detail))
v=load(O/'reports/verification.json');body=load(O/'body_route_review/review.json');e=load(ROOT/'contracts/electrical_interfaces.json');c=load(ROOT/'contracts/components.json')
for kind in ['motion','imu','power','rear']:
 name=f'MORI_{kind}_P4';d=H/'kicad'/name;r=O/'reports'/name;p=d/(name+'.kicad_pcb')
 q=v['native_checks'][kind]
 check(kind+'_native_counts',all(q[x]==0 for x in ['ERC','DRC','unconnected','parity']) and not q['stale_inputs'])
 hashes=load(r/'check_commands.json')
 check(kind+'_current_checked_inputs',all((ROOT/f).exists() and sha(ROOT/f)==h for cmd in hashes for f,h in cmd['input_sha256'].items()))
 check(kind+'_body_review_hash',body['summary'][kind]['pcb_sha256']==sha(p))
 check(kind+'_exports_hash',all(load(r/f)['source_pcb_sha256']==sha(p) for f in ['exports.json','track_review_exports.json']))
 check(kind+'_no_native_exclusions',not load(d/(name+'.kicad_pro'))['board']['design_settings'].get('drc_exclusions',[]))
 check(kind+'_layer_metadata',load(d/'connectivity.json')['layers']==e['pcb_projects'][name]['layers'])
for row in load(O/'reports/schematic_exports.json'):
 check('schematic_pdf_'+Path(row['argv'][-1]).stem,sha(Path(row['argv'][-1]))==row['source_sha256'] and row['exit_code']==0)
check('P3R1_preserved',not v['P3R1_changed_files'])
check('current_revisions',c['revision']==e['revision']==REV)
old=load(H/'revisions/before_P4_contracts/electrical_interfaces.json')
def gp(rows):return sorted(tuple(str(r.get(k,'')) for k in ['domain','net','mcu_pin','peripheral','direction']) for r in rows)
check('GPIO_and_peripheral_assignments_unchanged',gp(old['pinmap'])==gp(e['pinmap']))
check('no_old_board_GH_SH_purchase_items',not any('GHS-TBT' in p['full_model'] or 'BM04B-SRSS' in p['full_model'] for p in c['components'] if p['quantity']>0))
check('no_fabrication_outputs',not any(p.suffix.lower() in ['.gbr','.drl','.gbrjob'] for kind in ['motion','imu','power','rear'] for p in (H/'kicad'/f'MORI_{kind}_P4').rglob('*')))
check('root_BOM_and_harness_current',sha(ROOT/'hardware/bom.csv')==sha(H/'bom.csv') and sha(ROOT/'hardware/harness.csv')==sha(H/'interfaces'/f'harness_{REV}.csv'))
parts=list(csv.DictReader((O/'assembly_parts_with_mpn.csv').open(encoding='utf-8-sig')))
counts=collections.Counter(a['main_bom_id'] for a in parts if float(a.get('quantity') or 0)>0)
by={r['id']:r for r in c['components']}
check('assembly_quantity_to_BOM',all(by[id]['quantity']==n for id,n in counts.items()),dict(counts))
check('rear_seat_2D_review',body['rear_seats']['status']=='PASS')
check('load_path_audit_current',load(O/'reports/MORI_power_P4/load_path_audit.json')['pcb_sha256']==sha(H/'kicad/MORI_power_P4/MORI_power_P4.kicad_pcb') and load(O/'reports/MORI_power_P4/load_path_audit.json')['status']=='PASS')
check('mechanical_read_snapshot_current',load(H/'handoff/mechanical_P4.json')['mechanical_sha256']==sha(ROOT/'contracts/mechanical_interfaces.json'))
gate=load(O/'reports/budget_gate.json');req=[r for r in c['components'] if r['quantity']>0]
check('budget_unknowns_not_zeroed',gate['required_lines']==len(req) and gate['unknown_price_ids']==[r['id'] for r in req if r.get('unit_price_cny') is None] and gate['full_landed_total_cny'] is None)
check('not_claiming_manufacturing_or_physical_pass',not c['procurement_release'] and not c['manufacturing_release'] and e['physical_tests']=='NOT_TESTED' and not e['manufacturing_outputs_allowed'])
check('routing_rejection_not_overridden',c['pcb_routing_style_review']['status']=='FAIL' and e['pcb_routing_style_review']['status']=='FAIL')
report=dict(revision=REV,scope='Engineering file consistency only; a PASS here is not layout acceptance.',status='PASS' if all(r['status']=='PASS' for r in checks) else 'FAIL',checks=checks,layout_acceptance='FAIL',routing_requirements='FAIL',physical_tests='NOT_TESTED',source_R14='FAIL',mechanical_fit='BLOCKED',charging_and_procurement='BLOCKED')
(O/'reports/delivery_consistency.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(report['status'],len(checks),'consistency checks')
for row in checks:
 if row['status']=='FAIL':print(row)
raise SystemExit(0 if report['status']=='PASS' else 1)
