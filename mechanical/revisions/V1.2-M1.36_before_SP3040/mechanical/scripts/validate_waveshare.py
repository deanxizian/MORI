"""Evidence, unchanged structure, per-component units and actual-solid fit."""
from common import *
from validate_head_cleanup import geometry_record
import hashlib

def validate_waveshare(solids,Solid,iv,check):
    w=P.get('waveshare_detail',{})
    if not w.get('enabled'):return
    base=json.loads((PROJECT/w['baseline_geometry']).read_text());now={o.name.removeprefix(PREFIX):geometry_record(o) for o in parts()}
    changed=sorted(n for n in now if now[n]!=base['parts'].get(n));retired=sorted(set(base['parts'])-set(now));allow=set(w['changed_existing_ids']+w.get('approved_mount_change_ids',[]))
    later=P.get('head_mount_simplification',{}).get('changed_existing_ids',[]) if P.get('head_mount_simplification',{}).get('enabled') else []
    allow.update(later);unexpected=sorted(set(changed)-allow)
    a=P.get('assembly_completion',{})
    if a.get('enabled'):allow.update(a['changed_existing_ids']+a['new_ids'])
    allow.update(declared_cap_edge_changes())
    unexpected=sorted(set(changed)-allow)
    source=json.loads((PROJECT/w['source_manifest']).read_text());sources=[{'file':r['file'],'matches_sha256':hashlib.sha256((PROJECT/r['file']).read_bytes()).hexdigest()==r['sha256']} for r in source['sources']]
    cam=solids['CAM_Mainboard'].o;refs=json.loads(cam['component_reference_index']);pcb=next(r for r in refs if r['reference']=='PCB');v=np.array([tuple(vertices_world(cam)[i]) for i in range(*pcb['vertices'])]);size=np.ptp(v,axis=0)
    # Source board is deliberately not tilted with optics: X/Z outline37mm.
    correct_outline=max(abs(size-np.array([37,w['cam']['pcb_thickness_mm'],37])))<.002
    lcd_unchanged=now['Display_PCB']==base['parts']['Display_PCB']
    hits=[]
    names=w['changed_existing_ids']
    for i,n in enumerate(names):
        for other,b in solids.items():
            if other==n or other in names[:i]:continue
            vol=iv(solids[n],b)
            if vol>.02:hits.append({'part':n,'obstacle':other,'volume_mm3':vol})
    scope={'baseline':base['revision'],'changed':changed,'unexpected_changes':unexpected,'removed':retired,'LCD_original_mesh_unchanged':lcd_unchanged,'PCB_outline_measured_from_mesh_mm':size.tolist(),'component_groups':len(refs),'source_checks':sources,'printed_changes_authorized':w.get('approved_mount_change_ids',[])}
    scope['later_print_changes_checked_separately']={'ids':later,'report':'simple_head_mounts_validation.json'}
    ok=not unexpected and not retired and lcd_unchanged and correct_outline and all(s['matches_sha256'] for s in sources)
    check('waveshare_source_and_scope','PASS' if ok else 'FAIL','微雪原厂LCD几何保持；CAM按官方板框与照片重建，修改范围和来源可追溯',scope,'Per-part complete world/local mesh hashes vsM1.32; actual PCB vertex bounds and input SHA256. Photo dimensions are assumptions, not metrology.')
    check('waveshare_nominal_fit','PASS' if not hits else 'FAIL','微雪新建器件与现有总装实体的名义穿插检查',{'intersections':hits,'threshold_mm3':.02},'AABB broadphase plus actual closed triangle-solid intersections including containment. Photo uncertainty is not a qualified tolerance.')
    check('waveshare_as_built_and_flex','NOT_TESTED','微雪实物厚度、孔径、接插件版本及相机FPC到货复核；走线延后',w['arrival_measurements'])
    r={'revision':P['revision'],'source_scope_status':'PASS' if ok else 'FAIL','nominal_fit':'PASS' if not hits else 'FAIL','scope':scope,'intersections':hits,'physical_fit':'NOT_TESTED','wiring':'DEFERRED','manufacturing_release':False};save_json(ROOT/'reports/waveshare_validation.json',r)
