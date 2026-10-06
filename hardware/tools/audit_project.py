#!/usr/bin/env python3
"""Cross-file checks. Use KiCad's bundled Python for native PCB loading."""
from pathlib import Path
import csv, datetime, hashlib, json, math, re, zipfile
import xml.etree.ElementTree as ET
import pcbnew

R = Path(__file__).resolve().parents[1]
P = R.parent
read = lambda p: json.loads((R/p).read_text())
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
checks = []

def check(name, ok, detail):
    checks.append(dict(check=name,status='PASS' if ok else 'FAIL',detail=detail))

mech = read('mechanical_interfaces.json')
check('mechanical_sources',all(sha(P/p)==h for p,h in mech['mechanical_source_sha256'].items()),
      'params, derived report and export manifest match recorded mechanical SHA256')
vol = read('reports/model_volume_mass.json')
exports=json.loads((P/'reports/export_manifest.json').read_text())
paths={x['id']:P/x['file'] for x in exports['parts']}
check('STL_volume_sources',all(sha(paths[x['id']])==x['sha256'] for x in vol),
      str(len(vol))+' installed STL volume sources; coupons excluded')

pins=list(csv.DictReader((R/'pinmap.csv').open()))
board_h=(R/'firmware/main/board.h').read_text()
defines=dict(re.findall(r'#define PIN_(\w+) GPIO_NUM_(\d+)',board_h))
check('GPIO_firmware_to_pinmap',all(defines.get(x['signal'])==x['gpio'] for x in pins)
      and len(pins)==len(defines)==24, '24 physical GPIO mappings, not chip-only capabilities')
gpios={int(x['gpio']) for x in pins}
check('GPIO_unique_and_reserved',len(gpios)==24 and not gpios.intersection({0,3,19,20,35,36,37,38,43,44,45,46}),
      'N8R8 PSRAM, USB, console, boot and v1.1 RGB pins reserved')
calc=read('reports/calculation_results.json')
counts=48*((22**3*23)/(12*10**3))
distance=float(re.search(r'WHEEL_M_PER_COUNT \(([0-9.]+)f\)',board_h).group(1))
check('encoder_units',math.isclose(counts,979.616,abs_tol=1e-7)
      and math.isclose(counts,calc['kinematics']['encoder_output_counts_x4'],abs_tol=1e-7)
      and math.isclose(distance,math.pi*.095/counts,abs_tol=1e-12),
      '48 CPR already x4; 20.4086667 gear ratio; 1:1 belt; 979.616 output counts/rev')
cfg=(R/'firmware/sdkconfig').read_text()
check('compiled_safety_defaults',all('# CONFIG_'+n+' is not set' in cfg for n in
      ['MORI_POWER_STAGE_VERIFIED','MORI_ENABLE_BALANCE','MORI_HEAD_VERIFIED']),
      'All three hardware/balance/head gates disabled in the actual build config')

conn=read('kicad/connectivity.json')
xml=ET.parse(R/'reports/netlist.xml')
netpins={(n.get('ref'),n.get('pin')):net.get('name').lstrip('/')
         for net in xml.findall('.//nets/net') for n in net.findall('node')}
expected={(c['ref'],n):pin['net'] for c in conn for n,pin in c['pins'].items() if pin['net']}
check('schematic_connectivity',all(netpins.get(key)==value for key,value in expected.items()),
      str(len(expected))+' connected component pins agree with native exported netlist')
board=pcbnew.LoadBoard(str(R/'kicad/MORI_carrier.kicad_pcb'))
footprints={f.GetReference():f for f in board.GetFootprints()}
pads={(ref,p.GetNumber()):p.GetNetname().lstrip('/') for ref,f in footprints.items() for p in f.Pads()}
check('PCB_pad_connectivity',all(pads.get(key)==value for key,value in expected.items()),
      'Every intended schematic component pin has its matching native PCB pad/net')
params=json.loads((P/'params.json').read_text())
actual_holes=[]
for i,xy in enumerate(params['structure']['deck_mount_xy_mm'],1):
    fp=footprints['H'+str(i)]
    pos=fp.GetPosition()
    actual_holes.append(abs(pcbnew.ToMM(pos.x)-100-xy[0])<1e-5 and
                        abs(pcbnew.ToMM(pos.y)-100-xy[1])<1e-5 and
                        all(abs(pcbnew.ToMM(p.GetDrillSize().x)-3.4)<1e-5 for p in fp.Pads()))
check('deck_hole_alignment',all(actual_holes),'4 holes at Blender ±40,±42; actual native drill 3.4mm; Z/assembly untested')
check('unrouted_prototype_marked',len(board.GetTracks())==0 and board.GetAreaCount()==0
      and not read('kicad/generation.json')['fabrication_allowed'],
      '0 tracks / 0 copper zones; no fabrication release')
cby={c['ref']:c for c in conn}
check('USB_and_encoder_power_path',cby['J12']['pins']['3']['net']=='LOGIC_5V_RAW'
      and cby['D1']['pins']['1']['net']=='DEVKIT_5V'
      and cby['D1']['pins']['2']['net']=='LOGIC_5V_RAW'
      and all(cby[j]['pins'][pin]['net']=='DEVKIT_5V' for j,pin in [('J14','1'),('J4','4'),('J5','4')])
      and 'UNPLUG whole J12' in cby['J12']['note'],
      'Disconnect J12 for USB; retain J14 and both encoder 5V feeds; physical backfeed test NOT_TESTED')
check('clamp_revision',cby['R14']['value']=='25k5_0.1pct' and calc['regen']['clamp_on_tolerance_V'][0]>8.4,
      '25.5k/10k divider with2.2M hysteresis; arithmetic only, overshoot NOT_TESTED')

manifest=read('handoff/baseline_manifest.json')
with zipfile.ZipFile(R/'handoff/firmware_baseline.zip') as z:
    snapshot_ok=set(z.namelist())==set(manifest['sha256']) and all(
        hashlib.sha256(z.read(p)).hexdigest()==h and sha(R/p)==h
        for p,h in manifest['sha256'].items())
check('software_snapshot_integrity',snapshot_ok and manifest['version']=='HW-SW-0.4',
      'ZIP entries match manifest and current hardware firmware/pinmap/wiring/test sources')
physical=list(csv.DictReader((R/'tests/physical_test_record.csv').open()))
check('no_fabricated_physical_pass',all(x['status']=='NOT_TESTED' for x in physical),
      str(len(physical))+' physical checks remain NOT_TESTED')
bom=list(csv.DictReader((R/'bom.csv').open()));budget=read('reports/budget.json')
cost=lambda row:float(row['unit_price'])*int(row['quantity'])
check('BOM_budget',math.isclose(sum(cost(x) for x in bom if x['group']!='optional'),budget['complete_robot_including_one_time'],abs_tol=.001)
      and math.isclose(sum(cost(x) for x in bom if x['minimal_balance_included']=='yes'),budget['minimal_balance_including_battery_charger_fixture'],abs_tol=.001),
      'Quantity-aware USD totals; quoted prices vs allowances remain distinct')

commands=sum([read('reports/verification_commands_'+g+'.json') for g in ['software','cad']],[])
check('verification_log_hashes',all(sha(R/c['log'])==c['log_sha256'] for c in commands),
      'Recorded command logs still match their execution records')
out=dict(date_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),checks=checks,
         status='PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL',
         scope='Cross-file integrity only. PCB DRC FAIL (unrouted); hardware NOT_TESTED.')
(R/'reports/project_audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
print(out['status'],len(checks),'cross-file checks')
for item in checks:
    if item['status']=='FAIL': print(item['check'],item['detail'])
raise SystemExit(0 if out['status']=='PASS' else 1)
