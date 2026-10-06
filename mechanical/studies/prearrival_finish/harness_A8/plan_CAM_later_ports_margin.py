"""Same constructive search with a 0.3 mm physical-obstacle clearance bound."""
from pathlib import Path
MARGIN_SCRIPT=Path(__file__).resolve()
MARGIN_BASE=MARGIN_SCRIPT.parent/'plan_CAM_later_ports_grid.py'
prefix,run=MARGIN_BASE.read_text().split('\nrows=[]\noverall_started=',1)
__file__=str(MARGIN_BASE);exec(compile(prefix,str(MARGIN_BASE),'exec'),globals());__file__=str(MARGIN_SCRIPT)
from itertools import product
GRID_SCRIPT=MARGIN_SCRIPT
GRID_OUT=LATER_OUT/'grid_margin_approach';GRID_OUT.mkdir(exist_ok=True)
nominal_collision=collision_sweep
def collision_sweep(port,shape,targets,native_domain=None):
    hit=nominal_collision(port,shape,targets,native_domain)
    if hit or native_domain is not None:
        return hit
    pad=.3
    padded=manifold.Manifold.batch_hull([shape.translate(list(v)) for v in product([-pad,pad],repeat=3)])
    bb=np.asarray(padded.bounding_box())
    for name,(solid,lo,hi,_) in targets.items():
        if np.any(bb[:3]>hi) or np.any(bb[3:]<lo):
            continue
        volume=max(0.,float((padded^solid).volume()))
        if volume>1e-5:
            return dict(obstacle=name,kind='physical_clearance_bound',allocated_gap_mm=.3,padded_overlap_mm3=volume)
    return None
exec(compile('rows=[]\noverall_started='+run,str(MARGIN_BASE),'exec'),globals())
report.update(optimizer_base_sha256=sha(MARGIN_BASE),physical_solids_check='All free-motion swept bounds padded by +/-0.3 mm axis-aligned cube, a superset of a 0.3 mm Euclidean ball',
    initial_mating_margin='NOT_TESTED; initial 0 to 8 mm axial mating uses the original nominal overlap-domain check',
    clearance_does_not_include_actual_part_tolerances=True)
(GRID_OUT/'screen.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
