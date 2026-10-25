"""Nominal open-path clearance; deliberately not an acoustic qualification."""
from common import *
from microphone_geometry import microphone_paths


def validate_microphones(solids,Solid,iv,check):
    from build import beam
    q=P['microphone_acoustics'];rows=[]
    for d in microphone_paths(installed=True):
        points=d.get('probe_points',[d['start'],d['inner'],d['outside']])
        probe=beam('microphone_free_air_probe',points[0],points[1],q['airway_probe_radius_mm'])
        for a,b in zip(points[1:],points[2:]):
            union(probe,beam('microphone_shell_air_probe',a,b,q['airway_probe_radius_mm']))
        a=Solid(probe);hits=[]
        # Package and sound-port geometry are photo estimates; exclude its own package from external air-path clearance.
        # Its modeled port is not an acoustic measurement.
        excluded='Onboard_MIC_'+d['side']
        for n,b in solids.items():
            if n==excluded or b.group=='dock':continue
            v=iv(a,b)
            if v>.005:hits.append({'part':n,'volume_mm3':v})
        rows.append({'side':d['side'],'estimated_port_center_mm':list(d['port']),
                     'probe_polyline_mm':[list(p) for p in points],
                     'nominal_probe_radius_mm':q['airway_probe_radius_mm'],
                     'solid_intersections':hits,'excluded_unmeasured_package':excluded})
        SOLIDS.pop(probe.name,None);bpy.data.objects.remove(probe,do_unlink=True)
    alive=set(solids);retired=q['retired_print_ids'];onboard=['Onboard_MIC_L','Onboard_MIC_R']
    ok=not q['printed_ducts'] and not alive.intersection(retired) and all(n in alive for n in onboard) and not any(r['solid_intersections'] for r in rows)
    report={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','mode':q['mode'],
            'removed_print_ids':retired,'preserved_onboard_mics':onboard,'paths':rows,
            'method':'Actual closed-solid intersection of connected 0.4mm-radius nominal open-air probes from the installed microphone pose through the existing cavity/shell opening. No duct or hole is added. Its own assumed package is excluded at the photo-estimated port; paths sharing a shell opening do not demonstrate channel isolation.',
            'acoustic_performance':'NOT_TESTED','port_metrology':'BLOCKED',
            'limits':'Assumed/photo-registered coordinates only. A clear nominal path does not prove sensitivity, beamforming, channel isolation, dust protection or speaker/servo-noise rejection. Real CAM-board port alignment and recordings remain necessary.'}
    save_json(ROOT/'reports/microphone_open_path.json',report)
    check('microphone_open_path_nominal','PASS' if ok else 'FAIL','取消两根打印导管，保留板载双麦与模型中的开放进声路径',report,report['method'])
    check('microphone_open_cavity_audio','NOT_TESTED','无导管方案的拾音、双麦串音及扬声器/舵机噪声影响尚未录音验证',{'mode':q['mode'],'speaker_chamber':'Shell-mounted purchased enclosed speaker; no printed rear cup'},'No acoustic solver or physical recording. Shared head cavity has no claimed microphone isolation.')
