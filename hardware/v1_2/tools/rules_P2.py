"""Translate the user's KiCad/Rules v1.0 JSON, including pair priorities.

The repository is read only. Every project gets its own real .kicad_dru.
The input snapshot and per-board applicability remain with the P2 delivery.
"""
from pathlib import Path
import json, hashlib

R=Path(__file__).resolve().parents[1]
SOURCE=Path('/Users/dean/Documents/KiCad/Rules/pcb-rules.json')
COMMIT='f756532aa67112a9d437c18e8ca00ac8fba2c9b4'

def roles(kind,nets):
    vcc=['+3V3','+5V_MOTION','CAM_3V3','BAT_IN','BAT_REV','BAT_MON','W9_IN','W_PRE','W_VM','H6_IN','H_PRE','H_VM','VBUS_CHARGE']
    gnd=['GND','W_DUMP_D','H_DUMP_D']
    return dict(P24V=[],VCC=['/'+x for x in vcc if '/'+x in nets],GND=['/'+x for x in gnd if '/'+x in nets],Mark=[])

def write_rules(kind,d,name,nets):
    out=R/'layout_P2';out.mkdir(exist_ok=True)
    snapshot=out/'pcb-rules-source.json'
    if not snapshot.exists():snapshot.write_bytes(SOURCE.read_bytes())
    data=json.loads(snapshot.read_text());role=roles(kind,nets);lines=['(version 1)',
        '# Source: https://github.com/deanxizian/KiCad/tree/'+COMMIT+'/Rules',
        '# Generated from all 47 source rules; applicability and limitations: rule_mapping.json.',
        '# No 24 V rail exists in MORI. Source P24V is NOT mapped to the 3S pack.']
    def rule(label,condition,*constraints):
        lines.append('(rule '+json.dumps(label)+'\n'+('  (condition '+json.dumps(condition)+')\n' if condition else '')+''.join('  '+c+'\n' for c in constraints)+')')
    def isrole(r,obj):return '('+' || '.join(f"{obj}.NetName == '{n}'" for n in role[r])+')' if role[r] else '(0 == 1)'
    obj={'arc':"{x}.Type == 'Arc'",'track':"{x}.Type == 'Track'",'smd_pad':"{x}.Type == 'Pad' && {x}.Pad_Type == 'SMD'",
      'through_hole_pad':"{x}.Type == 'Pad' && {x}.Pad_Type == 'Through-hole'",'via':"{x}.Type == 'Via'",'polygon':"{x}.Type == 'Zone'",
      'copper_text':"({x}.Type == 'Text' || {x}.Type == 'Text Box')"}
    statuses=[]
    for rr in reversed(data['rules'][:7]):
        rid=rr['id'];scope=rr['scope']['a'];rrrole=scope.split(':')[1] if scope.startswith('network_role:') else None
        if rid in ['R02','R03','R04','R01']:continue
        cond="A.NetName != B.NetName"
        if rrrole:cond+=' && ('+isrole(rrrole,'A')+' || '+isrole(rrrole,'B')+')'
        rule(rid+' default',cond,f'(constraint clearance (min {rr["parameters"]["gap_mm"]:.8f}mm))')
        matrix={}
        for pair,gap in rr.get('clearance_overrides_mm',{}).items():
            a,b=pair.split('|')
            if a not in obj or b not in obj:continue
            f=lambda o,x:'('+obj[o].format(x=x)+')'
            paircond='('+f(a,'A')+' && '+f(b,'B')+')'
            if a!=b:paircond='('+paircond+' || ('+f(b,'A')+' && '+f(a,'B')+'))'
            matrix.setdefault(gap,[]).append(paircond)
        for gap,conditions in matrix.items():
            rule(rid+' object pairs '+str(gap),cond+' && ('+' || '.join(conditions)+')',f'(constraint clearance (min {gap:.8f}mm))')
        if rr['parameters']['ignorepadtopadclearanceinfootprint']:
            rule(rid+' original same-package pad condition',cond+" && A.Type == 'Pad' && B.Type == 'Pad' && A.Parent == B.Parent",'(constraint clearance (min 0mm))')
    rule('R01 via-pad physical any net',"(A.Type == 'Via' && B.Type == 'Pad') || (B.Type == 'Via' && A.Type == 'Pad')",'(constraint physical_clearance (min 0.1999996mm))')
    rule('R05-R07 hole to copper',None,'(constraint hole_clearance (min 0.2999994mm))')
    rule('R09 signal width',None,'(constraint track_width (min 0.1999996mm) (opt 0.1999996mm) (max 2.00000108mm))')
    power=isrole('VCC','A')+' || '+isrole('GND','A')
    rule('R08 power and return width',power,'(constraint track_width (min 0.1999996mm) (opt 0.499999mm) (max 5.00000016mm))')
    rule('R29 absolute holes',None,'(constraint hole_size (min 0.0999998mm) (max 5.00000016mm))')
    rule('R15-R16 through via geometry',"A.Type == 'Via'",'(constraint via_diameter (min 0.499999mm) (opt 0.499999mm) (max 1.00000054mm))',
      '(constraint hole_size (min 0.2499995mm) (opt 0.2499995mm) (max 0.499999mm))',"(constraint assertion \"A.Via_Type == 'Through'\")")
    rule('R23 via count',None,'(constraint via_count (max 500))')
    rule('R27 minimum track angle',"A.Type == 'Track' && B.Type == 'Track'",'(constraint track_angle (min 60))')
    rule('R26 solid polygon connection',None,'(constraint zone_connection solid)')
    rule('R25 through-hole thermals',"A.Type == 'Pad' && A.Pad_Type == 'Through-hole'",'(constraint zone_connection thermal_reliefs)',
      '(constraint thermal_relief_gap (opt 0.254mm))','(constraint thermal_spoke_width (opt 0.2999994mm))','(constraint min_resolved_spokes 4)')
    rule('R43 silk-to-silk',"A.Layer == B.Layer",'(constraint silk_clearance (min 0.0499999mm))')
    rule('R42 silk-to-exposed-pad',"A.Type == 'Pad' || B.Type == 'Pad'",'(constraint silk_clearance (min 0.00999998mm))')
    rule('R39 differential geometry',"A.inDiffPair('*')",'(constraint track_width (min 0.381mm) (opt 0.381mm) (max 0.381mm))',
      '(constraint diff_pair_gap (min 0.254mm) (opt 0.254mm) (max 0.254mm))','(constraint diff_pair_uncoupled (max 12.7mm))')
    rule('R40 hole-to-hole',None,'(constraint hole_to_hole (min 0.1499997mm))')
    rule('MORI existing copper-to-edge',None,'(constraint edge_clearance (min 0.50mm))')
    (d/(name+'.kicad_dru')).write_text('\n\n'.join(lines)+'\n')
    for rr in data['rules']:
        rid=rr['id'];s='IMPLEMENTED';note='Native constraints/settings plus P2 validation.'
        if not rr['enabled']:s='DISABLED_IN_SOURCE';note='Not enabled as a source constraint; existing independent KiCad checks retained.'
        elif rid in ['R02','R04']:s='NOT_APPLICABLE';note={'R02':'No 24 V rail.','R04':'No fiducials / Mark class.'}[rid]
        elif rid=='R39':
            s='IMPLEMENTED' if kind=='power' else 'NOT_APPLICABLE'
            note='Power: /KELVIN_P and /KELVIN_N use source differential width/gap/uncoupled limits.' if kind=='power' else 'No differential pairs on this carrier; purchased-module USB stays on that module.'
        elif rid in ['R10','R17']:s='NOT_APPLICABLE';note='Two copper layers; no inner power plane.'
        elif rid in ['R11','R12','R14','R33','R34','R35','R36','R37']:
            s='SUPPLEMENTAL_REVIEW';note='Router setting/topology not fully equivalent in KiCad DRC; review geometric evidence. R14 exact 0.5 mm setback is not guaranteed by autorouter.'
        elif rid in ['R30','R31','R45','R46']:s='SUPPLEMENTAL_REVIEW';note='No dedicated testpoint footprints; use defined connector pads in probe map. Manufacturing fixture purpose/coverage is not qualified.'
        elif rid=='R03':note='M2 courtyard radius 2.2 mm plus 0.5 mm keepout expansion, assumed assembly allowance. No imported NB-B2 screw diameter.'
        statuses.append(dict(id=rid,enabled=rr['enabled'],implementation=s,note=note))
    mapping=dict(source_url='https://github.com/deanxizian/KiCad',source_commit=COMMIT,source_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
       roles=role,POWER=role['VCC']+role['GND'],rules=statuses,limitations=['Fill/Region are not Zone aliases; these independent copper object types are absent.',
       'Source explicit zero values and same-package pad condition preserved. No per-violation DRC exclusion.',
       'Carrier does not carry USB D+/D-, DVP, QSPI or RF antenna traces.'])
    (d/'rule_mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
    return role
