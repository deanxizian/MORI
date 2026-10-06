"""Finite vertical insertion of the complete two-plug H02 into the open body.

The bridge, upper shell, CAM harness, H01 and H04 are deliberately later steps.
This is a held-shape insertion proposal, not evidence of hand access or tools.
"""
from pathlib import Path
INSERT_SCRIPT=Path(__file__).resolve();INSERT_A8=INSERT_SCRIPT.parent
INSERT_HELPER=INSERT_A8/'screen_H02_preinstalled_route.py'
__file__=str(INSERT_HELPER)
exec(compile(INSERT_HELPER.read_text().split('\nstarted=time.time();pools=',1)[0],str(INSERT_HELPER),'exec'),globals())
__file__=str(INSERT_SCRIPT)
checked=json.loads((OUT/'verification.json').read_text())
assert checked['status']=='PASS' and checked['screen_sha256']==sha(OUT/'screen.json')
saved=json.loads((OUT/'screen.json').read_text());chosen=saved['selected']['routes']
meshpath=OUT/'wire_solids.json';raw=json.loads(meshpath.read_text())
wires={n:manifold.Manifold(manifold.Mesh64(np.array(d['vertices_mm']),np.array(d['triangles'],dtype=np.uint64))) for n,d in raw.items()}
ports=['motion_J2','power_J13'];shapes={**wires,**{'Plug_'+n:plug[n].m for n in ports}}
targets={n:data(phys[n]) for n in core}
not_installed={'motion_J5'}|{p for g in ['H01','H02','H04'] for p in pairings[g]}
targets.update({'Plug_'+n:data(s.m) for n,s in plug.items() if n not in not_installed and not n.startswith('rear_')})
targets.update({'fixed_wire_'+n:(r['m'],r['lo'],r['hi'],r['tree']) for n,r in fixed.items() if n.startswith('H03_')})
own_boards={'Plug_motion_J2':'MCU_Carrier','Plug_power_J13':'Power_Module'}
domains={n:shapes[n]^targets[b][0] for n,b in own_boards.items()}
rows=[];started=time.time()
for z in np.arange(0,100.01,.5):
    fail=None
    for name,shape in shapes.items():
        placed=shape.translate([0,0,float(z)]);box=np.array(placed.bounding_box())
        for other,(m,lo,hi,tree) in targets.items():
            if np.any(box[:3]>=hi) or np.any(box[3:]<=lo):continue
            overlap=placed^m
            if own_boards.get(name)==other:overlap-=domains[name]
            volume=max(0.,float(overlap.volume()))
            if volume>1e-5:fail=dict(moving=name,obstacle=other,intersection_mm3=volume);break
        if fail:break
    if not fail:
        for row in chosen:
            p=resample(row['curve_mm'],.04)+[0,0,float(z)]
            fail=check_curve(p,targets,rad=HOD/2+.02,extra=0.)
            if fail:fail.update(wire=row['id']);break
    rows.append(dict(z_mm=float(z),status='PASS' if fail is None else 'FAIL',failure=fail))
    if fail:break
report=dict(status='PASS' if len(rows)==201 and all(r['status']=='PASS' for r in rows) else 'FAIL',
    scope='201 finite vertical positions for the held-shape two-plug H02 assembly, before the bridge/upper shell/CAM/H01/H04',
    script_sha256=sha(INSERT_SCRIPT),helper_sha256=sha(INSERT_HELPER),protected_sources=protected,
    source_files={str(p.relative_to(PROJECT)):sha(p) for p in [OUT/'screen.json',OUT/'verification.json',meshpath]},
    body_core_source_objects=len(core),other_mating_allocations=len([n for n in targets if n.startswith('Plug_')]),
    installed_other_wire_ids=[n for n in targets if n.startswith('fixed_wire_')],
    deliberate_native_mating_domains_mm3={n:float(m.volume()) for n,m in domains.items()},
    rows=rows,nominal_wire_gap_requirement_mm=.3,
    plug_fit='ASSUMED_ORIGINAL_DOMAIN_ONLY',plug_margin='NOT_TESTED',continuous_motion='NOT_TESTED',
    hands_and_curve_retention='NOT_TESTED',main_applied=False,whole_harness='BLOCKED',manufacturing_release=False,
    blender_version=bpy.app.version_string,elapsed_s=time.time()-started)
(OUT/'open_deck_insertion.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('H02_OPEN_DECK',report['status'],len(rows),rows[-1],flush=True)
