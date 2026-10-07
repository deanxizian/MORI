"""Inventory the actual local toolchain and software inputs; never include credentials/data."""
import datetime,hashlib,json,pathlib,platform,subprocess,sys,os
from git_metadata import project_git

ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=ROOT/os.environ.get('MORI_REPORT_ROOT','reports/v1')
OUT.mkdir(parents=True,exist_ok=True)
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def command(args):
 try:
  p=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=45)
  return {'command':args,'exit_code':p.returncode,'output':(p.stdout+p.stderr).strip()}
 except (OSError,subprocess.TimeoutExpired) as error:return {'command':args,'exit_code':None,'error':str(error)}

versions=[['bash','tools/node-env.sh','--version'],['bash','tools/node-env.sh','exec','node','--version'],[sys.executable,'-VV'],['cc','--version'],['git','-C','/Users/dean/esp/esp-idf','rev-parse','HEAD'],['git','-C','/Users/dean/esp/esp-idf','describe','--tags','--always'],['bash','-c','source /Users/dean/esp/esp-idf/export.sh >/dev/null 2>&1 && idf.py --version && xtensa-esp32s3-elf-gcc --version && cmake --version && ninja --version']]
for compiler in (ROOT/'.state/toolchains').glob('*/bin/arm-none-eabi-gcc'):
 versions.append([str(compiler),'--version'])
environment={'recorded_utc' :datetime.datetime.now(datetime.timezone.utc).isoformat(),'source':'HOST','platform':platform.platform(),'tools':[command(c) for c in versions],'project_git':project_git(ROOT),'mobile_scope':'NOT_APPLICABLE: paused by user, web only'}
(OUT/'environment.json').write_text(json.dumps(environment,indent=2,ensure_ascii=False))

excluded={'__pycache__','node_modules','managed_components','build','build_v1','build_adapter_check','dist','.pytest_cache','.git'}
paths=[]
for prefix in ['contracts','firmware/motion','firmware/interaction','backend','apps/console','simulation','tools','docs','.github']:
 for p in (ROOT/prefix).rglob('*'):
  if p.is_file() and not p.is_symlink() and not set(p.relative_to(ROOT).parts)&excluded and not any(part.startswith('build') for part in p.relative_to(ROOT).parts[:-1]) and p.name!='.env':paths.append(p)
paths += [ROOT/p for p in ['AGENTS.md','MORI_SPEC_V1.md','README_SOFTWARE_V1.md','THIRD_PARTY_NOTICES.md','package.json','pnpm-lock.yaml','pnpm-workspace.yaml','refs/sources.lock.json','software/interface_change_requests.md']]
paths += [ROOT/p for p in ['MORI_SPEC_V1_2.md','README_SOFTWARE_V1_2.md','software/references_v1_2.lock.json','software/THIRD_PARTY_V1_2.md','software/inputs/v1_2/03_CODEX_SOFTWARE.md'] if (ROOT/p).exists()]
inputs={str(p.relative_to(ROOT)):sha(p) for p in sorted(set(paths))}
protected={p:sha(ROOT/p) for p in ['params.json','config/geometry.json','contracts/mechanical_interfaces.json']}
artifacts={str(p.relative_to(ROOT)):sha(p) for domain in ['motion','interaction'] for p in (ROOT/f'firmware/{domain}/build_v1').glob('*.bin')}
artifacts.update({str(p.relative_to(ROOT)):sha(p) for folder in ['firmware/motion/build_stm32','firmware/interaction/build_v1_2'] for p in (ROOT/folder).glob('*') if p.suffix in ('.bin','.elf')})
evidence={str(p.relative_to(ROOT)):sha(p) for p in (OUT/'runs').rglob('*') if p.is_file()}
for folder in [OUT/'design']:
 evidence.update({str(p.relative_to(ROOT)):sha(p) for p in folder.rglob('*') if p.is_file()})
for name in ['acceptance.md','acceptance.json','environment.json','arm_toolchain.json','arm_download.json','interaction_dependencies_before.lock','interaction_sdkconfig_before','SIMULATED_s288.csv','SIMULATED_commands.jsonl','SIMULATED_dynamics_v1_2.json']:
 p=OUT/name
 if p.exists():evidence[str(p.relative_to(ROOT))]=sha(p)
(OUT/'file_manifest.json').write_text(json.dumps({'source_sha256':inputs,'build_binary_sha256':artifacts,'evidence_sha256':evidence,'protected_reference_sha256_at_inventory':protected,'note':'Protected files are read-only references; other tasks may update them independently. No equality to an invented prior snapshot is asserted.'},indent=2,ensure_ascii=False))

licenses=[]
store=ROOT/'node_modules/.pnpm'
packages=list(store.glob('*/node_modules/*/package.json'))+list(store.glob('*/node_modules/@*/*/package.json'))
for p in packages:
 data=json.loads(p.read_text());license_files=[x for x in p.parent.iterdir() if x.is_file() and x.name.lower().startswith(('license','licence','copying','notice'))]
 licenses.append({'package':data.get('name'),'version':data.get('version'),'license_declaration':data.get('license','NOT_DECLARED'),'package_json':str(p.relative_to(ROOT)),'package_sha256':sha(p),'license_files':{str(x.relative_to(ROOT)):sha(x) for x in license_files}})
(OUT/'node_dependency_licenses.json').write_text(json.dumps(licenses,indent=2,ensure_ascii=False))
print(json.dumps({'source_files':len(inputs),'binary_files':len(artifacts),'node_packages':len(licenses),'output':str(OUT)},ensure_ascii=False))
