"""Explicit independent native placement trial; preserve source and fixed parts."""
from R184_power_group_geometry import *
rev='R184A';out=b/(rev+'-plan.json');assert not out.exists()
selection=json.loads((b/'R184-power-group-pairs.json').read_text())['solutions'][0]
delete=retired-{'a64ead90-f8fb-47e5-9d8d-700e6f43096f','8e35b6ed-a6d6-434a-9abd-edb9e740bbac','953e253f-2ff4-45f0-b26c-bc55efacd3e2'}
snap={u:dict(net=c.by_id[u].GetNetname(),layer=c.board.GetLayerName(c.by_id[u].GetLayer()),width_mm=c.by_id[u].GetWidth()/1e6,start_mm=list(xy(c.by_id[u].GetStart())),end_mm=list(xy(c.by_id[u].GetEnd()))) for u in sorted(delete)}
trans=[]
for ref in ['D1602','C1602','R1601']:
    f=footprints[ref];row=selection[ref];old=xy(f.GetPosition())
    spec=dict(reference=ref,from_mm=list(old),delta_mm=[row['position_mm'][i]-old[i] for i in range(2)],rotation_deg=row['rotation_deg'])
    if any(k['name'].startswith('BODY_'+ref+'_') and '_VIA_' in k['name'] for k in c.keepouts):
        spec.update(reconstruct_fixed_via_guards=True,rotate_fixed_via_guards=True,repartition_fixed_via_guards=True)
    trans.append(spec)
via_specs=[]
for u in sorted(released_vias):
    v=c.by_id[u];contacts=via_contact_layers(c.board,v,delete)
    spec=dict(uuid=u,source_expected=via_snapshot(c.board,v),remaining_contact_layers=contacts,
              reason='The explicitly removed terminal branches are being rebuilt for the coordinated clamp/charge-pump group. No ground via is removed; full original connectivity and all power checks remain mandatory before adoption.')
    check=obsolete_via_removal_check(c.board,v,spec,delete)
    assert check['allowed'],(u,check)
    via_specs.append(spec)
rc1=selection['R1601']['pads']['2']['position_mm']
rc2=list(xy(pads['C1603.1'].GetPosition()))
assert math.dist(rc1,[41.125,18.825])<1e-7
rc1=[round(x,6) for x in rc1]
routes=[dict(net='Net-(C1603-~-Pad1)',layer='B.Cu',width_mm=.2,points_mm=[rc1,[41.125,18.925],rc2])]
plan=dict(revision=rev,board_sha256=c.sha,scope='Unadopted native group placement after explicitly releasing the UPS 5 V bridge. D301 and C1603 remain fixed, including the original C1603 ground return. Three non-ground terminal vias are explicitly retired. All displaced circuits, original UPS 5 V continuity/width and reference ground must be restored before acceptance.',
          delete_copper=sorted(delete),deleted_copper_expected=snap,translations=trans,remove_obsolete_vias=via_specs,routes=routes,vias=[],activate_pth_layers=[])
out.write_text(json.dumps(plan,indent=2)+'\n')
(b/'R184A-selection.json').write_text(json.dumps(dict(source_sha256=c.sha,selected=selection,source='R184-power-group-pairs.json',selection_index=0,adopted=False),indent=2)+'\n')
print(json.dumps(dict(revision=rev,deleted_tracks=len(delete),retired_non_ground_vias=len(via_specs),translations=trans)),flush=True)
