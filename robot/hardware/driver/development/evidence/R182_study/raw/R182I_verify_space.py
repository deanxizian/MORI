"""Verify the independent space proposal after preserving KiCad project normalization."""
import hashlib, json, subprocess, sys
from pathlib import Path
sys.path.insert(0, 'robot/hardware/driver/development/scripts')
from copper_geometry import Copper, pcb, uid, xy, via_snapshot, polyset
b=Path('robot/.state/c3-completion/trials');dev=Path('robot/hardware/driver/development')
source=dev/'native';dest=b/'R182I';board='MORI_Interface_C3.kicad_pcb'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
expected='13f4f91514c85d54c8802c1cb061967ee915272a3d1ad34daac18e419bb47d66'
assert sha(source/board)==expected
members={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
project=dest/'MORI_Interface_C3.kicad_pro'
a=json.loads((source/project.name).read_text());z=json.loads(project.read_text())
differences=[]
def diff(a,z,path=''):
    if isinstance(a,dict) and isinstance(z,dict):
        for k in sorted(set(a)|set(z)):
            if k not in a or k not in z:
                differences.append(dict(path=path+'/'+k,source=a.get(k),saved=z.get(k)))
            else:diff(a[k],z[k],path+'/'+k)
    elif isinstance(a,list) and isinstance(z,list) and len(a)==len(z):
        for i,(x,y) in enumerate(zip(a,z)):diff(x,y,path+'/'+str(i))
    elif a!=z:differences.append(dict(path=path,source=a,saved=z))
diff(a,z)
assert differences
assert all((d['path'].startswith('/board/design_settings/teardrop_parameters/') and
            d['path'].endswith('/td_enabled') and d['source'] is None and d['saved'] is False) or
           (d['path'] in ['/net_settings/net_colors','/net_settings/netclass_assignments'] and
            d['source'] is None and d['saved']=={}) for d in differences),differences
backup=b/'R182I-project-after-kicad-save.json'
with backup.open('xb') as f:f.write(project.read_bytes())
project.write_bytes((source/project.name).read_bytes())
with (b/'R182I-normalization.json').open('x') as f:
    json.dump(dict(first_build_checker='FAIL at non-PCB byte check; no acceptance reported',
       reason='KiCad save-only normalization; original project bytes restored in independent copy',
       preserved_saved_project=backup.name,differences=differences),f,indent=2)
r=subprocess.run(['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','drc',
  '--format','json','--schematic-parity','--severity-all','--exit-code-violations',
  '-o',str(b/'R182I-drc-restored-project.json'),str(dest/board)],text=True,capture_output=True)
assert r.returncode in (0,5),(r.returncode,r.stderr)
with (b/'R182I-project-restored-command.json').open('x') as f:
    json.dump(dict(argv=r.args,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr),f,indent=2)
s=Copper(source/board);t=Copper(dest/board)
sf={f.GetReference():f for f in s.footprints};tf={f.GetReference():f for f in t.footprints}
assert set(sf)==set(tf)
changed=[]
for ref,f in sf.items():
    g=tf[ref]
    if (xy(f.GetPosition()),f.GetOrientationDegrees(),int(f.GetLayer())) != (xy(g.GetPosition()),g.GetOrientationDegrees(),int(g.GetLayer())):
        changed.append(ref);continue
    assert {p.GetNumber():(xy(p.GetPosition()),p.GetNetname()) for p in f.Pads()}=={p.GetNumber():(xy(p.GetPosition()),p.GetNetname()) for p in g.Pads()},ref
assert sorted(changed)==['C301','U301']
assert {uid(v):via_snapshot(s.board,v) for v in s.vias}=={uid(v):via_snapshot(t.board,v) for v in t.vias}
sz={uid(z):z for z in s.board.Zones() if not z.GetIsRuleArea()};tz={uid(z):z for z in t.board.Zones() if not z.GetIsRuleArea()}
assert set(sz)==set(tz) and all(polyset(z.Outline()).equals(polyset(tz[k].Outline())) for k,z in sz.items())
edges=[d for d in t.board.GetDrawings() if t.board.GetLayerName(d.GetLayer())=='Edge.Cuts']
assert len(edges)==4
coords=[xy(v) for d in edges for v in (d.GetStart(),d.GetEnd())]
assert (min(x for x,y in coords),min(y for x,y in coords),max(x for x,y in coords),max(y for x,y in coords))==(0,0,70,40)
assert abs(t.board.GetDesignSettings().GetBoardThickness()/1e6-1.6)<1e-9 and t.board.GetCopperLayerCount()==6
assert all((dest/n).is_file() and sha(dest/n)==h for n,h in members.items() if n!=board)
assert members=={p.relative_to(source).as_posix():sha(p) for p in source.rglob('*') if p.is_file()}
d=json.loads((b/'R182I-drc-restored-project.json').read_text())
report=dict(source_sha256=expected,proposal_sha256=t.sha,outline_mm=[70,40],thickness_mm=1.6,
    layers=6,fixed_footprints_checked=len(sf)-2,moved_footprints=changed,
    fixed_connectors=[r for r in sorted(sf) if r.startswith('J')],fixed_mounts=[r for r in sorted(sf) if r.startswith('H')],
    fixed_core_pin_count=sum(len(list(sf[r].Pads())) for r in ('J101','J102','J105')),
    vias_unchanged=len(s.vias),original_ground_vias_unchanged=sum(v.GetNetname()=='GND' for v in s.vias),
    native_power_and_ground_zone_outlines_unchanged=len(sz),
    unchanged_non_PCB_members=[n for n in members if n!=board],
    unconnected_items=len(d['unconnected_items']),other_DRC=len(d['violations']),schematic_parity=len(d['schematic_parity']),
    placement_scope_check='PASS',electrical_acceptance='FAIL_UNROUTED',
    ground_reference_in_extra_strip='NOT_PRESENT',physical_fit='NOT_TESTED',
    adopted=False,manufacturing_release=False)
with (b/'R182I-space-check.json').open('x') as f:json.dump(report,f,indent=2)
print(json.dumps({k:v for k,v in report.items() if k!='unchanged_non_PCB_members'}))
