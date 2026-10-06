"""Join the proved negative-side return to the initial last-wire state.

Use adaptive controller edges: an unsuccessful coarse change is subdivided
before trying distant controls. Only continuously checked edges are retained.
The other three completed wires and all static upstream wires remain.
"""
from pathlib import Path
NP_SCRIPT=Path(__file__).resolve();NP_ROOT=NP_SCRIPT.parent
NP_HELPER=NP_ROOT/'check_CAM_sequential_continuous.py';__file__=str(NP_HELPER)
exec(compile(NP_HELPER.read_text().split('\n# Static mixed states',1)[0],str(NP_HELPER),'exec'),globals())
__file__=str(NP_SCRIPT)
NP_OUT=TC_OUT/'negative_prefix';NP_OUT.mkdir(exist_ok=True)
np_tail_path=TC_OUT/'negative_return_branch/screen.json';np_tail=json.loads(np_tail_path.read_text())
assert np_tail['status']=='PASS' and np_tail['complete_local_coverage']
assert np_tail['source_main_sha256']==source_hash and np_tail['helper_sha256']==sha(NP_HELPER)
import signal
np_stop=False
def np_request_stop(signum,frame):
    global np_stop
    np_stop=True
signal.signal(signal.SIGTERM,np_request_stop)
np_started=time.time();np_trials=[];np_intervals=[];np_path=[];np_tests=0;np_unresolved=None
old={k:np_tail['path'][0][k] for k in ['fraction','amplitude_mm','side_angle_deg']};np_path.append(old)
assert old=={'fraction':.8025,'amplitude_mm':10.5,'side_angle_deg':-6.}
step=.025;minimum_step=.0001953125
grid=[(a,b) for a in [0.,3.,6.,7.5,9.,10.5,12.,13.5,15.,18.,21.,24.]
      for b in [0.,-3.,3.,-6.,6.,-9.,9.,-12.,12.,-18.,18.,-24.,24.,-30.,30.,
                -36.,36.,-42.,42.,-48.,48.,-54.,54.,-60.,60.,-72.,72.,-84.,84.]]
while old['fraction']>0.:
    if np_stop:
        np_unresolved={'reason':'Requested stop at a safe checkpoint','next':old};break
    t=max(0.,round(old['fraction']-step,12));controls=(old['amplitude_mm'],old['side_angle_deg'])
    if t==0.:candidates=[(9.,0.)]
    else:
        preferred=([ (controls[0],0.),(9.,0.) ] if t<.7 else [])+[controls]
        nearest=sorted(grid,key=lambda q:((q[0]-controls[0])/3.)**2+((q[1]-controls[1])/12.)**2)
        candidates=list(dict.fromkeys(preferred+nearest))
        if step>minimum_step+1e-12:candidates=candidates[:12]
    attempts=[];found=None
    for amp,angle in candidates:
        if np_stop:break
        node={'fraction':t,'amplitude_mm':amp,'side_angle_deg':angle};edge=(node,old);np_tests+=1
        nominal=sc_test(3,edge,t,t)
        if nominal:
            attempts.append({'controls':[amp,angle],'nominal':nominal});continue
        sc_passed=[];sc_unproved=[];sc_nominal=[]
        try:sc_interval(3,edge,t,old['fraction']);err=None
        except Exception as exc:err=repr(exc)
        if err is not None:
            attempts.append({'controls':[amp,angle],'error':err,'first_unproved':sc_unproved[:1]});continue
        found=node;np_intervals+=sc_passed;break
    np_trials.append({'fraction':t,'step':step,'rejected':attempts,'accepted':found is not None})
    if found is None:
        if step>minimum_step+1e-12:
            step=max(minimum_step,step/2.);print('NEGATIVE_PREFIX_REFINE',t,'next',old['fraction'],'new_step',step,flush=True);continue
        np_unresolved={'fraction':t,'next':old,'tested':len(candidates),'reason':'No continuously clear edge found at minimum trial step'};break
    old=found;np_path.append(found)
    print('NEGATIVE_PREFIX_NODE',t,amp,angle,'rejected',len(attempts),'step',step,
          'intervals',len(np_intervals),'tests',np_tests,'seconds',round(time.time()-np_started,1),flush=True)
    progress={'status':'NOT_TESTED','complete':False,'path':list(reversed(np_path)),
              'accepted_intervals':np_intervals,'attempts':np_trials,'source_main_sha256':source_hash,
              'script_sha256':sha(NP_SCRIPT),'helper_sha256':sha(NP_HELPER)}
    (NP_OUT/'progress.json').write_text(json.dumps(progress,ensure_ascii=False,indent=2)+'\n')
    # Grow again after a successful small step; known local bends therefore
    # get fine resolution without forcing every distant interval to be tiny.
    step=min(.025,step*2.)
rows=sorted(np_intervals,key=lambda r:r['interval'][0])
coverage=bool(rows and rows[0]['interval'][0]==0. and rows[-1]['interval'][1]==.8025
              and all(a['interval'][1]==b['interval'][0] for a,b in zip(rows,rows[1:])))
good=coverage and np_unresolved is None
result={'status':'PASS' if good else 'BLOCKED','scope':'Last-wire prefix0..0.8025 joining the proved negative-side return',
    'source_main_sha256':source_hash,'script_sha256':sha(NP_SCRIPT),'helper_sha256':sha(NP_HELPER),
    'source_negative_return_sha256':sha(np_tail_path),'path':list(reversed(np_path)),
    'accepted_intervals':np_intervals,'complete_prefix_coverage':good,'complete_last_wire_coverage':False,
    'candidate_checks':np_tests,'interval_tests':sc_tests,'attempts':np_trials,'unresolved':np_unresolved,
    'ordinary_margin_mm':.3,'bare_contact_margin_mm':0.,'generic_0_3mm_contact_packing':'BLOCKED',
    'initial_three_wire_installation':'NOT_TESTED','final_tail0_875_to1_continuous':'NOT_TESTED',
    'terminal_insertion':'NOT_TESTED','feed_to_start':'NOT_TESTED','ties':'NOT_TESTED',
    'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-np_started}
(NP_OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('NEGATIVE_PREFIX_DONE',result['status'],len(np_intervals),np_unresolved,flush=True)
