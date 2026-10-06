"""Export head routing cross sections from current independent J3M solids.

Read-only diagnostic: does not change the assembly, selected hardware or wires.
"""
from pathlib import Path
PITCH_SPACE_SCRIPT = Path(__file__).resolve(); PITCH_SPACE_DIR = PITCH_SPACE_SCRIPT.parent
PITCH_SPACE_HELPER = PITCH_SPACE_DIR / 'check_cam_uart_mating_allocation.py'
__file__ = str(PITCH_SPACE_HELPER)
exec(compile(PITCH_SPACE_HELPER.read_text().split('\nrows=[];minimum_noncontact_gap', 1)[0], str(PITCH_SPACE_HELPER), 'exec'), globals())
__file__ = str(PITCH_SPACE_SCRIPT)
OUT = PITCH_SPACE_DIR / 'cam_pitch_flex'; OUT.mkdir(exist_ok=True)
sections = []
for z in [191., 193., 196., 200., 204., 208., 212., 216., 222.]:
    rows = []
    for name, group, m in reference_sources:
        bb = np.array(m.bounding_box())
        if bb[2] <= z <= bb[5] and np.all(bb[:2] <= 55) and np.all(bb[3:5] >= -55):
            paths = m.slice(z).to_polygons()
            if paths:
                rows.append({'name':name, 'group':group, 'polygons':[p.tolist() for p in paths]})
    sections.append({'z_mm':z, 'rows':rows})
out = {'status':'PASS', 'scope':'Diagnostic zero-pose solid sections, not clearance or strength qualification',
       'source_main_sha256':source_hash, 'source_script_sha256':sha(PITCH_SPACE_SCRIPT),
       'source_candidate_sha256':sha(candidate/'candidate.blend'), 'sections':sections,
       'bounds':[{'name':n,'group':g,'bounds_mm':list(m.bounding_box())} for n,g,m in reference_sources
                 if m.bounding_box()[5]>190 and m.bounding_box()[2]<260],
       'main_applied':False}
(OUT/'routing_sections.json').write_text(json.dumps(out, ensure_ascii=False, indent=2)+'\n')
assert sha(source)==source_hash
print('PITCH_ROUTING_SECTIONS',len(sections),flush=True)
