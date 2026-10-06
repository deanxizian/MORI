"""Record the adopted service requirements after the verified geometry build.

This is a documentation receipt; the original build input hash is preserved.
No dimensions consumed by construction phases or any hardware source change.
"""
from pathlib import Path
import json,hashlib,datetime
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=ROOT/'contracts/mechanical_interfaces.json';before=json.loads(p.read_text());oldhash=sha(p)
build=json.loads((ROOT/'mechanical/reports/build_manifest.json').read_text())
assert oldhash==build['input_sha256']['contracts/mechanical_interfaces.json']
after=json.loads(json.dumps(before))
for key in ['revision','mechanical_revision','current_geometry_revision']:after[key]='V1.2-M1.51'
after['current_authority']['scope']='M1.51: adopted two-piece front/rear body shells with bottom access and integral lower locating keys; original four frame axes unchanged. Other geometry is unchanged from M1.50. Full wired assembly remains BLOCKED.'
after['service']['prerequisites']=['DISARM and reliable external support; final power-cut method remains hardware-owned and pending','Support shell accessories and disconnect their leads as required; complete flexible-wire path remains BLOCKED','Remove four frame screws through bottom tool ports; withdraw front shell +Y and rear shell -Y; nominal rigid paths allow wheels to remain','Unplug battery, release two short tray retention screws and pull tray +Y']
after['body_front_rear_split']={'configuration':'config/geometry.json#/body_front_rear_split','adoption':'User accepted the front/rear split recommendation on its review page','current_printed_ids':['Body_Front','Body_Rear'],'retired_printed_ids':['Body_Upper','Body_Lower'],'retired_fasteners':['Shell_Screw_0..3','Shell_Insert_0..3'],'retained_interfaces':'All four Frame_Screw/Frame_Insert axes, speaker/rear-board native poses and seats','current_evidence':'mechanical/reports/body_split_validation.json','locators':'Two integral bottom keys; trial PA12 clearances; geometry checks do not qualify fit or strength','full_wired_assembly':'BLOCKED','physical_fit':'NOT_TESTED'}
allowed=['revision','mechanical_revision','current_geometry_revision','current_authority.scope','service.prerequisites','body_front_rear_split']
# Undo exactly the listed documentary edits and compare all remaining fields.
undo=json.loads(json.dumps(after))
for key in ['revision','mechanical_revision','current_geometry_revision']:undo[key]=before[key]
undo['current_authority']['scope']=before['current_authority']['scope'];undo['service']['prerequisites']=before['service']['prerequisites'];undo.pop('body_front_rear_split')
assert undo==before
source=sha(ROOT/'mechanical/mori_v1_2.blend')
p.write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n')
receipt=dict(status='PASS',kind='POST_BUILD_DOCUMENTATION_ONLY',source_blend_sha256=source,
 before_sha256=oldhash,after_sha256=sha(p),allowed_changed_fields=allowed,
 before_snapshot='mechanical/revisions/V1.2-M1.50_before_body_split/contracts/mechanical_interfaces.json',
 untouched_dimension_and_component_fields=True,build_input_hash_preserved=True,
 utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
assert sha(ROOT/'mechanical/mori_v1_2.blend')==source
(OUT/'contract_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n')
