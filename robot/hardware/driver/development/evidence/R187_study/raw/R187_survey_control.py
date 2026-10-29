"""Compare the promoted full-reference survey to the frozen R186 oracle."""
import hashlib, json
from pathlib import Path
b = Path('robot/.state/c3-completion/trials')
old = json.loads((b/'R186-full-reference-survey.json').read_text())
new = json.loads((b/'R187-source-reference-survey.json').read_text())
assert old['source_sha256'] == new['source_sha256']
a = {r['uuid']:r for r in old['tracks']}
c = {r['uuid']:r for r in new['tracks']}
assert a.keys() == c.keys()
errors = {u:abs(a[u]['missing_reference_mm2']-c[u]['missing_reference_mm2']) for u in a}
assert max(errors.values()) < 1e-12
assert all(a[u]['status'] == c[u]['status'] for u in a)
for k in ['non_GND_tracks_reviewed','flagged_tracks','flagged_nets']:
    assert old[k] == new[k]
path = Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
assert hashlib.sha256(path.read_bytes()).hexdigest() == old['source_sha256']
result = dict(status='PASS', source_sha256=old['source_sha256'], compared_tracks=len(a),
              maximum_difference_mm2=max(errors.values()), flags_match=True,
              source_saved=False, threshold_mm2=1e-6,
              frozen_oracle='R186-full-reference-survey.json; independently cross-checked by R186-reference-survey-control.json')
with (b/'R187-survey-control.json').open('x') as f:
    json.dump(result,f,indent=2);f.write('\n')
print(json.dumps(result))
