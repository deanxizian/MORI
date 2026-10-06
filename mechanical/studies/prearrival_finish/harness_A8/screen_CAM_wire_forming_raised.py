"""Try extra apex height during the same constant-length forming family."""
from pathlib import Path
FR_SCRIPT=Path(__file__).resolve();FR_ROOT=FR_SCRIPT.parent
FR_HELPER=FR_ROOT/'screen_CAM_wire_forming.py';__file__=str(FR_HELPER)
exec(compile(FR_HELPER.read_text().split('\nfm_reference,_,_=',1)[0],str(FR_HELPER),'exec'),globals())
__file__=str(FR_SCRIPT)
FR_OUT=FM_OUT/'raised';FR_OUT.mkdir(exist_ok=True)
fr_lengths=fm_lengths.copy();fr_started=time.time();fr_trials=[];fr_saved={}


def fr_curve(fraction,amplitude):
    extra=amplitude*math.sin(math.pi*fraction)
    fm_lengths[0]=fr_lengths[0]+extra
    fm_lengths[2]=fr_lengths[2]-extra
    assert fm_lengths[2]>.5
    p,s,e=fm_curve(fraction)
    assert abs(sum(fm_lengths)-sum(fr_lengths))<1e-9
    fm_lengths[:]=fr_lengths
    return p,s,e,extra


def fr_check(points,parameter,error,slot,fraction):
    for name,group,m,lo,hi,tree in fm_targets:
        keep=np.ones(len(points),bool)
        if name in {'Pitch_Yoke','CAM_Tie_Head','CAM_Tie_Band'}:
            keep&=~((parameter<=4.3+1e-5)&(abs(points[:,1]+1.5)<1e-5))
        if fraction==1. and name=='Pitch_Cradle':
            keep&=~((abs(points[:,0]-slots[slot,0])<1e-5)&(abs(points[:,1]-slots[slot,1])<1e-5)
                &(points[:,2]>=slots[slot,2]-5.-1e-5)&(points[:,2]<=slots[slot,2]+1e-5))
        ids=np.flatnonzero(keep)
        for span in np.split(ids,np.flatnonzero(np.diff(ids)>1)+1):
            if len(span)<2:continue
            hit=check_one(points[span],error,lo,hi,m,tree)
            if hit:return {'slot':slot,'object':name,**hit}
    return None


for amplitude in [6.,9.,12.,15.,18.]:
    rows=[];saved={}
    for fraction in np.linspace(0.,1.,41):
        base,parameter,error,extra=fr_curve(float(fraction),amplitude);hit=None
        for slot in range(4):
            p=base+[xx[slot]-xx[0],0,0]
            saved[f'f{fraction:.3f}_slot{slot}']=p
            hit=fr_check(p,parameter,error,slot,float(fraction))
            if hit:break
        rows.append({'fraction':float(fraction),'apex_extra_mm':extra,'status':'BLOCKED' if hit else 'PASS','hit':hit})
    good=all(r['status']=='PASS' for r in rows)
    fr_trials.append({'amplitude_mm':amplitude,'status':'PASS' if good else 'BLOCKED','rows':rows})
    print('FORMING_RAISED',amplitude,fr_trials[-1]['status'],[(r['fraction'],r['hit']['object']) for r in rows if r['hit']],round(time.time()-fr_started,2),flush=True)
    if good:
        fr_saved=saved;break
if fr_saved:np.savez_compressed(FR_OUT/'curves.npz',**fr_saved)
report={'status':'PASS' if fr_saved else 'BLOCKED','scope':'Finite41-position forming screen only',
 'source_main_sha256':source_hash,'script_sha256':sha(FR_SCRIPT),'helper_sha256':sha(FR_HELPER),
 'source_plain_screen_sha256':sha(FM_OUT/'screen.json'),'trials':fr_trials,
 'selected_amplitude_mm':fr_trials[-1]['amplitude_mm'] if fr_saved else None,
 'curves_sha256':sha(FR_OUT/'curves.npz') if fr_saved else None,
 'rule':'Initial upright straight gains A*sin(pi*f); return straight loses the same amount. All turns scale by f; total3D length and endpoints at f0/f1 remain unchanged.',
 'minimum_bend_radius_bound_mm':fm_meta['minimum_radius_bound_mm'],
 'continuous_motion':'NOT_TESTED','terminal_and_crimp_shapes':'NOT_TESTED','wire_packing':'NOT_TESTED',
 'initial_feed_to_upright_state':'NOT_TESTED','tie_threading_tightening':'NOT_TESTED',
 'uninstalled_CAM_board':True,'untightened_tie_final_solids_omitted':sorted(fm_deferred),
 'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-fr_started}
(FR_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('CAM_FORMING_RAISED_DONE',report['status'],flush=True)
