"""Locate the actual minimum at the finite reshaping cases which failed."""
from pathlib import Path
LOC_SCRIPT=Path(__file__).resolve();LOC_DIR=LOC_SCRIPT.parent
LOC_HELPER=LOC_DIR/'check_coupled_feed_relaxation.py';__file__=str(LOC_HELPER)
import sys
if '--raw' not in sys.argv:sys.argv.append('--raw')
exec(compile(LOC_HELPER.read_text().split("\nfor stage in ['radial_and_height'",1)[0],str(LOC_HELPER),'exec'),globals())
__file__=str(LOC_SCRIPT)
rows=[]
for u in [.4,.5,.6,.7]:
    points,err,bend,length=core_curve(7.6-.8*u,178+u,202.1+3.9*u,0.,45)
    tree=trees['Pitch_Yoke'];distances=np.array([tree.find_nearest(Vector(p))[3] for p in points]);i=int(np.argmin(distances))
    rows.append({'fraction':u,'minimum_sampled_centre_to_surface_mm':float(distances[i]),
        'wire_surface_gap_at_sample_mm':float(distances[i]-.3302),'point_mm':points[i].tolist(),
        'point_index':i,'nominal_gap_requirement_mm':.3,'curve_error_mm':err})
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
result={'status':'PASS','scope':'Diagnostic only; finite candidates still blocked if sampled gap<.3',
    'source_script_sha256':sha(LOC_SCRIPT),'source_curve_helper_sha256':sha(LOC_HELPER),
    'source_candidate_sha256':sha(OUT/'candidate.blend'),'rows':rows}
(OUT/'relaxation_minima.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(rows,ensure_ascii=False),flush=True)
