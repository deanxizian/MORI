"""Read-only four separate UART wires in vertical planes; no cable selection."""
from pathlib import Path
BASE=Path(__file__).resolve().with_name('check_outer_neck_probes.py')
exec(compile(BASE.read_text().split('# Endpoints are named')[0],str(BASE),'exec'),globals())
od=float(wire_rows['H06']['绝缘外径最大mm']);zmid=159.5;zs=[zmid+(i-1.5)*(od+.05) for i in range(4)]
angles=np.linspace(0,2*math.pi,361)[:-1];unit=np.column_stack([np.cos(angles),np.sin(angles),np.zeros(len(angles))])
trees={n:s.bvh() for n,s in ss.items()};accepted=[];rejects=collections.Counter()
for rr in np.arange(33.,54.01,.5):
    failed=None
    for z in zs:
        pp=unit*rr+np.array([0,0,z]);clear=od/2+.3+rr*math.sin(math.pi/360)+1e-4
        for name,s in ss.items():
            mask=np.all(pp>=s.lo-clear,axis=1)&np.all(pp<=s.hi+clear,axis=1)
            for p in pp[mask]:
                if trees[name].find_nearest(Vector(p))[3]<clear:failed=name;break
            if failed:break
            if np.all(pp>=s.lo) and np.all(pp<=s.hi):
                tiny=manifold.Manifold.sphere(.01,16).translate(pp[0].tolist())
                if (tiny^s.m).volume()>tiny.volume()*.5:failed=name;break
        if failed:break
    if failed:rejects[failed]+=1
    else:accepted.append(float(rr))
out=dict(status='PASS' if accepted else 'BLOCKED',source_blend_sha256=before,
         source_wire_csv_sha256=hashlib.sha256(wire_path.read_bytes()).hexdigest(),
         scope='Four unselected individual wires, same planar XY path at four different heights',
         groups=[dict(id='UART_FLAT',count=4,OD=od,z=zmid,bend=10.922,
                      members=['H06_1','H06_2','H06_3','H06_4'],
                      individual_plane_z_mm=zs,enclosing_diameter_mm=od,
                      diameter_meaning='Each individual wire diameter, not a circular four-wire bundle',
                      total_vertical_height_mm=3*(od+.05)+od,
                      accepted_centre_radii_mm=accepted,certified_external_project_gap_mm=.3,
                      intentional_within_group_insulation_gap_mm=.05)],
         rejects=dict(rejects),main_geometry_changed=False,selected_cable=False,
         within_group_gap_basis='ASSUMED packing gap; not 0.3mm external project spacing',
         static_circle_clearance='PASS' if accepted else 'BLOCKED',actual_retention='NOT_TESTED',
         limits=['No tape, jacket, cable clamp or ribbon stock has been selected.',
                 'The four insulation surfaces have a nominal 0.05mm packing gap within this group.',
                 'Static annular occupancy does not qualify the dynamic path or its installed approaches.'])
(HERE/'uart_flat_space.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
print('UART_FLAT_SPACE',out['status'],zs,accepted,time.time()-start,flush=True)
