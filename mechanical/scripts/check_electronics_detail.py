"""Read the separate PCB review blend and verify every editable reference.

This checks the derivative against the unchanged source assembly, not physical
samples or missing vendor dimensions. It never saves either Blender file.
"""
import sys, json, hashlib
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import *

scene = bpy.data.scenes['MORI_PCB_Component_Detail']
manifest = json.loads((ROOT/'reports/electronics_detail_manifest.json').read_text())
errors, checked, maximum = [], 0, 0.0
for row in manifest['per_reference_objects']:
    ob = bpy.data.objects[row['object']]
    source = bpy.data.objects[PREFIX + row['board']]
    refs = json.loads(source['component_reference_index'])
    ref = next(r for r in refs if r['reference'] == row['ref'])
    lo, hi = ref['vertices']
    expected = np.array([tuple(v.co) for v in source.data.vertices[lo:hi]])
    actual = np.array([tuple(v.co) for v in ob.data.vertices])
    if expected.shape != actual.shape:
        errors.append({'object': ob.name, 'error': 'vertex count'})
        continue
    error = float(np.max(np.abs(expected - actual)))
    transform_error = float(np.max(np.abs(np.array(ob.matrix_world)-np.array(source.matrix_world))))
    maximum = max(maximum, error, transform_error)
    if error > 0.0001 or transform_error > 0.0001 or ob.name not in scene.objects:
        errors.append({'object': ob.name, 'vertex_error_mm': error, 'transform_error': transform_error})
    if ob.get('reference') != row['ref'] or not ob.get('evidence'):
        errors.append({'object': ob.name, 'error': 'missing provenance'})
    checked += 1

current_hash = hashlib.sha256((ROOT/'mori_v1_2.blend').read_bytes()).hexdigest()
source_matches = current_hash == manifest['source_main_sha256'] == scene['source_main_sha256']
mm = scene.unit_settings.system == 'METRIC' and abs(scene.unit_settings.scale_length-.001) < 1e-8
result = {'status': 'PASS' if not errors and source_matches and mm else 'FAIL',
          'independent_reference_objects_checked': checked, 'maximum_coordinate_difference_mm': maximum,
          'source_main_hash_matches': source_matches, 'millimetre_scene': mm, 'errors': errors,
          'scope': 'Exact source mesh ranges and assembly transforms retained per reference. No physical metrology or missing vendor geometry qualification.'}
save_json(ROOT/'reports/electronics_detail_validation.json', result)
print(json.dumps(result, ensure_ascii=False))
if result['status'] != 'PASS':
    raise RuntimeError('PCB detail derivative does not match the main model')
