"""Check whether a longer shared rear withdrawal clears the under-deck plug."""
from pathlib import Path
EXT_SCRIPT=Path(__file__).resolve();EXT_HELPER=EXT_SCRIPT.parent/'diagnose_shell16_continuations.py'
__file__=str(EXT_HELPER)
exec(compile(EXT_HELPER.read_text().split('\nreports=[]',1)[0],str(EXT_HELPER),'exec'),globals())
__file__=str(EXT_SCRIPT)
OUT=ORDER_OUT/'shell16_extended_back';OUT.mkdir(exist_ok=True)
sources={str((ORDER_OUT/'shell16_rigid_continuations/screen.json').relative_to(PROJECT)):
         sha(ORDER_OUT/'shell16_rigid_continuations/screen.json')}
prior=json.loads((ORDER_OUT/'shell16_rigid_continuations/screen.json').read_text())
assert prior['paths'][0]['phases'][0]['status']=='PASS'
assert prior['script_sha256']==sha(EXT_HELPER)
rows=[];failure=None
for i,y in enumerate(np.arange(-14.,-40.01,-.5)):
    p=dict(a=16.,y=float(y),by=float(y),sz=14.,bz=18.)
    failure=check_rigid(p)
    rows.append(dict(index=i,pose=p,status='BLOCKED' if failure else 'PASS',failure=failure))
    if failure:break
    if i%20==0:print('SHELL16_EXTEND',y,flush=True)
clear_ys=[r['pose']['y'] for r in rows if r['status']=='PASS']
vertical=[]
for y in [-20.,-24.,-28.,-32.,-36.,-40.]:
    if y not in clear_ys:continue
    zero=shellpose(16.,y,0.)
    upper_low=min(m.transform(zero[:3,:4]).bounding_box()[2] for m in upper_rigid.values())
    end=math.ceil(max(body_max_z+1.-upper_low+4.,body_max_z+1.-bridge_min_z)*2)/2
    stage=[];vf=None
    for i,z in enumerate(np.arange(18.,end+.01,.5)):
        p=dict(a=16.,y=y,by=y,sz=float(z-4.),bz=float(z))
        vf=check_rigid(p)
        stage.append(dict(index=i,pose=p,status='BLOCKED' if vf else 'PASS',failure=vf))
        if vf:break
    vertical.append(dict(held_y_mm=y,endpoint_z_mm=end,status='BLOCKED' if vf else 'PASS',rows=stage))
    print('SHELL16_EXTEND_VERTICAL',y,vertical[-1]['status'],stage[-1],flush=True)
    if not vf:break
report=dict(status='PASS' if any(r['status']=='PASS' for r in vertical) else 'BLOCKED',
    scope='Rigid continuation only; no claim of wire movement or assembly',
    script_sha256=sha(EXT_SCRIPT),helper_sha256=sha(EXT_HELPER),source_files=sources,
    protected_sources=protected,horizontal_rows=rows,vertical_candidates=vertical,
    source_bounds_mm={n:list(phys[n].bounding_box()) for n in ['Load_Frame','Body_Upper','Yaw_Base']},
    shell16_plug_bounds_mm=list(upper_plugs['rear_J2'].transform(shellpose(16.,0.,14.)[:3,:4]).bounding_box()),
    all14_body_wires_present=True,plugs_unchanged=True,main_applied=False,manufacturing_release=False)
(OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('SHELL16_EXTEND_DONE',report['status'],rows[-1],flush=True)
