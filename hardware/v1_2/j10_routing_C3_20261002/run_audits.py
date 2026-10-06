from candidate import *
import runpy
import layout_P5, audit_body_P5, all_trace_review_P5R2 as ar
layout_P5.paths=lambda kind:(NAME,D,PCB,R)
audit_body_P5.paths=layout_P5.paths
runpy.run_path(str(ROOT/'hardware/v1_2/tools/audit_load_paths_P5.py'),run_name='__main__')
audit_body_P5.audit('power')
bb=k.LoadBoard(str(PCB));jj=json.loads((R/'body_review_final.json').read_text())
for ff in bb.GetFootprints():
 if ff.GetReference() in jj['components']:jj['components'][ff.GetReference()]['footprint']=ff.GetFPIDAsString()
dump(R/'body_review_final.json',jj)
ar.paths=layout_P5.paths
ar.source=lambda kind:(OLD,SD,SD/(OLD+'.kicad_pcb'))
ar.ROOT=ROOT;ar.O=HERE
before=ar.extract('power','before');after=ar.extract('power','after')
old={t['uuid']:t for t in before['tracks']};new=[t for t in after['tracks']if t['uuid']not in old or any(t[k]!=old[t['uuid']][k]for k in ['net','layer','a','z','width'])]
new_ids={t['uuid']for t in new};nets={t['net']for t in new}
dump(R/'changed_route_flags.json',{'changed_segment_count':len(new),'nets':sorted(nets),'flags':[x for x in after['candidates']if any(i in new_ids for i in x['uuids'])]})
for net in sorted(nets):
 if net=='/GND':continue
 (R/('net_'+net.strip('/').replace('+','p')+'.svg')).write_text(ar.picture(after,net))
print('CHANGED NETS',sorted(nets),flush=True)
