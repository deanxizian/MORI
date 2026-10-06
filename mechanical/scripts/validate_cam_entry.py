"""Require the current saved-model differential audit for the two CAM entries."""
import hashlib,json
from pathlib import Path
from common import PROJECT,ROOT,P,bpy

def validate_cam_entry(check):
    q=P.get('waveshare_detail',{}).get('entry_correction',{})
    if not q.get('enabled'):return
    folder=ROOT/'studies/prearrival_finish/cam_entry_adoption'
    row=json.loads((folder/'check.json').read_text())
    sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    source=sha(Path(bpy.data.filepath))
    ok=(row['status']=='PASS' and row['sources']['mechanical/mori_v1_2.blend']==source
        and row['sources']['config/geometry.json']==sha(PROJECT/'config/geometry.json')
        and row['script_sha256']==sha(folder/'check.py')
        and row['changed_native_parts']==['CAM_Mainboard'] and row['unchanged_native_parts']==208
        and len(row['unchanged_CAM_components'])==130 and len(row['poses'])==130
        and len(row['sibling_checks'])==262 and not row['failures']
        and row['candidate_faces_equal'] and row['candidate_max_coordinate_error_mm']<2e-5)
    ok=ok and all(sha(PROJECT/n)==h for n,h in row['production_inputs'].items())
    ok=ok and all(sha(PROJECT/n)==h for n,h in row['independent_candidate'].items())
    check('cam_entry_exact_scope','PASS' if ok else 'FAIL',
        'CAM两处照片入口修正：208件其他实体及130组板内元件保持，候选与新增材料检查通过',
        {'report':str((folder/'check.json').relative_to(ROOT)), 'source_current':ok},
        'Saved mesh differential, independent candidate equality and 130 current poses; no real mating qualification.')
    check('cam_entry_actual_mating','BLOCKED','CAM排线真实插深、触点面、补强片与版本未确认',q['limitations'])
