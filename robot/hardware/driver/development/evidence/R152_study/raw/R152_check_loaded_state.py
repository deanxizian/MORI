"""Check actual SES fixed-state and layer use after a no-routing load."""
import hashlib
import json
import runpy
from collections import Counter
from pathlib import Path

b=Path('robot/.state/c3-completion/trials')
helpers=runpy.run_path(str(b/'R152_extract_ses.py'))
policy=json.loads((b/'R152-joint-exchange2/R148E-joint.routing.json').read_text())
movable=set(policy['movable_signal_nets'])
rows=[]
for name in ['R152-routeB','R152-readbackC']:
    path=b/name/'result.ses'
    root=helpers['parse'](path)
    network=helpers['child'](helpers['child'](root,'routes'),'network_out')
    states=Counter();protected_movable=[];unfixed_other=[]
    for net in network[1:]:
        for item in net[2:]:
            type_=[x[1] for x in item if isinstance(x,list) and x[0]=='type']
            state=type_[0] if type_ else 'unfixed'
            states[(item[0],state)]+=1
            if item[0]=='wire' and net[1] in movable and state not in ['normal','unfixed']:
                protected_movable.append(net[1])
            if item[0]=='wire' and net[1] not in movable and state in ['normal','unfixed']:
                unfixed_other.append(net[1])
    result=json.loads((b/name/'result.json').read_text())
    row=dict(run=name,states=[dict(kind=k,state=s,count=n) for (k,s),n in sorted(states.items())],
             protected_movable_wire_count=len(protected_movable),
             protected_movable_nets=sorted(set(protected_movable)),
             unfixed_other_wire_nets=sorted(set(unfixed_other)),
             components=result['board_statistics']['components']['total_count'],
             pins=result['board_statistics']['items']['pin_count'],
             vias=result['board_statistics']['items']['via_count'],
             nets=result['board_statistics']['nets']['total_count'],
             classes=result['board_statistics']['nets']['class_count'],
             routing_enabled=result['settings_snapshot']['autorouter']['enabled'],
             active_layers=[x['routable'] for x in result['settings_snapshot']['layers']],
             result_ses_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    rows.append(row)
current=rows[-1]
assert current['protected_movable_wire_count']==0
assert current['unfixed_other_wire_nets']==[]
assert (current['components'],current['pins'],current['vias'],current['nets'])==(215,651,323,156)
assert current['routing_enabled'] is False
assert current['active_layers']==[True,False,True,True,False,True]
assert rows[0]['protected_movable_wire_count']>0
source=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert hashlib.sha256(source.read_bytes()).hexdigest()==policy['source_board_sha256']
report=dict(scope=__doc__,status='PASS',runs=rows,
            finding='type route imports as protected in this build; type normal is confirmed unfixed for selected signals. Other wires and all source vias remain protected.',
            native_unchanged=True,source_board_sha256=policy['source_board_sha256'],
            limits=['This validates transport loading, not native DRC, routing completeness, power, reference, thermal, or physical qualification.'])
out=b/'R152-loaded-state.json';assert not out.exists();out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,ensure_ascii=False))
