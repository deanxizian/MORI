"""Repeat bounded H06 body search with documented AMASS mating heights.

Independent route study. Keep PCB pin order, existing hardware and fixed wires;
use the cleaned J2 print candidate only in memory. No source files are saved.
"""
from pathlib import Path
NEW_SCRIPT=Path(__file__).resolve();NEW_DIR=NEW_SCRIPT.parent
BASE=NEW_DIR/'plan_h06_body_leads.py';__file__=str(BASE)
exec(compile(BASE.read_text().split('ports=json.loads')[0],str(BASE),'exec'),globals())
__file__=str(NEW_SCRIPT)
sys.path.insert(0,str(NEW_DIR/'amass_mating'))
from envelopes import rebuild

mate_rows=rebuild(plug,portrows,port_pins,globals(),'upper_with_thickness_allocation')
for name in ['Yaw_Base','Pitch_Yoke']:
    raw=np.load(NEW_DIR/'terminal_threading/cleaned'/f'{name}.npz')
    obj=ss[name].o;mesh=bpy.data.meshes.new('A8_H06_cleaned_'+name)
    mesh.from_pydata(raw['vertices_mm'].tolist(),[],raw['triangles'].tolist());mesh.update()
    obj.data=mesh;obj.matrix_world=Matrix.Identity(4);bpy.context.view_layer.update()
    ss[name]=Solid(obj)
obstacles=dict(ss);obstacles.update({'Plug_'+k:s for k,s in plug.items()})
trees={n:s.bvh() for n,s in obstacles.items()}

def clear(points,error,ignore=()):
    allowance=OD/2+MARGIN+np.linalg.norm(np.diff(points,axis=0),axis=1).max()/2+error+1e-4
    allobs=[(n,s.lo,s.hi,s.m,trees[n]) for n,s in obstacles.items() if n not in ignore]
    allobs += [(n,r['lo'],r['hi'],r['m'],r['tree']) for n,r in fixed.items() if n not in ignore]
    for name,lo,hi,solid,tree in allobs:
        mask=np.all(points>=lo-allowance,axis=1)&np.all(points<=hi+allowance,axis=1)
        for p in points[mask]:
            d=float(tree.find_nearest(Vector(p))[3])
            if d<allowance:return {'object':name,'point_mm':p.tolist(),'distance_mm':d,'required_mm':float(allowance)}
        # Each contiguous sample run is continuous and already farther than
        # allowance from the surface. One interior sample tests containment.
        ids=np.flatnonzero(mask)
        starts=ids[np.r_[True,np.diff(ids)>1]] if len(ids) else []
        for idx in starts:
            p=points[idx]
            if np.all(p>=lo) and np.all(p<=hi):
                tiny=manifold.Manifold.sphere(.01,16).translate(p.tolist())
                if (tiny^solid).volume()>tiny.volume()/2:return {'object':name,'point_mm':p.tolist(),'inside':True}
    return None

ports=json.loads((NEW_DIR/'h06_ports.json').read_text())
joined=json.loads((NEW_DIR/'joined_entry_screen.json').read_text())
STAGING_RADIUS=14.8
# Reuse the recorded analytic R7 quarter/S construction, extending the finite
# planar-control family. It writes no result until this script's own footer.
ARC_SOURCE=NEW_DIR/'plan_h06_body_arcs.py'
search=ARC_SOURCE.read_text().split('axes=[45,135,225,315];',1)[1].split('\nreport={',1)[0]
search='axes=[45,135,225,315];'+search
search=search.replace('[8.,12.,16.,20.,24.]','[8.,12.,16.,20.,24.,32.,40.,48.]')
exec(compile(search,str(ARC_SOURCE),'exec'),globals())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
possible=[list(p) for p in itertools.permutations(axes) if all(pools[f'{pin}_{a}'] for pin,a in enumerate(p,1))]
report={'status':'PASS' if possible else 'BLOCKED',
    'scope':'Individual bounded body-prefix pools with current AMASS height; not simultaneous packing or full head harness',
    'source_blend_sha256':source_hash,'source_script_sha256':sha(NEW_SCRIPT),
    'source_helpers':{str(p.relative_to(PROJECT)):sha(p) for p in [BASE,ARC_SOURCE,NEW_DIR/'amass_mating/envelopes.py']},
    'source_cleaned_J2_sha256':sha(NEW_DIR/'terminal_threading/cleaned/candidate.blend'),
    'source_dimensions_sha256':sha(NEW_DIR/'amass_mating/received_dimensions.json'),
    'source_ports_sha256':sha(NEW_DIR/'h06_ports.json'),'source_fixed_wires_sha256':sha(fixed_path),
    'source_installed_routes_sha256':sha(NEW_DIR/'joined_entry_screen.json'),
    'mating_mode':'upper_with_thickness_allocation','updated_mating_envelopes':mate_rows,
    'wire_OD_mm':OD,'required_radius_mm':REQUIRED_R,'staging_radius_mm':STAGING_RADIUS,
    'source_objects':len(ss),'mated_allocations':len(plug),'fixed_wires':len(fixed),
    'pools':pools,'trials':trials,'possible_individual_phase_assignments':possible,'elapsed_s':time.time()-start,
    'main_model_applied':False,'four_simultaneous_wires':'NOT_TESTED','physical_retention':'NOT_TESTED',
    'complete_harness':'BLOCKED','cut_lengths_released':False,
    'limitations':['AMASS upper depth5.9mm is conditional allocation; solder/heatshrink/lead departure not finalized.',
      '5mm PH terminal straight and port exit plane are allocated, not measured.',
      'Only zero head pose; four-wire packing, all moving solids and strain relief still required.',
      'No universal routing impossibility is inferred from this finite curve family.']}
(NEW_DIR/'body_leads/documented_mate_prefix_pools.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('H06_DOCUMENTED_MATES_PREFIX',report['status'],len(possible),'phase assignments',round(time.time()-start,2),flush=True)
