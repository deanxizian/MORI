"""Read-only native connectivity, actual ground contacts and local geometry for R152O."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import *
from plan_existing_copper import groups

b = Path('robot/.state/c3-completion/trials')
a = Copper('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c = Copper(b / 'R152O/MORI_Interface_C3.kicad_pcb')
out = b / 'R152O-inspection.json'
assert not out.exists()
assert a.sha == '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
assert c.sha == '7a74c8cf57681740216e47ab2f1b7f52af83a652cb6379c83d8dde4cb9353bd9'
metrics = json.loads((b / 'R152O-local-metrics.json').read_text())
net_names = sorted({p.GetNetname() for p in c.pads})
selected = [n for n in net_names if 'BAT_ADC' in n or n == '/FAULT_N']
connections = {n: {label: [g['pads'] for g in groups(d, n)]
                    for label, d in [('source', a), ('candidate', c)]}
               for n in selected}
adc = '/01 {slash} Core/BAT_ADC'
assert connections[adc]['candidate'] == [['J101.5', 'R1021.2', 'R1031.1']]
assert len(connections['/FAULT_N']['candidate']) == 4
upstream = next(n for n in selected if n.startswith('Net-'))
assert len(connections[upstream]['candidate']) == 2
assert connections[upstream]['candidate'] == connections[upstream]['source']
new = [t for t in c.segments if uid(t) not in a.by_id]
new_vias = [v for v in c.vias if uid(v) not in a.by_id]
assert len(new_vias) == 1 and new_vias[0].GetNetname() == 'GND'
via = new_vias[0]
contacts = via_contact_layers(c.board, via)
assert all(n in contacts for n in ['F.Cu', 'In1.Cu', 'In4.Cu'])
fps = {f.GetReference(): f for f in c.footprints}
refs = sorted({h['reference'] for row in metrics['new_tracks']
               for h in row['nominal_body_projections']} | {'D901'})
components = {ref: {'value': fps[ref].GetValue(),
                    'layer': c.board.GetLayerName(fps[ref].GetLayer()),
                    'position_mm': xy(fps[ref].GetPosition()),
                    'pads': [{'number': p.GetNumber(), 'net': p.GetNetname(),
                              'position_mm': xy(p.GetPosition())} for p in fps[ref].Pads()]}
              for ref in refs}
front_adc = [c.shapes[uid(t), 'F.Cu'] for t in new if t.GetNetname() == adc]
front_fault = [c.shapes[uid(t), 'F.Cu'] for t in c.segments
               if t.GetNetname() == '/FAULT_N' and t.GetLayer() == c.ids['F.Cu']]
sameface = [{'track_uuid': row['uuid'], 'net': row['net'], 'layer': row['layer'], **h}
            for row in metrics['new_tracks'] for h in row['nominal_body_projections'] if h['same_face']]
assert len(sameface) == 1 and sameface[0]['reference'] == 'J101'
data = {
    'scope': __doc__, 'source_sha256': a.sha, 'candidate_sha256': c.sha,
    'connectivity': connections,
    'battery_sampling_chain_complete': False,
    'new_ground_via': {'uuid': uid(via), **via_snapshot(c.board, via), 'native_contact_layers': contacts},
    'new_trace_lengths_mm': {n: sum(LineString([xy(t.GetStart()), xy(t.GetEnd())]).length
                                  for t in new if t.GetNetname() == n)
                             for n in sorted({t.GetNetname() for t in new})},
    'front_ADC_to_FAULT_min_copper_distance_mm': min(x.distance(y) for x in front_adc for y in front_fault),
    'same_face_nominal_body_intersections': sameface,
    'same_face_exception': 'J101.5 straight outward connector escape through the nominal housing lip only; all native keepouts preserved. Not zero body overlap or measured fit.',
    'projected_components': components,
    'limits': ['Nominal body envelopes and polygonized native copper only.',
               'Lengths and separation are local geometry; not ADC error, coupling, temperature or ampacity qualification.',
               'D901 retains its original series diode role and unchanged pads; only its downstream wide trace and existing via position change.'],
    'physical': 'NOT_TESTED', 'manufacturing_release': False,
}
out.write_text(json.dumps(data, indent=2) + '\n')
assert hashlib.sha256(Path(a.path).read_bytes()).hexdigest() == a.sha
assert hashlib.sha256(Path(c.path).read_bytes()).hexdigest() == c.sha
print(json.dumps({k: data[k] for k in ['connectivity', 'new_ground_via', 'new_trace_lengths_mm', 'front_ADC_to_FAULT_min_copper_distance_mm']}))
