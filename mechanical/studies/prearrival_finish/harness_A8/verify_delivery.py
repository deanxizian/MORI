"""Verify source preservation, report links and candidate result consistency."""
from pathlib import Path
from datetime import datetime,timezone
from html.parser import HTMLParser
from urllib.parse import urlparse,unquote
from urllib.request import urlopen
import json,hashlib,platform
HERE=Path(__file__).resolve().parent;PARENT=HERE.parent;ROOT=HERE.parents[3]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((HERE/'receipt.json').read_text())
for path,digest in receipt['sources'].items():assert sha(ROOT/path)==digest,path
source=json.loads((HERE/'central_uart_source_check.json').read_text())
curves=json.loads((HERE/'central_uart_curves.json').read_text())
ends=json.loads((HERE/'central_exit_check.json').read_text())
assert source['status']=='PASS' and ends['status']=='BLOCKED'
assert source['physical_source_objects']==209 and source['wire_pose_instances']==520
assert source['source_curve_sha256']==sha(HERE/'central_uart_curves.json')
assert source['source_readonly_helper_sha256']==sha(PARENT/'head_harness/check_loop_source_solids.py')
assert not source['source_solid_hits'] and not source['fourteen_fixed_wire_hits']
assert len(source['interwire_checks'])==78 and all(x['status']=='PASS' for x in source['interwire_checks'])
assert max(abs(p['each_centreline_length_mm']-33.2) for p in curves['selected']['poses'])<1e-9
assert all(r['clear_continuation_mm']==(2 if r['end']=='body' else 6) for r in ends['results'])
assert {r['first_clearance_bound_failure']['object'] for r in ends['results']}=={'Yaw_Base','Yaw_Reaction_Link'}
assert sha(ROOT/'mechanical/mori_v1_2.blend')==source['source_blend_sha256']

unions=json.loads((HERE/'central_route_unions.json').read_text())
radial=json.loads((HERE/'radial_endpoint_openings.json').read_text())
body=json.loads((HERE/'central_body_escape_graph.json').read_text())
yaw=json.loads((HERE/'central_yaw_escape_graph.json').read_text())
assert unions['status']=='PASS' and not unions['main_geometry_changed']
assert unions['source_blend_sha256']==source['source_blend_sha256']
assert len(radial['results'])==108 and all(x['status']=='BLOCKED' for x in radial['results'])
for result,frame in [(body,'body'),(yaw,'yaw')]:
    mesh=next(x for x in unions['frames'] if x['frame']==frame)
    assert sha(HERE/mesh['mesh'])==mesh['sha256']==result['source_mesh_sha256']
    assert result['source_blend_sha256']==source['source_blend_sha256']
    assert sha(HERE/result['reachable_nodes_file'])==result['reachable_nodes_sha256']
    assert result['finite_pose_obstacles_included'] and result['continuous_motion']=='NOT_TESTED'
    assert result['minimum_bend']=='NOT_TESTED' and not result['main_geometry_changed']
assert body['status']=='BLOCKED' and not body['path_mm']
assert body['reachable_with_wire_radius_and_project_gap']['node_count']==3448
assert yaw['status']=='PASS' and len(yaw['path_mm'])==101
assert yaw['widest_grid_path_clearance_bound_mm']>=yaw['required_centreline_clearance_mm']
assert (HERE/'endpoint_review.png').is_file() and (HERE/'ENTRY_REVIEW.md').is_file()
guides=json.loads((HERE/'crimp_guide_sources.json').read_text())
for name in ['JST_SPH004_crimp.pdf','JST_SSH003_crimp.pdf']:
    assert guides['sources'][name]['content_review']=='PASS'
    assert sha(HERE/'sources'/name)==guides['sources'][name]['sha256']
    assert (HERE/'sources'/name).read_bytes().startswith(b'%PDF-')
    assert (HERE/name.replace('.pdf','.png')).is_file()
assert guides['sources']['JST_SHD_series.html']['content_review']=='BLOCKED'
assert guides['failed_requests']['JST_official_global_contact.html']['status']=='BLOCKED'

# Additional lookup evidence is explicitly unversioned, manufacturer-hosted
# reference data. Preserve its successful files and failed production requests.
lookup=json.loads((HERE/'tooling_lookup_sources.json').read_text())
for row in lookup:
    if 'file' in row:
        assert sha(HERE/row['file'])==row['sha256'],row['file']
for part in ['SPH-004T-P0.5S','SSH-003T-P0.2-H']:
    response=json.loads((HERE/'sources'/f'JST_tooling_{part}.json').read_text())
    assert response['title']==part and response['tool_name']==part
    assert {response[f'awg{i}'] for i in range(1,4)}=={'28','30','32'}
page=(HERE/'sources/JST_application_tooling_index.html').read_text()
assert all(s in page for s in ['Strip Length (mm)','Crimp Height (mm)','Tensile Spec (N)'])
faq=(HERE/'sources/JST_FAQ_SH_H.html').read_text()
assert 'Both contacts share the same application crimp tooling' in faq
assert (HERE/'TOOLING_DETAILS.md').is_file()

# J1 is a joined local route, not an approved harness. Check its useful PASS
# results and its failed insertion attempts without collapsing the two scopes.
joined=json.loads((HERE/'joined_entry_screen.json').read_text())
candidate=json.loads((HERE/'joined_entry_candidate/screening.json').read_text())
spacing=json.loads((HERE/'joined_wire_spacing.json').read_text())
entry=json.loads((HERE/'joined_entry_candidate/terminal_entry.json').read_text())
assert joined['source_blend_sha256']==candidate['source_blend_sha256']==source['source_blend_sha256']
assert joined['source_obstacle_ids']==['Pitch_Yoke','Yaw_Base'] and not joined['fixed_wire_hits']
assert candidate['status']=='PASS' and spacing['status']=='PASS' and entry['status']=='BLOCKED'
assert candidate['source_route_sha256']==spacing['source_route_sha256']==sha(HERE/'joined_entry_screen.json')
assert candidate['candidate_blend_sha256']==entry['source_candidate_sha256']==sha(HERE/'joined_entry_candidate/candidate.blend')
assert candidate['changed_existing_ids']==['Pitch_Yoke','Yaw_Base'] and candidate['unchanged_physical_count']==207
assert not candidate['source_hits'] and not candidate['fourteen_fixed_wire_hits']
assert candidate['head_pose_count']==130 and candidate['wire_pose_instances']==520
assert all(len(row['remaining_components_mm3'])==1 for row in candidate['part_results'].values())
assert len(spacing['interwire_checks'])==78 and len(spacing['self_checks'])==13
assert spacing['minimum_interwire_surface_bound_mm']>=.3 and spacing['minimum_sampled_self_surface_bound_mm']>=.3
assert spacing['minimum_bend_mm']>=joined['required_bend_screen_mm'] and spacing['staging_length_spread_mm']<1e-9
assert len(entry['cases'])==16 and all(row['status']=='FAIL' for row in entry['cases'])
assert entry['source_pdf_sha256']==sha(ROOT/entry['source_pdf'])
assert not candidate['main_model_applied'] and candidate['whole_harness']=='BLOCKED'
for data,script in [(joined,'check_joined_entry.py'),(candidate,'build_joined_entry_candidate.py'),
                    (spacing,'check_joined_wire_spacing.py'),(entry,'check_terminal_entry.py')]:
    assert data['source_script_sha256']==sha(HERE/script),script

# Preserve J2's original limited PASS and its later failed full-mating audit.
# The cleaned copy must additionally pass raw Blender topology after reload.
read=lambda p:json.loads(p.read_text())
transit=read(HERE/'terminal_threading/transit_screen.json')
j2=read(HERE/'terminal_threading/candidate_screen.json')
storage=read(HERE/'terminal_threading/cleaned/storage_rebuild.json')
raw_audit=read(HERE/'terminal_threading/reloaded_mated_audit.json')
audit=read(HERE/'terminal_threading/cleaned/reloaded_mated_audit.json')
for data,script in [(transit,'plan_terminal_threading.py'),(j2,'build_threading_candidate.py'),
                    (storage,'rebuild_threading_storage.py'),(raw_audit,'verify_threading_candidate.py'),
                    (audit,'verify_threading_candidate.py')]:
    assert data['source_script_sha256']==sha(HERE/script),script
    assert data['source_blend_sha256']==source['source_blend_sha256']
assert sha(ROOT/transit['source_catalogue'])==transit['source_catalogue_sha256']
assert j2['source_transit_sha256']==sha(HERE/'terminal_threading/transit_screen.json')
assert j2['status']==storage['status']=='PASS'
assert j2['source_installed_route_sha256']==sha(HERE/'joined_entry_screen.json')
assert not j2['hardware_sweep_hits'] and not j2['fixed_wire_sweep_hits'] and not j2['installed_wire_hits']
assert j2['nominal_contact_to_source_gap_lower_bound_mm']>=.3
assert j2['unchanged_source_objects_excluding_two_prints']==207 and j2['head_motion_poses']==130
assert j2['changed_existing_ids']==storage['changed_existing_ids']==['Pitch_Yoke','Yaw_Base']
assert storage['source_helper_sha256']==sha(HERE/'repair_threading_storage.py')
assert j2['candidate_blend_sha256']==storage['source_candidate_sha256']==raw_audit['source_candidate_sha256']==sha(HERE/'terminal_threading/candidate.blend')
assert storage['candidate_blend_sha256']==audit['source_candidate_sha256']==sha(HERE/'terminal_threading/cleaned/candidate.blend')
assert any(r['status']=='FAIL' for r in raw_audit['raw_mesh_checks'])
assert all(r['status']=='PASS' and r['zero_area_faces']==0 and len(r['connected_vertex_counts'])==1 for r in audit['raw_mesh_checks'])
assert audit['cleaned_installed_source_check']['status']=='PASS' and not audit['cleaned_installed_source_check']['hits']
for data in [raw_audit,audit]:
    assert data['source_original_check_sha256']==sha(HERE/'terminal_threading/candidate_screen.json')
    assert data['source_mated_review_sha256']==sha(ROOT/'mechanical/studies/prearrival_preparation/mated_connector_review.json')
    assert data['status']=='BLOCKED' and data['mating_allocation_count']==29
    assert sum(r['status']=='BLOCKED' for r in data['installed_wire_vs_mates'])==39
    assert all(r['status']=='BLOCKED' for r in data['temporary_contact_sweep_vs_mates'])
    assert not data['main_geometry_changed'] and data['complete_harness']=='BLOCKED'
for filename,script in [('prefix_pools.json','plan_h06_body_leads.py'),('arc_prefix_pools.json','plan_h06_body_arcs.py'),
                        ('inner_arc_prefix_pools.json','plan_h06_body_arcs.py')]:
    d=read(HERE/'body_leads'/filename)
    assert d['status']=='BLOCKED' and d['source_script_sha256']==sha(HERE/script)
    assert d['source_J2_sha256']==sha(HERE/'terminal_threading/candidate_screen.json')
    assert d['source_ports_sha256']==sha(HERE/'h06_ports.json')
    assert d['source_fixed_wires_sha256']==sha(PARENT/'harness_A2/assembly_safe_review/fourteen_wire_solids.json')
    if 'source_helper_sha256' in d:assert d['source_helper_sha256']==sha(HERE/'plan_h06_body_leads.py')
    assert d['source_blend_sha256']==source['source_blend_sha256']
    assert not d['main_model_applied'] and not d['cut_lengths_released']

# Official AMASS archive, extracted PDFs and field-level derivation. Reading a
# drawing closes a source gap; it does not certify wire/solder/physical fit.
amass=HERE/'amass_mating'
for r in read(amass/'source_receipt.json'):
    assert r['http_status']==200 and sha(amass/r['file'])==r['sha256']
for r in read(amass/'archive_members.json'):
    assert sha(amass/r['file'])==r['sha256'] and (amass/r['file']).read_bytes().startswith(b'%PDF-')
d=read(amass/'received_dimensions.json')
assert d['status']=='PASS' and d['mating_pair']==['XT30UPB-M','XT30U-F']
assert d['above_board_seat_mm']['nominal']==17.1 and d['above_board_seat_mm']['independent_extremes']==[16.3,17.9]
assert not d['main_model_applied'] and d['full_harness']=='BLOCKED'
for mode in ['nominal','upper_with_thickness_allocation']:
    replay=read(amass/(mode+'_replay.json'))
    assert replay['source_blend_sha256']==source['source_blend_sha256']
    assert replay['source_script_sha256']==sha(HERE/'replay_amass_mating.py')
    assert replay['source_helper_sha256']==sha(amass/'envelopes.py')
    assert replay['source_dimensions_sha256']==sha(amass/'received_dimensions.json')
    assert replay['source_route_sha256']==sha(HERE/'joined_entry_screen.json')
    for i,digest in replay['source_contact_sweeps'].items():assert digest==sha(HERE/'terminal_threading'/f'terminal_sweep_{i}.npz')
    assert replay['mating_allocation_count']==29 and len(replay['replaced_clearance_envelopes'])==7
    assert len(replay['installed_wire_vs_mates'])==52 and len(replay['temporary_contact_sweep_vs_mates'])==4
    assert replay['status']==('PASS' if mode=='nominal' else 'BLOCKED')
    assert all(r['status']==replay['status'] for r in replay['installed_wire_vs_mates']+replay['temporary_contact_sweep_vs_mates'])
    assert not replay['main_model_applied'] and replay['whole_harness']=='BLOCKED'
newprefix=read(HERE/'body_leads/documented_mate_prefix_pools.json')
assert newprefix['status']=='BLOCKED' and newprefix['source_blend_sha256']==source['source_blend_sha256']
assert newprefix['source_script_sha256']==sha(HERE/'plan_h06_documented_mates.py')
for path,digest in newprefix['source_helpers'].items():assert sha(ROOT/path)==digest
assert newprefix['source_cleaned_J2_sha256']==sha(HERE/'terminal_threading/cleaned/candidate.blend')
assert newprefix['source_dimensions_sha256']==sha(amass/'received_dimensions.json')
assert all(r['exit_transition_hit'] is None for r in newprefix['trials'])
assert not newprefix['possible_individual_phase_assignments'] and not newprefix['main_model_applied']

# A later geometric path family solved the body-prefix routing. Keep earlier
# failed families above as history, and verify the wider new result separately.
bp=HERE/'body_prefix_v2'
bpdata={n:read(bp/(n+'.json')) for n in ['dubins_pools','packing','body_to_yaw_motion','other_loop_coexistence','preview_manifest','corridors']}
for name,script in [('dubins_pools','plan_body_dubins.py'),('packing','pack_body_prefix.py'),
                    ('body_to_yaw_motion','check_body_prefix_motion.py'),('other_loop_coexistence','check_prefix_other_loops.py'),
                    ('preview_manifest','render_body_prefix.py'),('corridors','inspect_body_prefix_space.py')]:
    record=bpdata[name]
    assert record['source_script_sha256']==sha(HERE/script),script
    assert record['source_blend_sha256']==source['source_blend_sha256']
    if 'source_helpers' in record:
        for path,digest in record['source_helpers'].items():assert sha(ROOT/path)==digest
    if 'source_helper_sha256' in record:assert record['source_helper_sha256']==sha(HERE/'plan_h06_documented_mates.py')
for name in ['dubins_pools','packing','body_to_yaw_motion','other_loop_coexistence','preview_manifest']:assert bpdata[name]['status']=='PASS'
bp_pack=bpdata['packing'];bp_motion=bpdata['body_to_yaw_motion'];bp_other=bpdata['other_loop_coexistence'];bp_preview=bpdata['preview_manifest']
assert bp_pack['source_pool_sha256']==sha(bp/'dubins_pools.json')
assert len(bp_pack['selected'])==4 and {r['pin'] for r in bp_pack['selected']}=={1,2,3,4}
assert len(bp_pack['selected_pairs'])==6 and all(r['status']=='PASS' for r in bp_pack['selected_pairs'])
assert bp_motion['source_packing_sha256']==sha(bp/'packing.json')
assert bp_motion['source_yaw_route_sha256']==sha(HERE/'joined_entry_screen.json')
assert bp_motion['source_fixed_wires_sha256']==sha(PARENT/'harness_A2/assembly_safe_review/fourteen_wire_solids.json')
assert bp_motion['source_cleaned_J2_sha256']==sha(HERE/'terminal_threading/cleaned/candidate.blend')
assert bp_motion['curves_sha256']==sha(bp/bp_motion['curves_file'])
assert len(bp_motion['rows'])==52 and all(r['status']=='PASS' and not r['hits'] for r in bp_motion['rows'])
assert len(bp_motion['mutual_checks'])==78 and all(r['status']=='PASS' for r in bp_motion['mutual_checks'])
assert len(bp_motion['self_checks'])==52 and all(r['status']=='PASS' for r in bp_motion['self_checks'])
assert bp_motion['minimum_pair_surface_gap_bound_mm']>=.3
assert bp_motion['head_pose_count']==130 and bp_motion['wire_pose_instances']==520
assert bp_motion['whole_harness']=='BLOCKED' and not bp_motion['main_model_applied']
assert bp_motion['anchor_design']==bp_motion['body_assembly']==bp_motion['temporary_threading']=='NOT_TESTED'
assert bp_other['source_motion_sha256']==bp_preview['source_motion_sha256']==sha(bp/'body_to_yaw_motion.json')
assert bp_other['source_curves_sha256']==bp_preview['source_curves_sha256']==sha(bp/'body_to_yaw_curves.npz')
assert bp_other['source_other_loops_sha256']==sha(PARENT/'head_harness/split_planar_loops_refined.json')
assert len(bp_other['checks'])==104 and all(r['status']=='PASS' for r in bp_other['checks'])
assert bp_other['full_eleven_wire_harness']=='BLOCKED'
assert bp_preview['candidate_sha256']==sha(bp/bp_preview['candidate_blend'])
assert bp_preview['main_geometry_unchanged'] and bp_preview['physical_parts_preserved_during_overlay']==209
for r in bp_preview['images']:assert sha(bp/r['file'])==r['sha256']
# Independently inspect the saved coordinates, including unchanged named pin
# starts, staging ends, and bounded length variation across every saved pose.
import numpy as np
arrays=np.load(bp/'body_to_yaw_curves.npz');ports=read(HERE/'h06_ports.json')
for pin in range(1,5):
    lengths=[]
    for r in [q for q in bp_motion['rows'] if q['pin']==pin]:
        points=arrays[r['array_key']]
        assert np.linalg.norm(points[0]-np.array(ports['body']['pins'][str(pin)]))<1e-8
        assert abs(points[-1,2]-206)<1e-8 and abs(np.linalg.norm(points[-1,:2])-14.8)<1e-8
        length=float(np.linalg.norm(np.diff(points,axis=0),axis=1).sum());lengths.append(length)
        assert abs(length-r['analytic_partial_length_mm'])<.002
    assert len(lengths)==13 and max(lengths)-min(lengths)<.00001

# J3 is a later, still unapproved candidate.  Validate complete source chains
# without changing the historical J1/J2 failures above into successful results.
j3=HERE/'assembly_feed_v3'
j3data={name:read(j3/(name+'.json')) for name in [
    'coupled_feed_screen','candidate_screen','cleaned/storage','reloaded_verification',
    'relaxation_screen','local_wire_order','journal_sections','upper_mouth_inspection','review_manifest']}
for name,script in [
    ('coupled_feed_screen','check_coupled_terminal_feed'),('candidate_screen','build_coupled_feed_candidate'),
    ('cleaned/storage','clean_coupled_feed_candidate'),('reloaded_verification','verify_coupled_feed_candidate'),
    ('relaxation_screen','check_coupled_feed_relaxation'),('local_wire_order','check_feed_wire_order'),
    ('journal_sections','inspect_coupled_feed_sections'),('upper_mouth_inspection','inspect_upper_feed_mouth'),
    ('review_manifest','publish_coupled_feed')]:
    record=j3data[name]
    assert record['status']=='PASS' and record['source_blend_sha256']==source['source_blend_sha256'],name
    assert record['source_script_sha256']==sha(HERE/(script+'.py')),name
    if 'source_helper_sha256' in record:assert record['source_helper_sha256']==sha(HERE/'plan_h06_documented_mates.py')
jfeed=j3data['coupled_feed_screen'];jbuild=j3data['candidate_screen'];jstore=j3data['cleaned/storage']
jreplay=j3data['reloaded_verification'];jrelax=j3data['relaxation_screen'];jorder=j3data['local_wire_order']
jwall=j3data['journal_sections'];jmouth=j3data['upper_mouth_inspection'];jreview=j3data['review_manifest']
assert jfeed['selected_radius_mm']==7.6 and jfeed['wire_OD_mm']==.6604
assert jfeed['reference_contact_dimensions_mm']==[.8,1.35,3.9]
assert jbuild['source_feed_sha256']==sha(j3/'coupled_feed_screen.json')
for name,digest in jbuild['source_J1'].items():assert digest==sha(HERE/'joined_entry_candidate'/f'{name}_candidate.npz')
assert jbuild['candidate_blend_sha256']==jstore['source_candidate_sha256']==sha(j3/'candidate.blend')
assert jstore['candidate_blend_sha256']==jreplay['source_candidate_sha256']==jrelax['source_candidate_sha256']==jreview['source_candidate_sha256']==jwall['source_cleaned_candidate_sha256']==sha(j3/'cleaned/candidate.blend')
assert jstore['source_mesh_audit_helper_sha256']==sha(HERE/'repair_threading_storage.py')
assert jreplay['source_storage_sha256']==sha(j3/'cleaned/storage.json')
assert jreplay['source_construction_sha256']==jorder['source_construction_sha256']==sha(j3/'candidate_screen.json')
assert jreplay['source_feed_sha256']==sha(j3/'coupled_feed_screen.json')
assert jreplay['source_mates_sha256']==sha(amass/'received_dimensions.json')
assert jreplay['source_wire_curves_sha256']==jrelax['source_installed_routes_sha256']==jorder['source_curves_sha256']==sha(bp/'body_to_yaw_curves.npz')
assert jreplay['source_fixed_wires_sha256']==sha(PARENT/'harness_A2/assembly_safe_review/fourteen_wire_solids.json')
assert jrelax['source_central_law_sha256']==sha(HERE/'central_uart_curves.json')
assert jorder['source_packing_sha256']==sha(bp/'packing.json')
for path,digest in jorder['source_sweeps'].items():assert digest==sha(ROOT/path)
for path,digest in jmouth['source_inputs'].items():assert digest==sha(ROOT/path)
assert jmouth['candidate_blend_sha256']==sha(j3/'cleaned/candidate.blend')
assert jmouth['finding']['design_closed'] is False and jmouth['geometry_changed'] is False
assert all(r['whole_part_positive_volume_components']==1 for r in jmouth['clipped_material'].values())
assert jreplay['changed_existing_ids']==jbuild['changed_existing_ids']==['Pitch_Yoke','Yaw_Base']
assert jreplay['unchanged_other_source_parts']==jstore['unchanged_other_sources']==207
assert jreplay['head_pose_count']==130 and jreplay['wire_pose_instances']==520
assert jreplay['all_source_count']==209 and jreplay['mating_allocation_count']==29 and jreplay['prior_static_wire_count']==14
assert len(jreplay['installed_wire_checks'])==52 and len(jreplay['feed_checks'])==4
assert all(r['status']=='PASS' and not r['hits'] for r in jreplay['installed_wire_checks']+jreplay['feed_checks'])
assert jreplay['nominal_contact_gap_bound_mm']>=.3 and jreplay['nominal_tail_gap_bound_mm']>=.3
for r in jreplay['topology']:
    assert r['status']=='PASS' and r['vertices_match_saved_npz'] and r['triangles_match_saved_npz']
    assert r['non_two_face_edges']==r['misoriented_edges']==r['zero_area_faces']==0
    assert len(r['connected_components'])==1
assert jrelax['row_count']==88 and all(r['status']=='PASS' for r in jrelax['rows'])
assert abs(jrelax['internal_length_growth_mm']-5.1)<1e-8
assert jrelax['intermediate_shape_between_stages']=='NOT_TESTED'
assert jorder['directed_pair_count']==12 and jorder['all_local_feed_orders_clear']
assert all(r['status']=='PASS' and r['outside_swept_clearance_envelope_bound_mm']>=0 for r in jorder['rows'])
assert jorder['body_tail_placement']==jorder['hand_and_tool_access']=='NOT_TESTED'
for r in jwall['wall_samples'].values():
    assert r['rays_sampled']==12240 and r['valid_rays']==11520 and not r['missing']
    assert len(r['excluded_entry_chamfer_rays'])==720 and all(q['status']=='NOT_APPLICABLE' for q in r['excluded_entry_chamfer_rays'])
assert jwall['minimum_all_part_wall']==jwall['strength']=='NOT_TESTED'
for r in [jreplay,jorder]:assert r['whole_harness']=='BLOCKED' and not r['main_applied']
for path,digest in jreview['checks'].items():assert digest==sha(j3/path)
for r in jreview['images']:assert r['sha256']==sha(j3/r['file'])
assert jreview['image_source_sections_sha256']==sha(j3/'sections.json')
assert jreview['image_plot_script_sha256']==sha(HERE/'plot_coupled_feed_review.py')
assert jreview['whole_harness']=='BLOCKED' and not jreview['manufacturing_release'] and not jreview['main_model_applied']
latest=read(PARENT/'work_status.json')['A8_harness_research']
assert latest['latest_review']=='harness_A8/cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/body_supply/complete_head/bridge_wire_stock/install_order/review/index.html'
assert latest['J3_upper_mouth_thin_edge']=='BLOCKED' and not latest['J3_applied']
assert latest['complete_UART_harness']==latest['final_harness_drawing']=='BLOCKED'

# J3M is a separate saved candidate. The historical J3 defect stays recorded.
jm=j3/'open_mouth'
jm_scripts={'candidate_screen':'build_open_feed_mouth','cleaned/storage':'clean_open_feed_mouth',
    'reloaded_verification':'verify_open_feed_mouth','relaxation_screen':'check_open_feed_relaxation',
    'journal_sections':'inspect_open_feed_sections','mouth_cleanup_audit':'audit_open_feed_mouth',
    'continuous_slack':'check_continuous_feed_slack','render_manifest':'render_open_feed_mouth',
    'review_manifest':'publish_open_feed_mouth'}
jmd={name:read(jm/(name+'.json')) for name in jm_scripts}
for name,script in jm_scripts.items():
    r=jmd[name]
    assert r['status']=='PASS' and r['source_script_sha256']==sha(HERE/(script+'.py')),name
    assert r.get('source_blend_sha256',r.get('source_main_sha256'))==source['source_blend_sha256'],name
    if 'source_helper_sha256' in r:assert r['source_helper_sha256']==sha(HERE/'plan_h06_documented_mates.py')
jmb=jmd['candidate_screen'];jms=jmd['cleaned/storage'];jmr=jmd['reloaded_verification']
jma=jmd['mouth_cleanup_audit'];jmc=jmd['continuous_slack'];jmv=jmd['review_manifest']
assert jmb['source_J3_construction_sha256']==sha(j3/'candidate_screen.json')
assert jmb['source_J3_cleaned_candidate_sha256']==jma['source_previous_candidate_sha256']==sha(j3/'cleaned/candidate.blend')
assert jmb['candidate_blend_sha256']==jms['source_candidate_sha256']==sha(jm/'candidate.blend')
assert jms['candidate_blend_sha256']==jmr['source_candidate_sha256']==jma['source_candidate_sha256']==jmc['source_candidate_sha256']==jmv['source_candidate_sha256']==sha(jm/'cleaned/candidate.blend')
assert jmd['relaxation_screen']['source_candidate_sha256']==jmd['journal_sections']['source_cleaned_candidate_sha256']==jmd['render_manifest']['source_saved_candidate_sha256']==sha(jm/'cleaned/candidate.blend')
assert jmr['source_storage_sha256']==jma['source_storage_sha256']==sha(jm/'cleaned/storage.json')
assert jmr['source_construction_sha256']==jma['source_construction_sha256']==sha(jm/'candidate_screen.json')
assert jmr['source_feed_sha256']==jmb['source_feed_sha256']==sha(jm/'coupled_feed_screen.json')==sha(j3/'coupled_feed_screen.json')
assert jmr['source_wire_curves_sha256']==jmc['source_installed_curves_sha256']==sha(bp/'body_to_yaw_curves.npz')
assert jmc['source_central_law_sha256']==sha(HERE/'central_uart_curves.json')
assert jmr['source_mates_sha256']==sha(amass/'received_dimensions.json')
assert jmr['source_fixed_wires_sha256']==sha(PARENT/'harness_A2/assembly_safe_review/fourteen_wire_solids.json')
assert jms['unchanged_other_sources']==jmr['unchanged_other_source_parts']==207
assert jmr['changed_existing_ids']==['Pitch_Yoke','Yaw_Base']
assert jmr['head_pose_count']==130 and jmr['wire_pose_instances']==520
assert jmr['all_source_count']==209 and jmr['mating_allocation_count']==29 and jmr['prior_static_wire_count']==14
assert len(jmr['installed_wire_checks'])==52 and len(jmr['feed_checks'])==4
assert all(r['status']=='PASS' and not r['hits'] for r in jmr['installed_wire_checks']+jmr['feed_checks'])
assert min(jmr['nominal_contact_gap_bound_mm'],jmr['nominal_tail_gap_bound_mm'])>=.3
for r in jmr['topology']:
    assert r['status']=='PASS' and r['vertices_match_saved_npz'] and r['triangles_match_saved_npz']
    assert r['non_two_face_edges']==r['misoriented_edges']==r['zero_area_faces']==0 and len(r['connected_components'])==1
assert jma['sections_checked_per_variant']==100 and jma['before_isolated_section_count']==92 and jma['after_isolated_section_count']==0
assert jma['roof_remaining_volume_mm3']<jma['roof_remaining_numerical_limit_mm3']==.005
assert jma['material_difference_below_mouth_z183_5_mm3']<.005 and not jma['changed_functional_axes']
assert abs(jma['journal_minimum_sample_unchanged_mm']-jwall['wall_samples']['J3']['minimum']['thickness_mm'])<1e-9
assert len(jmc['accepted_intervals'])==64 and not jmc['unresolved_intervals']
assert jmc['central_bend_radius_lower_bound_mm']>=jmc['required_bend_radius_mm']==6.9342
assert all(r['status']=='PASS' and r['minimum_source_extra_margin_bound_mm']>=0 and r['other_wire_surface_gap_bound_mm']>=.3 for r in jmc['accepted_intervals'])
assert jmc['free_tail_feeding']==jmc['hands_and_tool_access']==jmc['friction_and_dynamic_life']=='NOT_TESTED'
for r in read(jm/'check_script_provenance.json'):
    assert r['source_sha256']==sha(HERE/r['source']) and r['derived_sha256']==sha(HERE/r['derived'])
for path,digest in jmv['checks'].items():assert digest==sha(jm/path)
for r in jmv['images']:
    assert r['sha256']==sha(jm/r['file']) and r['source_mesh_sha256']==sha(ROOT/r['source_mesh'])
assert latest['J3M_upper_mouth_cleanup']==latest['J3M_saved_geometry_replay']==latest['J3M_continuous_angular_relaxation']=='PASS'
assert not latest['J3M_applied'] and not jmv['main_model_applied'] and not jmv['manufacturing_release']
assert jmv['whole_harness']==jmr['whole_harness']==jmc['whole_harness']=='BLOCKED'

# Conditional CAM-end allocation. Nominal component clearance is not mistaken
# for physical mating or for connection of the still-disjoint harness halves.
cp=HERE/'cam_pitch_port'
cp_scripts={'mating_allocation':'check_cam_uart_mating_allocation',
    'departure_screen':'plan_cam_uart_departure','coexistence_screen':'check_cam_departure_coexistence',
    'departure_v2/screen':'plan_cam_uart_departure_v2','lower_staging/coexistence_screen':'check_cam_lower_staging',
    'render_manifest':'render_cam_departure','review_manifest':'publish_cam_port_review'}
cpd={name:read(cp/(name+'.json')) for name in cp_scripts}
for name,script in cp_scripts.items():
    record=cpd[name];assert record['source_script_sha256']==sha(HERE/(script+'.py')),name
    if 'source_main_sha256' in record:assert record['source_main_sha256']==source['source_blend_sha256'],name
cm=cpd['mating_allocation'];cd=cpd['departure_screen'];cc=cpd['coexistence_screen']
cl=cpd['lower_staging/coexistence_screen'];cr=cpd['render_manifest'];cv=cpd['review_manifest']
assert cm['status']==cd['status']==cl['status']==cr['status']==cv['status']=='PASS'
assert cc['status']==cpd['departure_v2/screen']['status']=='BLOCKED'
assert cm['source_helper_sha256']==sha(HERE/'plan_h06_documented_mates.py')
for path,digest in cm['sources'].items():assert digest==sha(ROOT/path)
assert cm['head_poses']==130 and len(cm['rows'])==130 and all(not r['hits'] for r in cm['rows'])
assert cm['zero_pose_unplug_sweep']['status']=='PASS' and not cm['zero_pose_unplug_sweep']['hits']
assert cm['documented_reference']['housing_dimensions_mm']==[5.,2.8,5.]
assert cm['documented_reference']['derived_protrusion_mm']==2.
assert cm['allowance_meshes_sha256']==sha(cp/'allocation_meshes.npz')
assert cm['estimated_datum']['physical_pin_numbering'].startswith('BLOCKED')
assert cm['CAM_header_actual_manufacturer_and_revision']==cm['actual_insertion_depth']=='BLOCKED'
assert cm['geometry_with_uncertainties']=='NOT_TESTED' and not cm['hardware_or_pinmap_changed']
assert cd['source_helper_sha256']==sha(HERE/'check_cam_uart_mating_allocation.py')
assert cd['source_mating_allocation_sha256']==sha(cp/'mating_allocation.json')
assert cd['source_motion_checker_sha256']==sha(HERE/'check_body_prefix_motion.py')
assert cd['source_curves_sha256']==cc['source_head_curves_sha256']==cl['source_head_curves_sha256']==sha(cp/'departure_curves.npz')
assert cd['source_candidate_sha256']==cr['source_candidate_sha256']==sha(jm/'cleaned/candidate.blend')
assert len(cd['selected'])==2 and all(r['pair_surface_gap_bound_mm']>=.3 and min(r['arc_radii_mm'])>=6.9342 for r in cd['selected'])
assert cc['source_departure_sha256']==cl['source_head_screen_sha256']==sha(cp/'departure_screen.json')
assert cc['source_body_curves_sha256']==cl['source_original_body_curves_sha256']==sha(bp/'body_to_yaw_curves.npz')
assert cc['source_body_motion_sha256']==sha(bp/'body_to_yaw_motion.json')
assert cc['pair_count']==len(cc['rows'])==4160 and any(r['status']=='BLOCKED' for r in cc['rows'])
assert cl['source_pair_checker_sha256']==sha(HERE/'check_cam_departure_coexistence.py')
assert cl['source_original_coexistence_failure_sha256']==sha(cp/'coexistence_screen.json')
assert cl['candidate_body_curves_sha256']==sha(cp/'lower_staging/body_partial_curves.npz')
assert cl['datum_change_mm']==[206.,193.] and cl['head_pose_count']==130
assert cl['pair_count']==len(cl['rows'])==4160 and all(r['status']=='PASS' and r['surface_gap_bound_mm']>=.3 for r in cl['rows'])
assert len(cl['subset_proof'])==52 and all(r['removed_final_straight_length_mm']==13. and r['new_end_mm'][2]==193. and not r['new_cut_length_released'] for r in cl['subset_proof'])
assert cl['new_fixed_anchors']==cl['missing_service_loop']==cl['photo_uncertainties']=='NOT_TESTED'
assert cr['source_mating_mesh_sha256']==sha(cp/'allocation_meshes.npz') and cr['source_departure_curves_sha256']==sha(cp/'departure_curves.npz')
assert cr['comparison_blend_sha256']==sha(cp/'comparison.blend') and cr['source_geometry_unchanged']
assert cr['visible_source_parts']==['CAM_Mainboard']
for r in cr['images']:assert r['sha256']==sha(cp/r['file'])
for path,digest in cv['checks'].items():assert digest==sha(cp/path)
assert cv['source_update_sha256']==sha(cp/'source_update.json')
for record in [cm,cd,cc,cl,cv]:assert record['whole_harness']=='BLOCKED' and not record['main_applied'] and not record['manufacturing_release']
assert latest['CAM_catalogue_mate_nominal_allocation']==latest['CAM_pitch_fixed_departure']==latest['CAM_lower_Z193_disjoint_halves']=='PASS'
assert latest['CAM_old_Z206_combination']==latest['CAM_actual_connector']=='BLOCKED'
assert latest['CAM_yaw_pitch_service_loop']=='PASS' and not latest['CAM_route_applied']

# Connected individual candidates must never turn a failed whole bundle green.
cf=HERE/'cam_pitch_flex'
cf_pool=json.loads((cf/'side/flex_pool.json').read_text())
cf_pack=json.loads((cf/'side/packing.json').read_text())
cf_math=json.loads((cf/'side/math_bounds.json').read_text())
cf_diag=json.loads((cf/'side/full_pair_diagnostic.json').read_text())
cf_early=json.loads((cf/'early_turn/screen.json').read_text())
cf_render=json.loads((cf/'render_manifest.json').read_text())
cf_review=json.loads((cf/'review_manifest.json').read_text())
cf_photo=json.loads((cf/'photo_receipt.json').read_text())
for record,script in [(cf_pool,'plan_cam_pitch_flex_side.py'),(cf_pack,'check_cam_pitch_flex_packing.py'),
                      (cf_math,'audit_cam_pitch_flex_math.py'),(cf_diag,'diagnose_pitch_flex_pairs.py'),
                      (cf_early,'check_pitch_early_turn.py'),(cf_render,'render_pitch_flex_review.py'),
                      (cf_review,'publish_pitch_flex_review.py')]:
    assert record['source_script_sha256']==sha(HERE/script),script
    assert not record['main_applied']
assert cf_pool['source_main_sha256']==cf_pack['source_main_sha256']==cf_diag['source_main_sha256']==cf_early['source_main_sha256']==source['source_blend_sha256']
assert cf_pool['status']==cf_math['status']==cf_early['status']=='PASS'
assert cf_pack['status']==cf_diag['status']=='BLOCKED' and not cf_pack['simultaneous_assignments']
assert len(cf_pack['rows'])==19 and all(r['status']=='PASS' for r in cf_pack['rows'])
assert cf_pack['source_pool_sha256']==cf_math['source_pool_sha256']==cf_diag['source_pool_sha256']==sha(cf/'side/flex_pool.json')
assert cf_pack['source_curves_sha256']==cf_diag['source_curves_sha256']==cf_pool['curves_sha256']==sha(cf/'side/flex_candidates.npz')
assert all(p['status']=='PASS' and p['unresolved_intervals']==0 and p['maximum_constant_length_error_bound_mm']<.001 for r in cf_math['rows'] for p in r['poses'])
assert cf_early['radius_mm']>=cf_pool['required_radius_mm'] and not cf_early['hits']
assert all(r['status']=='PASS' for r in cf_early['pair_checks'])
assert cf_early['minimum_head_tail_gap_bound_mm']>=.3
assert cf_early['full_rejoined_curve']=='NOT_TESTED' and cf_early['curve_sha256']==sha(cf/'early_turn/early_turn.npz')
assert cf_early['source_pair_diagnostic_sha256']==sha(cf/'side/full_pair_diagnostic.json')
assert cf_photo['source_sha256']==sha(ROOT/cf_photo['source'])
photo_record=json.loads((ROOT/cf_photo['source']).read_text())
assert cf_photo['photo_sha256']==photo_record['photo_sha256']==sha(ROOT/'mechanical/sources/waveshare_detail/esp32-s3-cam-ovxxxx-3_1.jpg')
assert cf_photo['photo_board_face_position']=='PASS' and cf_photo['actual_mating_cavity_views']=='BLOCKED'
assert cf_photo['slot_evidence']=='ASSUMED_MODEL_INFERENCE' and not cf_photo['formal_pinmap_or_hardware_changed']
assert cf_render['harness_status']=='BLOCKED' and cf_render['comparison_blend_sha256']==sha(cf/'comparison.blend')
assert cf_render['source_pair_diagnostic_sha256']==sha(cf/'side/full_pair_diagnostic.json')
for row in cf_render['images']:assert row['sha256']==sha(cf/row['file'])
for path,digest in cf_review['files'].items():assert sha(ROOT/path)==digest,path
assert cf_review['whole_harness']=='BLOCKED' and not cf_review['manufacturing_release']
assert latest['CAM_individual_constant_length_routes']==latest['CAM_board_face_photo_position']=='PASS'
assert latest['CAM_whole_four_wire_packing']=='PASS' and latest['CAM_early_turn_full_rejoin']=='NOT_TESTED'

# A coherent CAM-side four-wire group now passes. The missing lower fan-in
# must stay explicit: this does not override the earlier complete-route
# packing failure or establish supplier cut lengths.
cpar=HERE/'cam_parallel_pitch'
par_tail=read(cpar/'shifted_tail_screen.json');par_tmath=read(cpar/'tail_math_bounds.json')
par_loop=read(cpar/'following_arc/screen.json');par_pack=read(cpar/'following_arc/packing.json')
par_lmath=read(cpar/'following_arc/math_bounds.json');par_render=read(cpar/'render_manifest.json')
par_review=read(cpar/'review_manifest.json')
for record,script in [(par_tail,'screen_parallel_shifted_tails.py'),(par_tmath,'audit_parallel_tail_math.py'),
                      (par_loop,'plan_cam_following_arc.py'),(par_pack,'check_cam_parallel_bundle.py'),
                      (par_lmath,'audit_cam_following_arc.py'),(par_render,'render_cam_parallel_review.py'),
                      (par_review,'publish_cam_parallel_review.py')]:
    assert record['status']=='PASS' and not record['main_applied']
    assert record.get('script_sha256',record.get('source_script_sha256'))==sha(HERE/script),script
assert par_tail['source_main_sha256']==par_loop['source_main_sha256']==par_pack['source_main_sha256']==source['source_blend_sha256']
assert par_loop['helper_sha256']==sha(HERE/'plan_cam_parallel_arcs.py')
assert par_pack['source_helper_sha256']==sha(HERE/'plan_cam_following_arc.py')
assert par_pack['source_pack_helper_sha256']==sha(HERE/'check_cam_pitch_flex_packing.py')
assert par_pack['source_pool_sha256']==par_lmath['source_screen_sha256']==sha(cpar/'following_arc/screen.json')
assert par_pack['source_curves_sha256']==par_render['source_curves_sha256']==par_loop['curves_sha256']==sha(cpar/'following_arc/curves.npz')
assert par_loop['tail_curves_sha256']==par_pack['source_tail_curves_sha256']==par_tmath['source_curves_sha256']==sha(cpar/'shifted_tails.npz')
assert par_tmath['source_report_sha256']==par_loop['tail_report_sha256']==sha(cpar/'shifted_tail_screen.json')
assert par_tmath['minimum_curvature_radius_lower_bound_mm']>=par_tmath['minimum_required_mm']
assert par_tmath['length_interval_width_mm']<.001
assert len(par_loop['selected'])==len(par_pack['rows'])==len(par_lmath['rows'])==3
for row in par_pack['rows']:
    assert row['status']=='PASS' and not row['failures']
    assert len(row['self_checks'])==40 and len(row['mutual_checks'])==60 and len(row['body_prefix_checks'])==2080
    assert all(x['status']=='PASS' for x in row['self_checks']+row['mutual_checks']+row['body_prefix_checks'])
    assert row['minimum_mutual_gap_bound_mm']>=.3 and row['minimum_prefix_gap_bound_mm']>=.3
for row in par_lmath['rows']:
    assert row['status']=='PASS' and row['start_straight']['lower_mm']>=5 and row['column_straight']['lower_mm']>=.5
    assert min(row['upper_radius']['lower_mm'],row['lower_radius_mm'])>=par_loop['minimum_radius_required_mm']
assert par_pack['whole_harness']==par_review['whole_harness']=='BLOCKED'
assert par_loop['fan_in']==par_loop['anchors']=='NOT_TESTED'
assert par_render['source_geometry_unchanged'] and par_render['comparison_blend_sha256']==sha(cpar/'comparison.blend')
for row in par_render['images']:assert row['sha256']==sha(cpar/row['file'])
for path,digest in par_review['files'].items():assert sha(ROOT/path)==digest,path
assert latest['CAM_parallel_partial_bundle']==latest['CAM_parallel_analytic_length_radius']=='PASS'
assert latest['CAM_parallel_fan_in']=='PASS' and latest['CAM_parallel_anchors']=='NOT_TESTED'

# Current connected candidate: historical disjoint studies retain their own
# original outcomes; only this compositional proof closes nominal connectivity.
cfan=HERE/'cam_fan_in'; cl=cfan/'short_tail_v2'; ft=cfan/'four_bend_transition'
cloop=read(cl/'screen.json'); clpack=read(cl/'packing.json'); clmath=read(cl/'math_bounds.json')
fpool=read(ft/'pool.json'); fpack=read(ft/'packing.json'); fmath=read(ft/'math_bounds.json')
fjoins=read(cfan/'joins.json'); frender=read(cfan/'render_manifest.json'); freview=read(cfan/'review_manifest.json')
for record,script in [(cloop,'plan_cam_short_tail_v2.py'),(clpack,'check_cam_short_tail_bundle.py'),
    (clmath,'audit_cam_short_tail_arc.py'),(fpool,'plan_cam_yaw_fan_four_bends.py'),
    (fpack,'pack_cam_fan_transitions.py'),(fmath,'audit_cam_fan_math.py'),
    (fjoins,'verify_cam_fan_joins.py'),(frender,'render_cam_fan_review.py'),(freview,'publish_cam_fan_review.py')]:
    assert record['status']=='PASS' and not record['main_applied']
    assert record.get('script_sha256',record.get('source_script_sha256'))==sha(HERE/script),script
for record in [cloop,clpack,fpool,fpack,fjoins,freview]:assert record['source_main_sha256']==source['source_blend_sha256']
assert cloop['helper_sha256']==clpack['source_helper_sha256']==sha(HERE/'plan_cam_following_arc.py')
assert cloop['source_arc_helper_sha256']==sha(HERE/'plan_cam_parallel_arcs.py')
assert clpack['source_pack_helper_sha256']==fpool['source_pair_helper_sha256']==sha(HERE/'check_cam_pitch_flex_packing.py')
assert cloop['tail_trim_mm']==2.5 and len(cloop['selected'])==len(clpack['rows'])==len(clmath['rows'])==1
assert cloop['original_tail_curves_sha256']==sha(cpar/'shifted_tails.npz')
assert cloop['tail_report_sha256']==sha(cpar/'shifted_tail_screen.json')
assert cloop['tail_curves_sha256']==clpack['source_tail_curves_sha256']==clmath['source_tail_sha256']==fpool['source_tail_sha256']==sha(cl/'tails.npz')
assert clpack['source_pool_sha256']==clmath['source_screen_sha256']==fpool['source_loop_screen_sha256']==sha(cl/'screen.json')
assert cloop['curves_sha256']==clpack['source_curves_sha256']==fpool['source_loop_curves_sha256']==frender['source_curves_sha256']==sha(cl/'curves.npz')
assert fpool['source_helper_sha256']==fpack['source_helper_sha256']==sha(HERE/'plan_cam_yaw_fan_v4.py')
assert fpool['source_parameters_sha256']==sha(cfan/'curvature_prefilter_v4/parameters.json')
assert fpool['source_previous_pool_sha256']==sha(cfan/'fan_in_v4/pool.json')
assert fpool['source_previous_curves_sha256']==sha(cfan/'fan_in_v4/curves.npz')
assert fpool['curves_sha256']==fpack['source_curves_sha256']==frender['source_fan_curves_sha256']==sha(ft/'curves.npz')
assert fpack['source_pool_sha256']==fmath['source_pool_sha256']==sha(ft/'pool.json')
assert fpack['source_math_sha256']==sha(ft/'math_bounds.json')
assert fpack['source_CAM_bundle_sha256']==fpool['source_loop_packing_sha256']==sha(cl/'packing.json')
assert clpack['source_body_prefix_sha256']==fpool['source_body_prefix_sha256']==frender['source_prefix_sha256']==sha(cp/'lower_staging/body_partial_curves.npz')
assert len(fpool['rows'])==4 and all(len(row['candidates'])==3 for row in fpool['rows'])
for row in clpack['rows']:
    assert row['status']=='PASS' and not row['failures']
    assert len(row['self_checks'])==40 and len(row['mutual_checks'])==60 and len(row['body_prefix_checks'])==2080
    assert all(x['status']=='PASS' for x in row['self_checks']+row['mutual_checks']+row['body_prefix_checks'])
    assert row['minimum_mutual_gap_bound_mm']>=.3 and row['minimum_prefix_gap_bound_mm']>=.3
assert clmath['rows'][0]['start_straight']['lower_mm']>=5
assert min(clmath['rows'][0]['upper_radius']['lower_mm'],clmath['rows'][0]['lower_radius_mm'])>=cloop['minimum_radius_required_mm']
assert len(fmath['rows'])==12 and all(r['status']=='PASS' and r['minimum_radius_lower_mm']>=fpool['required_radius_mm'] and r['unresolved_intervals']==0 and r['maximum_length_error_mm']<=.001 for r in fmath['rows'])
assert len(fpack['individual_replay'])==12 and len(fpack['pairs'])==54 and len(fpack['assignments'])==81
for r in fpack['individual_replay']:
    assert r['status']==r['self']['status']==r['connections']['status']=='PASS' and r['source_hit'] is None
    assert min(r['connections']['minimum_other_loop_gap_mm'],r['connections']['minimum_other_prefix_gap_mm'])>=.3
assert all(r['status']=='PASS' and r['gap_bound_mm']>=.3 for r in fpack['pairs'])
assert fjoins['checked_seams']==1560 and fjoins['maximum_endpoint_error_mm']<3e-5 and fjoins['maximum_sampled_tangent_error_deg']<.3
assert len(fjoins['trim_rows'])==4 and all(r['status']=='PASS' and r['trimmed_straight_mm']==2.5 for r in fjoins['trim_rows'])
assert fjoins['tail_radius_lower_mm']==par_tmath['minimum_curvature_radius_lower_bound_mm']
assert fjoins['tail_length_lower_mm']==par_tmath['length_lower_mm']-2.5
assert fpack['anchors']=='NOT_TESTED' and fpack['whole_harness']==freview['whole_harness']=='BLOCKED'
assert frender['source_geometry_unchanged'] and frender['source_candidate_sha256']==sha(jm/'cleaned/candidate.blend')
assert frender['source_packing_sha256']==sha(ft/'packing.json') and frender['source_tails_sha256']==sha(cl/'tails.npz')
assert frender['fan_assignment']==fjoins['fan_assignment']==fpack['assignments'][0]
assert len(frender['images'])==4 and frender['comparison_blend_sha256']==sha(cfan/'comparison.blend')
for r in frender['images']:assert r['sha256']==sha(cfan/r['file'])
for record in [fjoins,freview]:
    for path,digest in record['files'].items():assert sha(ROOT/path)==digest,path
assert latest['CAM_connected_route']==latest['CAM_connected_route_seams']=='PASS' and not latest['CAM_connected_route_applied']
recheck_dir=PARENT/'supplier_made_harness/recheck_20261004'
source_recheck=read(recheck_dir/'delivery.json')
assert source_recheck['status']=='PASS'
for path,digest in source_recheck['files'].items():assert sha(recheck_dir/path)==digest,path

# One CAM yaw-side anchor is a separate nominal candidate, not all anchors.
ca=HERE/'cam_anchors';cc=ca/'candidate_v3/cleaned'
anchor=read(ca/'candidate_v3/screen.json');anchor_storage=read(cc/'storage_verification.json')
anchor_install=read(cc/'servo_installation_replay.json');anchor_tool=read(cc/'tool_replay.json')
anchor_render=read(ca/'render_manifest.json');anchor_review=read(ca/'review_manifest.json')
assert all(x['status']=='PASS' for x in [anchor,anchor_storage,anchor_install,anchor_tool,anchor_render,anchor_review])
assert anchor['source_script_sha256']==sha(HERE/'build_CAM_anchor_candidate_v3.py')
assert anchor['source_main_sha256']==source['source_blend_sha256']
for check in ['support_check','tie_check']:
    assert anchor[check]['source']['status']==anchor[check]['wires']['status']=='PASS'
    assert anchor[check]['source']['relative_checks']==2653
    assert anchor[check]['wires']['routes_checked']==44 and anchor[check]['wires']['grip_sweeps_checked']==4
assert anchor['support_check']['combined_components']==1 and anchor['support_check']['host_root_overlap_mm3']>5
assert anchor['tie_check']['host_intersection_mm3']==anchor['tie_check']['support_intersection_mm3']==0
assert anchor['added_print_parts']==anchor['added_screws']==0 and anchor['proposed_ties']==1
assert anchor['pitch_servo_straight_insertion']['status']=='BLOCKED'
assert anchor['whole_harness']=='BLOCKED' and not anchor['main_applied']
for record,script in [(anchor_storage,'verify_CAM_anchor_cleaned_storage.py'),(anchor_install,'verify_CAM_anchor_cleaned_installation.py'),(anchor_tool,'verify_CAM_anchor_tool.py')]:
    assert record['script_sha256']==sha(HERE/script)
    assert record['source_main_sha256']==source['source_blend_sha256'] and not record['main_applied']
assert anchor_storage['unchanged_physical_parts']==207 and anchor_storage['changed_vs_main']==['Pitch_Yoke','Yaw_Base']
for row in anchor_storage['raw_checks']:
    assert row['status']=='PASS' and row['positive_components']==1
    assert all(row['raw_topology'][key]==0 for key in ['boundary_edges','nonmanifold_edges','inconsistent_edges','degenerate_triangles'])
bound=anchor_storage['intended_union_storage_bound']
assert bound['status']=='PASS' and max(bound['maximum_new_vertex_to_reference_mm'],bound['maximum_reference_vertex_to_new_mm'])<.001
assert bound['absolute_volume_delta_mm3']<.05
assert anchor_storage['candidate_blend_sha256']==anchor_tool['candidate_blend_sha256']==anchor_render['candidate_blend_sha256']==sha(cc/'candidate.blend')
assert anchor_install['candidate_yoke_sha256']==anchor_tool['candidate_yoke_sha256']==sha(cc/'Pitch_Yoke.npz')
selected=next(r for r in anchor_install['accepted'] if r['waypoints_mm'][2][1]==6.5)
assert selected['status']=='PASS' and not selected['hits'] and selected['checked_samples']==1066
assert min(r['continuous_gap_lower_bound_mm'] for r in selected['segment_clearances'][1:])>.39
assert anchor_tool['sampled_span_deg']==240 and anchor_tool['angle_endpoints_deg']==[-120,120] and not anchor_tool['hits']
assert len(anchor_tool['checked_angles_deg'])==121
assert anchor_render['installation_report_sha256']==sha(cc/'servo_installation_replay.json')
assert anchor_render['script_sha256']==sha(HERE/'render_CAM_anchor_review.py') and len(anchor_render['images'])==9
assert anchor_render['review_blend_sha256']==sha(ca/'review.blend') and anchor_render['physical_geometry_preserved']
for row in anchor_render['images']:assert sha(ca/row['file'])==row['sha256']
for path,digest in anchor_review['files'].items():assert sha(ROOT/path)==digest,path
assert anchor_review['script_sha256']==sha(HERE/'publish_CAM_anchor_review.py')
assert latest['CAM_yaw_side_anchor_candidate']=='PASS' and latest['CAM_all_anchors']=='NOT_TESTED'
assert not latest['CAM_yaw_side_anchor_applied'] and latest['CAM_yaw_side_anchor_tie_installation']=='NOT_TESTED'

# Directional tie and bench checks are incremental; they do not qualify the
# flexible threading operation or close the whole harness installation.
ct=HERE/'cam_tie_install'
tie_screen=read(ct/'oriented_tie_screen.json');tie_bench=read(ct/'bench_access.json')
tie_render=read(ct/'render_manifest.json');tie_review=read(ct/'review_manifest.json')
tie_sources=read(ct/'sources/receipt.json');tie_dims=read(ct/'sources/dimensions.json')
for record,script in [(tie_screen,'screen_CAM_tie_installation.py'),(tie_bench,'check_CAM_tie_bench_access.py'),(tie_render,'render_CAM_tie_installation.py'),(tie_review,'publish_CAM_tie_installation.py')]:
    assert record['status']=='PASS' and record['script_sha256']==sha(HERE/script)
    assert not record['main_applied']
for record in [tie_screen,tie_bench,tie_review]:assert record['source_main_sha256']==source['source_blend_sha256']
assert tie_screen['candidate_sha256']==tie_bench['candidate_sha256']==tie_render['source_candidate_sha256']==sha(cc/'candidate.blend')
assert tie_screen['accepted_indices']==[0,1,2,3]
for i,row in enumerate(tie_screen['trials']):
    assert row['status']==row['source']['status']==row['wires']['status']=='PASS'
    assert row['source']['relative_checks']==2653 and row['wires']['routes_checked']==44
    assert row['wires']['grip_sweeps_checked']==4 and row['yoke_intersection_mm3']<.001
    assert row['strap_components']==1 and row['strap_volume_mm3']>80
    assert abs(row['strap_volume_mm3']-row['analytic_strap_volume_mm3'])<.02
    # Avoid repeating the invalid empty-band error: inspect the saved actual
    # triangles independently of the generator's JSON status.
    a=np.load(ct/f'band_{i}.npz');vertices=a['vertices_mm'];triangles=a['triangles']
    assert len(vertices)>10 and len(triangles)>10
    centered=vertices-vertices.mean(axis=0);tv=centered[triangles]
    volume=np.einsum('ij,ij->i',tv[:,0],np.cross(tv[:,1],tv[:,2])).sum()/6
    assert volume>80 and abs(volume-row['strap_volume_mm3'])<1e-6
actual=np.load(ct/'oriented_band.npz');selected_band=np.load(ct/'band_1.npz')
assert np.array_equal(actual['vertices_mm'],selected_band['vertices_mm'])
assert np.array_equal(actual['triangles'],selected_band['triangles'])
assert tie_bench['closed_ring_slide_from_below']['status']=='BLOCKED'
assert len(tie_bench['closed_ring_slide_from_below']['hits'])==93
assert {r['object'] for r in tie_bench['closed_ring_slide_from_below']['hits']}=={'Pitch_Servo'}
assert tie_bench['closed_ring_before_servo']['status']=='PASS' and not tie_bench['closed_ring_before_servo']['hits']
route=tie_bench['servo_with_preplaced_tie']
assert route['status']=='PASS' and route['checked_samples']==1066 and not route['hits']
assert min(r['continuous_gap_lower_bound_mm'] for r in route['segment_clearances'])>.80
for k in ['tail_corridor','cutter_approach']:assert tie_bench[k]['status']=='PASS' and not tie_bench[k]['hits']
assert not tie_bench['cutter_approach']['local_lead_hits']
assert tie_bench['same_tool_with_final_pitch_loops']['status']=='BLOCKED' and len(tie_bench['same_tool_with_final_pitch_loops']['hits'])==4
assert tie_bench['tie_threading_and_tightening']==tie_bench['full_harness_installation']=='NOT_TESTED'
assert tie_bench['whole_harness']==tie_review['whole_harness']=='BLOCKED'
assert len(tie_render['images'])==4 and tie_render['physical_geometry_preserved']
assert sha(ct/'review.blend')==tie_render['review_sha256']
for r in tie_render['images']:assert sha(ct/r['file'])==r['sha256']
assert not tie_dims['procurement_variant_frozen'] and not tie_dims['physical_measurement']
assert len(tie_dims['drawings'])==3 and not tie_dims['manufacturing_release']
for r in tie_sources['sources']:
    if 'file' in r:
        p=ct/'sources'/r['file'];assert p.read_bytes().startswith(b'%PDF-') and sha(p)==r['sha256']
for path,digest in tie_review['files'].items():assert sha(ROOT/path)==digest,path
assert latest['CAM_tie_catalogue_receipt']==latest['CAM_tie_bench_working_volumes']=='PASS'
assert latest['CAM_tie_full_installation']=='NOT_TESTED' and not latest['CAM_tie_main_applied']

# Connector-side anchor is a new independent candidate, not main adoption.
cpa=HERE/'cam_pitch_anchor';cpc=cpa/'connector_anchor'
cr=read(cpc/'root_v3_screen.json');cb=read(cpc/'assembly.json');cv=read(cpc/'render_manifest.json');cpub=read(cpa/'review_manifest.json')
for r,script in [(cr,'build_CAM_connector_anchor_v3.py'),(cb,'check_CAM_connector_anchor_assembly.py'),(cv,'render_CAM_connector_anchor.py'),(cpub,'publish_CAM_connector_anchor.py')]:
    assert r['status']=='PASS' and r['script_sha256']==sha(HERE/script)
    assert r['source_main_sha256']==source['source_blend_sha256']
    assert not r['main_applied'] and r['whole_harness']=='BLOCKED'
assert cr['helper_sha256']==cb['helper_sha256']==sha(HERE/'screen_CAM_pitch_anchor_warp.py')
assert cr['construction_helper_sha256']==sha(HERE/'build_CAM_connector_anchor.py')
assert cb['root_report_sha256']==cv['root_report_sha256']==sha(cpc/'root_v3_screen.json')
assert cb['part_sha256']==sha(cpc/'Pitch_Cradle.npz')
assert cr['rows'][0]['source']['status']==cr['rows'][0]['wires']['status']=='PASS'
assert cr['rows'][0]['source']['nearest_below_2mm']['gap_mm']>.399
assert cr['rows'][0]['wires']['routes_checked']==600 and cr['rows'][0]['wires']['grip_sweeps_checked']==4
assert cr['rows'][0]['combined_components']==1 and cr['rows'][0]['root_overlap_mm3']>22
assert not cr['wires_relocated'] and cr['added_print_parts']==0
assert cb['rows']['plug_after_board_from_below']['status']=='BLOCKED'
assert cb['rows']['preplugged_CAM_to_detached_cradle']['status']=='PASS'
assert cb['rows']['preclosed_tie_below_on_bench']['status']=='PASS'
assert cb['full_assembly']==cb['flexible_tie_threading_and_tension']=='NOT_TESTED'
assert cv['unchanged_other_physical_parts']==208 and cv['outside_change_region_difference_mm3']<.05
assert cv['stored_volume_components']==1 and cv['stored_symmetric_volume_difference_mm3']<.05
assert cv['review_sha256']==sha(cpc/'review.blend')
for r in cv['images']:assert r['sha256']==sha(cpc/r['file'])
for p,h in cpub['files'].items():assert sha(ROOT/p)==h,p
for name in ['Pitch_Cradle','addition','z212.0_band','z212.0_head']:
    a=np.load(cpc/(name+'.npz'));v=a['vertices_mm'];f=a['triangles'];tv=(v-v.mean(0))[f]
    volume=float(np.einsum('ij,ij->i',tv[:,0],np.cross(tv[:,1],tv[:,2])).sum()/6)
    assert volume>1.,name
for p in ['support_screen.json','warp_v1/screen.json','warp_v2/screen.json','clamp_positions/screen.json','clamp_below/screen.json']:
    assert read(cpa/p)['status']=='BLOCKED'
assert latest['CAM_connector_anchor_candidate']=='PASS' and not latest['CAM_connector_anchor_applied']
assert latest['CAM_connector_anchor_full_installation']=='NOT_TESTED'

# The new work-access page does not promote the prior bounded installation
# to a whole-harness PASS. Verify the failure and the exact length datums too.
cwi=HERE/'cam_connector_install'
cw=read(cwi/'work_access.json');clen=read(cwi/'route_datums.json')
cwr=read(cwi/'render_manifest.json');cwp=read(cwi/'review_manifest.json')
for r,script in [(cw,'check_CAM_connector_work_access.py'),(clen,'prepare_CAM_route_datums.py'),(cwr,'render_CAM_connector_work.py'),(cwp,'publish_CAM_connector_work.py')]:
    assert r['status']=='PASS' and r['script_sha256']==sha(HERE/script)
    assert r['source_main_sha256']==source['source_blend_sha256']
    assert not r['main_applied'] and r['whole_harness']=='BLOCKED'
for p,h in cw['inputs'].items():assert sha(HERE/p)==h,p
assert cw['helper_sha256']==sha(HERE/'screen_CAM_pitch_anchor_warp.py')
down=next(r for r in cw['rows'] if r['angle_about_tail_axis_deg']==180.)
assert down['status']=='PASS' and not down['bench']['hits']
assert down['fixture_only']['minimum_gap_below_5mm']['gap_mm']>2.13
assert down['temporary_wires_only']['minimum_gap_below_5mm']['gap_mm']>1.55
assert down['final_prescribed_loops']['status']=='BLOCKED'
assert cw['service_fixture_levels']['open_head_on_robot']['status']=='BLOCKED'
assert cw['service_fixture_levels']['detached_pitch_module_no_shells']['status']=='PASS'
assert cw['complete_harness_installation']==cw['real_tie_threading_tension_and_cutting']=='NOT_TESTED'
assert cw['tail_work_volume']['status']=='PASS'
for r in cw['rows']:
    for prefix,bounds in [('tool_',r['tool_bounds_mm']),('sweep_',r['continuous_approach_bounds_mm'])]:
        a=np.load(cwi/(prefix+str(r['angle_about_tail_axis_deg'])+'.npz'));v=a['vertices_mm'];f=a['triangles']
        assert np.max(np.abs(np.r_[v.min(0),v.max(0)]-bounds))<1e-7
        q=(v-v.mean(0))[f];volume=float(np.einsum('ij,ij->i',q[:,0],np.cross(q[:,1],q[:,2])).sum()/6)
        assert volume>1.,prefix
for p,h in clen['sources'].items():assert sha(ROOT/p)==h,p
for p,h in clen['outputs'].items():assert sha(cwi/p)==h,p
assert clen['pose_wire_instances']==len(clen['pose_rows'])==520
assert clen['maximum_polyline_source_length_difference_mm']<.003
assert not clen['cut_lengths_released'] and not clen['manufacturing_release']
assert len(clen['rows'])==4 and {r['geometry_slot'] for r in clen['rows']}=={'H06-G1','H06-G2','H06-G3','H06-G4'}
for r in clen['rows']:
    assert r['cut_length_mm'] is None and r['cut_length_status']=='BLOCKED'
    assert abs(r['total_routed_model_mm']-sum(r[k] for k in ['body_prefix_model_mm','yaw_transition_model_mm','pitch_core_model_mm','CAM_tail_model_mm']))<1e-8
    assert 107.74<r['between_candidate_clamp_centres_model_mm']<107.76
    marks=r['datums'];assert all(a['distance_from_body_exit_model_mm']<b['distance_from_body_exit_model_mm'] for a,b in zip(marks,marks[1:]))
    assert abs(marks[-1]['distance_from_body_exit_model_mm']-r['total_routed_model_mm'])<1e-8
    assert abs(marks[3]['distance_from_body_exit_model_mm']-marks[2]['distance_from_body_exit_model_mm']-r['between_candidate_clamp_centres_model_mm'])<1e-8
assert cwr['physical_parts_unchanged']==209 and cwr['source_candidate_sha256']==sha(cpc/'review.blend')
assert cwr['source_work_report_sha256']==sha(cwi/'work_access.json')
assert cwr['review_sha256']==sha(cwi/'review.blend')
for r in cwr['images']:assert r['sha256']==sha(cwi/r['file'])
for p,h in cwp['files'].items():assert sha(ROOT/p)==h,p
assert latest['CAM_supplier_cut_lengths']=='BLOCKED' and latest['CAM_whole_connected_installation']=='BLOCKED'

# Joining local passes exposed a failed full subassembly path. Preserve and
# verify that failure rather than letting the page imply assembly approval.
cwc=HERE/'cam_wired_cradle'
wcs=read(cwc/'screen.json');wct=read(cwc/'sequence_tools.json')
wcw=read(cwc/'witnesses.json');wcr=read(cwc/'render_manifest.json');wcp=read(cwc/'review_manifest.json')
for r,script in [(wcs,'check_CAM_wired_cradle_insertion.py'),(wct,'check_CAM_sequence_tools.py'),
                 (wcw,'prepare_CAM_cradle_witnesses.py'),(wcr,'render_CAM_wired_cradle.py'),(wcp,'publish_CAM_wired_cradle.py')]:
    assert r['script_sha256']==sha(HERE/script)
    assert r['source_main_sha256']==source['source_blend_sha256']
    assert not r['main_applied'] and r['whole_harness']=='BLOCKED'
assert wcs['status']==wct['status']=='BLOCKED'
assert wcw['status']==wcr['status']==wcp['status']=='PASS'
assert wcs['helper_sha256']==sha(HERE/'screen_CAM_pitch_anchor_warp.py')
assert wct['helper_sha256']==wcw['helper_sha256']==sha(HERE/'check_CAM_wired_cradle_insertion.py')
assert len(wcs['rows'])==15 and all(r['geometry']['status']=='PASS' and not r['geometry']['hits'] for r in wcs['rows'])
assert [r['lift_mm'] for r in wcs['rows'] if r['status']=='PASS']==[0.,3.,6.]
assert 'CAM_without_own_UART' in wcs['moving_ids']
assert all(abs(r['curves']['exact_core_length_mm']-wcs['core_length_mm'])<1e-8 for r in wcs['rows'])
assert wcs['continuous_motion']==wcs['formation_to_this_curve']=='NOT_TESTED'
assert wcs['source_anchor_sha256']==sha(cpc/'Pitch_Cradle.npz') and wcs['curves_sha256']==sha(cwc/'curves.npz')
assert len(wct['rows'])==48 and all(r['status']=='BLOCKED' for r in wct['rows'])
assert wcw['screen_sha256']==wcr['screen_sha256']==sha(cwc/'screen.json')
assert wcw['curves_sha256']==sha(cwc/'review_curves.npz') and wcr['witnesses_sha256']==sha(cwc/'witnesses.json')
cross=next(r for r in wcw['rows'] if r['lift_mm']==42.)
assert cross['physical_envelope_overlap_demonstrated'] and cross['surface_gap_upper_bound_mm']<-.65
assert cross['separated_arclength_mm']>60 and cross['sample_center_distance_mm']<.002
assert next(r for r in wcw['rows'] if r['lift_mm']==9.)['gap_bound_mm']<.3
assert wcr['physical_parts_restored_unchanged']==209
assert wcr['source_candidate_sha256']==sha(cpc/'review.blend') and wcr['review_sha256']==sha(cwc/'review.blend')
for r in wcr['images']:assert r['sha256']==sha(cwc/r['file'])
for p,h in wcp['files'].items():assert sha(ROOT/p)==h,p
assert latest['CAM_tested_42mm_insertion']=='BLOCKED' and latest['CAM_sequence_tool_cases']==48

# The profiled tool is a more specific ASSUMED envelope, not a replacement
# vendor model or a waiver of the previous full installation failures.
cpt=HERE/'cam_profiled_tool'
pts=read(cpt/'screen.json');ptb=read(cpt/'both_anchors.json');ptx=read(cpt/'sensitivity.json')
ptl=read(cpt/'late_servo_sequence.json');ptr=read(cpt/'render_manifest.json');ptp=read(cpt/'review_manifest.json')
for r,script in [(pts,'check_CAM_profiled_tool.py'),(ptb,'check_CAM_two_anchor_tool_access.py'),
                 (ptx,'check_CAM_profile_sensitivity.py'),(ptl,'check_CAM_late_servo_sequence.py'),
                 (ptr,'render_CAM_profiled_tool.py'),(ptp,'publish_CAM_profiled_tool.py')]:
    assert r['script_sha256']==sha(HERE/script)
    assert r['source_main_sha256']==source['source_blend_sha256']
    assert not r['main_applied'] and r['whole_harness']=='BLOCKED' and not r['manufacturing_release']
assert pts['status']==ptr['status']==ptp['status']=='PASS'
assert ptb['status']==ptx['status']==ptl['status']=='BLOCKED'
assert len(pts['rows'])==28 and len(ptb['rows'])==26 and len(ptx['rows'])==4
assert [(r['profile'],r['angle_deg']) for r in pts['rows'] if r['status']=='PASS']==[('photo_profile',30.),('photo_profile',45.)]
assert [(r['anchor'],r['angle_deg']) for r in ptb['rows'] if r['status']=='PASS']==[('yaw',30.),('yaw',45.)]
pt30=next(r for r in ptb['rows'] if r['anchor']=='yaw' and r['angle_deg']==30.)
assert pt30['wire_minimum']['gap_lower_bound_mm']>1.3
pt30x=next(r for r in ptx['rows'] if r['case']=='expanded_transition' and r['angle_deg']==30.)
assert pt30x['status']=='PASS' and pt30x['wire_minimum']['gap_lower_bound_mm']>.6
assert next(r for r in ptx['rows'] if r['case']=='expanded_transition' and r['angle_deg']==45.)['status']=='BLOCKED'
for r in [q for q in ptb['rows'] if q['anchor']=='connector']:
    assert r['tail']['status']=='BLOCKED'
    assert {h['object'] for h in r['tail']['hits']}=={'Pitch_Servo'}
assert ptl['tie_work']['tail_fixture']['status']=='PASS'
assert ptl['tie_work']['tail_wires']['status']==ptl['pitch_servo_path']['status']==ptl['yaw_servo_path']['status']=='BLOCKED'
assert ptl['yaw_servo_path']['first_failure']['fixture']['hits'][0]['object']=='CAM_Tie_Head'
assert pts['helper_sha256']==sha(HERE/'check_CAM_sequence_tools.py')
assert ptb['helper_sha256']==sha(HERE/'check_CAM_profiled_tool.py')
assert ptx['helper_sha256']==ptl['helper_sha256']==sha(HERE/'check_CAM_two_anchor_tool_access.py')
assert ptr['source_candidate_sha256']==sha(cwc/'review.blend') and ptr['review_sha256']==sha(cpt/'review.blend')
assert ptr['physical_parts_restored_unchanged']==209 and len(ptr['images'])==5
assert ptr['screen_sha256']==sha(cpt/'screen.json') and ptr['both_anchors_sha256']==sha(cpt/'both_anchors.json')
for r in ptr['images']:assert r['sha256']==sha(cpt/r['file'])
for p,h in ptp['files'].items():assert sha(ROOT/p)==h,p
ptsrc=read(cpt/'sources/receipt.json')
assert ptsrc['dimensions_mm']=={'length':125,'width':60,'depth':19,'head_A':11,'jaw_B':10,'joint_D':6.5}
assert not ptsrc['physical_measurement'] and not ptsrc['tool_purchase_selected']
assert len(ptsrc['images'])==3
for r in ptsrc['images']:assert r['sha256']==sha(cpt/'sources'/r['file'])
assert ptb['source_receipt_sha256']==sha(cpt/'sources/receipt.json')
ptloose=read(HERE/'cam_sequence_loose/screen.json')
assert ptloose['status']=='BLOCKED' and not ptloose['main_applied'] and ptloose['whole_harness']=='BLOCKED'
assert ptloose['source_main_sha256']==source['source_blend_sha256']
assert ptloose['script_sha256']==sha(HERE/'screen_CAM_loose_assembly.py')
assert ptloose['curves_sha256']==sha(HERE/'cam_sequence_loose/curves.npz')
assert latest['CAM_yaw_profiled_tool_nominal']=='PASS' and latest['CAM_whole_connected_installation']=='BLOCKED'

# Real-thickness temporary tail route supersedes neither the old failed box
# nor the unresolved full assembly. Replay and widening evidence are local.
ctr=HERE/'cam_tail_ribbon'
tro=read(ctr/'screen.json');tri=read(ctr/'inner_corridor.json');trv=read(ctr/'verification.json')
trr=read(ctr/'render_manifest.json');trp=read(ctr/'review_manifest.json')
for r,script in [(tro,'check_CAM_tail_ribbon_access.py'),(tri,'check_CAM_tail_inner_corridor.py'),
                 (trv,'verify_CAM_tail_ribbon.py'),(trr,'render_CAM_tail_ribbon.py'),(trp,'publish_CAM_tail_ribbon.py')]:
    assert r['script_sha256']==sha(HERE/script)
    assert r['source_main_sha256']==source['source_blend_sha256']
    assert not r['main_applied'] and not r['manufacturing_release']
assert tro['status']=='BLOCKED' and len(tro['shapes'])==48 and not tro['passed']
assert tri['status']==trv['status']==trr['status']==trp['status']=='PASS'
assert len(tri['rows'])==36 and len(tri['passed'])==36
assert all(r['status']==r['fixture']['status']==r['wires']['status']=='PASS' for r in tri['rows'])
assert trv['source_screen_sha256']==sha(ctr/'inner_corridor.json')
assert trv['source_tail_sha256']==trr['tail_sha256']==sha(ctr/'inner_tail_34.npz')
assert trv['geometry']['components']==1 and trv['geometry']['non_two_face_edges']==0
assert abs(trv['geometry']['volume_mm3']-trv['geometry']['analytic_strip_volume_mm3'])<.025
assert trv['nominal']['wire_gap']['gap_lower_bound_mm']>3.6
assert trv['nominal']['rigid_excluding_start_contact']['nearest_below_3mm']['gap_mm']>=.5
assert len(trv['sensitivity_rows'])==9 and all(r['status']=='PASS' for r in trv['sensitivity_rows'])
assert min(r['rigid_excluding_start_contact']['nearest_below_3mm']['gap_mm'] for r in trv['sensitivity_rows'])>=.4
assert min(r['wire_gap']['gap_lower_bound_mm'] for r in trv['sensitivity_rows'])>3.5
assert tri['source_sections_sha256']==sha(ctr/'sections.json')
assert trr['source_candidate_sha256']==sha(cwc/'review.blend') and trr['review_sha256']==sha(ctr/'review.blend')
assert trr['physical_parts_preserved_unchanged']==209
for r in trr['images']:assert r['sha256']==sha(ctr/r['file'])
for p,h in trp['files'].items():assert sha(ROOT/p)==h,p
assert latest['CAM_connector_temporary_tail_route']=='PASS'
assert latest['CAM_connector_full_threading_tightening']=='NOT_TESTED'

# CAM-only seating preserves length but does not close the new screw stage.
cbl=HERE/'cam_board_last';bls=read(cbl/'screen.json');blv=read(cbl/'verification.json')
blr=read(cbl/'render_manifest.json');blp=read(cbl/'review_manifest.json')
assert bls['status']=='PASS' and len(bls['rows'])==16
assert all(r['status']=='PASS' and r['wire_gap_bound_mm']>=.3 for r in bls['rows'])
assert max(abs(r['curve']['analytical_total_length_change_mm']) for r in bls['rows'])<1e-9
assert min(r['curve']['minimum_radius_bound_mm'] for r in bls['rows'])>=6.9342
assert blv['status']=='BLOCKED' and all(r['status']=='PASS' for r in blv['rigid_sweeps'])
assert [r['screw'] for r in blv['driver_access'] if r['status']=='BLOCKED']==['CAM_Mount_Screw_0']
assert all({h['object'] for h in t['solid_hits']}=={'Pitch_Servo'} for t in blv['driver_access'][0]['trials'])
assert blr['status']==blp['status']=='PASS' and blr['physical_parts_preserved_unchanged']==209
for r,script in [(bls,'check_CAM_board_last.py'),(blv,'verify_CAM_board_last.py'),(blr,'render_CAM_board_last.py'),(blp,'publish_CAM_board_last.py')]:
    assert r['script_sha256']==sha(HERE/script)
    assert r.get('source_main_sha256',r.get('main_source_sha256'))==source['source_blend_sha256']
    assert not r['main_applied'] and r['whole_harness']=='BLOCKED'
assert bls['curves_sha256']==sha(cbl/'curves.npz')
assert blv['screen_sha256']==blr['screen_sha256']==sha(cbl/'screen.json')
assert blr['verification_sha256']==sha(cbl/'verification.json') and blr['review_sha256']==sha(cbl/'review.blend')
for r in blr['images']:assert r['sha256']==sha(cbl/r['file'])
for p,h in blp['files'].items():assert sha(ROOT/p)==h,p
assert latest['CAM_board_last_straight_driver']=='BLOCKED' and latest['CAM_board_last_position_count']==16

# Four proposed same-length socket screws close the nominal tool obstacle;
# their approval and the complete cable installation are still separate.
csk=HERE/'cam_socket_tool';sks=read(csk/'screen.json');skv=read(csk/'verification.json')
skr=read(csk/'render_manifest.json');skp=read(csk/'review_manifest.json')
assert sks['status']==skv['status']==skr['status']==skp['status']=='PASS'
assert sks['changes']['quantity_change']==0 and sks['changes']['printed_changes']==[] and sks['changes']['axis_changes']==[]
assert len(sks['changes']['proposed_replacements'])==4
assert all(r['status']=='PASS' for r in sks['screw_paths'])
for field in ['continuous_key_sweeps','entry_paths','grip_allocations','screw_arrival_paths']:
    assert len(skv[field])==4 and all(r['status']=='PASS' for r in skv[field])
assert len(skv['head_motion'])==130 and all(r['status']=='PASS' for r in skv['head_motion'])
assert skv['continuous_key_angle_range_deg']==[-30,30] and skv['continuous_key_axial_travel_mm']==8
assert sks['catalogue_tool']['short_leg_mm']==4.5 and sks['screw']['length_mm']==5
for record,script in [(sks,'check_CAM_socket_tool.py'),(skv,'verify_CAM_socket_tool.py'),(skr,'render_CAM_socket_tool.py'),(skp,'publish_CAM_socket_tool.py')]:
    assert record['script_sha256']==sha(HERE/script)
    assert record['source_main_sha256']==source['source_blend_sha256']
    assert record['main_applied'] is False and record['whole_harness']=='BLOCKED'
assert skv['screen_sha256']==skr['screen_sha256']==sha(csk/'screen.json')
assert skr['verification_sha256']==sha(csk/'verification.json') and skr['physical_parts_preserved_unchanged']==209
assert skr['review_sha256']==sha(csk/'review.blend')
for image in skr['images']:assert image['sha256']==sha(csk/image['file'])
for p,h in skp['files'].items():assert sha(ROOT/p)==h,p
for row in read(csk/'sources/receipt.json')['files']:
    assert row['status']=='PASS' and row['sha256']==sha(csk/'sources'/row['file'])
assert latest['CAM_socket_screw_candidate']=='PASS' and latest['CAM_socket_screw_candidate_main_applied'] is False
assert skp['approval']==latest['CAM_socket_screw_candidate_approval']=='PENDING_USER_CONFIRMATION'

# The later continuous wire-to-solid check is separate from the historical
# sixteen-pose check and does not grant continuous wire-to-wire clearance.
bws=read(cbl/'continuous_wire_solids.json')
assert bws['status']=='PASS' and not bws['unproved_intervals']
assert bws['source_main_sha256']==source['source_blend_sha256']
assert bws['script_sha256']==sha(HERE/'check_CAM_board_wire_sweeps.py')
assert bws['helper_sha256']==sha(HERE/'check_CAM_board_last.py')
assert bws['screen_sha256']==sha(cbl/'screen.json')
assert bws['continuous_wire_to_wire_packing']=='NOT_TESTED'
assert bws['minimum_wire_to_solid_surface_gap_mm']==.3 and bws['travel_mm']==6
assert not bws['main_applied'] and bws['whole_harness']=='BLOCKED'
for stage in ['mating','seating']:
    intervals=sorted((r['interval_mm'] for r in bws['passed_intervals'] if r['stage']==stage))
    assert intervals[0][0]==0 and intervals[-1][1]==6
    assert all(a[1]==b[0] for a,b in zip(intervals,intervals[1:]))
assert latest['CAM_board_last_continuous_wire_to_solids']=='PASS'
assert latest['CAM_board_last_continuous_wire_to_wire']=='PASS'
assert latest['CAM_board_last_continuous_intervals']==len(bws['passed_intervals'])==128

# Continuous packing closes the four-wire mating/seating substep. Preserve
# the new, separately incomplete forming investigation and its failures.
bpack=read(cbl/'continuous_packing.json')
assert bpack['status']=='PASS' and not bpack['unproved_intervals']
assert bpack['source_main_sha256']==source['source_blend_sha256']
assert bpack['script_sha256']==sha(HERE/'check_CAM_board_continuous_packing.py')
assert bpack['helper_sha256']==sha(HERE/'check_CAM_board_last.py')
assert bpack['source_screen_sha256']==sha(cbl/'screen.json')
assert len(bpack['static_subset_checks'])==14 and all(r['status']=='PASS' for r in bpack['static_subset_checks'])
assert all(r['status']=='PASS' for r in bpack['analytical_axis_separation'])
intervals=sorted(r['interval_mm'] for r in bpack['adaptive_intervals'])
assert len(intervals)==8 and intervals[0][0]==0 and intervals[-1][1]==6
assert all(a[1]==b[0] for a,b in zip(intervals,intervals[1:]))
assert bpack['arclength_deficit_upper_bound_mm']<.001
assert bpack['numerical_self_cutoff_mm']<bpack['self_contact_nonlocal_arclength_mm']==2
assert bpack['material_speed_bound_mm_per_mm']==1 and bpack['minimum_required_surface_gap_mm']==.3
assert bpack['curve_formation_and_terminal_feed']==bpack['tie_threading_tightening']=='NOT_TESTED'
assert bpack['whole_harness']=='BLOCKED' and not bpack['main_applied']
cfm=HERE/'cam_wire_forming';fms=read(cfm/'screen.json');fmr=read(cfm/'raised/screen.json')
fmw=read(cfm/'collision_witness.json');fmv=read(cfm/'render_manifest.json');fmp=read(cfm/'review_manifest.json')
for report,script in [(fms,'screen_CAM_wire_forming.py'),(fmr,'screen_CAM_wire_forming_raised.py'),
    (fmw,'check_CAM_forming_collision_witness.py'),(fmv,'render_CAM_wire_forming.py'),(fmp,'publish_CAM_installation_progress.py')]:
    assert report['script_sha256']==sha(HERE/script),script
    assert report['source_main_sha256']==source['source_blend_sha256']
    assert not report['main_applied'] and report['whole_harness']=='BLOCKED'
assert fms['status']=='BLOCKED' and len(fms['rows'])==41
assert fmr['status']=='PASS' and fmr['selected_amplitude_mm']==9
assert fmr['source_plain_screen_sha256']==sha(cfm/'screen.json')
assert fmr['curves_sha256']==sha(cfm/'raised/curves.npz')
assert len(fmr['trials'][-1]['rows'])==41 and all(r['status']=='PASS' for r in fmr['trials'][-1]['rows'])
assert fmr['trials'][0]['status']=='BLOCKED' and fmr['trials'][0]['amplitude_mm']==6
assert fmr['continuous_motion']==fmr['terminal_and_crimp_shapes']==fmr['wire_packing']=='NOT_TESTED'
assert fmw['status']=='PASS' and fmw['rejected_path_status']=='FAIL' and fmw['inside_witness']['sphere_inside_fraction']>.99
assert fmw['source_curves_sha256']==sha(cfm/'curves.npz')
assert fmv['source_raised_screen_sha256']==sha(cfm/'raised/screen.json')
assert fmv['review_sha256']==sha(cfm/'review.blend')
assert fmp['packing_sha256']==sha(cbl/'continuous_packing.json')
assert fmp['wire_solids_sha256']==sha(cbl/'continuous_wire_solids.json')
assert fmp['minimum_packing_gap_bound_mm']>=.3
for row in fmv['images']:assert row['sha256']==sha(cfm/row['file'])
for path,digest in fmp['files'].items():assert sha(ROOT/path)==digest,path
assert latest['CAM_initial_forming_direct']=='BLOCKED' and latest['CAM_initial_forming_raised_positions']=='PASS'
fm_contact=read(cfm/'terminals/screen.json');fm_cont=read(cfm/'continuous/screen.json')
fm_audit=read(cfm/'continuous/math_audit.json');fm_housed=read(cfm/'housed/screen.json')
fm_end=read(cfm/'end_approach/screen.json');fm_vis=read(cfm/'terminals/render_manifest.json')
fm_pub=read(cfm/'terminals/review_manifest.json')
fm_lift6=read(cfm/'lifted_end/screen.json');fm_lift2=read(cfm/'lifted_end2/screen.json')
for report,script in [(fm_contact,'check_CAM_forming_terminals.py'),(fm_cont,'check_CAM_forming_continuous.py'),
    (fm_audit,'audit_CAM_forming_bounds.py'),(fm_housed,'screen_CAM_housed_forming.py'),
    (fm_end,'check_CAM_forming_end_approach.py'),(fm_vis,'render_CAM_forming_contact_review.py'),
    (fm_pub,'publish_CAM_forming_contacts.py'),(fm_lift6,'screen_CAM_forming_lifted_end.py'),
    (fm_lift2,'screen_CAM_forming_lifted_end2.py')]:
    assert report['script_sha256']==sha(HERE/script),script
    assert report['source_main_sha256']==source['source_blend_sha256']
    assert not report['main_applied'] and report['whole_harness']=='BLOCKED' and not report['manufacturing_release']
assert fm_contact['status']==fm_audit['status']==fm_vis['status']==fm_pub['status']==fm_lift2['status']=='PASS'
assert fm_cont['status']==fm_lift6['status']=='BLOCKED'
assert fm_contact['contact_nominal_box_mm']==[.8,1.35,3.9]
assert fm_contact['contact_source_pdf_sha256']==sha(PARENT/'supplier_made_harness/recheck_20261004/JST_SH.pdf')
assert len(fm_contact['contact_rows'])==41 and all(x['status']=='PASS' for x in fm_contact['contact_rows'])
assert abs(fm_contact['nominal_contact_contact_gap_mm']-.2)<1e-8
assert fm_contact['contact_contact_0_3mm_margin']=='BLOCKED'
assert fm_contact['poses_sha256']==sha(cfm/'terminals/poses.npz')
assert fm_cont['source_raised_screen_sha256']==sha(cfm/'raised/screen.json')
assert fm_cont['source_terminal_screen_sha256']==sha(cfm/'terminals/screen.json')
assert not fm_cont['complete_coverage'] and len(fm_cont['unproved_intervals'])==31 and fm_cont['error']
fm_intervals=sorted(fm_cont['passed_intervals'],key=lambda x:x['interval'][0])
assert fm_intervals[0]['interval'][0]==0 and fm_intervals[-1]['interval'][1]<1
assert all(a['interval'][1]==b['interval'][0] for a,b in zip(fm_intervals,fm_intervals[1:]))
assert all(x['status']=='PASS' and x['interval'][1]>x['interval'][0] for x in fm_intervals)
assert fm_cont['amplitude_mm']==9 and fm_cont['wire_OD_mm']==.6604
assert fm_cont['ordinary_surface_margin_mm']==.3 and fm_cont['seating_nonpenetration_margin_mm']==0
assert fm_cont['minimum_contact_gap_lower_bound_mm']>=.3
assert any(x['failure'].get('gap_mm',1)<.3 for x in fm_cont['unproved_intervals'])
assert all(x['failure']['kind']=='contact' and x['failure']['object']=='Pitch_Cradle' for x in fm_cont['unproved_intervals'])
assert fm_cont['wire_to_wire']==fm_cont['wire_to_contact']==fm_cont['terminal_to_housing_insertion']=='NOT_TESTED'
assert len(fm_audit['shape_checks'])==len(fm_audit['velocity_diagnostics'])==51
assert fm_housed['status']==fm_end['status']=='BLOCKED'
assert [x['amplitude_mm'] for x in fm_housed['trials']]==[12,15,18]
assert any(x['housing']['hits'] for tr in fm_housed['trials'] for x in tr['rows'])
assert not any(h['physical_surface_intersection_witness'] for r in fm_end['rows'] for h in r['hits'])
assert fm_vis['source_terminal_screen_sha256']==sha(cfm/'terminals/screen.json')
assert fm_vis['source_housed_screen_sha256']==sha(cfm/'housed/screen.json')
assert fm_vis['review_sha256']==sha(cfm/'terminals/review.blend')
fm_source_instances=read(ROOT/'mechanical/reports/assembly_instances.json')
fm_dock_instances=[v for v in fm_source_instances.values() if v['group']=='dock']
assert len(fm_dock_instances)==5 and len(fm_source_instances)-len(fm_dock_instances)==209
# The render preserves every physical source object, including the separate
# five-piece maintenance cradle; robot-only checks above deliberately use209.
assert fm_vis['physical_source_objects_preserved']==len(fm_source_instances)
for row in fm_vis['images']:assert row['sha256']==sha(cfm/'terminals'/row['file'])
assert fm_pub['source_continuous_sha256']==sha(cfm/'continuous/screen.json')
assert fm_pub['source_math_audit_sha256']==sha(cfm/'continuous/math_audit.json')
assert fm_pub['continuous_passed_intervals']==len(fm_intervals) and fm_pub['continuous_status']=='BLOCKED'
assert fm_pub['new_lifted2_screen_sha256']==sha(cfm/'lifted_end2/screen.json')
assert fm_lift2['final_plug_lift_mm']==2 and fm_lift6['final_plug_lift_mm']==6
assert fm_lift2['final_endpoint_error_mm']<1e-8 and abs(fm_lift2['total_planar_length_change_mm'])<1e-8
assert fm_lift2['continuous_forming']==fm_lift2['continuous_mating']=='NOT_TESTED'
assert all(x['status']=='PASS' for x in fm_lift2['trials'][-1]['rows']+fm_lift2['mating_rigid_samples'])
assert len(fm_lift2['mating_rigid_samples'])==25
assert any(x['status']=='BLOCKED' for x in fm_lift6['mating_rigid_samples'])
assert fmp['forming_contacts_delivery_sha256']==sha(cfm/'terminals/review_manifest.json')
assert fmp['forming_continuous_to_stage_solids']=='BLOCKED'
for path,digest in fm_pub['files'].items():assert sha(ROOT/path)==digest,path
assert latest['CAM_initial_forming_continuous']=='BLOCKED' and latest['CAM_initial_forming_terminal_shapes']=='PASS'
assert latest['CAM_initial_forming_continuous_intervals']==len(fm_intervals)
assert latest['CAM_initial_forming_wire_packing']=='BLOCKED' and latest['CAM_initial_forming_housed_trials']=='BLOCKED'
assert not latest['CAM_initial_forming_continuous_complete_coverage']
assert latest['CAM_initial_forming_lift2_positions']=='PASS' and latest['CAM_initial_forming_lift2_continuous']=='NOT_TESTED'

# The new forming screen includes upstream conductors and preserves its
# real nominal collision. A successful PCB descent cannot override it.
l2=cfm/'lifted_end2';l2board=read(l2/'board_descent_continuous.json');l2pack=read(l2/'packing_screen.json')
l2witness=read(l2/'packing_collision_witness.json');l2stop=read(l2/'continuous_interrupted.json')
l2vis=read(l2/'render_manifest.json');l2pub=read(l2/'review_manifest.json')
for data,script in [(l2board,'check_CAM_lift2_board_descent.py'),(l2pack,'check_CAM_lift2_forming_packing.py'),
                    (l2vis,'render_CAM_lift2_review.py'),(l2pub,'publish_CAM_lift2_review.py')]:
    assert data['script_sha256']==sha(HERE/script),script
    assert data['source_main_sha256']==source['source_blend_sha256']
    assert not data['main_applied'] and data['whole_harness']=='BLOCKED' and not data['manufacturing_release']
assert l2board['status']=='PASS' and l2board['complete_coverage'] and not l2board['unproved_intervals'] and not l2board['error']
l2intervals=sorted(l2board['passed_intervals'],key=lambda x:x['interval_mm'][0])
assert len(l2intervals)==1057 and l2intervals[0]['interval_mm'][0]==2 and l2intervals[-1]['interval_mm'][1]==8
assert all(x['status']=='PASS' and x['interval_mm'][1]>x['interval_mm'][0] for x in l2intervals)
assert all(x['interval_mm'][1]==y['interval_mm'][0] for x,y in zip(l2intervals,l2intervals[1:]))
assert all(x['status']=='PASS' and x['intersection_mm3']<1e-7 for x in l2board['exact_convex_plug_sweep'])
assert l2board['source_finite_screen_sha256']==sha(l2/'screen.json')
assert l2board['supersedes_distance_only_diagnostic_sha256']==sha(l2/'board_descent_distance_bound.json')
l2old=read(l2/'board_descent_distance_bound.json')
assert l2old['status']=='BLOCKED' and l2old['script_sha256']==sha(HERE/'check_CAM_lift2_board_distance_bound.py')
assert l2pack['status']==l2pack['wire_packing_status']=='BLOCKED' and len(l2pack['wire_rows'])==41
assert l2witness['status']=='FAIL' and l2witness['source_packing_sha256']==sha(l2/'packing_screen.json')
assert l2witness['upper_bound_actual_centre_distance_mm']<l2witness['combined_radii_mm']==.6604
assert l2stop['status']=='NOT_TESTED' and not l2stop['complete_coverage']
assert l2stop['blocking_witness_sha256']==sha(l2/'packing_collision_witness.json')
assert l2stop['source_script_sha256']==sha(HERE/'check_CAM_forming_lift2_continuous.py')
for sub,script in [('apex_revision','screen_CAM_lift2_forming_apex.py'),('side_turn','screen_CAM_lift2_forming_side_turn.py'),
                   ('sequential_bends','screen_CAM_lift2_sequential_bends.py'),('one_wire_at_a_time','screen_CAM_lift2_one_wire_at_a_time.py')]:
    d=read(l2/sub/'screen.json');assert d['status']=='BLOCKED' and d['script_sha256']==sha(HERE/script)
    assert d['source_main_sha256']==source['source_blend_sha256'] and not d['main_applied']
    assert all(t['status']=='BLOCKED' and t['rows'][-1]['status']=='BLOCKED' for t in d['trials'])
assert l2vis['physical_source_objects_preserved']==len(fm_source_instances)
assert l2vis['review_sha256']==sha(l2/'review.blend')
for row in l2vis['images']:assert row['sha256']==sha(l2/row['file'])
assert l2pub['status']=='PASS' and l2pub['forming_wire_packing']=='PASS' and l2pub['continuous_forming_complete']
assert l2pub['historical_simultaneous_wire_packing']=='BLOCKED'
for path,digest in l2pub['files'].items():assert sha(ROOT/path)==digest,path
assert fm_pub['new_lifted2_delivery_sha256']==sha(l2/'review_manifest.json')
assert latest['CAM_lift2_board_descent_continuous']=='PASS' and latest['CAM_lift2_board_descent_intervals']==len(l2intervals)
assert latest['CAM_lift2_nominal_wire_collision']=='FAIL' and latest['CAM_lift2_revised_forming_trials']=='PASS'

# The replacement order is a finite path with every other conductor present.
# Nominal terminal nonpenetration cannot certify continuous motion, the
# generic terminal margin, crimp geometry or supplier manufacturing release.
outer=read(l2/'outer_first_forming/screen.json');outercontacts=read(l2/'outer_first_forming/contacts.json')
seq=read(l2/'contact_refined_forming/screen.json');seqvis=read(l2/'contact_refined_forming/render_manifest.json')
for data,script in [(outer,'plan_CAM_outer_first_forming.py'),(outercontacts,'check_CAM_outer_first_contacts.py'),
                    (seq,'refine_CAM_outer_contact_path.py'),(seqvis,'render_CAM_contact_refined_forming.py')]:
    assert data['script_sha256']==sha(HERE/script),script
    assert data['source_main_sha256']==source['source_blend_sha256'] and not data['main_applied']
    assert data['whole_harness']=='BLOCKED' and not data['manufacturing_release']
assert outer['status']=='PASS' and outercontacts['nominal_nonpenetration']=='BLOCKED'
assert all(r['status']=='PASS' for r in outercontacts['static_wire_fixture_checks'])
assert len(outercontacts['static_wire_fixture_checks'])==8
assert seq['status']=='PASS' and seq['first_unresolved_step'] is None and seq['wire_order']==[3,2,1,0]
assert seq['source_previous_path_sha256']==sha(l2/'outer_first_forming/screen.json')
assert seq['source_previous_contacts_sha256']==sha(l2/'outer_first_forming/contacts.json')
assert seq['curves_sha256']==sha(l2/'contact_refined_forming/curves.npz')
assert len(seq['all_contact_positions'])==644 and all(r['status']=='PASS' for r in seq['all_contact_positions'])
for s in seq['stages']:
    nodes=s['path'];assert s['status']=='PASS' and len(nodes)==41
    assert nodes[0]['fraction']==0 and nodes[-1]['fraction']==1
    assert nodes[0]['side_angle_deg']==nodes[-1]['side_angle_deg']==0
    for a,b in zip(nodes,nodes[1:]):
        assert abs(b['fraction']-a['fraction']-.025)<1e-9
        edges=a['finite_edge_checks_to_next'];assert len(edges)==3
        assert all(r['status']=='PASS' and a['fraction']<r['fraction']<b['fraction'] for r in edges)
assert seq['generic_0_3mm_contact_packing']=='BLOCKED' and seq['continuous_motion']=='NOT_TESTED'
assert seq['wire_structure_margin_mm']==seq['contact_structure_margin_mm']==.3
assert seq['bare_contact_wire_nonpenetration_margin_mm']==0
assert seqvis['source_path_sha256']==sha(l2/'contact_refined_forming/screen.json')
assert seqvis['physical_source_objects_preserved']==len(fm_source_instances)
assert seqvis['review_sha256']==sha(l2/'contact_refined_forming/review.blend')
for r in seqvis['images']:assert r['sha256']==sha(l2/'contact_refined_forming'/r['file'])
assert l2pub['new_sequence_finite_status']=='PASS' and l2pub['new_sequence_positions']==644
assert latest['CAM_sequential_forming_positions']==latest['CAM_sequential_forming_contact_nonpenetration']=='PASS'
assert latest['CAM_sequential_forming_position_count']==644
assert latest['CAM_sequential_forming_continuous']=='BLOCKED' and latest['CAM_sequential_forming_contact_margin']=='BLOCKED'
assert latest['CAM_sequential_forming_wire_intersection']=='FAIL' and latest['CAM_sequential_forming_finite_evidence_superseded']
assert not latest['CAM_sequential_forming_main_applied']

# Later evidence restricts the earlier finite PASS: a real intermediate
# conductor overlap was found, while the revised local search has its own
# explicit coverage. Do not silently turn partial coverage into a full path.
contdir=l2/'contact_refined_forming/continuous'
sc=read(contdir/'screen.json');sd=read(contdir/'first_failure_segment_distance.json')
sv=read(contdir/'render_manifest.json');ma=read(contdir/'math_audit.json')
rc=read(l2/'contact_refined_forming/return_corridor/screen.json')
rcc=read(l2/'contact_refined_forming/return_corridor/continuous/screen.json')
kc=read(l2/'contact_refined_forming/critical_return_continuous/screen.json')
for data,script in [(sc,'check_CAM_sequential_continuous.py'),(sd,'diagnose_CAM_continuous_margin.py'),
    (sv,'render_CAM_continuous_return_conflict.py'),(ma,'audit_CAM_sequential_displacement.py'),
    (rc,'refine_CAM_return_corridor.py'),(rcc,'check_CAM_return_corridor_continuous.py'),
    (kc,'plan_CAM_critical_return_continuous.py')]:
    assert data['script_sha256']==sha(HERE/script),script
    assert data['source_main_sha256']==source['source_blend_sha256'] and not data['main_applied']
assert sc['status']=='BLOCKED' and not sc['complete_coverage'] and sc['nominal_intermediate_failures']
assert sc['source_path_sha256']==sha(l2/'contact_refined_forming/screen.json')
assert sd['source_failure_sha256']==sha(contdir/'screen.json') and sd['real_intersection']=='FAIL'
nearest=sd['closest'];points=nearest['points_mm']
point_distance=sum((a-b)**2 for a,b in zip(*points))**.5
assert abs(point_distance-nearest['polyline_distance_mm'])<1e-8
assert point_distance+nearest['smooth_curve_error_sum_mm']+nearest['numeric_guard_mm']<.6604
assert sv['source_diagnosis_sha256']==sha(contdir/'first_failure_segment_distance.json')
assert sv['review_sha256']==sha(contdir/'conflict_review.blend') and sv['physical_source_objects_preserved']==214
for r in sv['images']:assert r['sha256']==sha(contdir/r['file'])
assert ma['status']=='PASS' and len(ma['rows'])==120 and not ma['complete_geometric_clearance_proof']
assert all(r['max_wire_violation_mm']<=0 and r['contact_max_fraction_of_bound']<=1 for r in ma['rows'])
assert rc['status']=='PASS' and rcc['status']=='BLOCKED' and not rcc['complete_local_coverage']
assert not kc['complete_last_wire_coverage'] and kc['whole_harness']=='BLOCKED' and not kc['manufacturing_release']
assert latest['CAM_critical_return_continuous']==kc['status']
assert latest['CAM_critical_return_complete_local_coverage']==kc['complete_local_coverage']
assert not latest['CAM_critical_return_full_sequence_coverage']
if kc['status']=='PASS':
    local_intervals=sorted(kc['accepted_intervals'],key=lambda r:r['interval'][0])
    assert kc['complete_local_coverage'] and kc['unresolved'] is None
    assert local_intervals[0]['interval'][0]==.75 and local_intervals[-1]['interval'][1]==.875
    assert all(a['interval'][1]==b['interval'][0] for a,b in zip(local_intervals,local_intervals[1:]))
else:assert not kc['complete_local_coverage'] and kc['unresolved'] is not None
assert l2pub['new_sequence_continuous']=='BLOCKED' and l2pub['new_sequence_nominal_wire_collision']=='FAIL'
assert l2pub['critical_return_continuous_status']==kc['status'] and not l2pub['critical_return_full_sequence_coverage']

# Current negative-side route has separate full receipts. Preserve all old
# failed controls above; a local PASS never turns them into a passed path.
newdir=l2/'contact_refined_forming'
complete=read(newdir/'negative_complete/screen.json')
junctions=read(newdir/'negative_complete/junctions.json')
first3=read(newdir/'first_three_continuous/screen.json')
lastwire=read(newdir/'negative_tail/screen.json')
returnvis=read(newdir/'negative_return_branch/render_manifest.json')
for report,script in [(complete,'verify_CAM_complete_forming.py'),(junctions,'check_CAM_forming_junctions.py'),
    (first3,'check_CAM_first_three_continuous.py'),(lastwire,'check_CAM_negative_tail.py'),
    (returnvis,'render_CAM_negative_return.py')]:
    assert report['status']=='PASS' and report['script_sha256']==sha(HERE/script)
    assert report['source_main_sha256']==source['source_blend_sha256']
    assert not report['main_applied'] and not report['manufacturing_release']
    assert report['whole_harness']=='BLOCKED'
for path,digest in complete['source_files'].items():assert sha(ROOT/path)==digest,path
assert complete['complete_four_wire_forming_coverage'] and complete['stage_boundary_identity']=='PASS'
assert complete['wire_order']==[3,2,1,0] and not complete['wire_order_is_electrical_pinmap']
assert complete['wire_outer_diameter_mm']==.6604 and complete['ordinary_margin_mm']==.3
assert complete['bare_contact_margin_mm']==0 and complete['generic_0_3mm_contact_packing']=='BLOCKED'
assert complete['material_length_invariant']=='PASS' and not complete['bend_bound_is_material_qualification']
assert complete['nominal_curve_radius_lower_bound_mm']>7.1
assert complete['retained_static_wire_pairs']==12 and len(junctions['endpoints'])==8
assert all(r['status']=='PASS' and r['wire_to_static_maximum_error_mm']<1e-8
    and r['contact_symmetric_difference_mm3']<1e-7 and r['nominal_endpoint_failure'] is None
    for r in junctions['endpoints'])
assert first3['complete_first_three_coverage'] and lastwire['complete_last_wire_coverage']
assert not first3['unproved_intervals'] and not lastwire['unproved_intervals']
allintervals=first3['passed_intervals']+lastwire['combined_intervals']
assert complete['continuous_interval_count']==len(allintervals)
for stage in range(4):
    intervals=sorted([r for r in allintervals if r['stage']==stage],key=lambda r:r['interval'][0])
    assert intervals[0]['interval'][0]==0 and intervals[-1]['interval'][1]==1
    assert all(a['interval'][1]==b['interval'][0] for a,b in zip(intervals,intervals[1:]))
    assert all(r['status']=='PASS' and r['interval'][0]<r['interval'][1] for r in intervals)
    assert complete['coverage'][stage]['interval_count']==len(intervals)
assert returnvis['source_path_sha256']==sha(newdir/'negative_return_branch/screen.json')
assert returnvis['physical_source_objects_preserved']==214
assert returnvis['review_sha256']==sha(newdir/'negative_return_branch/review.blend')
for r in returnvis['images']:
    assert r['sha256']==sha(newdir/'negative_return_branch'/r['file'])
    assert r['all_four_wires_and_contacts_present']
assert l2pub['current_forming_receipt_sha256']==sha(newdir/'negative_complete/screen.json')
assert l2pub['current_forming_interval_count']==complete['continuous_interval_count']
assert latest['CAM_current_forming_continuous']=='PASS' and latest['CAM_current_forming_complete_coverage']
assert latest['CAM_current_forming_interval_count']==complete['continuous_interval_count']
assert latest['CAM_current_forming_receipt_sha256']==sha(newdir/'negative_complete/screen.json')
assert latest['CAM_current_forming_boundary_identity']=='PASS' and not latest['CAM_current_forming_main_applied']
for key in ['feed_to_start','terminal_insertion','ties','other_seven_cross_joint_wires']:
    assert complete[key]=='NOT_TESTED'
assert complete['complete_connected_installation']=='BLOCKED'
approachdir=newdir/'housing_approach'
housing=read(approachdir/'screen.json');housingvis=read(approachdir/'render_manifest.json')
for report,script in [(housing,'screen_CAM_housing_approach.py'),(housingvis,'render_CAM_housing_approach.py')]:
    assert report['status']=='PASS' and report['script_sha256']==sha(HERE/script)
    assert report['source_main_sha256']==source['source_blend_sha256']
    assert not report['main_applied'] and not report['manufacturing_release']
assert housing['source_forming_sha256']==sha(newdir/'negative_complete/screen.json')
assert housing['approach_vector_mm']==[0.,0.,-8.] and housing['ordinary_margin_mm']==.3
assert len(housing['rigid_checks'])==219 and len(housing['wire_checks'])==12
assert all(r['status']=='PASS' for r in housing['rigid_checks']+housing['wire_checks'])
assert housing['terminal_cavity_and_lance_fit']=='BLOCKED' and housing['contact_insertion_process']=='NOT_TESTED'
assert housingvis['source_screen_sha256']==sha(approachdir/'screen.json')
assert housingvis['physical_source_objects_preserved']==214 and housingvis['review_sha256']==sha(approachdir/'review.blend')
for row in housingvis['images']:
    assert row['sha256']==sha(approachdir/row['file'])
    assert row['transparent_for_inspection_only']==['Pitch_Cradle']
assert l2pub['housing_external_approach']=='PASS' and l2pub['housing_contact_insertion']=='NOT_TESTED'
assert l2pub['housing_approach_receipt_sha256']==sha(approachdir/'screen.json')
assert latest['CAM_housing_external_approach']=='PASS' and latest['CAM_housing_terminal_insertion']=='NOT_TESTED'

# Root-tie tool clearance now retains the complete current forming fixture.
# Its nominal tool result must not erase the separate margin and feed failures.
rootdir=newdir/'root_tie_access'
roottool=read(rootdir/'screen.json');rootvis=read(rootdir/'render_manifest.json')
rootfeed=read(rootdir/'contact_feed.json')
for report,script,status in [(roottool,'check_CAM_forming_tie_access.py','PASS'),
    (rootvis,'render_CAM_forming_tie_access.py','PASS'),
    (rootfeed,'check_CAM_root_contact_feed.py','BLOCKED')]:
    assert report['status']==status and report['script_sha256']==sha(HERE/script)
    assert report['source_main_sha256']==source['source_blend_sha256'] and not report['main_applied']
for report in [roottool,rootfeed]:
    assert report['helper_sha256']==sha(HERE/'check_CAM_sequential_continuous.py')
    assert report['source_forming_sha256']==sha(newdir/'negative_complete/screen.json')
    assert report['whole_harness']=='BLOCKED' and not report['manufacturing_release']
for key,filename in [('bench','bench_access.json'),('tool','cutter_allocation.npz'),
    ('sweep','cutter_swept.npz'),('tie_head','oriented_head.npz'),('tail_corridor','tail_corridor.npz')]:
    assert roottool['source_'+key+'_sha256']==sha(HERE/'cam_tie_install'/filename)
fixture_ids={r['object'] for r in housing['rigid_checks']}
assert roottool['source_fixture_count']==len(roottool['source_fixture_ids'])==219
assert set(roottool['source_fixture_ids'])==set(rootfeed['all_fixture_ids'])==fixture_ids
assert roottool['wire_portions']==12 and roottool['free_contact_count']==4
assert roottool['straight_approach_mm']==60 and roottool['ordinary_wire_margin_mm']==.3
assert len(roottool['tool_sweep_construction_checks'])==2
assert all(r['status']=='PASS' and r['symmetric_difference_mm3']<1e-7
           for r in roottool['tool_sweep_construction_checks'])
assert [r['angle_about_tail_axis_deg'] for r in roottool['trials']]==[0,-15,15,-30,30,-60,60,-90,90,180]
assert roottool['nominal_clear_angles_deg']==[0,15]
for trial in roottool['trials']:
    assert {r['object'] for r in trial['rigid_checks']}==fixture_ids
    assert len(trial['wire_checks'])==12 and len(trial['contact_checks'])==4
    if trial['angle_about_tail_axis_deg'] not in [0,15]:
        assert trial['nominal_tool_sweep']=='BLOCKED'
        continue
    assert trial['nominal_tool_sweep']=='PASS' and trial['general_0_3mm_allowance']=='BLOCKED'
    assert all(r['nominal_nonpenetration']=='PASS' for r in trial['rigid_checks'])
    assert all(r['status']=='PASS' for r in trial['wire_checks']+trial['contact_checks'])
    short=[r for r in trial['rigid_checks'] if r['general_0_3mm_allowance']!='PASS']
    assert {r['object'] for r in short}=={'CAM_Tie_Head','CAM_Tie_Band'}
    assert all(abs(r['gap_mm']-.25)<1e-6 for r in short)
tail=roottool['tail_corridor']
assert tail['status']=='PASS' and {r['object'] for r in tail['rigid_checks']}==fixture_ids
assert len(tail['wire_checks'])==12 and len(tail['contact_checks'])==4
assert all(r['nominal_nonpenetration']=='PASS' for r in tail['rigid_checks'])
assert all(r['status']=='PASS' for r in tail['wire_checks']+tail['contact_checks'])
assert {r['object'] for r in tail['rigid_checks'] if r['expected_boundary_at_tail_exit']}=={'CAM_Tie_Head','CAM_Tie_Band'}
for key in ['tool_closure_and_cut','manipulation_and_force','flexible_tie_threading_and_tightening',
            'complete_initial_feed','actual_cutter_grasp','all_anchors']:
    assert roottool[key]=='NOT_TESTED'
assert rootfeed['contact_dimensions_mm']==[.8,1.35,3.9]
assert not rootfeed['wire_or_tie_removed_to_force_pass']
assert rootfeed['real_terminal_collision']==rootfeed['all_alternative_routes']=='NOT_TESTED'
assert len(rootfeed['rows'])==4
for row in rootfeed['rows']:
    assert row['status']=='BLOCKED' and row['translation_range_relative_root_mm']==[-2,6]
    for key in ['sweep_intersections','witness_intersections']:
        assert {r['object'] for r in row[key]}=={'Pitch_Yoke','CAM_Tie_Band'}
        assert all(r['intersection_mm3']>1e-7 for r in row[key])
assert rootvis['helper_sha256']==sha(HERE/'render_CAM_contact_refined_forming.py')
assert rootvis['source_screen_sha256']==sha(rootdir/'screen.json')
assert rootvis['physical_source_objects_preserved']==214 and rootvis['complete_harness']=='BLOCKED'
assert rootvis['review_sha256']==sha(rootdir/'review.blend')
for row in rootvis['images']:assert row['sha256']==sha(rootdir/row['file'])
for published,keys in [(l2pub,('root_tie_tool_nominal','root_tie_general_rigid_margin',
    'root_tie_outward_tail_space','root_tie_tight_contact_feed','root_tie_full_installation')),
    (latest,('CAM_root_tie_cutter_nominal','CAM_root_tie_general_rigid_margin',
    'CAM_root_tie_outward_tail_space','CAM_root_tie_tight_contact_feed','CAM_root_tie_full_installation'))]:
    assert [published[k] for k in keys]==['PASS','BLOCKED','PASS','BLOCKED','NOT_TESTED']
assert l2pub['root_tie_tool_receipt_sha256']==latest['CAM_root_tie_tool_receipt_sha256']==sha(rootdir/'screen.json')
assert l2pub['root_tie_feed_receipt_sha256']==latest['CAM_root_tie_feed_receipt_sha256']==sha(rootdir/'contact_feed.json')

# Uninstalled-tie seating is a separate completed substep; no initial-feed claim.
rsdir=newdir/'root_seating/aligned_tails'
rscheck=read(rsdir/'verification.json')
assert rscheck['status']=='PASS' and rscheck['script_sha256']==sha(HERE/'verify_CAM_root_seating.py')
assert rscheck['source_main_sha256']==source['source_blend_sha256']
for filename,digest in rscheck['source_files'].items():assert sha(ROOT/filename)==digest,filename
assert rscheck['finite_positions']==21 and rscheck['continuous_intervals']==256
assert rscheck['complete_offset_coverage']==[0.,1.5]
assert rscheck['minimum_terminal_straight_whole_family_lower_mm']>5.2
assert rscheck['physical_source_objects_preserved']==214
assert rscheck['full_feed_or_assembly_identity']=='NOT_TESTED'
assert not rscheck['main_applied'] and not rscheck['manufacturing_release'] and rscheck['whole_harness']=='BLOCKED'
assert l2pub['root_wire_seating_receipt_sha256']==latest['CAM_root_wire_seating_receipt_sha256']==sha(rsdir/'verification.json')
assert l2pub['root_wire_seating_continuous']==latest['CAM_root_wire_seating_continuous']=='PASS'
assert l2pub['root_wire_seating_intervals']==latest['CAM_root_wire_seating_intervals']==256
assert l2pub['initial_terminal_bypass']==latest['CAM_initial_terminal_bypass']=='BLOCKED'
assert l2pub['tie_threading_and_tightening']==latest['CAM_tie_threading_and_tightening']=='NOT_TESTED'
assert l2pub['terminal_catalogue_span_is_complete_envelope'] is False
assert latest['CAM_terminal_catalogue_span_is_complete_envelope'] is False
extra=HERE/'ssh_catalogue_addendum';extra_source=read(extra/'retrieval.json')
assert extra_source['status']==200 and extra_source['content_type']=='application/pdf'
assert extra_source['sha256']==sha(extra/'JST_eLBT.pdf')
assert (extra/'JST_eLBT.pdf').read_bytes().startswith(b'%PDF-')
assert not extra_source['manufacturing_release']
assert (extra/'README.md').is_file() and (extra/'contact_page2.png').is_file()

# Source progress does not qualify the still-rejected initial feed candidates.
supdir=HERE/'supplier_source_update';supcheck=read(supdir/'verification.json')
assert supcheck['status']=='PASS' and supcheck['script_sha256']==sha(HERE/'publish_supplier_source_update.py')
for name,digest in supcheck['source_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in supcheck['protected_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in supcheck['outputs'].items():assert sha(supdir/name)==digest,name
assert supcheck['guide_feed_candidates']==16 and supcheck['guide_feed_passes']==0
assert supcheck['upright_positions']==21 and supcheck['raised_candidates']==3
assert supcheck['raised_positions_per_candidate']==21 and supcheck['raised_candidate_passes']==0
assert supcheck['initial_feed_to_root_seating']=='BLOCKED'
assert supcheck['staged_radius_certificate']=='NOT_TESTED'
assert not supcheck['source_dimensions_are_complete_terminal_envelope']
assert not supcheck['main_applied'] and not supcheck['manufacturing_release']
assert supcheck['vertical_free_feed']==latest['CAM_vertical_free_feed']=='PASS'
assert supcheck['vertical_feed_allocations']==8
assert supcheck['vertical_feed_receipt_sha256']==latest['CAM_vertical_free_feed_receipt_sha256']
assert supcheck['vertical_feed_scope']==latest['CAM_vertical_free_feed_scope']
assert supcheck['progressive_staging']==latest['CAM_progressive_staging']=='BLOCKED'
assert supcheck['progressive_staging_positions']==latest['CAM_progressive_staging_positions']==41
assert supcheck['public_M5_reference']=='PASS' and supcheck['actual_servo_horn_interface']=='BLOCKED'
ordered_dir=HERE/'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/ordered_feed_recovery'
ordered_pub=read(ordered_dir/'publication.json')
assert ordered_pub['status']=='PASS' and ordered_pub['script_sha256']==sha(HERE/'publish_CAM_ordered_feed.py')
assert sha(ordered_dir/'publication.json')==supcheck['ordered_publication_sha256']==latest['CAM_ordered_publication_sha256']
for name,digest in ordered_pub['source_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in ordered_pub['outputs'].items():assert sha(ordered_dir/name)==digest,name
assert ordered_pub['feed_finite_positions']==latest['CAM_ordered_terminal_feed_positions']==4205
assert ordered_pub['recovery_finite_positions']==latest['CAM_ordered_recovery_positions']==41
assert ordered_pub['retraction_sweeps']==4 and latest['CAM_ordered_retraction_sweep']=='PASS'
assert ordered_pub['boundary_match']==latest['CAM_ordered_boundary_match']=='PASS'
assert ordered_pub['feed_continuous']==ordered_pub['recovery_continuous']==latest['CAM_ordered_continuous']==supcheck['ordered_continuous']=='PASS'
assert ordered_pub['feed_continuous_intervals']==latest['CAM_ordered_feed_continuous_intervals']==supcheck['ordered_feed_continuous_intervals']==1228
assert ordered_pub['recovery_continuous_intervals']==latest['CAM_ordered_recovery_continuous_intervals']==supcheck['ordered_recovery_continuous_intervals']==256
assert ordered_pub['body_supply']==latest['CAM_body_supply']==supcheck['ordered_body_supply']=='BLOCKED'
assert ordered_pub['body_supply_audit']=='PASS'
assert not ordered_pub['main_applied'] and not ordered_pub['manufacturing_release']
assert ordered_pub['whole_harness']=='BLOCKED'
large_dir=ordered_dir.parent/'large_contact_downstream'
large_pub=read(large_dir/'publication.json')
assert large_pub['status']=='PASS' and large_pub['script_sha256']==sha(HERE/'publish_CAM_large_contact_downstream.py')
assert sha(large_dir/'publication.json')==ordered_pub['larger_contact_publication_sha256']==supcheck['larger_contact_publication_sha256']==latest['CAM_large_contact_publication_sha256']
for name,digest in large_pub['source_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in large_pub['outputs'].items():assert sha(large_dir/name)==digest,name
assert large_pub['contact_dimensions_mm']==[1.,1.8,4.1]
assert large_pub['root_seating_continuous']==large_pub['forming_continuous']==latest['CAM_large_contact_seating']==latest['CAM_large_contact_forming']=='PASS'
assert large_pub['root_seating_intervals']==latest['CAM_large_contact_seating_intervals']==ordered_pub['larger_contact_seating_intervals']==256
assert large_pub['forming_intervals']==latest['CAM_large_contact_forming_intervals']==ordered_pub['larger_contact_forming_intervals']==1735
assert large_pub['forming_complete'] and not large_pub['main_applied'] and not large_pub['manufacturing_release']
assert large_pub['whole_harness']==large_pub['body_supply']=='BLOCKED'
large_forming=read(large_dir/'start_delay/continuous.json')
assert large_forming['status']=='PASS' and large_forming['complete_coverage'] and large_forming['error'] is None
assert not large_forming['unproved_intervals'] and len(large_forming['passed_intervals'])==1735
assert len(large_forming['boundary_rows'])==8 and all(r['status']=='PASS' for r in large_forming['boundary_rows'])

# Keep upper-stage and local neck candidate passes separate from the rejected
# original path and unfinished whole-member assembly/material supply.
body_review_dir=ordered_dir.parent/'body_supply/complete_head'
body_review=read(body_review_dir/'publication.json')
assert body_review['status']=='PASS' and body_review['script_sha256']==sha(HERE/'publish_CAM_body_supply_review.py')
assert sha(body_review_dir/'publication.json')==latest['CAM_body_supply_publication_sha256']==supcheck['body_supply_review_sha256']
for name,digest in body_review['source_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in body_review['protected_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in body_review['outputs'].items():assert sha(body_review_dir/name)==digest,name
assert body_review['physical_source_objects']==209 and body_review['archived_blend_source_objects']==214
assert body_review['full_head_old_sequence']==latest['CAM_full_member_body_sequence']=='BLOCKED'
assert body_review['larger_contact_neck']==latest['CAM_larger_contact_neck']=='BLOCKED'
assert body_review['neck_roll_offset_trials']==latest['CAM_neck_pose_trials']==49
assert body_review['coupled_variants']==10 and body_review['images_visually_reviewed']
assert body_review['whole_harness']=='BLOCKED' and not body_review['main_applied'] and not body_review['manufacturing_release']

neck_candidate_dir=body_review_dir/'larger_neck_candidate'
neck_candidate=read(neck_candidate_dir/'publication.json')
assert neck_candidate['status']=='PASS' and neck_candidate['script_sha256']==sha(HERE/'publish_CAM_larger_neck_candidate.py')
assert sha(neck_candidate_dir/'publication.json')==body_review['larger_neck_candidate_publication_sha256']==latest['CAM_larger_neck_candidate_publication_sha256']==supcheck['larger_neck_candidate_publication_sha256']
for name,digest in neck_candidate['source_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in neck_candidate['protected_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in neck_candidate['outputs'].items():assert sha(neck_candidate_dir/name)==digest,name
assert neck_candidate['local_continuous_neck']==body_review['larger_neck_candidate']==latest['CAM_larger_neck_candidate']==supcheck['larger_neck_candidate']=='PASS'
assert not any([neck_candidate['main_applied'],body_review['larger_neck_candidate_main_applied'],latest['CAM_larger_neck_candidate_main_applied'],supcheck['larger_neck_candidate_main_applied']])
assert neck_candidate['contact_evidence']=='ASSUMED' and neck_candidate['contact_dimensions_mm']==[1.,1.8,4.1]
assert neck_candidate['source_objects']==209 and neck_candidate['mating_allocations']==29 and neck_candidate['fixed_wires']==14
assert neck_candidate['four_directions']==4 and neck_candidate['intervals_per_direction']==410
assert min(neck_candidate['contact_gap_bound_mm'],neck_candidate['wire_gap_bound_mm'])>.3
assert neck_candidate['wall_sample_rays']==12240 and 1.47<neck_candidate['journal_wall_candidate_mm']<1.49
assert neck_candidate['journal_wall_candidate_mm']<neck_candidate['journal_wall_before_mm']
assert neck_candidate['full_material_supply']==neck_candidate['full_assembly_sequence']=='NOT_TESTED'
assert neck_candidate['whole_harness']=='BLOCKED' and not neck_candidate['manufacturing_release']
assert neck_candidate['changed_candidate_parts']==['Yaw_Base','Pitch_Yoke']
nc_verify=read(neck_candidate_dir/'verification.json')
nc_storage=read(neck_candidate_dir/'cleaned/storage.json')
nc_plot=read(neck_candidate_dir/'plot.json')
assert nc_verify['status']==nc_storage['status']==nc_plot['status']=='PASS'
assert nc_verify['source_candidate_sha256']==nc_storage['output_candidate_sha256']==sha(neck_candidate_dir/'cleaned/candidate.blend')
assert nc_verify['storage_receipt_sha256']==sha(neck_candidate_dir/'cleaned/storage.json')
assert nc_storage['unchanged_robot_objects']==207
assert len(nc_verify['rows'])==4 and all(r['status']=='PASS' and r['spans']==410 for r in nc_verify['rows'])
assert len(nc_verify['pair_rows'])==6 and all(r['status']=='PASS' for r in nc_verify['pair_rows'])
assert all(r['status']=='PASS' and r['zero_area_faces']==0 and r['non_two_face_edges']==0 and len(r['connected_components'])==1 for r in nc_verify['topology'].values())
assert all(not r['missing'] and r['valid_rays']==12240 for r in nc_verify['finite_journal_wall_samples'].values())
assert nc_plot['verification_sha256']==sha(neck_candidate_dir/'verification.json')
assert nc_plot['output_sha256']==sha(neck_candidate_dir/'comparison.png')

# Current staged diagnostics explicitly evaluate hidden proxies, account for
# every rigid member, and include complete wire material without claiming a
# complete supply path. Preserve both the source-proxy correction and failures.
staged_dir=body_review_dir/'split_assembly';staged_pub=read(staged_dir/'publication.json')
assert staged_pub['status']=='PASS' and staged_pub['script_sha256']==sha(HERE/'publish_CAM_staged_supply_review.py')
assert staged_pub['source_main_sha256']==source['source_blend_sha256']
assert sha(staged_dir/'publication.json')==body_review['staged_supply_publication_sha256']==latest['CAM_staged_supply_publication_sha256']==supcheck['staged_supply_publication_sha256']
for name,digest in staged_pub['source_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in staged_pub['protected_files'].items():assert sha(ROOT/name)==digest,name
for name,digest in staged_pub['outputs'].items():assert sha(staged_dir/name)==digest,name
assert staged_pub['source_objects']==staged_pub['assigned_source_objects']==209
assert staged_pub['body_rigid_positions']==408 and staged_pub['yaw_with_horn_positions']==181 and staged_pub['cradle_CAM_positions']==141
assert staged_pub['yaw_with_horn_members']==22 and staged_pub['cradle_CAM_members']==14
assert staged_pub['complete_four_wire_material_present'] and staged_pub['full_material_supply']=='BLOCKED'
assert all(153<v<162 for v in staged_pub['temporary_upright_lengths_mm'])
assert staged_pub['LCD_overlap_after_refresh_mm3']==0 and .007<staged_pub['front_camera_support_overlap_mm3']<.008
assert staged_pub['front_camera_support_clearance']=='BLOCKED' and staged_pub['images_visually_reviewed']
assert staged_pub['whole_harness']=='BLOCKED' and staged_pub['continuous_full_assembly']=='NOT_TESTED'
assert not staged_pub['main_applied'] and not staged_pub['manufacturing_release']
assert {r['part'] for r in staged_pub['source_proxy_pose_refresh']}=={'Display_PCB','LCD_Mount_Screw_0','LCD_Mount_Screw_1','LCD_Mount_Screw_2'}
staged_members=read(staged_dir/'screen.json')
assert sum(len(v) for v in staged_members['membership'].values())==len(set.union(*(set(v) for v in staged_members['membership'].values())))==209
assert len(read(staged_dir/'pitch_stages/screen.json')['yaw_members'])==21
staged_diag=read(staged_dir/'pitch_stages/interface_contacts/diagnosis.json')
assert all(r['status']=='PASS' for r in staged_diag['order_rows'])
stock_dir=body_review_dir/'bridge_wire_stock'
for rel,script,helper in [('screen.json','screen_CAM_bridge_wire_stock.py','plan_h06_documented_mates.py'),
    ('body_fixed_flex/screen.json','plan_CAM_bridge_stock_flex.py','screen_CAM_bridge_wire_stock.py'),
    ('PH_open_bridge/screen.json','plan_CAM_PH_open_bridge_entry.py','screen_CAM_bridge_wire_stock.py'),
    ('bridge_over_stock/screen.json','screen_CAM_bridge_over_stock.py','screen_CAM_bridge_wire_stock.py')]:
    d=read(stock_dir/rel)
    assert d['script_sha256']==sha(HERE/script) and d['helper_sha256']==sha(HERE/helper)
    assert d['source_split_report_sha256']==sha(staged_dir/'screen.json')
    assert d['source_objects']==209 and d['present_source_objects']==122 and d['fixed_wire_solids']==14 and d['mating_allocations']==29
    assert d['status']==d['whole_harness']=='BLOCKED' and not d['main_applied'] and not d['manufacturing_release']
remaining_by_id={r['id']:r for r in read(PARENT/'work_status.json')['remaining']}
assert remaining_by_id['head_front_contact']['status']=='BLOCKED'
assert '已建入' in remaining_by_id['harness']['detail'] and '尚未完整建模' not in remaining_by_id['harness']['detail']
cam_first_dir=stock_dir/'install_order/review'
cam_first_pub=read(cam_first_dir/'publication.json')
cam_first_delivery=read(cam_first_dir/'delivery.json')
assert cam_first_pub['script_sha256']==sha(HERE/'publish_CAM_first_order_review.py')
assert cam_first_delivery['script_sha256']==sha(HERE/'verify_CAM_first_order_delivery.py')
assert cam_first_delivery['publication_sha256']==sha(cam_first_dir/'publication.json')
for path,digest in cam_first_pub['source_files'].items():assert sha(ROOT/path)==digest,path
for path,digest in cam_first_pub['outputs'].items():assert sha(cam_first_dir/path)==digest,path
assert cam_first_pub['body_finite_positions']==408 and cam_first_pub['bare_plug_paths']==6
assert cam_first_pub['full_harness']=='BLOCKED' and not cam_first_pub['main_applied']
assert remaining_by_id['harness']['evidence']==latest['latest_review']

class Links(HTMLParser):
    def __init__(self):super().__init__();self.links=[]
    def handle_starttag(self,tag,attrs):
        for key,val in attrs:
            if key in ['href','src'] and val:self.links.append(val)
links=[]
parser=Links();parser.feed((staged_dir/'index.html').read_text())
for href in parser.links:
    u=urlparse(href)
    if u.scheme or u.netloc or not u.path:continue
    assert (staged_dir/unquote(u.path)).resolve().is_file(),href
    links.append(dict(page=str((staged_dir/'index.html').relative_to(ROOT)),target=href,status='PASS'))
parser=Links();parser.feed((neck_candidate_dir/'index.html').read_text())
for href in parser.links:
    u=urlparse(href)
    if u.scheme or u.netloc or not u.path:continue
    assert (neck_candidate_dir/unquote(u.path)).resolve().is_file(),href
    links.append(dict(page=str((neck_candidate_dir/'index.html').relative_to(ROOT)),target=href,status='PASS'))
parser=Links();parser.feed((body_review_dir/'index.html').read_text())
for href in parser.links:
    u=urlparse(href)
    if u.scheme or u.netloc or not u.path:continue
    assert (body_review_dir/unquote(u.path)).resolve().is_file(),href
    links.append(dict(page=str((body_review_dir/'index.html').relative_to(ROOT)),target=href,status='PASS'))
parser=Links();parser.feed((supdir/'index.html').read_text())
for href in parser.links:
    u=urlparse(href)
    if u.scheme or u.netloc or not u.path:continue
    assert (supdir/unquote(u.path)).resolve().is_file(),href
    links.append(dict(page=str((supdir/'index.html').relative_to(ROOT)),target=href,status='PASS'))
for page in [large_dir/'index.html',ordered_dir/'index.html',l2/'index.html',HERE/'index.html',HERE/'joined_entry_candidate/index.html',HERE/'terminal_threading/index.html',amass/'index.html',bp/'index.html',j3/'index.html',jm/'index.html',cp/'index.html',cf/'index.html',cpar/'index.html',cfan/'index.html',ca/'index.html',ct/'index.html',cpa/'index.html',cwi/'index.html',cwc/'index.html',cpt/'index.html',ctr/'index.html',cbl/'index.html',csk/'index.html',cfm/'index.html',cfm/'terminals/index.html',PARENT/'index.html',PARENT/'head_harness/index.html',PARENT/'supplier_made_harness/index.html']:
    parser=Links();parser.feed(page.read_text())
    for href in parser.links:
        u=urlparse(href)
        if u.scheme or u.netloc or not u.path:continue
        path=(page.parent/unquote(u.path)).resolve()
        if path!=HERE/'delivery.json':assert path.is_file(),(str(page),href)
        links.append(dict(page=str(page.relative_to(ROOT)),target=href,status='PASS'))

# Refresh only newly changed text within existing receipts. All geometry and
# historical test results keep their original status and source hashes.
allowed={str((PARENT/f).relative_to(ROOT)) for f in ['index.html','work_status.json',
    'head_harness/index.html','supplier_made_harness/index.html']}
refresh=[]
for mp in [PARENT/'M1_47_delivery.json',PARENT/'harness_A2/delivery.json',
           PARENT/'head_harness/delivery.json',PARENT/'supplier_made_harness/delivery.json']:
    d=json.loads(mp.read_text());changed=[]
    for path,digest in d['files'].items():
        new=sha(ROOT/path)
        if new==digest:continue
        assert path in allowed,('Unexpected change',str(mp),path)
        d['files'][path]=new;changed.append(path)
    if changed:
        d['A8_document_update']={'updated_utc':datetime.now(timezone.utc).isoformat(),
            'updated_paths':changed,'scope':'Text links and work status only; geometry and earlier checks unchanged.',
            'review':'harness_A8/index.html'}
        mp.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
    refresh.append(dict(path=str(mp.relative_to(ROOT)),updated_paths=changed))
url='http://127.0.0.1:58201/mechanical/studies/prearrival_finish/harness_A8/index.html'
with urlopen(url,timeout=10) as r:
    html=r.read();assert r.status==200 and hashlib.sha256(html).hexdigest()==sha(HERE/'index.html')
http={'status':200,'saved_source_matches':True,'url':url}
for filename in ['index.html','publication.json','review/head_shell_order_collision.png','review/larger_contact_neck_section.png']:
    p=body_review_dir/filename
    body_url='http://127.0.0.1:58201/'+str(p.relative_to(ROOT))
    with urlopen(body_url,timeout=10) as r:assert r.status==200 and hashlib.sha256(r.read()).hexdigest()==sha(p)
http['body_supply_review_url']='http://127.0.0.1:58201/'+str((body_review_dir/'index.html').relative_to(ROOT))
for filename in ['index.html','publication.json','comparison.png']:
    p=neck_candidate_dir/filename
    candidate_url='http://127.0.0.1:58201/'+str(p.relative_to(ROOT))
    with urlopen(candidate_url,timeout=10) as r:assert r.status==200 and hashlib.sha256(r.read()).hexdigest()==sha(p)
http['larger_neck_candidate_url']='http://127.0.0.1:58201/'+str((neck_candidate_dir/'index.html').relative_to(ROOT))
for filename in ['index.html','publication.json','review/assembly_order.png','review/wire_stock.png','review/contact_sections.png']:
    p=staged_dir/filename;staged_url='http://127.0.0.1:58201/'+str(p.relative_to(ROOT))
    with urlopen(staged_url,timeout=10) as r:assert r.status==200 and hashlib.sha256(r.read()).hexdigest()==sha(p)
http['staged_supply_review_url']='http://127.0.0.1:58201/'+str((staged_dir/'index.html').relative_to(ROOT))
joined_url='http://127.0.0.1:58201/mechanical/studies/prearrival_finish/harness_A8/joined_entry_candidate/index.html'
with urlopen(joined_url,timeout=10) as r:
    assert r.status==200 and hashlib.sha256(r.read()).hexdigest()==sha(HERE/'joined_entry_candidate/index.html')
http['joined_candidate_url']=joined_url
for rel in ['cam_wire_forming/lifted_end2/contact_refined_forming/start.png','cam_wire_forming/lifted_end2/contact_refined_forming/last_wire_sideways.png','cam_wire_forming/lifted_end2/contact_refined_forming/all_four_positioned.png','cam_wire_forming/lifted_end2/contact_refined_forming/screen.json','cam_wire_forming/lifted_end2/index.html','cam_wire_forming/lifted_end2/upstream_collision.png','cam_wire_forming/lifted_end2/board_at8.png','cam_wire_forming/lifted_end2/board_at2.png','cam_wire_forming/lifted_end2/board_descent_continuous.json','cam_wire_forming/terminals/index.html','cam_wire_forming/terminals/loose_terminals.png','cam_wire_forming/terminals/housing_collision.png','cam_wire_forming/continuous/screen.json','cam_wire_forming/index.html','cam_wire_forming/direct_bend_conflict.png','cam_wire_forming/raised_bend_candidate.png','cam_wire_forming/upright_start.png','cam_board_last/continuous_packing.json','cam_socket_tool/index.html','cam_socket_tool/key_access.png','cam_socket_tool/socket_closeup.png','cam_socket_tool/sources/Wera_05022040001.pdf','cam_board_last/index.html','cam_board_last/board_raised6.png','cam_board_last/screw_tool_obstruction.png','terminal_threading/index.html','amass_mating/index.html','amass_mating/sources/XT30UPB_M_2025V1.pdf','body_prefix_v2/index.html',
            'assembly_feed_v3/index.html','assembly_feed_v3/coupled_feed_sections.png','assembly_feed_v3/journal_comparison.png',
            'assembly_feed_v3/open_mouth/index.html','assembly_feed_v3/open_mouth/mouth_before.png','assembly_feed_v3/open_mouth/mouth_after.png',
            'cam_pitch_port/index.html','cam_pitch_port/left_departure.png','cam_pitch_port/forward_departure.png',
            'cam_pitch_flex/index.html','cam_pitch_flex/zero.png','cam_pitch_flex/tightest.png',
            'cam_parallel_pitch/index.html','cam_parallel_pitch/zero.png','cam_parallel_pitch/down20.png','cam_parallel_pitch/up25.png',
            'cam_fan_in/index.html','cam_fan_in/zero.png','cam_fan_in/down20.png','cam_fan_in/up25.png','cam_fan_in/overview.png',
            'cam_anchors/index.html','cam_anchors/anchor_detail.png','cam_anchors/anchor_zero.png',
            'cam_anchors/anchor_down20.png','cam_anchors/anchor_up25.png','cam_anchors/removal_0.png',
            'cam_anchors/removal_1.png','cam_anchors/removal_2.png','cam_anchors/removal_3.png','cam_anchors/removal_4.png',
            'cam_tie_install/index.html','cam_tie_install/tie_orientation.png','cam_tie_install/tool_detail.png',
            'cam_tie_install/tool_overview.png','cam_tie_install/ring_below.png',
            'cam_tie_install/sources/CAD_10-0585-001-CSC.pdf','cam_tie_install/sources/CAD_10-0585-001-CSH.pdf',
            'cam_tie_install/sources/CAD_10-0585-003-CSE.pdf','cam_pitch_anchor/index.html',
            'cam_pitch_anchor/connector_anchor/connector_detail.png','cam_pitch_anchor/connector_anchor/connector_before_tie.png',
            'cam_pitch_anchor/connector_anchor/connector_overview.png','cam_pitch_anchor/connector_anchor/connector_down20.png',
            'cam_connector_install/index.html','cam_connector_install/work_detail.png','cam_connector_install/work_overview.png',
            'cam_connector_install/installed_tool_conflict.png','cam_connector_install/length_datums_REFERENCE_ONLY.csv',
            'cam_wired_cradle/index.html','cam_wired_cradle/seated.png','cam_wired_cradle/raised42.png',
            'cam_wired_cradle/wire_conflict42.png','cam_wired_cradle/neck_gap9.png',
            'cam_profiled_tool/index.html','cam_profiled_tool/yaw30_local.png','cam_profiled_tool/yaw30_full.png',
            'cam_profiled_tool/old45.png','cam_profiled_tool/new45.png','cam_profiled_tool/connector_work.png',
            'cam_profiled_tool/profile_comparison.svg','cam_profiled_tool/sources/official_top.png',
            'cam_profiled_tool/sources/official_head_dimensions.png',
            'cam_tail_ribbon/index.html','cam_tail_ribbon/tail_section_comparison.png',
            'cam_tail_ribbon/tail_overview.png','cam_tail_ribbon/tail_top.png']:
    target_url=url.rsplit('/',1)[0]+'/'+rel
    with urlopen(target_url,timeout=10) as r:
        assert r.status==200 and hashlib.sha256(r.read()).hexdigest()==sha(HERE/rel)
    http[rel]={'url':target_url,'status':200,'saved_source_matches':True}
for suffix in ['negative_complete/screen.json','negative_complete/junctions.json',
               'first_three_continuous/screen.json','negative_tail/screen.json',
               'negative_return_branch/side6.png','negative_return_branch/side3.png',
               'negative_return_branch/returned.png','housing_approach/screen.json',
               'housing_approach/initial.png','housing_approach/final.png','housing_approach/SOURCE_NOTE.md',
               'root_tie_access/screen.json','root_tie_access/contact_feed.json','root_tie_access/README.md',
               'root_tie_access/complete_tool.png','root_tie_access/root_detail.png',
               'root_seating/aligned_tails/README.md','root_seating/aligned_tails/continuous.json',
               'root_seating/aligned_tails/verification.json','root_seating/aligned_tails/before_seating.png',
               'root_seating/aligned_tails/seated.png','root_seating/aligned_tails/complete_leads.png',
               'root_seating/ordered_feed_recovery/index.html','root_seating/ordered_feed_recovery/publication.json',
               'root_seating/large_contact_downstream/index.html','root_seating/large_contact_downstream/README.md',
               'root_seating/large_contact_downstream/publication.json','root_seating/large_contact_downstream/root_continuous.json',
               'root_seating/large_contact_downstream/start_delay/continuous.json','root_seating/body_supply/README.md']:
    rel='cam_wire_forming/lifted_end2/contact_refined_forming/'+suffix
    target_url=url.rsplit('/',1)[0]+'/'+rel
    with urlopen(target_url,timeout=10) as response:
        assert response.status==200 and hashlib.sha256(response.read()).hexdigest()==sha(HERE/rel)
    http[rel]={'url':target_url,'status':200,'saved_source_matches':True}
for rel in ['ssh_catalogue_addendum/README.md','ssh_catalogue_addendum/JST_eLBT.pdf',
            'ssh_catalogue_addendum/contact_page2.png','ssh_catalogue_addendum/retrieval.json',
            'ssh_catalogue_addendum/apsh/JST_eAPSH.pdf','ssh_catalogue_addendum/apsh/page1_mupdf.png',
            'ssh_catalogue_addendum/apsh/README.md','ssh_catalogue_addendum/apsh/retrieval.json',
            'supplier_source_update/index.html','supplier_source_update/README.md','supplier_source_update/verification.json']:
    target_url=url.rsplit('/',1)[0]+'/'+rel
    with urlopen(target_url,timeout=10) as response:
        assert response.status==200 and hashlib.sha256(response.read()).hexdigest()==sha(HERE/rel)
    http[rel]={'url':target_url,'status':200,'saved_source_matches':True}
rows=[p for p in HERE.rglob('*') if p.is_file() and p.name!='delivery.json' and '__pycache__' not in p.parts]
result=dict(status='PASS',scope='A8 source receipt, bounded local/endpoint investigations and report preservation only',
    verified_utc=datetime.now(timezone.utc).isoformat(),main_geometry_unchanged=True,
    main_model_sha256=source['source_blend_sha256'],local_harness_segment='PASS',
    complete_head_harness='BLOCKED',manufacturing_drawing='BLOCKED',physical_crimp_and_life='NOT_TESTED',
    endpoint_investigation={'body_finite_graph':'BLOCKED','yaw_single_polyline_clearance':'PASS',
        'bends_four_simultaneous_wires_retention':'NOT_TESTED','main_geometry_changed':False},
    crimp_series_guidance='PASS',actual_wire_terminal_process_qualified='NOT_TESTED',
    exact_terminal_tooling_reference='PASS',
    exact_terminal_tooling_scope='Unversioned public test-jst manufacturer host; production queries returned403; not a qualified wire/process combination',
    joined_entry_candidate={'wire_geometry':'PASS','terminal_reference_entry':'BLOCKED','applied':False,
        'physical_retention':'NOT_TESTED','whole_harness':'BLOCKED',
        'review':'joined_entry_candidate/index.html'},
    terminal_threading_candidate={'reference_contact_vs_207_sources_and_14_fixed_wires':'PASS',
        'cleaned_raw_topology':'PASS','local_wire_vs_209_sources':'PASS','old29_mating_envelopes':'BLOCKED',
        'historical_single_cubic_body_family':'BLOCKED','body_four_wire_prefix':'PASS','main_applied':False,'whole_harness':'BLOCKED',
        'review':'terminal_threading/index.html'},
    AMASS_source_receipt_and_mating_dimension_derivation='PASS',
    AMASS_mating_replay={'nominal':'PASS','upper_allocation':'BLOCKED',
        'historical_single_cubic_body_prefix':'BLOCKED','current_body_to_yaw_prefix':'PASS',
        'current_prefix_review':'body_prefix_v2/index.html',
        'review':'amass_mating/index.html','main_model_applied':False,'physical_clearance':'NOT_TESTED'},
    body_to_yaw_candidate={'status':'PASS','scope':'Four prefixes and local yaw curves only',
        'head_pose_count':130,'source_objects':209,'mating_allocations':29,'earlier_fixed_wires':14,
        'pair_gap_lower_bound_mm':bp_motion['minimum_pair_surface_gap_bound_mm'],'other_local_yaw_groups':'PASS',
        'main_applied':False,'anchor_design':'NOT_TESTED','assembly':'NOT_TESTED','whole_harness':'BLOCKED',
        'review':'body_prefix_v2/index.html'},
    coupled_feed_candidate={'status':'PASS','scope':'Nominal loose-contact and trailing-wire local feed, finite reshaping and installed-motion checks',
        'head_pose_count':130,'finite_wire_shape_checks':88,'local_feed_order_pairs':12,
        'saved_candidate_sha256':sha(j3/'cleaned/candidate.blend'),
        'upper_exit_thin_edge':'BLOCKED','sampled_journal_radial_wall_mm':jwall['wall_samples']['J3']['minimum']['thickness_mm'],
        'full_print_strength':'NOT_TESTED','body_loose_tail_and_hands':'NOT_TESTED',
        'main_applied':False,'whole_harness':'BLOCKED','review':'assembly_feed_v3/index.html'},
    open_mouth_candidate={'status':'PASS','scope':'Four local mouth roofs removed; saved-solid replay and prescribed continuous angular reshaping only',
        'saved_candidate_sha256':sha(jm/'cleaned/candidate.blend'),'local_roof_cleanup':'PASS',
        'head_pose_count':130,'continuous_slack_intervals':64,'minimum_sampled_journal_wall_mm':jma['journal_minimum_sample_unchanged_mm'],
        'whole_harness':'BLOCKED','main_applied':False,'full_strength':'NOT_TESTED','review':'assembly_feed_v3/open_mouth/index.html'},
    CAM_end_candidate={'nominal_catalogue_mate':'PASS','pitch_fixed_departure':'PASS','old_Z206_combination':'BLOCKED',
        'lower_Z193_disjoint_halves':'PASS','connected_service_loop':'NOT_TESTED','actual_mate':'BLOCKED',
        'physical_pin_view':'BLOCKED','main_applied':False,'whole_harness':'BLOCKED','review':'cam_pitch_port/index.html'},
    CAM_flex_candidate={'individual_connected_candidates':'PASS','individual_count':19,
        'whole_curve_bounds_at_finite_angles':'PASS','whole_four_wire_packing':'BLOCKED',
        'early_S_turn_local':'PASS','early_turn_full_rejoin':'NOT_TESTED',
        'photo_board_face_position':'PASS','actual_mating_cavity_views':'BLOCKED',
        'anchor_design':'NOT_TESTED','supplier_cut_lengths':'BLOCKED',
        'main_applied':False,'whole_harness':'BLOCKED','review':'cam_pitch_flex/index.html'},
    CAM_parallel_candidate={'four_wire_CAM_side_bundle':'PASS','candidate_count':3,'head_pose_count':130,
        'minimum_mutual_gap_bound_mm':par_pack['rows'][0]['minimum_mutual_gap_bound_mm'],
        'whole_angle_length_and_radius_bounds':'PASS','continuous_collision':'NOT_TESTED',
        'neck_to_loop_fan_in':'NOT_TESTED','anchors':'NOT_TESTED','whole_harness':'BLOCKED',
        'main_applied':False,'review':'cam_parallel_pitch/index.html'},
    CAM_connected_UART_candidate={'nominal_connected_four_wire_paths':'PASS','head_pose_count':130,
        'transition_candidates':12,'mutual_candidate_pair_checks':54,'simultaneous_assignments':81,
        'checked_seams':1560,'minimum_CAM_side_gap_bound_mm':clpack['rows'][0]['minimum_mutual_gap_bound_mm'],
        'whole_span_radius_and_length_bounds':'PASS','continuous_collision':'NOT_TESTED','anchors':'NOT_TESTED',
        'full_installation':'NOT_TESTED','actual_CAM_mate':'BLOCKED','whole_harness':'BLOCKED',
        'main_applied':False,'supplier_cut_lengths':'BLOCKED','review':'cam_fan_in/index.html'},
    CAM_one_anchor_candidate={'status':'PASS','scope':'One integral support and assumed tie allocation with nominal servo service checks',
        'added_print_parts':0,'added_screws':0,'proposed_ties':1,'stored_mesh_topology':'PASS',
        'servo_installation_samples':1066,'tool_sample_span_deg':240,'raw_other_parts_preserved':207,
        'all_anchors':'NOT_TESTED','tie_and_whole_harness_installation':'NOT_TESTED','physical_retention':'NOT_TESTED',
        'main_applied':False,'whole_harness':'BLOCKED','supplier_cut_lengths':'BLOCKED','review':'cam_anchors/index.html'},
    CAM_tie_bench_candidate={'status':'PASS','scope':'Official dimensional receipts, directional installed allocation, and incremental rigid bench checks only',
        'official_PDFs_received':3,'nonempty_band_check':'PASS','servo_with_preplaced_tie':'PASS',
        'ring_slide_after_servo_fitted':'BLOCKED','tool_vs_final_service_loop':'BLOCKED',
        'flexible_threading_tightening':'NOT_TESTED','hands_and_actual_tool':'NOT_TESTED',
        'whole_harness':'BLOCKED','main_applied':False,'supplier_cut_lengths':'BLOCKED','review':'cam_tie_install/index.html'},
    CAM_connector_anchor_candidate={'status':'PASS','scope':'Short integral departure anchor, tie allocation and finite bench order only',
        'new_print_parts':0,'changed_existing_ids':['Pitch_Cradle'],'wires_relocated':False,
        'preplugged_board_insertion':'PASS','plug_after_board_direct_insertion':'BLOCKED',
        'full_flexible_installation':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,
        'review':'cam_pitch_anchor/index.html'},
    CAM_connector_work_candidate={'status':'PASS','scope':'Detached work envelopes and model-only routed length datums',
        'downward_tool_on_detached_pitch_module':'PASS','same_tool_on_assembled_robot':'BLOCKED',
        'model_length_pose_instances':520,'supplier_cut_lengths':'BLOCKED','whole_installation':'NOT_TESTED',
        'whole_harness':'BLOCKED','main_applied':False,'review':'cam_connector_install/index.html'},
    CAM_wired_cradle_candidate={'status':'BLOCKED','scope':'Constant-length prescribed assembly family; not all possible flexible motions',
        'rigid_sample_positions':15,'clear_wire_sample_lifts_mm':[0,3,6],
        'original_42mm_lift_self_intersection':'FAIL','sequence_tool_cases':48,'successful_tool_cases':0,
        'continuous_motion':'NOT_TESTED','whole_harness':'BLOCKED','main_applied':False,
        'review':'cam_wired_cradle/index.html'},
    CAM_profiled_tool_candidate={'status':'PASS','scope':'Publication and conditional local tool-work geometry only',
        'manufacturer_dimensions':'PASS','complete_tool_profile':'ASSUMED','actual_tool_fit':'NOT_TESTED',
        'yaw_preferred_angle_deg':30,'yaw_reference_wire_gap_bound_mm':pt30['wire_minimum']['gap_lower_bound_mm'],
        'yaw_expanded_profile_wire_gap_bound_mm':pt30x['wire_minimum']['gap_lower_bound_mm'],
        'CAM_tail_workspace':'BLOCKED','late_servo_sequence':'BLOCKED','complete_CAM_installation':'BLOCKED',
        'main_applied':False,'whole_harness':'BLOCKED','review':'cam_profiled_tool/index.html'},
    CAM_temporary_tail_candidate={'status':'PASS','scope':'Temporary real-thickness strip through existing local gap only',
        'local_route_cases':36,'widened_shifted_cases':9,'nominal_rigid_gap_mm':.5,'expanded_rigid_gap_mm':.4,
        'shape_material_evidence':'ASSUMED','full_threading_tightening':'NOT_TESTED','complete_CAM_installation':'BLOCKED',
        'whole_harness':'BLOCKED','main_applied':False,'review':'cam_tail_ribbon/index.html'},
    CAM_board_last_candidate={'nominal_wire_positions':'PASS','positions':16,'constant_length':'PASS',
        'continuous_rigid_sweeps':'PASS','straight_driver_access':'BLOCKED','blocked_screw':'CAM_Mount_Screw_0',
        'continuous_wire_deformation':'NOT_TESTED','initial_feed_and_tightening':'NOT_TESTED',
        'whole_harness':'BLOCKED','main_applied':False,'review':'cam_board_last/index.html'},
    CAM_socket_screw_candidate={'status':'PASS','scope':'Four unchanged-axis M2x5 socket screws and catalogue extra-short key',
        'continuous_key_work_angle_deg':60,'continuous_axial_travel_mm':8,'head_motion_poses':130,
        'quantity_change':0,'printed_changes':[],'approval':latest['CAM_socket_screw_candidate_approval'],
        'whole_harness':'BLOCKED','main_applied':False,'review':'cam_socket_tool/index.html'},
    CAM_board_last_continuous_wire_to_solids={'status':'PASS','travel_mm':6,'stages':['mating','seating'],
        'intervals':len(bws['passed_intervals']),'nominal_surface_gap_mm':.3,
        'wire_to_wire':'PASS','whole_harness':'BLOCKED','main_applied':False},
    CAM_board_last_continuous_packing={'status':'PASS','intervals':8,'static_checks':14,
        'minimum_gap_bound_mm':fmp['minimum_packing_gap_bound_mm'],'main_applied':False,'whole_harness':'BLOCKED'},
    CAM_initial_forming={'direct_path':'FAIL','raised_path_samples':'PASS','raised_amplitude_mm':9,'sample_count':41,
        'continuous_to_solids':'BLOCKED','continuous_passed_intervals':len(fm_intervals),'continuous_coverage':False,
        'terminal_shapes':'PASS','terminal_evidence':'Nominal catalogue span boxes; actual post-crimp profile unknown',
        'forming_wire_packing':'BLOCKED','terminal_to_housing_insertion':'NOT_TESTED',
        'housed_trials':'BLOCKED','new_lift2_positions':'PASS','new_lift2_continuous':'NOT_TESTED',
        'new_lift2_board_descent':'PASS','new_lift2_board_descent_intervals':len(l2intervals),
        'new_lift2_wire_collision':'FAIL','revised_forming_candidates_finite':'PASS','revised_positions':644,
        'revised_order':[3,2,1,0],'revised_contact_nonpenetration':'PASS','revised_continuous':'BLOCKED',
        'revised_wire_intersection':'FAIL','critical_return_continuous':kc['status'],
        'critical_return_complete_local_coverage':kc['complete_local_coverage'],'critical_return_full_sequence_coverage':False,
        'revised_generic_terminal_margin':'BLOCKED',
        'main_applied':False,'whole_harness':'BLOCKED',
        'review':'cam_wire_forming/lifted_end2/index.html'},
    CAM_current_four_wire_forming={'status':'PASS','continuous_coverage':True,
        'interval_count':complete['continuous_interval_count'],'stage_boundary_identity':'PASS',
        'material_length_invariant':'PASS','curve_radius_lower_bound_mm':complete['nominal_curve_radius_lower_bound_mm'],
        'contact_evidence':'ASSUMED catalogue-span boxes; not actual crimped parts',
        'terminal_insertion':'NOT_TESTED','initial_feed':'NOT_TESTED','ties':'NOT_TESTED',
        'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
        'receipt':'cam_wire_forming/lifted_end2/contact_refined_forming/negative_complete/screen.json'},
    CAM_housing_external_approach={'status':'PASS','travel_mm':8.,'rigid_checks':219,
        'nonjoining_wire_checks':12,'contact_cavity_and_lance':'BLOCKED','contact_insertion':'NOT_TESTED',
        'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},
    CAM_root_tie_access={'nominal_tool_sweep':'PASS','general_rigid_margin':'BLOCKED',
        'outward_tail_space':'PASS','tight_contact_feed':'BLOCKED','full_tie_installation':'NOT_TESTED',
        'rigid_checks_per_candidate':219,'wire_portions':12,'bare_contacts':4,
        'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},
    CAM_root_wire_seating={'finite_positions':21,'continuous_intervals':256,'continuous_coverage':'PASS',
        'whole_family_terminal_straight_lower_mm':rscheck['minimum_terminal_straight_whole_family_lower_mm'],
        'initial_terminal_bypass':'BLOCKED','tie_threading_tightening':'NOT_TESTED',
        'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False},
    SSH_extra_catalogue={'receipt':'PASS','complete_catalogue_box_includes_lance':False,
        'actual_terminal_fit':'NOT_TESTED','contact_MPN':'SSH-003T-P0.2-H'},
    CAM_larger_contact_sequence={'allocated_box_mm':[1.,1.8,4.1],'dimension_evidence':'ASSUMED',
        'upper_feed_continuous':'PASS','upper_feed_intervals':1228,
        'recovery_continuous':'PASS','recovery_intervals':256,
        'seating_continuous':'PASS','seating_intervals':256,
        'forming_continuous':'PASS','forming_intervals':1735,'forming_boundaries':8,
        'body_material_supply':'NOT_TESTED','ties':'NOT_TESTED','actual_terminal_insertion':'NOT_TESTED',
        'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
        'review':'cam_wire_forming/lifted_end2/contact_refined_forming/root_seating/large_contact_downstream/index.html'},
    CAM_staged_supply_review={'publication':'PASS','source_objects':209,'yaw_with_horn_members':22,'cradle_CAM_members':14,
        'full_nominal_wire_material_present':True,'full_material_supply':'BLOCKED','fixed_wire_solids':14,
        'LCD_proxy_pose_corrected':True,'front_camera_support_clearance':'BLOCKED',
        'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
        'review':str((staged_dir/'index.html').relative_to(HERE))},
    CAM_full_body_supply_review={'publication':'PASS','full_head_old_sequence':'BLOCKED',
        'larger_contact_neck':'BLOCKED','neck_pose_trials':49,'coupled_variants':10,
        'whole_material_supply':'NOT_TESTED','main_applied':False,'whole_harness':'BLOCKED',
        'manufacturing_release':False,'review':str((body_review_dir/'index.html').relative_to(HERE))},
    CAM_larger_neck_candidate={'local_continuous_neck':'PASS','topology':'PASS',
        'contact_dimensions_mm':[1.,1.8,4.1],'evidence':'ASSUMED','directions':4,'intervals_per_direction':410,
        'contact_gap_bound_mm':neck_candidate['contact_gap_bound_mm'],
        'wire_gap_bound_mm':neck_candidate['wire_gap_bound_mm'],
        'journal_wall_minimum_sample_mm':neck_candidate['journal_wall_candidate_mm'],
        'whole_material_supply':'NOT_TESTED','whole_assembly':'NOT_TESTED',
        'main_applied':False,'whole_harness':'BLOCKED','manufacturing_release':False,
        'review':str((neck_candidate_dir/'index.html').relative_to(HERE))},
    supplier_source_update={'receipt':'PASS','APSH_catalogue':'RETRIEVED',
        'M5_official_arm_reference':'PASS','M5_arm_MORI_interface':'BLOCKED',
        'vertical_free_feed_allocations':8,'vertical_free_feed':'PASS',
        'vertical_free_feed_scope':supcheck['vertical_feed_scope'],
        'progressive_staging':'BLOCKED','progressive_staging_positions':41,
        'initial_feed_to_root_seating':'BLOCKED','whole_harness':'BLOCKED',
        'manufacturing_release':False,'review':'supplier_source_update/index.html'},
    links=links,http=http,updated_text_manifests=refresh,
    versions={'python':platform.python_version(),'blender':'5.2.2 LTS d13f752e3b9c'},
    files={str(p.relative_to(ROOT)):sha(p) for p in sorted(rows)})
(HERE/'delivery.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'status':'PASS','files':len(rows),'local_links':len(links),'main_unchanged':True,'http':http},ensure_ascii=False))
