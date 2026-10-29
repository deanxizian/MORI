"""Native side-change fixtures and deliberate rejection controls.

Fixture copper is not refilled/qualified; only explicit structural assertions
are tested. Negative copies deliberately retain the original audit hash so they
also fail provenance. Their specific pad/guard failures are required separately.
"""
import copy,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import *
from footprint_side_change import validate_side_change
from review_planned_delta import review
b=Path('robot/.state/c3-completion/trials');out=b/'R178-side-change-tests';out.mkdir(exist_ok=False)
dev=Path('robot/hardware/driver/development');src=dev/'native';board='MORI_Interface_C3.kicad_pcb'
a=Copper(str(src/board));fs={f.GetReference():f for f in a.footprints};f=fs['D302']
spec={'reference':'D302','from_mm':list(xy(f.GetPosition())),'delta_mm':[0,0],'rotation_deg':90,
 'side_change':{'from_face':'B.Cu','to_face':'F.Cu','from_rotation_deg':f.GetOrientationDegrees(),'axis':'LEFT_RIGHT','reason':'Isolated native mirror fixture; never adopted.'}}
plan={'revision':'R178_D302_SIDE_FIXTURE','board_sha256':a.sha,'translations':[spec]}
pp=out/'plan.json';pp.write_text(json.dumps(plan,indent=2)+'\n');commands=[];rows=[]
def run(argv):
 t=time.time();r=subprocess.run(argv,text=True,capture_output=True);commands.append({'argv':argv,'returncode':r.returncode,'stdout':r.stdout,'stderr':r.stderr,'elapsed_seconds':time.time()-t})
 (out/'commands.json').write_text(json.dumps(commands,indent=2)+'\n');assert r.returncode==0,r.stderr
py=str(Path(sys.executable).absolute());scripts=dev/'scripts';fixture=out/'native'
run([py,str(scripts/'build_trial.py'),str(src),str(fixture),str(pp)])
reg=out/'regression.json';run([py,str(scripts/'audit_candidate.py'),str(src/board),str(fixture/board),str(reg)])
base_args=(str(src/board),str(fixture/board),str(pp),str(reg),str(dev/'evidence/R168G/regression.json'))
r=review(*base_args);(out/'positive-review.json').write_text(json.dumps(r,indent=2)+'\n')
padkeys=['pad_'+uid(p) for p in f.Pads()]
guards=[z for z in a.zones if z.GetZoneName().startswith('BODY_D302_')]
keys=['declared_side_change_D302','footprint_D302','translation_source_D302','exact_moved_pad_set','exact_moved_guard_set','exact_moved_footprint_set']+padkeys+['moved_guard_'+uid(z) for z in guards]+['zone_constraints_'+uid(z) for z in guards]
assert all(r['checks'][k] for k in keys)
rows.append({'name':'native_B_180_to_F_90_save_reload','status':'PASS','structural_checks':keys,'overall_fixture_status':r['status'],'overall_errors':r['errors']})
for name in ['wrong_pad_net','wrong_pad_size','guard_on_original_face']:
 bd=pcb.LoadBoard(str(fixture/board));ff=next(g for g in bd.GetFootprints() if g.GetReference()=='D302');pad=next(p for p in ff.Pads() if p.GetNumber()=='2')
 if name=='wrong_pad_net':
  pad.SetNet(next(n for n in bd.GetNetInfo().NetsByNetcode().values() if n.GetNetname()=='GND'));target='pad_'+uid(pad)
 elif name=='wrong_pad_size':
  sz=pad.GetSize();pad.SetSize(pcb.VECTOR2I(sz.x+10000,sz.y));target='pad_'+uid(pad)
 else:
  z=next(z for z in bd.Zones() if z.GetZoneName().startswith('BODY_D302_'));z.SetLayer(pcb.B_Cu);target='zone_constraints_'+uid(z)
 dest=out/(name+'.kicad_pcb');pcb.SaveBoard(str(dest),bd)
 rr=review(base_args[0],str(dest),*base_args[2:]);(out/(name+'-review.json')).write_text(json.dumps(rr,indent=2)+'\n')
 assert rr['status']=='FAIL' and rr['checks'][target] is False and rr['checks']['regression_hashes'] is False
 rows.append({'name':name,'status':'PASS','specific_rejection':target,'provenance_also_rejected':True})
for name in ['same_face','missing_reason','wrong_source_rotation','fixed_connector','other_diode','wrong_diode_value','wrong_diode_footprint','source_polarity_swap']:
 s=copy.deepcopy(spec);part=f;owned=guards
 if name=='same_face':s['side_change']['to_face']='B.Cu'
 elif name=='missing_reason':s['side_change'].pop('reason')
 elif name=='wrong_source_rotation':s['side_change']['from_rotation_deg']=f.GetOrientationDegrees()+90
 elif name in ['other_diode','wrong_diode_value','wrong_diode_footprint','source_polarity_swap']:
  part=pcb.FOOTPRINT(f)
  if name=='other_diode':part.SetReference('D301')
  elif name=='wrong_diode_value':part.SetValue('BAT54C')
  elif name=='wrong_diode_footprint':part.SetFPID(pcb.LIB_ID('C3_Packages','D_SOD-123'))
  else:
   pads={q.GetNumber():q for q in part.Pads()};a1=pads['1'].GetNet();a2=pads['2'].GetNet();pads['1'].SetNet(a2);pads['2'].SetNet(a1)
 else:
  part=fs['J702'];owned=[z for z in a.zones if z.GetZoneName().startswith('BODY_J702_')]
 try:validate_side_change(a.board,part,owned,s)
 except (ValueError,KeyError,TypeError):rows.append({'name':name,'status':'PASS','rejected':True})
 else:raise AssertionError('Unexpected accepted scope: '+name)
# Existing two-pad resistor behavior remains supported by the same validator.
rpart=fs['R716'];rspec=copy.deepcopy(spec);rspec['reference']='R716';rspec['side_change']['from_rotation_deg']=rpart.GetOrientationDegrees();rspec['side_change']['from_face']=a.board.GetLayerName(rpart.GetLayer());rspec['side_change']['to_face']='F.Cu' if rspec['side_change']['from_face']=='B.Cu' else 'B.Cu';rguards=[z for z in a.zones if z.GetZoneName().startswith('BODY_R716_')]
assert validate_side_change(a.board,rpart,rguards,rspec)
rows.append({'name':'existing_resistor_validator','status':'PASS'})
(out/'result.json').write_text(json.dumps({'scope':__doc__,'status':'PASS','tests':rows,'test_count':len(rows),'fixture_adopted':False},indent=2)+'\n')
print(json.dumps({'status':'PASS','tests':len(rows)}))
