"""Verify the study package and promoted nominal model, without manufacturing release."""
from pathlib import Path
import json,hashlib,zipfile,re,csv
H=Path(__file__).resolve().parent;ROOT=H.parents[2];BASE=ROOT/'mechanical/revisions/V1.2-M1.38_before_prearrival'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
checks=[]
def check(k,ok,data): checks.append(dict(id=k,status='PASS' if ok else 'FAIL',evidence=data))
for rel in ['contracts/components.json']:
 p=ROOT/rel;b=BASE/rel
 check('unchanged_'+rel,b.exists() and sha(p)==sha(b),{'current_sha256':sha(p),'baseline_exists':b.exists()})
animation=read(ROOT/'mechanical/animation/manifest.json')
check('animation_matches_existing_release_manifest',sha(ROOT/'mechanical/mori_assembly_animation.blend')==animation['animation_blend_sha256'] and sha(ROOT/'mechanical/mori_v1_2.blend')==animation['source_blend_sha256'],{'reference':'mechanical/animation/manifest.json','animation_sha256':animation['animation_blend_sha256'],'current_revision':'V1.2-M1.39'})
c=read(H/'jlc_coupons/manifest.json')
for part in c['parts']:
 p=ROOT/part['file'];t=part['topology']
 check(part['id'],sha(p)==part['sha256'] and part['connected_components']==1 and all(t[k]==0 for k in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles','inconsistent_stl_normals']),{'sha256':sha(p),'dimensions_mm':part['dimensions_mm'],'topology':t})
with zipfile.ZipFile(H/'MORI_PA12_fit_coupons.zip') as z:
 check('zip_integrity',z.testzip() is None and len([n for n in z.namelist() if n.endswith('.stl')])==7,{'sha256':sha(H/'MORI_PA12_fit_coupons.zip'),'stl_count':7})
 for part in c['parts']:
  dat=z.read('MORI_PA12_fit_coupons/'+part['id']+'.stl')
  check('packaged_'+part['id'],hashlib.sha256(dat).hexdigest()==part['sha256'],{})
missing=[]
for page in [H/'index.html',H/'jlc_coupons/index.html']:
 for url in re.findall(r'(?:href|src)="([^"]+)"',page.read_text()):
  if url.startswith(('http:','https:','#','data:')):continue
  if not (page.parent/url.split('#')[0]).exists():missing.append([str(page.relative_to(H)),url])
check('local_links',not missing,missing)
rows=list(csv.DictReader((H/'fastener_inventory.csv').open(encoding='utf-8-sig')))
check('fastener_inventory',len(rows)==129 and len({r['part_id'] for r in rows})==129,{'count':len(rows)})
for f,n,k in [('servo_candidate_motion.json',130,'poses'),('camera_aperture_candidate.json',775,'nominal_rays')]:
 r=read(H/f);check(f,r['status']=='PASS' and r[k]==n,{'status':r['status'],k:r[k]})
pre=read(ROOT/'mechanical/reports/prearrival_validation.json')
check('promoted_main_local_geometry',pre['status']=='PASS',{'report':'mechanical/reports/prearrival_validation.json','revision':pre['revision']})
val=read(ROOT/'mechanical/reports/validation.json');check('no_geometric_failures',val['counts']['FAIL']==0,val['counts'])
cfg=read(ROOT/'config/geometry.json');check('IMU_two_holes_retained',cfg['prearrival_completion']['imu_assessment']['withdrawn_by_user'] and pre['material']['IMU_native_model_unchanged'],{'native_board_changed':False,'third_point_proposal':'WITHDRAWN_BY_USER'})
build=read(ROOT/'mechanical/reports/build_manifest.json');changed_sources=[f for f,h in build['input_sha256'].items() if sha(ROOT/f)!=h];check('current_build_input_hashes',not changed_sources,changed_sources)
out={'baseline':'V1.2-M1.38','current_revision':cfg['revision'],'status':'PASS' if all(r['status']=='PASS' for r in checks) else 'FAIL','checks':checks,'scope':'Package/link/hash and already-recorded geometric evidence checks. No manufacturing, physical-fit or strength qualification; ear nuts/camera promoted to current model, IMU expansion withdrawn; no whole-robot manufacturing release.'}
(H/'delivery_check.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print('PREARRIVAL_DELIVERY_CHECK',out['status'],len(checks))
for r in checks:
 if r['status']=='FAIL':print(r)
