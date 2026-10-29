"""Prioritize real native opens and allow explicit coupled signal rerouting."""
import hashlib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0,'robot/hardware/driver/development/scripts')
from copper_geometry import Copper
from prepare_freerouting import closing

b = Path('robot/.state/c3-completion/trials')
out = b / (sys.argv[1] if len(sys.argv)>1 else 'R152-joint-exchange')
assert not out.exists();out.mkdir()
source = Path('robot/hardware/driver/development/native/MORI_Interface_C3.kicad_pcb')
c = Copper(source)
assert c.sha == '958eee80ba27a607e52507fcefe4c5b5aa4234d08a8d7bdb6f1257e79dea89a1'
groups = c.pad_groups()
open_nets = {n for n,g in groups.items() if len(g)>1 and not n.startswith('unconnected-')}
coupled = {'/CLR_N', '/01 {slash} Core/WHEEL_ADC', '/01 {slash} Core/ACT_CURRENT_ADC',
           'Net-(U1001-D3_{slash}_current_ADC)', 'Net-(U1001-S2_{slash}_WHEEL_sense)',
           'Net-(D1001-K)'}
assert coupled <= set(groups)
active = open_nets | coupled
original = b / 'R152-exchange2/R148E-r13.dsn'
text = original.read_text()
translation = json.loads((original.parent/'translation.json').read_text())
power_nets = {n for x in translation['classes'] if x['source_class'] in ['VCC','GND'] for n in x['nets']}
movable = active - power_nets
classes = []
for m in reversed(list(re.finditer(r'(?m)^    \(class\s',text))):
    start=m.start()+4;end=closing(text,start);scope=text[start:end+1]
    nested=re.search(r'\n\s+\(circuit',scope).start()
    tokens=re.findall(r'"(?:\\.|[^"\\])*"|[^\s()]+',scope[:nested])
    assert tokens[0]=='class'
    nets=[json.loads(t) if t.startswith('"') else t for t in tokens[2:]]
    body=scope[nested:-1]
    replacements=[]
    for work in [False,True]:
        members=sorted(n for n in nets if (n in active)==work)
        if not members:continue
        name=tokens[1]+('_work' if work else '_skip')
        replacements.append('(class '+name+'\n      '+'\n      '.join(json.dumps(n) for n in members)+body+')')
        classes.append(dict(name=name,nets=members,active=work))
    text=text[:start]+'\n    '.join(replacements)+text[end+1:]
unlocked=[]
for m in reversed(list(re.finditer(r'\(wire\s',text))):
    start=m.start();end=closing(text,start);scope=text[start:end+1]
    found=re.search(r'\(net\s+("(?:\\.|[^"\\])*"|[^\s()]+)\)',scope)
    assert found
    net=json.loads(found[1]) if found[1].startswith('"') else found[1]
    if net in movable:
        assert scope.count('(type protect)')==1
        unlocked.append(net)
        # Freerouting calcFixed recognizes normal as UNFIXED. KiCad's route
        # token is not equivalent: this build imports it as USER_FIXED.
        text=text[:start]+scope.replace('(type protect)','(type normal)')+text[end+1:]
target=out/'R148E-joint.dsn';target.write_text(text)
report=dict(scope=__doc__, source_board_sha256=c.sha,
            input_sha256=hashlib.sha256(original.read_bytes()).hexdigest(),
            output_sha256=hashlib.sha256(target.read_bytes()).hexdigest(),
            open_nets={n:len(groups[n]) for n in sorted(open_nets)},
            coupled_connected_nets=sorted(coupled), movable_signal_nets=sorted(movable),
            source_wire_paths_marked_normal=len(unlocked), existing_vias='protected',
            requires_loaded_fixed_state_validation=True,
            existing_power_and_ground_tracks='protected', classes=classes,
            ignore_classes=sorted(x['name'] for x in classes if not x['active']),
            native_unchanged=hashlib.sha256(source.read_bytes()).hexdigest()==c.sha,
            limits=['All native source files and interfaces remain untouched.',
                    'Routing proposals may replace only explicitly reviewed signal tracks; preserve source vias unless a later exact native plan qualifies their removal.',
                    'Source power continuity, ground, references, and every original connection still require native regression.'])
target.with_suffix('.routing.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['open_nets','coupled_connected_nets','source_wire_paths_marked_normal','ignore_classes','native_unchanged']},ensure_ascii=False))
