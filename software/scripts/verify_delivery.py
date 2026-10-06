#!/usr/bin/env python3
"""Read-only source/archive/default gate verification; no hardware operations."""
import argparse,hashlib,json,pathlib,re,sys,zipfile
SW=pathlib.Path(__file__).resolve().parents[1]
ROOT=SW.parent
FW=SW/'firmware_work/firmware'

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(require_current=False):
    original=json.loads((SW/'reports/baseline_integrity.json').read_text())
    checks={p:digest(ROOT/p)==sha for p,sha in original['source_hashes'].items() if not p.startswith('hardware/handoff/')}
    with zipfile.ZipFile(SW/'reference_sources/HW-SW-0.3_firmware_baseline.zip') as archive:
        for name,sha in original['baseline_manifest']['sha256'].items():
            checks['extracted baseline member '+name]=hashlib.sha256(archive.read(name)).hexdigest()==sha
    adopted=json.loads((SW/'reports/hw04_adoption.json').read_text())
    manifest=adopted['baseline_manifest']['sha256']
    archived_manifest=json.loads((SW/'reference_sources/HW-SW-0.4_baseline_manifest.json').read_text())
    checks['adopted manifest matches archive']=adopted['baseline_manifest']==archived_manifest
    checks['authorized HW-SW-0.4']=adopted['handoff']==archived_manifest['version']=='HW-SW-0.4'
    with zipfile.ZipFile(SW/'reference_sources/HW-SW-0.4_firmware_baseline.zip') as archive:
        for name,sha in manifest.items():
            checks['adopted baseline member '+name]=hashlib.sha256(archive.read(name)).hexdigest()==sha
    current_matches=all((ROOT/p).is_file() and digest(ROOT/p)==sha for p,sha in adopted['source_hashes'].items())
    for p,sha in adopted['old_simulated_sha256'].items():
        checks['historical simulation preserved '+p]=(SW/p).is_file() and digest(SW/p)==sha
    for p,sha in adopted['preserved_implementation_sha256'].items():
        checks['existing implementation preserved '+p]=(SW/p).is_file() and digest(SW/p)==sha
    checks['dependencies.lock unchanged']=digest(FW/'dependencies.lock')==manifest['firmware/dependencies.lock']
    checks['pinmap matches HW-SW-0.4']=digest(SW/'firmware_work/pinmap.csv')==manifest['pinmap.csv']
    checks['wiring matches HW-SW-0.4']=digest(SW/'firmware_work/wiring.csv')==manifest['wiring.csv']
    io=(FW/'components/mori_core/include/mori_io.h').read_text()
    checks['active requirements version HW-SW-0.4']='#define MORI_REQUIREMENTS_BASELINE "HW-SW-0.4"' in io
    pins={'BATTERY':1,'NTC_L':2,'NTC_R':4,'AIN1':5,'AIN2':6,'BIN1':7,'BIN2':8,'ENC_LA':9,'ENC_LB':10,
          'ENC_RA':11,'ENC_RB':12,'LCD_MOSI':13,'LCD_CLK':14,'LCD_CS':15,'IMU_INT':16,'SDA':17,'SCL':18,
          'ARM':21,'LCD_DC':39,'LCD_RST':40,'HEAD':41,'HEARTBEAT':42,'FAULT':47,'ESTOP':48}
    board=(FW/'main/board.h').read_text()
    for name,num in pins.items():checks['GPIO '+name]=bool(re.search(rf'#define PIN_{name} GPIO_NUM_{num}\b',board))
    config=(FW/'sdkconfig').read_text()
    for key in ['MORI_POWER_STAGE_VERIFIED','MORI_ENABLE_BALANCE','MORI_HEAD_VERIFIED','MORI_AXES_VERIFIED']:
        checks[key+' default off']=f'CONFIG_{key}=y' not in config
        checks[key+' Kconfig default n']=bool(re.search(rf'config {key}\n(?:(?!config ).)*?default n', (FW/'main/Kconfig.projbuild').read_text(),re.S))
    installed=FW/'build/config/sdkconfig.h'
    if installed.exists():
        for key in ['MORI_POWER_STAGE_VERIFIED','MORI_ENABLE_BALANCE','MORI_HEAD_VERIFIED','MORI_AXES_VERIFIED']:
            checks[key+' default binary gate off']=f'#define CONFIG_{key} 1' not in installed.read_text()
    source_manifest=SW/'reports/delivery_manifest.json'
    if source_manifest.exists():
        delivery=json.loads(source_manifest.read_text())
        for p,sha in delivery['source_sha256'].items():
            checks['source hash '+p]=(SW/p).is_file() and digest(SW/p)==sha
        for p,sha in delivery['artifact_sha256'].items():
            checks['built artifact hash '+p]=(SW/p).is_file() and digest(SW/p)==sha
    else:
        checks['delivery source/artifact manifest exists']=False
    for name,passed in checks.items():print(('PASS ' if passed else 'FAIL ')+name)
    print(f'{sum(checks.values())}/{len(checks)} checks; physical NOT_TESTED')
    current=json.loads((ROOT/'hardware/handoff/baseline_manifest.json').read_text()).get('version','UNKNOWN')
    print(('PASS' if current_matches else 'FAIL')+' current upstream source alignment: '+current+'; physical validation NOT_TESTED')
    return all(checks.values()) and (not require_current or current_matches)
if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--require-current-handoff',action='store_true',help='fail if current hardware/protected inputs differ from explicitly adopted HW-SW-0.4; this does not approve power-on')
    args=parser.parse_args();sys.exit(0 if verify(args.require_current_handoff) else 1)
