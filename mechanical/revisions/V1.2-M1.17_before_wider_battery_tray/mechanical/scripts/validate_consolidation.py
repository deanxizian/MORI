"""Checks for genuine physical consolidation, not object-count cosmetics."""
from common import *

def validate_consolidation(solids,check):
    if not P.get('part_consolidation',{}).get('enabled'):return
    data=json.loads((ROOT/'reports/part_consolidation.json').read_text())
    rows=[]
    for row in data['changed_prints']:
        a=solids[row['id']];pieces=a.m.decompose()
        rows.append({'id':a.name,'motion_group':a.group,'positive_solids':sum(m.volume()>.01 for m in pieces),'cavity_components':sum(m.volume()<-.01 for m in pieces),'volume_mm3':a.m.volume()})
    ids=set(solids);retired=data['retired_ids']
    printed=[n for n,a in solids.items() if a.o.get('category')=='PRINTABLE' and a.o.get('export_candidate')]
    ok=not (ids&set(retired)) and len(printed)==P['part_consolidation']['target_robot_print_count']
    ok=ok and all(r['positive_solids']==1 and r['cavity_components']==0 for r in rows)
    ok=ok and solids['Pitch_Yoke'].group=='yaw' and all(solids[n].group=='body' for n in ['Yaw_Base','Yaw_Reaction_Link'])
    data['status']='PASS' if ok else 'FAIL';data['current_robot_print_ids']=sorted(printed);data['physical_components']=rows
    data['scope']='Connected solid meshes, object inventory and correct rigid motion groups only; service paths, FOV and motion have separate checks. No print/strength qualification.'
    save_json(ROOT/'reports/part_consolidation.json',data)
    check('physical_part_consolidation','PASS' if ok else 'FAIL','本体打印件最终数量与合并实体检查；保留固定/转动分组',{'print_before':data['robot_print_before'],'print_after':len(printed),'fasteners_before':data['fasteners_before'],'fasteners_after':data['fasteners_after'],'parts':rows},data['scope'])
