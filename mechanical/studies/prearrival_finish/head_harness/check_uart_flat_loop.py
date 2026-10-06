"""Apply the existing planar solver to a four-wire vertical arrangement.

Each individual wire has the same XY curve and its own constant Z; all four
lengths therefore equal the solved planar length, without radial sliding.
Detailed source-solid, endpoint and retention checks are still required.
"""
from pathlib import Path
import sys,hashlib,json
HERE=Path(__file__).resolve().parent
helper=HERE/'check_split_planar_loops.py';code=helper.read_text()
# Run the same finite refined parameter family without importing any prior
# PASS row. Record the exact helper hash and modified study assumptions.
code=code.replace("source=HERE/'split_yaw_space.json'", "source=HERE/'uart_flat_space.json'")
code=code.replace("REFINE='--refine' in sys.argv", "REFINE=True")
code=code.replace("previous=json.loads((HERE/'split_planar_loops.json').read_text()) if REFINE else None", "previous=None")
code=code.replace("    if REFINE:\n        earlier=next(g for g in previous['groups'] if g['id']==group['id'])\n        if earlier['status']=='PASS':all_results.append(earlier);continue\n", "")
code=code.replace("(HERE/('split_planar_loops_refined.json' if REFINE else 'split_planar_loops.json'))", "(HERE/'uart_flat_planar_loop.json')")
exec(compile(code,str(helper),'exec'),globals())
result_path=HERE/'uart_flat_planar_loop.json';out=json.loads(result_path.read_text())
flat=json.loads((HERE/'uart_flat_space.json').read_text())['groups'][0]
out.update(scope='Four parallel unselected UART wires in separate constant-Z planes',
           physical_group_count=4,individual_plane_z_mm=flat['individual_plane_z_mm'],
           diameter_meaning='Each separate wire, not a circular four-wire bundle',
           individual_wire_geometric_lengths='PASS' if out['status']=='PASS' else 'BLOCKED',
           physical_wire_lengths='NOT_TESTED',actual_retention='NOT_TESTED',
           planar_solver_sha256=hashlib.sha256(helper.read_bytes()).hexdigest(),
           prior_solver_limits='Original circular-bundle qualifications do not imply four-wire retention.')
out['limitations']=['All four constant-Z curves have the same solved XY length at 13 sampled yaw poses.',
                   'Every wire remains a PLACEHOLDER / ASSUMED route using an unselected catalogue wire.',
                   'The 0.05mm within-group packing gap is a study assumption, not the external 0.3mm project gap.',
                   'No tape, jacket, clamp, approach, terminal or dynamic lifetime has been qualified.',
                   'No source-solid, installed-sequence or inter-group motion result follows from the planar solver.']
result_path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
