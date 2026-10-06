#!/usr/bin/env python3
"""Reproducible catalogue fit / wire loss screening. No ampacity certification."""
import csv, json, math, sys, hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
def dump(name,obj):
    p=HERE/'results'/name; p.parent.mkdir(exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def table(name,rows):
    with (HERE/'results'/name).open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def within(inner,outer): return outer[0] <= inner[0] and inner[1] <= outer[1]
def main():
    facts=json.loads((HERE/'facts.json').read_text())
    wires={w['id']:w for w in facts['wires']}; terms={t['model']:t for t in facts['terminals']}
    pairs=[('Alpha2622','SXH-001T-P0.6'),('Alpha2622','SXH-001T-P0.6N'),
           ('Alpha6713','SXH-001T-P0.6'),('Alpha6713','SXH-001T-P0.6N'),
           ('Alpha2626','SSHL-002T-P0.2'),('Alpha2622','SSHL-002T-P0.2')]
    fit=[]
    for wi,ti in pairs:
        w,t=wires[wi],terms[ti]; a=t['awg_range'][0]<=w['awg']<=t['awg_range'][1]; o=within(w['od_mm'],t['od_mm'])
        fit.append({'wire':wi,'terminal':ti,'AWG_label_screen':'PASS' if a else 'FAIL',
                    'whole_OD_tolerance_screen':'PASS' if o else 'FAIL',
                    'catalogue_two_field_screen':'PASS' if a and o else 'FAIL',
                    'metal_area_and_plating_qualification':'BLOCKED','actual_crimp_process':'NOT_TESTED',
                    'release':'BLOCKED'})
    bend=[]
    for w in wires.values():
        od=w.get('od_mm'); mult=w.get('bend_multiple_catalogue')
        rad=(mult+0.5)*od[1] if od and mult else None
        bend.append({'wire':w['id'],'max_OD_mm':od[1] if od else None,
                     'catalogue_multiple':mult,'conservative_centreline_radius_mm':round(rad,4) if rad else None,
                     'R6p5_screen':('PASS' if 6.5>=rad else 'FAIL') if rad else 'BLOCKED',
                     'dynamic_life':'NOT_TESTED',
                     'note':'MORI assumes catalogue radius could be inner radius and adds wire radius; not a manufacturer definition of bend datum.'})
    loss=[]
    for wid in ('Alpha2622','Alpha6713'):
        w=wires[wid];r20=w['dcr_ohm_per_1000ft_nominal_20C']/304.8
        for length in facts['model']['one_way_length_scenarios_m']:
            for load in facts['loads']:
                i=load['current_A'];rw=2*length*r20
                loss.append({'wire':wid,'load_case':load['id'],'one_way_length_m':length,'loop_length_m':2*length,
                   'current_A':i,'loop_R_nominal_20C_ohm':round(rw,8),
                   'wire_drop_nominal_V':round(i*rw,6),'wire_loss_nominal_W':round(i*i*rw,6),
                   'wire_drop_DCR_times1p3_V':round(i*rw*1.3,6),
                   'illustrative_drop_including_one_XH_pair_initial_V':round(i*(rw+2*.01),6),
                   'illustrative_drop_including_one_XH_pair_after_env_V':round(i*(rw+2*.02),6),
                   'USB_tail_splitter_drop_included':False,'ampacity_status':'NOT_TESTED'})
    example={'Alpha2626_ohm_per_m_nominal_20C':wires['Alpha2626']['dcr_ohm_per_1000ft_nominal_20C']/304.8,
             'SPK_load_current_A':None,'SPK_note':'BTL + and - both active. No unverified speaker power used to manufacture an RMS current.'}
    # Sanity checks independent of any claimed actual route or load measurement.
    assert within([1.0668,1.1684],[.9,1.9]) and not within([1.0668,1.1684],[1.3,1.9])
    assert math.isclose(15.9/304.8,0.05216535433070866)
    assert math.isclose((5+.5)*1.1684,6.4262) and (5+.5)*1.2954 > 6.5
    assert len(loss)==30 and all(r['wire_drop_DCR_times1p3_V']>=r['wire_drop_nominal_V'] for r in loss)
    # Exact schematic evidence: reject the stock Rd-equipped breakout as a ready source.
    import xml.etree.ElementTree as ET
    tree=ET.parse(HERE/'sources/Adafruit_5978_schematic.sch')
    nets={n.attrib['name']:[p.attrib for p in n.findall('.//pinref')] for n in tree.findall('.//nets/net')}
    parts={p.attrib['name']:p.attrib for p in tree.findall('.//parts/part')}
    assert parts['R2']['value']=='5.1K' and parts['SJ1']['device']=='CLOSED'
    def has_pin(net,part,pin): return any(p['part']==part and p['pin']==pin for p in nets[net])
    assert has_pin('GND','R2','1') and has_pin('N$1','R2','2') and has_pin('N$1','SJ1','2')
    assert has_pin('CC1','SJ1','1') and has_pin('CC1','X1','CC1')
    usb={'parts':parts,'nets':nets,'scope':'Read-only manufacturer Eagle source; not modified or adopted'}
    dump('Adafruit_5978_net_extract.json',usb)
    table('terminal_fit.csv',fit);table('bend_screen.csv',bend);table('voltage_drop.csv',loss)
    dump('calculations.json',{'status':'PASS','meaning':'Numerical and source-field screening completed, not product/harness release',
          'inputs_sha256':hashlib.sha256((HERE/'facts.json').read_bytes()).hexdigest(),
          'equations':['R_loop=2*L_oneway*R_per_m','deltaV=I*R_loop','P_wire=I^2*R_loop',
                       'R_centreline_assumed=(catalogue_bend_multiple+0.5)*OD_max'],
          'terminal_fit':fit,'bend_screen':bend,'power_loss':loss,'audio_reference':example,
          'notes':['No ambient/rise or allowable ampacity can be derived without thermal data.',
                   'The terminal 3A rating is conditional on22AWG and genuine matched qualified parts.',
                   'H_BUS carries signal; two power-loop conductors each carry I, not2I.',
                   'DCR is nominal20C; 1.3 factor is sensitivity, not a temperature measurement.',
                   'Current targets do not qualify startup, fault clearing or regenerative pulses.'],
          'commands':[sys.executable+' '+str(Path(__file__).resolve())],'python':sys.version})
    baseline=json.loads((HERE/'inputs/protected_baseline.json').read_text())
    diff=[]
    for name,h in baseline['files'].items():
        p=ROOT/name
        if not p.exists() or hashlib.sha256(p.read_bytes()).hexdigest()!=h: diff.append(name)
    dump('source_preservation.json',{'status':'PASS' if not diff else 'FAIL','checked_files':len(baseline['files']),
                                    'formal_files':baseline['formal_count'],'changed':diff,
                                    'not_rerun':'Native ERC/DRC and full mechanical assembly review, because no design was edited.'})
    if diff: raise RuntimeError('Protected source change found: '+repr(diff))
    print(json.dumps({'calculation_rows':len(loss),'terminal_pairs':len(fit),'protected_files_unchanged':len(baseline['files']),
                       'physical_tests':'NOT_TESTED','harness_release':'BLOCKED'},ensure_ascii=False))
if __name__=='__main__':main()
