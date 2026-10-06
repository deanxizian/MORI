"""Reproduce range checks and the scoped handoff. No CAD, BOM or pinmap writes."""
from datetime import datetime, timezone
from hashlib import sha256
from html import unescape
from pathlib import Path
import csv
import json
import re
import sys

BASE = Path(__file__).resolve().parent
ROOT = BASE.parents[2]
def read(name): return json.loads((BASE / name).read_text())
def sha(path): return sha256(path.read_bytes()).hexdigest()
def write(name, obj):
    path = BASE / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + '\n')
def csv_write(name, rows):
    with (BASE / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

formal = read('inputs/formal_mechanical_P5R7.json')
j5 = next(x for x in formal['boards']['MORI_motion_P5R7']['connectors'] if x['ref'] == 'J5')
assert (j5['mpn'], j5['mating'], j5['contact']) == ('B4B-PH-K-S(LF)(SN)', 'PHR-4', 'SPH-002T-P0.5S')
assert [p['net'] for p in j5['pins']] == ['/CAM_RX', '/CAM_TX', '/CAM_3V3', '/GND']
a8 = read('inputs/hardware_A8_evidence.json')['h06_no_splice_study']
assert a8['wire_reference']['base_mpn'] == '2841/7'
assert a8['wire_reference']['orderable_suffix'] is None
assert a8['status'] == 'BLOCKED'

alpha = unescape(re.sub('<[^>]+>', ' ', (BASE / 'sources/Alpha_2841_7.html').read_text()))
alpha = re.sub(r'\s+', ' ', alpha)
for needle in ('30 (7/38) AWG Silver Plated Copper', '0.024+/- 0.002', '10X Cable Diameter', '0.88 Lbs, Maximum'):
    assert needle in alpha, needle
excerpt = alpha[alpha.index('Construction Diameters'):alpha.index('Applicable Specifications', alpha.index('Construction Diameters'))]
write('results/alpha_fields.json', {'source':'sources/Alpha_2841_7.html','sha256':sha(BASE/'sources/Alpha_2841_7.html'),
    'base_mpn':'2841/7','awg':30,'strands':7,'strand_awg':38,'conductor':'Silver Plated Copper',
    'nominal_stranded_bundle_diameter_mm':round(0.012*25.4,4),
    'bundle_diameter_is_metal_area':False,'actual_metal_area_mm2':None,
    'insulation':'PTFE','od_mm':[round((.024-.002)*25.4,4),round((.024+.002)*25.4,4)],
    'construction_excerpt':excerpt,'exact_order_suffix':None,'approved_combination':False})

od = [round((.024-.002)*25.4,4),round((.024+.002)*25.4,4)]
terms = [
    {'mpn':'SPH-002T-P0.5S','awg_min':24,'awg_max':30,'area_mm2':[.05,.22],'od_mm':[.8,1.5],'source':'sources/JST_PH.pdf p2','role':'FORMAL_HANDOFF_VALUE'},
    {'mpn':'SPH-004T-P0.5S','awg_min':28,'awg_max':32,'area_mm2':[.032,.08],'od_mm':[.5,.9],'source':'sources/JST_PH.pdf p2','role':'RECEIVED_CONDITIONAL_RESEARCH_CANDIDATE'},
    {'mpn':'SSH-003T-P0.2-H','awg_min':28,'awg_max':32,'area_mm2':[.032,.081],'od_mm':[.4,.8],'source':'sources/JST_SH.pdf p1-p2','role':'CAM_END_CONDITIONAL_CANDIDATE_NOT_ACTUAL_HEADER_IDENTIFICATION'},
]
rows=[]
for t in terms:
    ag=t['awg_min']<=30<=t['awg_max']
    o=t['od_mm'][0]<=od[0] and od[1]<=t['od_mm'][1]
    rows.append({'terminal':t['mpn'],'record_role':t['role'],'wire':'Alpha 2841/7 research reference',
        'wire_awg':30,'wire_OD_min_mm':od[0],'wire_OD_max_mm':od[1],
        'terminal_OD_min_mm':t['od_mm'][0],'terminal_OD_max_mm':t['od_mm'][1],
        'AWG_screen':'PASS' if ag else 'FAIL','full_OD_range_screen':'PASS' if o else 'FAIL',
        'metal_area_and_material_approval':'BLOCKED','actual_crimp':'NOT_TESTED',
        'scope':'Catalogue AWG and insulation OD only','source':t['source']})
csv_write('compatibility.csv', rows)
assert [r['full_OD_range_screen'] for r in rows] == ['FAIL','PASS','PASS']

lookup=read('sources/JST_tooling_SPH-004T-P0.5S_20261003.json')
ix=next(i for i in range(1,10) if lookup.get('awg'+str(i))=='30')
current_reference = {k:lookup[k+str(ix)] for k in ['strip_length','crimp_height','tensile_spec']}
assert current_reference == {'strip_length':'1.9~2.5','crimp_height':'0.50~0.55','tensile_spec':'5.00'}
old_rows=read('inputs/hardware_process_reference_values.json')['reference_rows']
old=next(r for r in old_rows if r['series_as_printed']=='SPH-004-P0.5S' and r['awg']==30)
write('process_sources.json', {
    'status':'BLOCKED','meaning':'Reference transcription only; no approved Alpha 2841/7 process',
    'historical':{'date':'2001-01-29','doc':'H4009/017-00','source':'sources/JST_SPH004_crimp_2001.pdf','row':old},
    'query':{'captured':'2026-10-03','host':'test-jst.jst.com','source':'sources/JST_tooling_SPH-004T-P0.5S_20261003.json',
             'process_revision':None,'for_exact_wire':None,'units':{'strip_length':'mm','crimp_height':'mm','tensile_spec':'N'},'awg30':current_reference,
             'applicator':lookup['sap_scp'],'industry_standard':lookup['is_scp'],'hand_tool':lookup['yrs_series']},
    'catalogue_tooling':{'source':'sources/JST_PH.pdf p2','machine':'AP-K2N','applicator':'MKS-L-10','dies':'APLMK SPH004-05S'},
    'combination_approved_dimensions':{'wire_crimp_height_mm':None,'wire_crimp_width_mm':None,'insulation_crimp_height_mm':None,'insulation_crimp_width_mm':None,'strip_length_mm':None},
    'approved_pull_limit_N':None,'approved_contact_retention_N':None,'approved_assembly_pull_N':None,
    'do_not_merge':'Old table, test-host query and tooling categories remain separate; no mixed acceptance specification.',
})

gaps=[
 ('G01','Exact wire ordering code, colours/marking and lot','Alpha 2841/7 base model only','Supplier wire document and traceable lot; no existing approved colour/package suffix'),
 ('G02','Metal cross section/tolerances, silver plating and PTFE compatibility','30 AWG 7/38 silver-plated copper; stranded bundle nominal 0.3048 mm','Actual wire cross section and JST/qualified supplier process approval; bundle diameter is not metal area'),
 ('G03','Formal contact substitution decision','Formal J5 remains SPH-002; SPH-004 received as research candidate','Hardware versioned approval after combination evidence; no substitution made here'),
 ('G04','Crimp tooling and current process revision','Catalogue AP-K2N / MKS-L-10 / APLMK SPH004-05S; test-host lookup retained separately','Actual press/applicator/dies, calibration, approved process sheet'),
 ('G05','Strip length and both barrel height/width tolerances','Historical and test-host reference values only','Approved combination dimensions, measurement locations and sampling'),
 ('G06','Maximum finished contact length/width/thickness','Generic uncrimped contact callouts 5.7 / 2.08 / 1.5 mm only','Finished-wire drawing including lance, bellmouth, cut-off tab, burr, protruding conductor, twist/bend tolerances'),
 ('G07','Lance protrusion/direction and housing retention','Lance illustrated; no accepted numeric envelope or retention force','Exact contact drawing/revision and insertion/retention specification'),
 ('G08','Cut-off tab, burr and bellmouth limits','General visual inspection required; no PH-specific numeric maxima retrieved','Specific handling manual and inspection method; do not flatten or trim lance to pass'),
 ('G09','Temporary protection and maximum protected envelope','No selected protector or validated threading method','Non-damaging removable protection design, maximum width/height/length and removal access; include in mechanical sweep'),
 ('G10','First-article crimp qualification','No physical tests; 5 N is source-table value only','Cross sections, pull-test method/speed/fixture/sample acceptance, resistance and housing retention records'),
 ('G11','CAM physical mating interface','Existing electrical 1-to-1 map retained; actual header full MPN/mating face unresolved','Exact board socket/housing/latch orientation and physical continuity confirmation'),
 ('G12','BODY-side unhoused delivery and full feed sequence','New off-robot sequence is a mechanical candidate','Approve delivery end, label all four leads, number cavities from verified view; validate full protected feed, insertion and strain relief'),
 ('G13','Cut lengths, end datums and flex endurance','No manufacturing lengths or dynamic lifetime qualification','Mechanical length/branch datums, validated slack/bend/anchoring and cycle test specification'),
]
csv_write('missing_inputs.csv',[{'id':i,'field':f,'known':k,'needed':n,'status':'BLOCKED'} for i,f,k,n in gaps])

gate=read('inputs/PH_terminal_gate_review.json')
handoff={
 'schema_version':'1.0','revision':'CAM-PH-RECON-R1','date_local':'2026-10-06','owner':'hardware',
 'evidence_review':'PASS','full_combination_approval':'BLOCKED','manufacturing_release':'BLOCKED','physical_tests':'NOT_TESTED',
 'formal_changes':False,'supplier_contacted':False,'orders':False,'messages_to_other_threads':False,
 'formal_source':{'path':'hardware/v1_2/handoff/mechanical_P5R7.json','sha256':sha(BASE/'inputs/formal_mechanical_P5R7.json'),'board':'MORI_motion_P5R7','reference':'J5','header':j5['mpn'],'housing':j5['mating'],'contact':j5['contact'],'unchanged':True},
 'pinmap':{'motion_J5_to_CAM_J11':['1->1','2->2','3->3','4->4'],'motion_nets':[p['net'] for p in j5['pins']],'CAM_pin3':'Local 3V3 level reference, not main CAM power','changed':False,'source':'inputs/head_interface_pinmap_revA.csv'},
 'received_candidate':{'wire_base':'Alpha 2841/7','order_suffix':None,'awg':30,'stranding':'7/38 AWG','conductor':'Silver Plated Copper','insulation':'PTFE','full_OD_range_mm':od,'OD0p6604_meaning':'Upper bound of the candidate insulation OD, not nominal diameter and not manufacturing selection','actual_metal_area_mm2':None,'body_contact':'SPH-004T-P0.5S','body_housing':'PHR-4','CAM_contact_candidate':'SSH-003T-P0.2-H','CAM_housing_candidate':'SHR-04V-S','actual_CAM_header_MPN':None,'research_received':True,'formally_selected':False,'sources':['inputs/hardware_A8_README.md','inputs/hardware_A8_evidence.json','inputs/hardware_process_comparison_README.md']},
 'screens':rows,
 'catalogue_common_OD_PH004_SH_mm':[.5,.8],
 'formal_PH002_OD_shortfall_even_at_candidate_max_mm':round(.8-od[1],4),
 'JST_default_conductor':'Tin-plated annealed stranded copper; other constructions require compatibility checking; silver-plated wire not declared categorically impossible',
 'bare_contact_envelope':{'exact_finished_length_max_mm':None,'exact_finished_width_max_mm':None,'exact_finished_thickness_max_mm':None,'lance_protrusion_max_mm':None,'burr_max_mm':None,'cutoff_tab_max_mm':None,'bellmouth_max_mm':None,'bend_twist_max_deg':None,
   'generic_catalogue_callouts_mm':{'length':5.7,'transverse_height':2.08,'transverse_width':1.5},'generic_is_uncrimped':True,'generic_is_finished_bounding_box':False,'generic_tolerances_mm':None,
   'mechanical_screen_oriented_xyz_mm':gate['terminal_drawing']['nominal_oriented_xyz_mm'],'mechanical_screen_padding_mm':gate['clearance_padding_mm'],'screen_status':gate['status'],'screen_scope':gate['scope'],'hardware_accepts_screen_as_qualified_fit':False},
 'detailed_document_access':{'SPH004_drawing':'BLOCKED - named official drawing exists behind identity/email request form','SPH002_drawing':'BLOCKED - same gate','PHR4_drawing':'BLOCKED - same gate','PH_manual_names':['CHM-1-105.pdf','CHM-1-2201.pdf'],'manual_contents_obtained':False,'form_submitted':False},
 'assembly_candidate':{'name':'Off-robot CAM/Pitch_Cradle preassembly, BODY PH contacts left outside housing until neck/guide feed','candidate_only':True,'end_left_unhoused':'BODY / motion J5 / PHR-4','supersedes_previous_SH_free_end_plan':False,'full_feed':'NOT_TESTED','protected_terminal_envelope_mm':None,'draw_or_purchase_release':False},
 'guardrails':['Keep assembly de-energized; preinstalled CAM end does not permit live bare BODY contacts.',
    'Do not use contacts or their lances as pull hooks, flatten lances, trim metal or deform contact boxes to fit a gate.',
    'Temporary contact protection must avoid contact-surface contamination, be removable and have its own measured/documented envelope in the route check.',
    'Do not use 5 N source tensile value or the wire maximum pull tension as the assembly pulling force.',
    'Mark each free conductor by the unchanged logical circuit; final cavity/mating-view instructions require actual connector confirmation.',
    'Use correctly mating test fixtures, not oversized meter probes in female contacts; inspect after feeding and verify retention/continuity/shorts before power.',
    'Do not implement on main geometry or substitute formal contact without an explicit approved handoff.'],
 'missing_inputs':'missing_inputs.csv','process_reference':'process_sources.json',
 'mechanical_main':{'reported_revision':'M1.49 C5 + K1','new_guides_and_clamps_adopted':False,'main_changed':False,'full_model_revalidated':False},
}
write('handoff.json',handoff)

baseline=read('protected_baseline.json')
changed=[p for p,h in baseline['files'].items() if not (ROOT/p).exists() or sha(ROOT/p)!=h]
write('results/preservation.json',{'status':'PASS' if not changed else 'FAIL','checked_files':len(baseline['files']),'changed':changed,'prior_manifest_mismatches_at_start':baseline['prior_manifest_mismatches'],'native_ERC_DRC':'NOT_APPLICABLE - no board or schematic changes; no new run claimed'})
assert not changed, changed
write('results/calculations.json',{'status':'PASS','scope':'Range and unit checks only','wire_OD_mm':od,'PH002_shortfall_mm':round(.8-od[1],4),'common_PH004_SH_OD_mm':[.5,.8],'AWG_OD_screens':rows,'finished_dimensions':'BLOCKED','crimp_test':'NOT_TESTED'})
print(json.dumps({'evidence':'PASS','formal_contact_unchanged':j5['contact'],'protected_files':len(baseline['files']),'wire_OD_mm':od,'compatibility':[r['full_OD_range_screen'] for r in rows],'manufacturing':'BLOCKED'},ensure_ascii=False))
