"""Read-only sections for the original bridge and temporary wire-tail route."""
from pathlib import Path
DIAG_SCRIPT=Path(__file__).resolve()
DIAG_HELPER=DIAG_SCRIPT.parent/'screen_bridge_then_shell_over_wires.py'
__file__=str(DIAG_HELPER)
exec(compile(DIAG_HELPER.read_text().split('\nstarted=time.time();',1)[0],str(DIAG_HELPER),'exec'),globals())
__file__=str(DIAG_SCRIPT)
OUT=STOCK_OUT/'bridge_then_shell_over_wires'
source=json.loads((OUT/'screen.json').read_text())
row=source['bridge_rows'][-1]
t=trans(z=row['lift_mm'])
hits=[]
for pin,m in stock_terminals.items():
    for n in bridge_solids:
        intersection=m^bridge_solids[n].transform(t[:3,:4])
        if intersection.volume()>1e-5:
            hits.append(dict(pin=pin,obstacle=n,volume_mm3=float(intersection.volume()),
                world_bounds_mm=list(intersection.bounding_box()),
                bridge_local_bounds_mm=list(intersection.translate([0,0,-row['lift_mm']]).bounding_box())))
sections={n:{str(z):[p.tolist() for p in original_parts[n].slice(z).to_polygons()]
    for z in [110,125,132,134,136,139,143,145.6,146,147,150,160,166]}
    for n in ['Yaw_Base','Yaw_Bearing']}
radial_sections={str(angle):{n:[np.column_stack([p[:,0],-p[:,1]]).tolist()
    for p in original_parts[n].rotate([0,0,-angle]).rotate([90,0,0]).slice(0).to_polygons()]
    for n in ['Yaw_Base','Yaw_Bearing']} for angle in [45,135,225,315]}
theta=math.acos(1-(146.-139.)/8.)
radius=11.5+8-8*math.sin(theta)
probe_point=np.array([radius*math.cos(5*math.pi/4),radius*math.sin(5*math.pi/4),146.])
probe=manifold.Manifold.sphere(.005,24).translate(probe_point.tolist())
probe_fraction=float((probe^original_parts['Yaw_Base']).volume()/probe.volume())
report=dict(status='PASS',scope='Diagnostic native solid sections only',source_main_sha256=source_hash,
    script_sha256=sha(DIAG_SCRIPT),helper_sha256=sha(DIAG_HELPER),
    bridge_first_failure_lift_mm=row['lift_mm'],terminal_hits=hits,
    source_bounds={n:list(original_parts[n].bounding_box()) for n in bridge},sections=sections,
    radial_sections=radial_sections,
    bare_bridge_candidate_centre_probe=dict(staging_radius_mm=11.5,lower_bend_radius_mm=8.,
        point_mm=probe_point.tolist(),probe_radius_mm=.005,solid_fraction=probe_fraction,
        centre_inside=bool(probe_fraction>.99),scope='One exact analytic point; no global impossibility claim'),
    source_screen_sha256=sha(OUT/'screen.json'),main_applied=False)
(OUT/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print('DIAG_TAIL_HITS',json.dumps(hits),flush=True)
assert all(sha(PROJECT/p)==h for p,h in protected.items())
