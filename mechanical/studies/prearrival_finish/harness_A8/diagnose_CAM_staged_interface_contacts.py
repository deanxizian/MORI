"""Locate source-interface overlaps and check the horn-before-cradle order.

No geometry or interface is repaired or waived. Numerical contact, actual
solid penetration and unselected manufacturer parts stay separate findings.
"""
from pathlib import Path
DIC_SCRIPT=Path(__file__).resolve();DIC_HELPER=DIC_SCRIPT.parent/'screen_CAM_staged_pitch_installation.py'
__file__=str(DIC_HELPER)
exec(compile(DIC_HELPER.read_text().split('\nrows=[];started=time.time()',1)[0],str(DIC_HELPER),'exec'),globals())
__file__=str(DIC_SCRIPT)
DIC_OUT=PST_OUT/'interface_contacts';DIC_OUT.mkdir(exist_ok=True)
rows=[];started=time.time();base=fixture|upper|bridge|yaw|keeper_screws|reaction_retainer
check('complete_yaw_with_horn',[(trans(z=float(z)),) for z in np.arange(0,90.01,.5)],
      [yaw|horn],fixture|upper|bridge,'Horn staged with the physical servo before yaw-unit insertion; placeholder interface remains unresolved.')
check('cradle_CAM_over_installed_horn',[(trans(z=float(z)),) for z in np.arange(0,70.01,.5)],
      [cradle],base|horn,'Both short shafts remain loose; all other source yaw pieces, including output and horn, are included.')

contacts=[]
axis=np.array([0.,math.cos(math.radians(10)),math.sin(math.radians(10))])
for a,b in [('Head_Front','Display_Frame'),('Head_Front','Display_PCB'),('Pitch_Lock_Screw','Pitch_Output')]:
    overlap=solids[a]^solids[b];vol=max(0.,float(overlap.volume()))
    raw=overlap.to_mesh64();vertices=np.asarray(raw.vert_properties[:,:3]);faces=np.asarray(raw.tri_verts)
    key=a+'__'+b
    np.savez_compressed(DIC_OUT/(key+'.npz'),vertices_mm=vertices,triangles=faces)
    probes=[]
    directions=[('optic_normal',axis),('X',np.array([1.,0.,0.]))] if a=='Head_Front' else [('X',np.array([1.,0.,0.]))]
    for label,v in directions:
        for shift in [-.2,-.1,-.05,-.01,-.001,0,.001,.01,.05,.1,.2]:
            ov=solids[a]^solids[b].translate((shift*v).tolist())
            probes.append(dict(axis=label,shift_mm=shift,intersection_mm3=max(0.,float(ov.volume()))))
    contacts.append(dict(a=a,b=b,intersection_mm3=vol,bounds_mm=list(overlap.bounding_box()) if len(vertices) else None,
        overlap_mesh=str((DIC_OUT/(key+'.npz')).relative_to(PROJECT)),
        components_mm3=[float(x.volume()) for x in overlap.decompose()],
        surface_gap_bounded_search_mm=float(solids[a].min_gap(solids[b],1.)),
        optic_axis_projected_extent_mm=float(np.ptp(vertices@axis)) if len(vertices) else 0.,
        diagnostic_translations=probes,physical_contact_intent='NOT_ESTABLISHED',geometry_changed=False))
    print('STAGED_INTERFACE_CONTACT',key,vol,contacts[-1]['bounds_mm'],probes,flush=True)
report=dict(status='PASS',scope='Completed diagnostic record; source overlap and unresolved transmission are not waived',
    script_sha256=sha(DIC_SCRIPT),helper_sha256=sha(DIC_HELPER),source_main_sha256=source_hash,
    protected_sources=protected,substituted_unadopted_prints={n:dict(path=str(p.relative_to(PROJECT)),sha256=sha(p)) for n,p in replacements.items()},
    order_rows=rows,source_contacts=contacts,contact_acceptance='BLOCKED_PENDING_DIAGNOSIS',
    transmission_interfaces='BLOCKED_PENDING_VENDOR',main_applied=False,whole_harness='BLOCKED',
    manufacturing_release=False,elapsed_s=time.time()-started)
(DIC_OUT/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert all(sha(PROJECT/p)==h for p,h in protected.items())
print('STAGED_INTERFACE_DIAGNOSIS_DONE',round(time.time()-started,2),flush=True)
