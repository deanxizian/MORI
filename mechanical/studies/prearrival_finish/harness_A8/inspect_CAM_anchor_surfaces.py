"""Read-only surfaces near nominal H06 clamp datums; no mounting geometry yet."""
from pathlib import Path
ANCHOR_SCRIPT=Path(__file__).resolve();ANCHOR_ROOT=ANCHOR_SCRIPT.parent
ANCHOR_HELPER=ANCHOR_ROOT/'plan_cam_yaw_fan_v4.py';__file__=str(ANCHOR_HELPER)
exec(compile(ANCHOR_HELPER.read_text().split('\nrng=np.random.default_rng',1)[0],str(ANCHOR_HELPER),'exec'),globals())
__file__=str(ANCHOR_SCRIPT)
OUT=ANCHOR_ROOT/'cam_anchors';OUT.mkdir(exist_ok=True)
queries={'yaw_loop_base':np.mean(anchor_points,axis=0),
         'CAM_tail_end':np.mean([q[-1] for q in tails],axis=0),
         'body_J5_departure':np.mean([body[f'pin{i}_yaw0'][0] for i in range(1,5)],axis=0)}
for pin in range(1,5):queries[f'neck_pin{pin}']=body[f'pin{pin}_yaw0'][-1]
rows=[]
for label,point in queries.items():
    hits=[]
    for name,group,m,lo,hi,tree in ob:
        loc,normal,index,distance=tree.find_nearest(Vector(point))
        hits.append({'object':name,'group':group,'distance_mm':float(distance),
            'nearest_mm':list(loc),'normal':list(normal),'bounds_mm':[lo.tolist(),hi.tolist()]})
    hits.sort(key=lambda r:r['distance_mm']);rows.append({'datum':label,'point_mm':point.tolist(),'nearest':hits[:16]})
record={'status':'PASS','scope':'Read-only nominal source surface inventory, not a clamp fit approval',
    'source_main_sha256':source_hash,'script_sha256':sha(ANCHOR_SCRIPT),'source_helper_sha256':sha(ANCHOR_HELPER),
    'rows':rows,'main_applied':False,'anchor_design':'NOT_TESTED'}
(OUT/'surfaces.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
for row in rows:
    print(row['datum'],row['point_mm'])
    for q in row['nearest'][:10]:print(q['object'],q['group'],round(q['distance_mm'],3),q['nearest_mm'])
assert sha(source)==source_hash
