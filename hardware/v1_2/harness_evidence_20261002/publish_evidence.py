"""Publish a read-only engineering-evidence handoff; no CAD or contract replacement."""
from pathlib import Path
import csv
import hashlib
import json

ROOT=Path(__file__).resolve().parent
PROJECT=ROOT.parents[2]

def hash_file(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    receipt=json.loads((ROOT/'receipt_and_range_checks.json').read_text())
    assert receipt['status']=='PASS' and receipt['body_assembly_status']=='FAIL'
    assert receipt['formal_source_files_verified_unchanged']==249
    manifests=[]
    for name in ['sources_manifest.json','additional_sources_manifest.json']:
        records=json.loads((ROOT/name).read_text())
        for r in records:
            if r['status']=='PASS': assert hash_file(ROOT/'sources'/r['name'])==r['sha256']
        manifests+=records
    for file in ROOT.glob('*.csv'):
        with file.open(encoding='utf-8-sig',newline='') as f:
            rows=list(csv.DictReader(f))
        assert rows and all(None not in r and all(v is not None for v in r.values()) for r in rows),str(file)
    # Preserve exact live-page observation and its date; do not confuse min tier with one-off cost.
    page=(ROOT/'sources/lcsc_SPH002_C111515.html').read_text()
    start=page.index('"productCode":"C111515"')
    pos=page.index('"productPriceList":',start)+len('"productPriceList":')
    tiers,_=json.JSONDecoder().raw_decode(page[pos:])
    assert tiers[0]['ladder']==100 and tiers[0]['productPrice']=='0.0086'
    lcsc=next(r for r in manifests if r['name']=='lcsc_SPH002_C111515.html')
    procurement={'observation_date_utc':lcsc['accessed_utc'],'source_url':lcsc['source_url'],'source_sha256':lcsc['sha256'],
                 'part':'JST SPH-002T-P0.5S','supplier_sku':'C111515','listed_stock_at_capture':1320200,
                 'minimum_quantity':100,'multiple':100,'unit_price_at_minimum':0.0086,'currency':'USD',
                 'material_total_at_minimum':0.86,'CNY_quote':None,'shipping':None,'crimping_cost':None,
                 'wire_cost':None,'status':'BLOCKED','scope':'Supplier catalogue availability observed; not domestic CNY checkout or completed harness quotation',
                 'custom_harness_service_url':'https://lcsccable.com/services?id=wire',
                 'supplier_contacted':False,'order_placed':False,
                 'Alpha_6711_6712_cut_length_availability':'BLOCKED','approved_crimp_process':'NOT_TESTED'}
    assert '"stockNumber":1320200' in page[start:pos]
    (ROOT/'procurement_observation.json').write_text(json.dumps(procurement,ensure_ascii=False,indent=2)+'\n')
    artifacts={str(p.relative_to(PROJECT)):hash_file(p) for p in sorted(ROOT.iterdir()) if p.is_file() and p.name not in ['publication.json']}
    result={
        'revision':'V1.2-H0.5-P5R7-prearrival-A5-harness-evidence',
        'date':'2026-10-02','scope':'Evidence and received-review supplement only; no formal PCB replacement, wire selection, mechanical adoption, cut-length or manufacturing release',
        'status':'BLOCKED','source_integrity_status':'PASS',
        'formal_boards':{'motion':'P5R7','rear':'P5R7','power':'P5R6','imu':'P5R4'},
        'base_mechanical_revision':'V1.2-M1.47','base_mechanical_blend_sha256':receipt['source_blend_sha256'],
        'received_static_report_sha256':'0b788e94e7045d15d864c82ef58d46dbbbf770110b34a082d374b223f89d81c1',
        'static_scope_status':'PASS','static_scope':'H01-H04 only; 14 wires, 91 pair checks, 130 head poses; assumed terminal exits',
        'received_body_sequence_sha256':'74ed4fdb5d4db7c97b28c787cea37d1effc9819d42d883f17c5708d365bc7acc',
        'body_assembly_status':'FAIL','body_positions_checked':407,
        'known_body_assembly_conflicts':receipt['body_assembly_conflicts'],
        'tool_access':receipt['bridge_screw_tools'],
        'wire_catalogue_range_checks':receipt['wire_catalogue_checks'],
        'wire_materials_selected':False,'harness_crimp_qualification':'NOT_TESTED',
        'j10_side_entry_candidate':{'reference':'hardware/v1_2/prearrival_20261002/j10_refinement_C2/README.md','status':'BLOCKED',
                                    'actual_mated_wire_center_Z_mm':None,'release_stroke_mm':None,
                                    'note':'Public PH outline does not establish these fields; passing trial values remain assumptions. C2 placement-only has unrouted affected nets; PHC1 DRC results are not C2 results.'},
        'vendor_cable_evidence':{
            'SCS0009':{'manufacturer':'FEETECH','spec_revision':'A/0 2020-11-23','page4_type':'5264-3P','page4_length_mm':150,
                        'page4_pin_table':{'1':'GND','2':'VCC','3':'TTL'},'page8_example_pin_table':{'1':'DATA','2':'power','3':'GND'},
                        'actual_mated_view_confirmed':False,'wire_AWG':None,'wire_OD_max_mm':None,'bend_radius_mm':None,'dynamic_life':None,
                        'status':'BLOCKED','note':'Potential view/example-port distinction unresolved; do not manufacture by numbered table alone.'},
            'S288':{'manufacturer':'Unitree','supplied_cable_description':'PH2.0','manual_page3_numbered_functions':{'1':'SIGNAL','2':'VCC','3':'GND'},
                     'actual_connector_manufacturer_part':None,'wire_AWG':None,'wire_OD_max_mm':None,'bend_radius_mm':None,'dynamic_life':None,
                     'status':'BLOCKED','note':'Left/right port views mirrored; no current board pin change or voltage change authorized.'},
            'LCD35079_FFC':{'supplier':'Waveshare','supplied_spec':{'pins':18,'pitch_mm':0.5,'length_mm':200,'contacts':'same side'},
                            'actual_cable_part':None,'width_mm':None,'thickness_mm':None,'static_bend_radius_mm':None,'dynamic_life':None,
                            'status':'BLOCKED','note':'CAM and LCD are in the same pitch group. If both ends and supports move rigidly together, static routing is appropriate; do not require dynamic qualification solely because the head rotates.'}},
        'purchasing':procurement,'formal_source_files_verified_unchanged':249,
        'required_next_inputs':['PHR-8/S8B-PH-K-S actual mated wire-exit and release drawing',
                                'Exact small-quantity wire and crimp process/quote',
                                'SCS0009 numbering/view clarification and original cable specifications',
                                'S288 original cable and LCD FFC dimensional/bend specifications'],
        'main_document':str((ROOT/'README.md').relative_to(PROJECT)),
        'supplier_draft_not_sent':str((ROOT/'supplier_request_DRAFT_NOT_SENT.md').relative_to(PROJECT)),
        'artifact_hashes':artifacts}
    target=PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A5_harness.json'
    encoded=(json.dumps(result,ensure_ascii=False,indent=2)+'\n').encode()
    if target.exists():
        assert target.read_bytes()==encoded,'Refusing to rewrite a published handoff; create a new revision.'
    else:target.write_bytes(encoded)
    out={'status':'PASS','scope':'Evidence publication only','handoff':str(target.relative_to(PROJECT)),
         'sha256':hash_file(target),'native_CAD_changed':False,'mechanical_model_changed':False,
         'manufacturing_exports_created':False}
    (ROOT/'publication.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(out,ensure_ascii=False))

if __name__=='__main__':main()
