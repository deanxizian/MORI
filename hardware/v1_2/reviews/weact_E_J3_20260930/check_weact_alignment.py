"""Reproducible catalogue-to-native coordinate audit. Does not edit CAD."""
import json, math, csv, hashlib
from pathlib import Path
O=Path(__file__).resolve().parent
ROOT=O.parents[3]
pins=json.loads((O/'sources/weact_pin_alignment.json').read_text())
inv=json.loads((O/'native_baseline_inventory.json').read_text())
fp=next(f for f in inv['motion']['footprints'] if f['ref']=='U100')
baseline={p['n']:p for p in fp['pads']}
source={r['solid']:r['pin_xy'] for r in pins['source_pins']}
# STEP product names identify these solids as P1..P5, not interchangeable sets.
groups={'A':162,'B':161,'C':160,'D':159,'E':32}
signal={'E1':'GND','E2':'GND','E3':'PA10','E4':'PA14/SWCLK',
        'E5':'PA9','E6':'PA13/SWDIO','E7':'NRST','E8':'3V3'}
rows=[]
for name,p in baseline.items():
    if name[0] not in groups:continue
    old=p['xy']; new=[old[0]+(2.54 if name.startswith('E') else 0),old[1]]
    target=[new[0]-35,-26.5-new[1]]
    group=source[groups[name[0]]]
    corrected=[[x,-88-y] for x,y in group]
    near=min(corrected,key=lambda q:math.dist(q,target))
    i=corrected.index(near); flipped=group[i]
    rows.append({'pin':name,'vendor_connector':'P'+str('ABCDE'.index(name[0])+1),
                 'vendor_pin':int(name[1:]),'signal':signal.get(name),
                 'carrier_net':p['net'],'old_native_xy_mm':old,'correct_native_xy_mm':new,
                 'world_xy_mm':target,'STEP_correct_pose_pin_xy_mm':near,
                 'document_vs_STEP_error_mm':math.dist(near,target),
                 'old_flipped_pose_xy_mm':flipped,
                 'flipped_pose_error_mm':math.dist(flipped,target)})
rows.sort(key=lambda r:(r['pin'][0],int(r['pin'][1:])))
assert len(rows)==68
assert max(r['document_vs_STEP_error_mm'] for r in rows)<.005
result={'date':'2026-09-30','status':'PASS','status_scope':'Documented pin positions with corrected component-up orientation, not assembly or manufacturing qualification',
 'official_STEP_source_sha256':hashlib.sha256((ROOT/'hardware/v1_2/sources/weact_f4/WeAct-STM32F4_64PIN-CoreBoard_V11 3D.step').read_bytes()).hexdigest(),
 'source_group_identification':{'A':'P1, solid 162','B':'P2, solid 161','C':'P3, solid 160','D':'P4, solid 159','E':'P5, solid 32'},
 'coordinate_basis':'Official Board Shape component-side view, P1/P2/P3/P4/P5 labels and dimensioned 2.54 mm pitch; cross-check named STEP product placements. XY positions quantized to dimensioned nominal values, not rounded tessellation used as dimensions.',
 'component_up_R_STEP_to_world':[[0,-1,0],[1,0,0],[0,0,1]],
 'component_up_translation_xy_mm':[61.016,-160.078],
 'component_down_candidate_R_STEP_to_world':[[0,-1,0],[-1,0,0],[0,0,-1]],
 'component_down_candidate_translation_xy_mm':[61.016,72.078],
 'component_down_example':'P1.1 (VB) falls into carrier B2 (GND) under the old flipped mechanical candidate; hole-set overlap does not establish pin compatibility.',
 'required_native_E_change_mm':[2.54,0],
 'A_D_pad_positions_and_numbers_unchanged':True,
 'E_nrst_network_unchanged':True,
 'E_pin_mapping':signal,
 'maximum_nominal_to_STEP_residual_mm':max(r['document_vs_STEP_error_mm'] for r in rows),
 'rows':rows}
(O/'weact_alignment_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
with (O/'weact_68_pin_alignment.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
print('68 pins checked; maximum STEP/nominal residual mm:',result['maximum_nominal_to_STEP_residual_mm'])
print('E correction: native (+2.54,0); A-D unchanged. Component-up orientation REQUIRED.')
