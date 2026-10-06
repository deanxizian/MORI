"""Replay prior static route candidates on the newly received board solids."""
from pathlib import Path
HERE=Path(__file__).resolve().parent
code=(HERE/'harness_routes.py').read_text().split('specs=')[0]
replacement="""# Received rearJ3 is now B-side and Y-shifted; replace its envelope too.
hand=json.loads((PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json').read_text())
p=plug['rear_J3'];cc=(p.lo+p.hi)/2;bb=hand['rear_J3']['nominal_screen']['plug_world_bounds_mm'];tt=(np.array(bb[:3])+bb[3:])/2
tr=Matrix.Translation(Vector(tt))@Matrix.Rotation(math.pi,4,'X')@Matrix.Translation(-Vector(cc))
p.o.matrix_world=tr@p.o.matrix_world;bpy.context.view_layer.update();plug['rear_J3']=Solid(p.o)
obstacles=dict(ss)"""
assert code.count('obstacles=dict(ss)')==1
code=code.replace('obstacles=dict(ss)',replacement)
code=code.replace('with bpy.data.libraries.load(', "for existing in list(bpy.data.objects):\n    if existing.name.startswith(PREFIX+'PREARRIVAL_Plug_') and existing.get('mori_owner')==OWNER:bpy.data.objects.remove(existing,do_unlink=True)\nwith bpy.data.libraries.load(",1)
exec(compile(code,str(HERE/'harness_routes.py'),'exec'))
old=json.loads((HERE/'harness_routes.json').read_text());rows=[]
for row in old['static_routes']:
    if row['status']!='PASS':continue
    pts=np.array(row['curve_mm']);rad=row['bundle_diameter_allocation_mm']/2
    hs=solid_hits(pts,rad)
    rows.append(dict(id=row['id'],status='PASS' if not hs else 'FAIL',solid_hits=hs,scope='Same prior candidate centreline/assumed diameter only. No terminal fanout, anchors, mutual crowding or wire qualification.'))
    print('P5R7_ROUTE_REPLAY',row['id'],rows[-1]['status'],hs[:2],flush=True)
# The higher, component-up core invalidated old H01. Refine only this route
# against the complete received candidate, with the same assumed OD/R.
for row in rows:
    if row['status']=='PASS':continue
    assert row['id']=='H01',row['id']
    radius=1.6;R=6;exa,a,aa=endpoint('power_J17',radius);exb,b,ab=endpoint('motion_J1',radius)
    attempts=0
    for za,zb,yback in itertools.product([140,142,144,146,148],[140,142,144,146,148],[-34,-39,-44,-48]):
        attempts+=1
        controls=[a,np.array([a[0],a[1],za]),np.array([a[0],yback,za]),np.array([b[0],yback,zb]),np.array([b[0],b[1],zb]),b]
        curve=rounded(controls,R)
        if curve is None:continue
        if not all(free(p,radius+.3) for p in resample(curve,.6)):continue
        if not all(line_free(p,q,radius+.3) for p,q in zip(curve,curve[1:])):continue
        hs=solid_hits(curve,radius)
        if hs:continue
        row.update(previous_path_conflicts=row['solid_hits'],solid_hits=[],status='PASS',route_changed=True,curve_mm=[p.tolist() for p in curve],controls_mm=[p.tolist() for p in controls],length_mm=sum(float(np.linalg.norm(q-p)) for p,q in zip(curve,curve[1:])),analytic_arc_radius_mm=R,bundle_diameter_allocation_mm=3.2,scope='Revised static candidate, analytic circular bends. Terminal fanout, strain relief, mutual crowding and actual cable remain open.')
        break
    row['refinement_attempts']=attempts
    print('H01_REFINEMENT',row['status'],row.get('length_mm'),attempts,flush=True)
result=dict(candidate_sha256=hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),base_report_sha256=hashlib.sha256((HERE/'harness_routes.json').read_bytes()).hexdigest(),received_handoff_sha256=hashlib.sha256((PROJECT/'hardware/v1_2/handoff/mechanical_P5R7.json').read_bytes()).hexdigest(),rows=rows,status='PASS' if all(x['status']=='PASS' for x in rows) else 'BLOCKED',remaining='H04 and complete moving harness were never passed by the old study. No released cut lengths or new print cuts.')
(HERE/'p5r7_receipt/route_replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
