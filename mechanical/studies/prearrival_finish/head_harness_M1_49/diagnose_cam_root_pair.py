"""Global-distance diagnosis of representative CAM1/2 pair failures."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];OUT=HERE/'remaining_routes'
sys.path.insert(0,str(HERE))
from curve_clearance import prepared,pair
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
file=OUT/'nine_higher_lift/combined/lower_nine_screen.json'
proof=json.loads(file.read_text());assert proof['status']=='BLOCKED'
for p,h in {**proof['sources'],**proof['inputs']}.items():assert sha(ROOT/p)==h,p
meta={};curves={};inputs={str(file.relative_to(ROOT)):sha(file)}
for folder in ['nine_higher','higher_cam_directed','higher_cam_stagger','cam_root_lift']:
    report=OUT/folder/'body_prefix_screen.json';data=report.parent/'body_prefix_candidates.npz'
    r=json.loads(report.read_text());assert sha(data)==r['curve_sha256']
    meta.update({x['id']:x for rows in r['pools'].values() for x in rows});curves.update(dict(np.load(data)))
    inputs.update({str(report.relative_to(ROOT)):sha(report),str(data.relative_to(ROOT)):sha(data)})
rows=[r for r in proof['prefix_pair_checks'] if {meta[r['a']]['endpoint'],meta[r['b']]['endpoint']}=={'CAM_1','CAM_2'}]
def cost(r):return sum(meta[r[n]].get('length_sort_mm',meta[r[n]].get('analytic_length_mm')) for n in ['a','b'])
rows.sort(key=cost);selected=[];seen=set()
for row in rows:
    a,b=meta[row['a']],meta[row['b']]
    key=tuple((v['endpoint'],v['entry_deg'],round(v['lead_mm'],3),v.get('plateau_mm'),v.get('height_return_length_mm')) for v in [a,b])
    if key in seen:continue
    seen.add(key);selected.append(row)
    if len(selected)==32:break
result=[]
for row in selected:
    a,b=row['a'],row['b'];ma,mb=meta[a],meta[b]
    check=pair(prepared(curves[a],ma['OD_mm']/2,ma['chord_error_mm']),prepared(curves[b],mb['OD_mm']/2,mb['chord_error_mm']))
    result.append(dict(a=a,b=b,metadata_a=ma,metadata_b=mb,**check))
report=dict(status='PASS',scope='Diagnosis completed, not route clearance approval',
    evaluated=len(result),results=result,best_sampled_pair=max(result,key=lambda r:r['gap_lower_bound_mm']),
    all_nine='BLOCKED',main_changed=False,inputs=inputs,script_sha256=sha(Path(__file__)))
(OUT/'CAM_pair_diagnosis.json').write_text(json.dumps(report,indent=2)+'\n')
print('CAM_PAIR_DIAGNOSIS',len(result),'best bound',report['best_sampled_pair']['gap_lower_bound_mm'],flush=True)
