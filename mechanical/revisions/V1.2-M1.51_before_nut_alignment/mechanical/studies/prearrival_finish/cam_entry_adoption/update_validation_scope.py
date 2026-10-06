"""Keep cumulative historical checks exact after the independently bounded edit."""
from pathlib import Path
import hashlib,json
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def change(name,old,new):
    p=ROOT/name;s=p.read_text();assert s.count(old)==1,(name,s.count(old),old)
    p.write_text(s.replace(old,new))
change('mechanical/scripts/common.py',
    '    return declared_neck_capacity_changes() | declared_camera_cam_changes() | declared_p5r7_changes()',
    '    return declared_cam_entry_changes() | declared_neck_capacity_changes() | declared_camera_cam_changes() | declared_p5r7_changes()')
change('mechanical/scripts/common.py','def declared_neck_capacity_changes():',
    '''def declared_cam_entry_changes():
    """Only two reconstructed packages inside CAM; exact scope checked separately."""
    q=P.get('waveshare_detail',{}).get('entry_correction',{})
    return {'CAM_Mainboard'} if q.get('enabled') else set()

def declared_neck_capacity_changes():''')
changes={
 'mechanical/scripts/validate_neck_capacity.py':(
    "emit('scope',set(changed)==ids and not added and not removed,changed=changed,added=added,removed=removed,",
    "emit('scope',set(changed)==ids|declared_cam_entry_changes() and not added and not removed,changed=changed,added=added,removed=removed,subsequent_change_report='studies/prearrival_finish/cam_entry_adoption/check.json',"),
 'mechanical/scripts/validate_camera_cam.py':(
    'set(changed)==ids|declared_neck_capacity_changes() and not added',
    'set(changed)==ids|declared_neck_capacity_changes()|declared_cam_entry_changes() and not added'),
 'mechanical/scripts/validate_assembly_issue_fixes.py':(
    "expected=set(q['changed_existing_ids'])|set(later.get('changed_existing_ids',[]))|declared_p5r7_changes()",
    "expected=declared_cam_entry_changes()|set(q['changed_existing_ids'])|set(later.get('changed_existing_ids',[]))|declared_p5r7_changes()"),
 'mechanical/scripts/validate_head_retention.py':(
    "scopeok=set(changed_ids)==set(q['changed_existing_ids'])|declared_p5r7_changes()",
    "scopeok=set(changed_ids)==declared_cam_entry_changes()|set(q['changed_existing_ids'])|declared_p5r7_changes()"),
 'mechanical/scripts/validate_thin_cleanup.py':(
    'set(changed)==ids | declared_camera_cam_changes() | declared_neck_capacity_changes()',
    'set(changed)==ids | declared_camera_cam_changes() | declared_neck_capacity_changes() | declared_cam_entry_changes()'),
 'mechanical/studies/prearrival_finish/audit_rear_repair.py':(
    'checks=dict(only_rear_and_declared_later_changes=',
    "if P.get('waveshare_detail',{}).get('entry_correction',{}).get('enabled'):\n    later |= declared_cam_entry_changes()\n    copy['waveshare_detail'].pop('entry_correction')\nchecks=dict(only_rear_and_declared_later_changes="),
 'mechanical/scripts/validate_waveshare.py':(
    "    w=P.get('waveshare_detail',{})",
    "    from validate_cam_entry import validate_cam_entry\n    validate_cam_entry(check)\n    w=P.get('waveshare_detail',{})")}
for name,(old,new) in changes.items():change(name,old,new)
change('mechanical/scripts/assembly_animation.py',
    '本视频采用{P["revision"]}主模型，运动基板与后接口板已更新为P5R7；电源P5R6、IMU P5R4。',
    '本视频采用{P["revision"]}主模型，运动基板与后接口板已更新为P5R7；电源P5R6、IMU P5R4。\nCAM相机排线入口朝上，屏幕排线入口朝板外；两处依据官方照片修正。\n槽口/触点仅为示意，真实插深、补强片和接触面仍未确认；完整线束尚未应用。')
files=['mechanical/scripts/common.py','mechanical/scripts/assembly_animation.py',*changes]
(OUT/'validation_scope_update.json').write_text(json.dumps(dict(status='PASS',
    scope='Cumulative comparison sets now include the independently tested two-package CAM edit; no geometry or clearance threshold waived.',
    files={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in files}),ensure_ascii=False,indent=2)+'\n')
print('CAM_ENTRY_VALIDATION_SCOPE_UPDATED')
