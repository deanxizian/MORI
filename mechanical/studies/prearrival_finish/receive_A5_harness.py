# -*- coding: utf-8 -*-
"""Read-only mechanical receipt of A5 supplier and wiring evidence."""
from pathlib import Path
import hashlib,json,datetime,sys
import bpy
HERE=Path(__file__).resolve().parent;PROJECT=HERE.parents[2]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
hpath=PROJECT/'hardware/v1_2/handoff/mechanical_P5R7_prearrival_A5_harness.json'
assert sha(hpath)=='fe9f1610b558665a1575ef24bfea5f309d2f8b052e894f1ef7a8e49ab0f8d5d8'
h=read(hpath);main=PROJECT/'mechanical/mori_v1_2.blend';mainsha=sha(main)
assert Path(bpy.data.filepath)==main and mainsha==h['base_mechanical_blend_sha256']
for path,digest in h['artifact_hashes'].items():assert sha(PROJECT/path)==digest,path
folder=PROJECT/'hardware/v1_2/harness_evidence_20261002';sources=[];unavailable=[]
for name in ['sources_manifest.json','additional_sources_manifest.json']:
    for r in read(folder/name):
        if r['status']!='PASS':unavailable.append(dict(name=r['name'],status=r['status']));continue
        p=folder/'sources'/r['name'];assert sha(p)==r['sha256'],r['name']
        sources.append(dict(file=str(p.relative_to(PROJECT)),sha256=r['sha256'],url=r['source_url']))
for filename,key in [('fourteen_validation.json','received_static_report_sha256'),('fourteen_body_sequence.json','received_body_sequence_sha256')]:
    assert sha(HERE/'harness_A2'/filename)==h[key]
static=read(HERE/'harness_A2/fourteen_validation.json');body=read(HERE/'harness_A2/fourteen_body_sequence.json')
assert static['status']=='PASS' and body['status']=='FAIL' and body['position_samples']==407
formal_manifest=PROJECT/'hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json'
formal=read(formal_manifest)
for p,d in formal.items():assert sha(PROJECT/p)==d,p
assert len(formal)==h['formal_source_files_verified_unchanged']==249
own=read(HERE/'harness_A2/ecowire_sources.json');wirechecks=[]
for r in own['products']:
    k=r['part_number'];v=h['wire_catalogue_range_checks'][k]
    assert r['AWG']==v['awg']
    assert abs(r['insulation_OD_min_mm']-v['od_min_mm'])<1e-10 and abs(r['insulation_OD_max_mm']-v['od_max_mm'])<1e-10
    assert 24<=v['awg']<=30 and .8<=v['od_min_mm']<=v['od_max_mm']<=1.5
    wirechecks.append(dict(part=k,status='PASS',scope='AWG and full OD catalogue window only',crimp_qualification='NOT_TESTED'))
groups=[]
for n in ['CAM_Mainboard','Display_PCB','Camera_PCB']:
    found=[o for o in bpy.data.objects if o.name.endswith(n)]
    assert len(found)==1,(n,[o.name for o in found])
    o=found[0];assert o.get('group')=='pitch',(n,o.get('group'))
    groups.append(dict(object=o.name,group=o['group'],matrix_world=[list(r) for r in o.matrix_world]))
out=dict(verified_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),status='PASS',
    scope='A5 evidence integrity, wire catalogue input consistency and saved-scene group check only',
    handoff=str(hpath.relative_to(PROJECT)),handoff_sha256=sha(hpath),main_sha256=mainsha,
    hardware_artifacts_checked=len(h['artifact_hashes']),sources=sources,unavailable_source_requests=unavailable,
    formal_source_files_verified=len(formal),wire_catalogue_checks=wirechecks,
    received_static_status=static['status'],received_body_assembly_status=body['status'],
    saved_optical_groups=groups,FFC_motion_requirement='Static only if both ends AND all supports remain on pitch group',
    FFC_documented=h['vendor_cable_evidence']['LCD35079_FFC']['supplied_spec'],
    SCS0009_numbering_conflict='BLOCKED pending supplier view/port clarification',
    J10_actual_exit_Z_mm=None,selected_wire=None,main_geometry_changed=False,manufacturing_release=False,
    limits=['Receipt does not validate prices/stock, crimp quality, undisclosed dimensions or physical assembly.',
        'No supplier contacted, no order, no wire cutting diagram and no electrical pin remapping.',
        'Fourteen static geometry PASS does not supersede407-position body assembly FAIL.',
        'No FFC thickness/width/bend radius is inferred from pitch or photographs; static routing itself is still pending.'])
(HERE/'hardware_A5_harness_receipt.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert sha(main)==mainsha
print('A5_RECEIPT',out['status'],'artifacts',out['hardware_artifacts_checked'],'sources',len(sources),'formal',len(formal),'pitch group',len(groups),flush=True)
