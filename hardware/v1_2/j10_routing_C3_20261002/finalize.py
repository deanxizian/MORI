"""Update candidate-only metadata, refill copper and run native checks."""
from candidate import *
import re,datetime
b=load();b.GetTitleBlock().SetRevision('J10-C3 / PROTOTYPE / NOT RELEASED')
b.GetTitleBlock().SetDate('2026-10-03')
b.GetTitleBlock().SetTitle('MORI power: J10 side-entry C3 routed candidate')
b.BuildConnectivity();k.ZONE_FILLER(b).Fill(b.Zones());save(b)
sch=D/(NAME+'.kicad_sch');s=sch.read_text()
s=re.sub(r'^\(title_block .*$', '(title_block (title "MORI power / J10-C3 / FUNCTIONAL SCHEMATIC") (date "2026-10-03") (rev "J10-C3 CANDIDATE") (comment 1 "Circuit unchanged; routed PROTOTYPE / physical NOT_TESTED / NOT RELEASED"))',s,flags=re.M)
sch.write_text(s)
j=json.loads((D/'connectivity.json').read_text());fps={f.GetReference():f for f in b.GetFootprints()}
for c in j['components']:
 if c['ref']not in fps:
  assert c['ref'].startswith('#'),c['ref']
  continue
 f=fps[c['ref']];c['placed_at']=[*xy(f.GetPosition()),f.GetOrientationDegrees()];c['side']='B'if f.GetLayer()==B else'F'
j['layout_revision']='J10-C3';j['native_source']=NAME+'.kicad_pcb';j['status']='PROTOTYPE / NOT_RELEASED'
dump(D/'connectivity.json',j)
dump(D/'layout_notes.json',{'revision':'J10-C3','immutable_placement_source':str(SD.relative_to(ROOT)),'current_placements':'../reports/FINAL_geometry.json','routing_review':'../ROUTING_REVIEW.md','physical_tests':'NOT_TESTED','manufacturing_release':'BLOCKED'})
check('FINAL')
args=[CLI,'sch','erc','--format','json','--severity-all','--exit-code-violations','-o',str(R/'FINAL_erc.json'),str(sch)]
c=subprocess.run(args,capture_output=True,text=True)
dump(R/'FINAL_erc_command.json',{'argv':args,'returncode':c.returncode,'stdout':c.stdout,'stderr':c.stderr,'schematic_sha256':sha(sch)})
print('ERC',c.returncode,flush=True);snapshot('FINAL')
dump(R/'versions.json',{'kicad_cli':subprocess.run([CLI,'--version'],capture_output=True,text=True).stdout.strip(),'pcbnew':k.GetBuildVersion(),'Python':sys.version,'utc':datetime.datetime.now(datetime.timezone.utc).isoformat()})
