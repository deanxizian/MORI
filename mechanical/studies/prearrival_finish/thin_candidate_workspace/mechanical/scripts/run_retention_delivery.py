"""Reconcile current source outputs without editing the saved robot."""
import sys,json,subprocess,datetime
from pathlib import Path
r=Path(__file__).resolve().parents[1];b='/Applications/Blender.app/Contents/MacOS/Blender';py='/Users/dean/.cache/codex-runtimes/mori-cad/bin/python'
steps=[('render',r/'scripts/render.py',[]),('export',r/'scripts/export.py',[]),('export_wheel_metal',r/'scripts/export_wheel_metal.py',[]),('finalize_structure_metadata',r/'scripts/finalize_structure_metadata.py',[]),('catalog',r/'scripts/catalog.py',['--ids','Pitch_Yoke,Yaw_Base,Yaw_Bearing,Yaw_Anti_Lift_Keeper,Yaw_Keeper_Screw_0,Yaw_Keeper_Screw_1,Yaw_Keeper_Insert_0,Yaw_Keeper_Insert_1']),('export_electronics_detail',r/'scripts/export_electronics_detail.py',[]),('check_electronics_detail',r/'scripts/check_electronics_detail.py',[]),('print_walls',r/'studies/interface_completion/audit_final_prints.py',[]),('delivery_check',r/'scripts/delivery_check.py',[])]
records=[]
for name,script,args in steps:
 model=r/('mori_electronics_detail.blend' if name=='check_electronics_detail' else 'mori_v1_2.blend')
 cmd=[py,str(script)] if name=='export_wheel_metal' else [b,'-b',str(model),'--python-exit-code','1','--python',str(script)]+(['--']+args if args else [])
 log=r/'reports'/('retention_'+name+'.log');start=datetime.datetime.now(datetime.timezone.utc).isoformat();print('RETENTION_DELIVERY',name,flush=True)
 with log.open('w') as f:out=subprocess.run(cmd,cwd=r.parent,stdout=f,stderr=subprocess.STDOUT)
 records.append(dict(stage=name,command=cmd,started_utc=start,finished_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),returncode=out.returncode,log=str(log.relative_to(r))))
 (r/'reports/head_retention_delivery_commands.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
 if out.returncode:raise SystemExit(out.returncode)
print('RETENTION_DELIVERY_COMPLETE',flush=True)
