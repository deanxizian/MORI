"""Try a2mm staging lift after the6mm state blocked the descending PCB."""
from pathlib import Path
F2_SCRIPT=Path(__file__).resolve();F2_ROOT=F2_SCRIPT.parent
F2_HELPER=F2_ROOT/'screen_CAM_forming_lifted_end.py';__file__=str(F2_HELPER)
exec(compile(F2_HELPER.read_text().split('\nfl_trials=[];',1)[0],str(F2_HELPER),'exec'),globals())
FL_SCRIPT=F2_SCRIPT;FL_HELPER=F2_HELPER;__file__=str(F2_SCRIPT)
FL_OUT=FM_OUT/'lifted_end2';FL_OUT.mkdir(exist_ok=True);fl_started=time.time()
fl_h=2.;fl_shrink=fl_h/(1.+math.pi/2.);fl_rt=wi_rt-fl_shrink/2.
fr_lengths[:]=fl_installed_lengths;fr_lengths[1]=math.pi*fl_rt;fr_lengths[5]-=fl_shrink;fr_lengths[7]+=fl_h
fm_core_length=sum(fr_lengths[:5]);fm_tail_parameter=sum(fr_lengths[5:7]);fm_lengths[:]=fr_lengths
assert abs(sum(fr_lengths)-sum(fl_installed_lengths))<1e-10
fl_end=sum(fr_lengths);fl_seat=(fl_end-5.-fl_h,fl_end-fl_h)
exec(compile('fl_trials=[];'+F2_HELPER.read_text().split('\nfl_trials=[];',1)[1],str(F2_SCRIPT),'exec'),globals())
