"""Nominal open-path clearance; deliberately not an acoustic qualification."""
from common import *
from microphone_geometry import microphone_paths


def validate_microphones(solids,Solid,iv,check):
    from build import beam
    q=P['microphone_acoustics'];rows=[]
    for d in microphone_paths():
        probe=beam('microphone_free_air_probe',d['start'],d['inner'],q['airway_probe_radius_mm'])
        union(probe,beam('microphone_shell_air_probe',d['inner'],d['outside'],q['airway_probe_radius_mm']))
        a=Solid(probe);hits=[]
        # The assumed package is a solid box without modeled MEMS holes.
        # Its own acoustic port cannot be certified by intersecting that box.
        excluded='Onboard_MIC_'+d['side']
        for n,b in solids.items():
            if n==excluded or b.group=='dock':continue
            v=iv(a,b)
            if v>.005:hits.append({'part':n,'volume_mm3':v})
        rows.append({'side':d['side'],'estimated_port_center_mm':list(d['port']),
                     'probe_polyline_mm':[list(d[k]) for k in ['start','inner','outside']],
                     'nominal_probe_radius_mm':q['airway_probe_radius_mm'],
                     'solid_intersections':hits,'excluded_unmeasured_package':excluded})
        SOLIDS.pop(probe.name,None);bpy.data.objects.remove(probe,do_unlink=True)
    alive=set(solids);retired=q['retired_print_ids'];onboard=['Onboard_MIC_L','Onboard_MIC_R']
    ok=not q['printed_ducts'] and not alive.intersection(retired) and all(n in alive for n in onboard) and not any(r['solid_intersections'] for r in rows)
    report={'revision':P['revision'],'status':'PASS' if ok else 'FAIL','mode':q['mode'],
            'removed_print_ids':retired,'preserved_onboard_mics':onboard,'paths':rows,
            'method':'Actual closed-solid intersection of two connected 0.4mm-radius nominal clearance probes per mic through the existing frame and shell openings. No rendering tube is added. The corresponding assumed microphone package is excluded at its unmodeled port.',
            'acoustic_performance':'NOT_TESTED','port_metrology':'BLOCKED',
            'limits':'Assumed/photo-registered coordinates only. A clear nominal path does not prove sensitivity, beamforming, channel isolation, dust protection or speaker/servo-noise rejection. Real CAM-board port alignment and recordings remain necessary.'}
    save_json(ROOT/'reports/microphone_open_path.json',report)
    check('microphone_open_path_nominal','PASS' if ok else 'FAIL','取消两根打印导管，保留板载双麦与模型中的开放进声路径',report,report['method'])
    check('microphone_open_cavity_audio','NOT_TESTED','无导管方案的拾音、双麦串音及扬声器/舵机噪声影响尚未录音验证',{'mode':q['mode'],'speaker_chamber':'Existing separate shell-mounted speaker cup retained'},'No acoustic solver or physical recording. Shared head cavity has no claimed microphone isolation.')
