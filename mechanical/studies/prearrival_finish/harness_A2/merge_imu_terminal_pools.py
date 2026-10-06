"""Merge screened local additions with the existing screened eight-pin pool."""
from pathlib import Path
import json,hashlib,sys
root=Path(__file__).resolve().parent
AXIAL='--axial-pairs' in sys.argv
UPPER='--upper' in sys.argv or AXIAL
names=['imu_refined_assembly_pools.json','imu_terminal_assembly_pools.json']+(['imu_upper_assembly_pools.json'] if UPPER else [])+(['imu_axial_pair_assembly_pools.json'] if AXIAL else [])
datasets=[json.loads((root/n).read_text()) for n in names]
for d in datasets:
    assert d['status']=='PASS'
    assert 'Nearest-face-normal sign is not used' in d['method']
    assert d['source_blend_sha256']==datasets[0]['source_blend_sha256']
    assert d['source_six_wire_sha256']==datasets[0]['source_six_wire_sha256']
pools={p:[] for p in map(str,range(1,9))}
for name,d in zip(names,datasets):
    for p,rows in d['pools'].items():
        for i,row in enumerate(rows):
            pools[p].append(dict(row,screened_source=dict(file=name,index=i)))
out=dict(status='PASS',scope='Eight-pin individual assembly-screened curve pool; simultaneous selection pending',
    source_blend_sha256=datasets[0]['source_blend_sha256'],
    source_six_wire_sha256=datasets[0]['source_six_wire_sha256'],
    sources={n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in names},
    pools=pools,main_modified=False,extra_print_holes=False)
(root/('imu_axial_complete_assembly_pools.json' if AXIAL else 'imu_dual_terminal_assembly_pools.json' if UPPER else 'imu_targeted_assembly_pools.json')).write_text(json.dumps(out,indent=2)+'\n')
print('TARGETED_POOL_MERGED',{p:len(r) for p,r in pools.items()})
