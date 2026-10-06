#!/usr/bin/env python3
"""Publish hardware-owned S3 interfaces/BOM; preserve mechanics and firmware."""
from pathlib import Path
from collections import defaultdict
from copy import deepcopy
import json
from logic5v_S3 import H,DEST,REPORT,NAME,REV,new_parts
R=H.parents[1]
read=lambda p:json.loads(p.read_text())
def put(p,data):p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')

def publish():
    assert read(REPORT/'verification.json')['status']=='PASS'
    cat=read(R/'contracts/components.json');e=read(R/'contracts/electrical_interfaces.json')
    sources=read(H/'sources/index.json');base=read(R/'config/project_baseline.json')
    # Idempotent re-run: derive modified BOM/IO from the actual saved pre-S3
    # contract, while keeping unrelated current top-level fields intact.
    old=read(H/'revisions/before_logic5V_S3_20260922/components.json')
    oe=read(H/'revisions/before_logic5V_S3_20260922/electrical_interfaces.json')
    cat['components']=deepcopy(old['components'])
    groups=defaultdict(list)
    for c in new_parts():
        if c['footprint'] and c['manufacturer']!='PCB':groups[c['mpn']].append(c)
    src_ids=[]
    known_sources={s['id'] for s in sources['sources']}
    prototype=deepcopy(next(c for c in old['components'] if c['id']=='logic_power'))
    for i,(mpn,parts) in enumerate(groups.items(),1):
        c=parts[0];sid='HW12-S3-'+str(i).zfill(2);src_ids.append(sid)
        if sid not in known_sources:
            sources['sources'].append(dict(id=sid,title=mpn+' manufacturer data / S3 selected value',url=c['source'] or None,
                local_path='hardware/v1_2/sources/parts/TI_TPS54302_RevC.pdf' if mpn=='TPS54302DDCR' else None,
                accessed_date='2026-09-22',notes='Design reference, not an order or measured qualification. Exact domestic quote/stock status is separately tracked.'))
        if mpn=='TPS54302DDCR':
            row=next(p for p in cat['components'] if p['id']=='logic_power')
            row.update(quantity=2,full_model=mpn,purpose='运动/交互板载5V降压IC（两个独立支路）',
                board_revision='S3 schematic; PCB pending',specification='4.5-28V input;400kHz;chip3A; system targets0.5A motion/1.5A CAM sustained',
                interface='Board-local3S-to5V; MCU modules retain their own3.3V. No separate Pololu5V modules.',
                dimensions_mm={'package_envelope_xyz':[2.9,2.8,1.1],'note':'TI DDC0006A IC envelope only; not a converter-module or board envelope. H1.1max.'},
                mass_g=None,shaft_hole_interface=None,connector_clearance_mm=None,
                source_ids=[sid],data_status='VENDOR_DOCUMENTED',unit_price_cny=None,quote_date=None,
                purchase_channel='立创商城',purchase_option='C311983 / TPS54302DDCR',
                selection_status='SELECTED_SCHEMATIC_ONLY',confirmation_status='CN_CATALOG_FOUND_QUOTE_PENDING',
                missing=['国内小批量结算价/库存','PCB布局与热设计','实际模块并发电流','纹波/瞬态/温升实测'],
                notes='Replaces the unpurchased Pololu D24V22F5 x2. No old module mass/envelope is reused. U60/U70. '+c['note'])
        else:
            matches=[p for p in cat['components'] if p['full_model']==mpn]
            if matches:
                row=matches[0];row['quantity']+=len(parts)
                row['purpose']+='; S3新增：'+','.join(p['ref'] for p in parts)
                row['source_ids']=list(dict.fromkeys(row['source_ids']+[sid]))
                row['notes']=(row.get('notes','')+'; '+c['note']).strip('; ')
            else:
                row=deepcopy(prototype);row.update(id='s3_'+str(i).zfill(2),category='pcb_part',
                    purpose='S3板载5V：'+','.join(p['ref'] for p in parts),quantity=len(parts),quantity_unit='piece',
                    full_model=mpn,board_revision='S3 schematic; PCB pending',specification=c['value'],
                    interface=c['footprint'],source_ids=[sid],source_date='2026-09-22',data_status='ASSUMED',
                    dimensions_mm=None,mass_g=None,mass_tolerance_g=None,shaft_hole_interface=None,connector_clearance_mm=None,
                    mechanical_contract_keys=[],mounting_release=False,purchase_channel='立创商城/授权分销，精确SKU待核价',
                    purchase_option=c['lcsc'] or mpn,unit_price_cny=None,currency='CNY',quote_date=None,
                    stock_status='NOT_LIVE_CHECKOUT_CONFIRMED',stock_quantity=None,tax_basis='UNKNOWN',shipping_basis='国内运费另列；未确认包邮',
                    confirmation_status='EXACT_QUOTE_PENDING',selection_status='SELECTED_SCHEMATIC_ONLY',included_in=None,
                    alternative_model=None,readaptation_requirement='额定、引脚、封装、反馈公差和环路稳定性重新核对',
                    missing=['国内精确MPN小批量报价/库存','封装与布局终审','实板测试'],notes=c['note'])
                cat['components'].append(row)
            row['schematic_references']=[NAME+':'+p['ref'] for p in parts]
    # The original raw-battery connector is visibly DNP in S3.
    xt=next(c for c in cat['components'] if c['id']=='p1_020')
    xt['quantity']=7;xt['purpose']=xt['purpose'].replace(', MORI_power_P1:J6','')+'; S3 J6不装'
    xt['notes']+='; J6 marked DNP in S3; previous P2 physical board remains unchanged.'
    pcb=next(c for c in cat['components'] if c['id']=='carrier_pcb')
    pcb.update(full_model='MORI_motion_P2 + MORI_imu_P2 + MORI_power_S3 (power PCB not laid out)',
        dimensions_mm={'motion_xy':[70,35],'imu_xy':[20,16],'power_xy':None,'power_thickness':None},
        specification='One prototype batch; S3 power outline/layer count/thickness pending mechanical and layout review',
        notes='Old power_P2 80x45 is not the new S3 outline. PCB fabrication/assembly cost must be re-quoted after freeze.',
        selection_status='POWER_PCB_DEFERRED_USER_REQUEST',missing=['S3电源PCB板框/层数/热设计','新PCB打样/装配报价'])
    cat.update(revision=REV,physical_tests='NOT_TESTED',engineering_revision_note='S3 schematic adds two PCB-local5V bucks. User explicitly deferred PCB/frame changes. P2 CAD is preserved; native S3 ERC/netlist audited. No procurement/fabrication release.')
    cat['excluded_duplicate_purchases']=[x for x in cat['excluded_duplicate_purchases'] if 'Pololu D24V22F5' not in str(x)]
    cat['excluded_duplicate_purchases'].append('Pololu D24V22F5 x2: unpurchased reference removed; replaced by TPS54302 S3 board circuits. PCB test pads included in board fabrication, not separately purchased.')
    cat['procurement_release']=cat['manufacturing_release']=False
    e.update(revision=REV,physical_tests='NOT_TESTED',pinmap=deepcopy(oe['pinmap']),harness=deepcopy(oe['harness']),
             hardware_freeze=False,pcb_release=False,manufacturing_outputs_allowed=False)
    for d in e['power_domains']:
        if d['id'] in ['MOTION5V','CAM5V']:
            motion=d['id']=='MOTION5V';d.update(status='S3_SCHEMATIC_NOT_TESTED_PCB_PENDING',location='power_board',
                regulator='TPS54302DDCR',regulator_ref='U60' if motion else 'U70',
                output_connector='MORI_power_S3.J17' if motion else 'MORI_power_S3.J18',
                output_pin_map={'1':'+5V_MOTION' if motion else '+5V_CAM','2':'GND'},
                setpoint_calculated_V=.596*(1+100/13.3),continuous_target_A=.5 if motion else 1.5,
                transient_target_A=.75 if motion else 2.,input_fuse='0451001.MRL' if motion else '0451002.MRL',
                qualification_status='NOT_TESTED',note='Independent input fuse, buck, L/C/FB and maintenance-disable. Shared battery/ground. '+
                ('To unchanged motion_P2 J1; WeAct onboard3V3 remains; no motor current.' if motion else 'To qualified CAM USB5V pigtail; never CAM BAT. Disconnect robot5V before host USB.'))
    e['shared_battery_note']='Separate buck/fuse branches reduce coupling; battery/ground/master fuse/reverse FET/shunt remain common causes. Input fuse is not instantaneous electronic isolation, and a single buck failure is not covered by an independent output OVP. CAM branch fault must be tested with motion loaded.'
    for r in e['pinmap']:r['revision']=REV
    for n,p,j,out in [(60,'M5','J17','+5V_MOTION'),(70,'C5','J18','+5V_CAM')]:
        for pn,net in [(1,out),(2,'GND')]:
            e['pinmap'].append(dict(revision=REV,domain='power',net=net,mcu_pin=None,peripheral='POWER',direction='supply_out' if pn==1 else 'return',
                connector=NAME+'.'+j,pin_number=pn,logic_level='5V nominal' if pn==1 else '0V',source_ids=src_ids,
                assignment_status='S3_SCHEMATIC_ONLY',boot_default='EN internally enabled; independent of ARM_Q',bench_status='NOT_TESTED',
                notes='Output voltage only; MCU3V3 remains local. No PCB connector position frozen.'))
    for c in new_parts():
        if c['ref'].startswith(('JP','TP')):
            for pn,p in c['pins'].items():
                e['pinmap'].append(dict(revision=REV,domain='power',net=p['net'],mcu_pin=None,peripheral='MAINTENANCE_TEST',
                    direction='passive_test_access',connector=NAME+'.'+c['ref'],pin_number=int(pn),logic_level='EN: float=ON, GND=OFF; never3S' if p['net'].endswith('_EN') else 'GND' if p['net']=='GND' else '5V nominal',
                    source_ids=src_ids,assignment_status='S3_SCHEMATIC_ONLY',boot_default='JP open; no shunt fitted',bench_status='NOT_TESTED',
                    notes=c['note']))
    for r in e['harness']:
        r['revision']=REV
        for k in ['id','from_']:
            r[k]=r[k].replace('MORI_power_P1',NAME).replace('MORI_motion_P1','MORI_motion_P2').replace('MORI_imu_P1','MORI_imu_P2')
        if r['from_'].startswith(NAME+'.'):
            r['view_direction']='Electrical terminal numbers only. S3 connector position, PCB side and cable approach are UNFROZEN; do not use a P1/P2 assembly view for S3.'
        if r['from_']=='MORI_motion_P2.J1':
            r.update(to=NAME+'.J17',wire_gauge='AWG26, GH SSHL-002T-P0.2; verify crimp/insulation',
                     notes='1->1 5V;2->2GND. Target0.5A/0.75A transient. Loop resistance <=0.15ohm; length pending mechanical routing.')
        if r['from_']==NAME+'.J6':
            r.update(to='NONE / DNP',status='DNP_NO_HARNESS',notes='RAW BAT, not5V. No external5V regulator modules in current S3 BOM.')
    for n,j,net,to,wire,peak,res in [(60,'J17','+5V_MOTION','MORI_motion_P2.J1','AWG26 GH',.75,.15),
                                 (70,'J18','+5V_CAM','CAM USB5V pigtail, exact assembly qualification pending','AWG22 XH; qualified USB power pigtail',2,.07)]:
        c=next(x for x in new_parts() if x['ref']==j)
        e['harness'].append(dict(revision=REV,id=NAME+':'+j,from_=NAME+'.'+j,to=to,
            nets=[dict(pin='1',signal=net),dict(pin='2',signal='GND')],connector=c['footprint'],length_mm=None,
            wire_gauge=wire,rated_current_A=None,design_peak_A=peak,max_loop_resistance_ohm=res,
            view_direction='Electrical pad numbers only; physical placement/orientation UNFROZEN.',status='SCHEMATIC_ONLY_NOT_TESTED',notes=c['note']))
    e['hardware_schematic_revision']=REV
    e['gpio_change']='NONE: MCU GPIO/peripheral/boot assignments retained; only power-board connectors added.'
    e['logic_power_startup']=dict(sequence='Both buck EN pins internally enable after master input rises; neither logic rail depends on ARM_Q.',
        maintenance='JP60 and JP70 independently ground EN only in cradle; loss of motion3V3 clears actuator ARM.',
        local_regulators='WeAct retains local3V3; CAM retains local regulators; no regulator outputs are paralleled.',
        backfeed='No automatic hostUSB power mux or independent output reverse-blocking added. Disconnect robotCAM5V before hostUSB.',
        validation='NOT_TESTED')
    e['active_schematics']={'power':f'hardware/v1_2/kicad/{NAME}/{NAME}.kicad_sch',
        'motion':'hardware/v1_2/kicad/MORI_motion_P2/MORI_motion_P2.kicad_sch','imu':'hardware/v1_2/kicad/MORI_imu_P2/MORI_imu_P2.kicad_sch'}
    e['pcb_revision_relationship']=dict(existing='P2',power_schematic='S3',synchronized=False,
        reason='User2026-09-22 deferred PCB changes while mechanical model evolves. No S3 PCB exists; P2 power does not include two new bucks.')
    e['historical_pcb_projects']=deepcopy(oe['pcb_projects'])
    e['pcb_projects']={}
    for kind,size in [('motion',[70,35]),('imu',[20,16]),('power',[80,45])]:
        name='MORI_'+kind+'_P2'
        e['pcb_projects'][name]=dict(path='hardware/v1_2/kicad/'+name,dimensions_mm=size,
            status='PRESERVED_P2_NOT_SYNCHRONIZED_TO_S3' if kind=='power' else 'UNCHANGED_P2_PROTOTYPE',fabrication_release=False)
    e['engineering_review']='hardware/v1_2/schematic_S3/README.md'
    e['schematic_validation']='hardware/v1_2/schematic_S3/reports/verification.json'
    sources['revision']=REV;base['hardware_revision']=REV
    put(R/'contracts/components.json',cat);put(R/'contracts/electrical_interfaces.json',e)
    put(H/'sources/index.json',sources);put(R/'config/project_baseline.json',base)
    mech=read(R/'contracts/mechanical_interfaces.json')
    put(H/'handoff/mechanical_S3.json',dict(revision=REV,mechanical_revision_read=mech.get('revision'),
        status='SCHEMATIC_ONLY_NO_MECHANICAL_FREEZE',power_board_outline_mm=None,mounting_holes=None,connector_positions=None,
        old_power_P2_mm=[80,45],old_P2_fits_S3=False,
        note='OldP2 board is retained historical copper. Do not treat80x45 as the new S3 footprint; old44x16x10 allocation is also not an approved new size.',
        removed_modules=['Pololu D24V22F5 x2'],new_power_circuits=['TPS54302DDCR x2 withL/C/fuses on future power board'],
        unchanged_modules=['WeAct F412RET6 V1.1 onboard3V3','Waveshare33700 local power'],
        requested_clearance=['Keep current16mm-high electrolytics and external9V/6V interfaces in future fit review.',
                            'CAM5V harness whole-loopR<=70mohm, motion<=150mohm; no cable lengths inferred.',
                            'Buck high-di/dt loops local; keep SW away from ADC/IMU and RF. Thermal copper is not yet sized.'],
        mass_g=None,physical_tests='NOT_TESTED',mechanical_contract_modified=False))
    print(REV,'published; mainBOM rows',len(cat['components']),'MCU GPIO unchanged')

if __name__=='__main__':publish()
