"""Record and apply the two explicit camera/CAM approvals. No hardware writes."""
import datetime, hashlib, json, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
M = ROOT / 'mechanical'
OUT = M / 'studies/prearrival_finish/camera_cam_adoption'
BASE = M / 'revisions/V1.2-M1.47_before_camera_CAM_approval'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()

g = json.loads((ROOT/'config/geometry.json').read_text())
assert g['revision'] == 'V1.2-M1.47', 'One-shot migration; inspect before reapplying.'
assert sha(M/'mori_v1_2.blend') == 'bcaa5736a8cdf43441a6a83a6cb69606546cc01d2c0d28d98f4c09383e07368f'
assert not BASE.exists()
OUT.mkdir(parents=True, exist_ok=True)
# Keep only the immutable comparison inputs needed by later geometry audits.
for rel in ['config/geometry.json', 'contracts/mechanical_interfaces.json',
            'mechanical/mori_v1_2.blend']:
    dst=BASE/rel; dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT/rel, dst)
native={str(p.relative_to(ROOT)):sha(p) for p in (ROOT/'hardware').rglob('*')
        if p.is_file() and p.suffix in ['.kicad_pcb','.kicad_sch','.kicad_pro']}
native['contracts/components.json']=sha(ROOT/'contracts/components.json')
record={'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'baseline_blend_sha256':sha(M/'mori_v1_2.blend'), 'protected_hardware':native,
        'approval_question_call':'call_TNngTkyHJFKcqFaa008Gmtb8',
        'answers':['采用该局部修正（推荐）','改用内六角螺钉（推荐）']}
(OUT/'approval.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
g['revision']='V1.2-M1.48'
q={
    'enabled':True, 'revision':g['revision'], 'approved':True,
    'changed_existing_ids':['Display_Frame']+[f'CAM_Mount_Screw_{i}' for i in range(4)],
    'baseline_blend':str((BASE/'mechanical/mori_v1_2.blend').relative_to(ROOT)),
    'approval_record':str((OUT/'approval.json').relative_to(ROOT)),
    'camera':{'outside_top_trim_mm':0.6, 'minimum_nominal_top_wall_mm':1.2,
              'minimum_nominal_shell_gap_mm':0.3,
              'approved_mesh':'mechanical/studies/prearrival_finish/camera_top_clearance/Display_Frame.npz',
              'historical_verification':'mechanical/studies/prearrival_finish/camera_top_clearance/verification.json'},
    'cam_screws':{'ids':[f'CAM_Mount_Screw_{i}' for i in range(4)],
        'specification':'DIN 912 / ISO 4762 M2x5 socket cap',
        'catalogue_reference':'Bossard BN610 1420569, A2',
        'diameter_mm':2.0, 'length_mm':5.0, 'head_diameter_mm':3.8,
        'head_height_mm':2.0, 'socket_AF_mm':1.5, 'socket_depth_mm':1.0,
        'thread_pitch_mm':0.4,
        'source_receipt':'mechanical/studies/prearrival_finish/harness_A8/cam_socket_tool/sources/receipt.json',
        'approved_mesh_directory':'mechanical/studies/prearrival_finish/harness_A8/cam_socket_tool',
        'historical_verification':'mechanical/studies/prearrival_finish/harness_A8/cam_socket_tool/verification.json',
        'tool':{'manufacturer':'Wera','model':'950 PKLS','sku':'05022040001',
                'hex_AF_mm':1.5,'long_leg_mm':90.0,'short_leg_mm':4.5},
        'geometry_note':'Nominal catalogue outer dimensions; thread helix omitted. Socket depth and tool bend envelope assumed; physical engagement NOT_TESTED.'},
    'limits':['Only approved outside camera-pocket top removal and four screw replacements.',
              'Camera, inner capture surfaces, PCB, holes, inserts and all other parts retain datums.',
              'No harness-channel candidate, wire anchors, new electrical source or other structure adopted.',
              'Nominal geometry only; PA12 wall strength, tolerances and physical tool access NOT_TESTED.']}
g['camera_cam_completion']=q
(ROOT/'config/geometry.json').write_text(json.dumps(g,ensure_ascii=False,indent=2)+'\n')
c=json.loads((ROOT/'contracts/mechanical_interfaces.json').read_text())
for k in ['revision','mechanical_revision','current_geometry_revision']:c[k]=g['revision']
c['camera_cam_completion']={'enabled':True,'revision':g['revision'],
    'geometry_source':'config/geometry.json#/camera_cam_completion',
    'changed_existing_ids':q['changed_existing_ids'],
    'approval_record':q['approval_record'],'manufacturing_release':False}
c['current_authority']['scope']='M1.48: two approved camera/CAM fixes only; 0.6mm continuous upper pocket trim and four DIN912 M2x5 screws. Remaining design/data gaps remain tracked separately.'
(ROOT/'contracts/mechanical_interfaces.json').write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n')
with (ROOT/'AGENTS.md').open('a') as f:
    f.write('\n- M1.48 user explicitly approves lowering the camera pocket outside upper edge by0.6mm (nominal top wall1.8→1.2mm) and four CAM mounting screws changed to DIN912/ISO4762 M2×5 socket cap, headØ3.8×2mm. Keep camera/capture surfaces, front shell, hole axes, inserts and screw length; no extra prints, steps or holes. Use the approved camera_top_clearance and cam_socket_tool candidates for independent comparison, short1.5mm Wera950PKLS tooling, and current-main motion/access checks. Only Display_Frame and CAM_Mount_Screw_0..3 may change. No harness routes/channels, electrical candidates or other geometry adopted with this change. Physical fits and PA12 strength remain NOT_TESTED.\n')
print('M1_48_CONFIG_APPLIED',len(native),'protected hardware files')
