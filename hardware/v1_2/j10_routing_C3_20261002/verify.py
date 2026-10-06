"""Recheck scope and immutable sources from actual native board files."""
from candidate import *
import re
a=k.LoadBoard(str(SD/(OLD+'.kicad_pcb')));b=k.LoadBoard(str(PCB))
def geometry(board):
 out={}
 for f in board.GetFootprints():
  pads=[]
  for p in f.Pads():pads.append({'number':p.GetNumber(),'xy':xy(p.GetPosition()),'rotation':p.GetOrientationDegrees(),'size':xy(p.GetSize()),'drill':xy(p.GetDrillSize()),'shape':int(p.GetShape()),'net':p.GetNetname(),'layers':p.GetLayerSet().FmtHex()})
  out[f.GetReference()]={'xy':xy(f.GetPosition()),'rotation':f.GetOrientationDegrees(),'layer':f.GetLayer(),'value':f.GetValue(),'footprint':f.GetFPIDAsString(),'body':rect(f),'pads':sorted(pads,key=lambda x:(x['number'],x['xy']))}
 return out
ga,gb=geometry(a),geometry(b);diff={r:{'before':ga.get(r),'after':gb.get(r)}for r in set(ga)|set(gb)if ga.get(r)!=gb.get(r)}
def edges(board):return sorted((int(x.GetShape()),xy(x.GetStart()),xy(x.GetEnd()),x.GetWidth())for x in board.GetDrawings()if isinstance(x,k.PCB_SHAPE)and x.GetLayer()==k.Edge_Cuts)
def zones(board):
 out=[]
 for z in board.Zones():
  p=z.Outline();out.append({'name':z.GetZoneName(),'net':z.GetNetname(),'layers':z.GetLayerSet().FmtHex(),'rule':z.GetIsRuleArea(),'tracks':z.GetDoNotAllowTracks(),'vias':z.GetDoNotAllowVias(),'polygons':[[xy(p.COutline(i).CPoint(n))for n in range(p.COutline(i).PointCount())]for i in range(p.OutlineCount())]})
 return sorted(out,key=lambda x:x['name'])
def sch_topology(p):
 s=p.read_text().replace(OLD,NAME);return re.sub(r'^\(title_block .*$', '',s,flags=re.M)
manifest=json.loads((ROOT/'hardware/v1_2/ph_hole_candidates_20261002/formal_source_hashes.json').read_text())
formal_bad=[p for p,h in manifest.items()if not (ROOT/p).is_file()or sha(ROOT/p)!=h]
source_manifest=json.loads((R/'input_hashes.json').read_text());source_bad=[p for p,h in source_manifest.items()if sha(ROOT/p)!=h]
native=json.loads((R/'FINAL_drc.json').read_text());erc=json.loads((R/'FINAL_erc.json').read_text())
checks={'all_component_and_numbered_pad_geometry_unchanged':not diff,'edge_cuts_unchanged':edges(a)==edges(b),'copper_layer_count_unchanged':a.GetCopperLayerCount()==b.GetCopperLayerCount(),'zone_and_body_rules_unchanged':zones(a)==zones(b),'custom_rules_identical':sha(SD/(OLD+'.kicad_dru'))==sha(D/(NAME+'.kicad_dru')),'schematic_circuit_unchanged':sch_topology(SD/(OLD+'.kicad_sch'))==sch_topology(D/(NAME+'.kicad_sch')),'formal_249_file_manifest_unchanged':not formal_bad,'C2_source_manifest_unchanged':not source_bad,'zero_DRC':not native['violations']and not native['unconnected_items']and not native['schematic_parity'],'DRC_matches_final_PCB':json.loads((R/'FINAL_command.json').read_text())['pcb_sha256']==sha(PCB)}
dump(R/'invariants.json',{'status':'PASS'if all(checks.values())else'FAIL','checks':checks,'footprint_count':len(gb),'numbered_pad_count':sum(len(v['pads'])for v in gb.values()),'footprint_differences':diff,'formal_files_checked':len(manifest),'formal_changed':formal_bad,'C2_source_changed':source_bad,'C2_sha256':sha(SD/(OLD+'.kicad_pcb')),'C3_sha256':sha(PCB),'mechanical_main_sha256':sha(ROOT/'mechanical/mori_v1_2.blend')})
print(checks,flush=True)
