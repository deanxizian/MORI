"""Pinned Arm GNU toolchain. Verify vendor checksum before extracting/executing.
Only installs under .state/toolchains; does not configure or connect a device.
"""
import hashlib,json,platform,tarfile,urllib.request
from pathlib import Path
hosts={('Darwin','arm64'):'darwin-arm64',('Linux','x86_64'):'x86_64-arm-none-eabi'}
system,machine=platform.system(),platform.machine()
if (system,machine) not in hosts:raise SystemExit('Provide a verified Arm GNU 14.2.Rel1 installation using MORI_ARM_BIN on this host')
suffix='darwin-arm64-arm-none-eabi' if system=='Darwin' else 'x86_64-arm-none-eabi'
name=f'arm-gnu-toolchain-14.2.rel1-{suffix}'
base='https://armkeil.blob.core.windows.net/developer/Files/downloads/gnu/14.2.rel1/binrel/'
path=Path('.state/toolchains');path.mkdir(parents=True,exist_ok=True)
archive=path/(name+'.tar.xz');url=base+archive.name
if not archive.exists():urllib.request.urlretrieve(url,archive)
digest=hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()
checksum_url=url+'.sha256asc'
expected=urllib.request.urlopen(checksum_url,timeout=60).read().decode()
if digest not in expected.split():raise SystemExit('Vendor SHA256 mismatch; not extracted')
if not (path/name).exists():
    with tarfile.open(archive) as f:f.extractall(path,filter='data')
out=Path('reports/v1_2');out.mkdir(parents=True,exist_ok=True)
(out/'arm_toolchain.json').write_text(json.dumps({'version':'14.2.Rel1','url':url,'sha256':digest,'vendor_checksum_url':checksum_url,'verified':True,'host':[system,machine]},indent=2)+'\n')
print(f'MORI_ARM_BIN={path.resolve()/name/"bin"}')
