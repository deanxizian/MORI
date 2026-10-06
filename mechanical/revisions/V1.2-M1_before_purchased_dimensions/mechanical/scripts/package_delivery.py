"""Package only current executed V1.2 mechanical evidence; preserve previous releases."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
import argparse,json,shutil,hashlib,zipfile,datetime
PROJECT=Path(__file__).resolve().parents[2]
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
class Links(HTMLParser):
 def __init__(self):super().__init__();self.refs=[]
 def handle_starttag(self,tag,attrs):self.refs.extend(v for k,v in attrs if k in ['href','src'])
def check(project):
 root=project/'mechanical';r=root/'reports';assert read(r/'validation.json')['counts']['FAIL']==0
 assert read(r/'delivery_consistency.json')['status']=='PASS';assert read(r/'rebuild_check.json')['status']=='PASS'
 e=read(r/'export_manifest.json');assert e['candidate_count']==e['exported_count']
 for i in e['parts']:assert i['status']=='PASS' and sha(root/i['file'])==i['sha256']
 for p,h in read(r/'build_manifest.json')['input_sha256'].items():assert sha(project/p)==h,p
 parser=Links();parser.feed((root/'index.html').read_text());missing=[u for u in parser.refs if not urlparse(u).scheme and urlparse(u).path and not(root/unquote(urlparse(u).path)).exists()];assert not missing,missing
 return len(parser.refs)
def copy(source,dest):
 dest.parent.mkdir(parents=True,exist_ok=True)
 if source.is_dir():shutil.copytree(source,dest,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.DS_Store'))
 else:shutil.copy2(source,dest)
def main():
 a=argparse.ArgumentParser();a.add_argument('--output-parent',required=True,type=Path);args=a.parse_args();check(PROJECT)
 dest=args.output_parent/'MORI_V1_2_M1';archive=args.output_parent/'MORI_V1_2_M1.zip'
 if dest.exists() or archive.exists():raise FileExistsError('Earlier releases are immutable: '+str(dest))
 names=['AGENTS.md','MORI_SPEC_V1_2.md','01_CODEX_MECHANICAL.md','config/geometry.json','contracts/mechanical_interfaces.json','reports/mechanical_v1_2.md','reports/decisions/ADR-MECH-012-v1_2-layout.md','mechanical/mori_v1_2.blend','mechanical/README.md','mechanical/index.html','mechanical/scripts','mechanical/sources/v1_2','mechanical/exports/templates']
 if (PROJECT/'contracts/components.json').exists():
  names.append('contracts/components.json')
  if (PROJECT/'hardware/v1_2/sources').exists():names.append('hardware/v1_2/sources')
 for n in names:copy(PROJECT/n,dest/n)
 root=PROJECT/'mechanical';rp=root/'reports'
 report_names=['validation','static_interference','head_motion','cable_motion','wheel_clearance','mesh_topology','battery_access','routing_review','mass_budget','derived','assembly_instances','build_manifest','intended_contacts','camera_kinematics','export_manifest','rebuild_check','body_head_envelope','parameter_comparison','parts_preview_manifest','delivery_consistency','head_load_estimate','display_outline_review','commands','render_manifest']
 for n in report_names:copy(rp/(n+'.json'),dest/'mechanical/reports'/(n+'.json'))
 for n in ['bom.csv','bom.json','组装与打印.md','外购与自制.md']:copy(rp/n,dest/'mechanical/reports'/n)
 for cmd in read(rp/'commands.json'):
  if 'log' in cmd:copy(root/cmd['log'],dest/'mechanical'/cmd['log'])
 for n in read(rp/'render_manifest.json'):copy(root/'renders'/(n['view']+'.png'),dest/'mechanical/renders'/(n['view']+'.png'))
 for n in read(rp/'parts_preview_manifest.json'):copy(root/n['file'],dest/'mechanical'/n['file'])
 for n in ['A','B']:
  for v in ['front','side','45']:copy(root/'renders/variants'/f'{n}_{v}.png',dest/'mechanical/renders/variants'/f'{n}_{v}.png')
 for path in list((root/'renders').glob('parts_sheet_*.jpg'))+[root/'renders/v1_2_shape_comparison.jpg']:copy(path,dest/'mechanical/renders'/path.name)
 for n in read(rp/'export_manifest.json')['parts']:copy(root/n['file'],dest/'mechanical'/n['file'])
 (dest/'README.md').write_text('''# MORI V1.2 mechanical candidate release

Open mechanical/index.html for the actual Blender gallery and all parts. Editable model: mechanical/mori_v1_2.blend. Report: reports/mechanical_v1_2.md. Rebuild: python3 mechanical/scripts/run_all.py; see mechanical/README.md for platform dependencies.

M1 complete, M2 partially complete and vendor interfaces blocked, M3 candidate files generated. Not a final manufactured/qualified robot. Shared inputs: config/geometry.json and contracts/mechanical_interfaces.json. The hardware-owned components.json is included as a read-only snapshot; missing dimensions and conditional full-display-box collisions remain explicit.

This package contains current mechanical evidence only. Previous A4 revisions and unrelated software/hardware stay in the original MORI project. No purchase, PCB freeze or balance validation is claimed.
''')
 check(dest)
 manifest={'revision':'V1.2-M1','created_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Mechanical pre-study; no manufacturing release','files':{str(p.relative_to(dest)):sha(p) for p in sorted(dest.rglob('*')) if p.is_file()}}
 (dest/'PACKAGE_MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for p in sorted(dest.rglob('*')):
   if p.is_file():z.write(p,p.relative_to(args.output_parent))
 with zipfile.ZipFile(archive) as z:assert z.testzip() is None
 assert all(sha(dest/p)==h for p,h in manifest['files'].items())
 print(json.dumps({'status':'PASS','delivery':str(dest),'archive':str(archive),'files':len(manifest['files'])+1,'zip_bytes':archive.stat().st_size,'zip_sha256':sha(archive)},ensure_ascii=False))
if __name__=='__main__':main()
