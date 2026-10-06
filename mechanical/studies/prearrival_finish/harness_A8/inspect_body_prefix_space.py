"""Export constant-height body wiring corridors from current study solids."""
from pathlib import Path
INSPECT_SCRIPT=Path(__file__).resolve();INSPECT_DIR=INSPECT_SCRIPT.parent
INSPECT_HELPER=INSPECT_DIR/'plan_h06_documented_mates.py';__file__=str(INSPECT_HELPER)
exec(compile(INSPECT_HELPER.read_text().split('\nports=json.loads',1)[0],str(INSPECT_HELPER),'exec'),globals())
__file__=str(INSPECT_SCRIPT)
OUT=INSPECT_DIR/'body_prefix_v2';OUT.mkdir(exist_ok=True)
levels=[133.,136.,139.,142.63999938964844,146.]
rows=[]
all_solids=[(n,s.lo,s.hi,s.m) for n,s in obstacles.items()]+[(n,r['lo'],r['hi'],r['m']) for n,r in fixed.items()]
for name,lo,hi,m in all_solids:
    if lo[2]>max(levels)+.64 or hi[2]<min(levels)-.64:continue
    record={'id':name,'bounds_mm':np.r_[lo,hi].tolist(),'sections':{}}
    for z in levels:
        if lo[2]>z+.631 or hi[2]<z-.631:continue
        # Intersect a slab and project to XY. This includes features not exactly
        # crossing the middle plane. Offset handles cable OD and project gap.
        slab=manifold.Manifold.cube([180,180,1.262],True).translate([0,0,z])
        cut=m^slab
        if cut.is_empty():continue
        cross=cut.project()
        record['sections'][str(z)]=[p.tolist() for p in cross.to_polygons()]
    rows.append(record)
result={'source_blend_sha256':source_hash,'source_script_sha256':hashlib.sha256(INSPECT_SCRIPT.read_bytes()).hexdigest(),
    'source_helper_sha256':hashlib.sha256(INSPECT_HELPER.read_bytes()).hexdigest(),
    'z_levels_mm':levels,'slab_half_height_mm':.631,'XY_expansion':'Not applied; polygons show slab projection only',
    'rows':rows,'updated_mating_envelopes':mate_rows,'main_model_applied':False}
(OUT/'corridors.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print('BODY_PREFIX_CORRIDORS',len(rows),flush=True)
