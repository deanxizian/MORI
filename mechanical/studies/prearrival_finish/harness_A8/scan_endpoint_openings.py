"""Screen radial exits at existing joint gaps, with no source geometry edits."""
from pathlib import Path
SCRIPT=Path(__file__).resolve();HELPER=SCRIPT.parent.parent/'head_harness/check_loop_source_solids.py'
__file__=str(HELPER)
exec(compile(HELPER.read_text().split('\ngroups=[]')[0],str(HELPER),'exec'),globals())
__file__=str(SCRIPT);OUT=SCRIPT.parent
src=OUT/'central_uart_curves.json';curves=json.loads(src.read_text())
assert before==curves['source_blend_sha256']
radius=curves['wire_od_max_mm']/2;rows=[]
for end,levels in [('body',[147.7,148.,148.3]),('yaw',[183.,184.,185.,186.,187.,188.])]:
    for z in levels:
        for angle in range(0,360,30):
            theta=math.radians(angle);unit=np.array([math.cos(theta),math.sin(theta),0.])
            ps=np.arange(6.8,35.001,.1)[:,None]*unit+np.array([0,0,z])
            # At the assembly zero, both groups use world coordinates. These
            # are point-radius probes only; curved approaches/motion follow.
            bad=None
            for name,s in ss.items():
                h=sample_clear(ps,radius,0,[name])
                if h:bad=h;break
            rows.append(dict(end=end,z_mm=z,zero_azimuth_deg=angle,
                status='BLOCKED' if bad else 'PASS',failure=bad))
        print('A8_RADIAL_LAYER',end,z,[r['zero_azimuth_deg'] for r in rows if r['end']==end and r['z_mm']==z and r['status']=='PASS'],flush=True)
out=dict(status='PASS' if all(any(r['status']=='PASS' and r['end']==end for r in rows) for end in ['body','yaw']) else 'BLOCKED',
    scope='Straight radial probe at assembly zero only; no continuous real cable or bend qualification',
    source_blend_sha256=before,source_curve_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),
    wire_od_max_mm=2*radius,external_project_gap_mm=.3,radial_probe_interval_mm=[6.8,35],
    results=rows,main_geometry_changed=False,head_motion='NOT_TESTED',minimum_bend='NOT_TESTED',
    limits=['A radial pass does not connect a vertical wire to it with a valid bend.',
        'Failed finite levels/angles are not exhaustive proof that no other exit exists.'])
(OUT/'radial_endpoint_openings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
assert hashlib.sha256(source.read_bytes()).hexdigest()==before
