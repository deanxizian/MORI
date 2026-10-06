"""Extract source projections of the saved shell16 stages without saving CAD."""
from pathlib import Path
VIEW16_SCRIPT=Path(__file__).resolve()
VIEW16_HELPER=VIEW16_SCRIPT.parent/'screen_shell16_joint_feed.py'
__file__=str(VIEW16_HELPER)
exec(compile(VIEW16_HELPER.read_text().split('\nfor label,poses in stages_for',1)[0],str(VIEW16_HELPER),'exec'),globals())
__file__=str(VIEW16_SCRIPT)
OUT=ORDER_OUT/'shell16_joint_feed'
report=json.loads((OUT/'screen.json').read_text())
assert report['script_sha256']==sha(VIEW16_HELPER)
assert report['status']=='PASS'
arrays=np.load(OUT/'curves.npz')
assert sha(OUT/'curves.npz')==report['curves_sha256']
planes={'YZ':np.array([[0,1,0,0],[0,0,1,0],[1,0,0,0]],dtype=float),
        'XZ':np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0]],dtype=float)}
scenes=[]
for label,stage,index in [('start','shell_release',0),('shell16','shell_release',60),('bridge18','bridge_lift',36)]:
    row=next(r for r in report['prefix_stages'] if r['stage']==stage)['rows'][index]
    p=row['pose'];st=shellpose(p['a'],p['y'],p['sz']);bt=trans(z=p['bz'])
    items={n:phys[n].transform((bt if n in bridge else st if n in upper else I)[:3,:4])
           for n in ['Load_Frame','Body_Upper','Yaw_Base','MCU_Carrier','Rear_Interface_PCB','Speaker']}
    items['Plug_rear_J2']=upper_plugs['rear_J2'].transform(st[:3,:4])
    projections={plane:{n:[np.asarray(a).tolist() for a in m.transform(T).project().to_polygons()]
                        for n,m in items.items()} for plane,T in planes.items()}
    scenes.append(dict(label=label,pose=p,projections=projections,
                       curves={str(pin):arrays[f'{stage}_pin{pin}_pose{index}'].tolist() for pin in range(1,5)}))
witnesses=[]
for label in ['bridge_only','together_vertical']:
    d=next(r for r in report['continuation_diagnostics'] if r['stage']==label)
    row=d['rows'][-1];p=row['pose'];f=row['failure']
    st=shellpose(p['a'],p['y'],p['sz']);bt=trans(y=p.get('by',0.),z=p['bz'])
    names=[f['a'],f['b']];items={}
    for n in names:
        if n.startswith('Plug_'):m=upper_plugs[n[5:]].transform(st[:3,:4])
        else:m=phys[n].transform((bt if n in bridge else st if n in upper else I)[:3,:4])
        items[n]=m
    overlap=items[names[0]]^items[names[1]]
    assert abs(overlap.volume()-f['intersection_mm3'])<1e-6
    b=np.asarray(overlap.bounding_box());items['overlap']=overlap
    witnesses.append(dict(label=label,pose=p,failure=f,center_mm=((b[:3]+b[3:])/2).tolist(),
       projections={plane:{n:[np.asarray(a).tolist() for a in m.transform(T).project().to_polygons()]
                            for n,m in items.items()} for plane,T in planes.items()}))
sources={str(p.relative_to(PROJECT)):sha(p) for p in [VIEW16_HELPER,OUT/'screen.json',OUT/'curves.npz',membership_path]}
d=dict(status='PASS',scope='Read-only source projections, not a new fit approval',
       script_sha256=sha(VIEW16_SCRIPT),source_files=sources,protected_sources=protected,
       scenes=scenes,witnesses=witnesses,main_applied=False,manufacturing_release=False)
(OUT/'projections.json').write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_PROJECTIONS_SAVED',len(scenes),len(witnesses),flush=True)
