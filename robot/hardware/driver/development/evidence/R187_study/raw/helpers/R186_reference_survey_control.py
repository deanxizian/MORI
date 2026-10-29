"""Cross-check full survey against the established audit's per-track calculation."""
import hashlib,json,sys
from pathlib import Path
sys.path.insert(0,'robot/hardware/driver/development/scripts')
import audit_candidate as audit
from copper_geometry import Copper
b=Path('robot/.state/c3-completion/trials');out=b/'R186-reference-survey-control.json';assert not out.exists()
path=Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
class TreatTracksAsNew(dict):
    def __contains__(self,key):return False
calls=0
def load(path):
    global calls
    obj=Copper(path);calls+=1
    if calls==1:obj.by_id=TreatTracksAsNew(obj.by_id)
    return obj
audit.Copper=load
r=audit.audit(str(path),str(path),Path('robot/hardware/driver/evidence/R108P'))
survey=json.loads((b/'R186-full-reference-survey.json').read_text())
expected={row['uuid']:row['missing_reference_mm2'] for row in survey['tracks']}
actual={row['uuid']:row['reference_uncovered_mm2_outside_existing_lands_and_own_transfers'] for row in r['new_copper_review'] if row['net']!='GND'}
assert expected.keys()==actual.keys()
differences={u:abs(expected[u]-actual[u]) for u in expected};assert max(differences.values())<1e-9
assert hashlib.sha256(path.read_bytes()).hexdigest()==survey['source_sha256']
out.write_text(json.dumps(dict(scope=__doc__,status='PASS',source_sha256=survey['source_sha256'],compared_tracks=len(expected),maximum_difference_mm2=max(differences.values()),
                              method='Read-only audit instance treats source tracks as new solely for its coverage loop; production files and PCB are unchanged.',physical='NOT_TESTED'),indent=2)+'\n')
print(json.dumps(dict(status='PASS',tracks=len(expected))))
