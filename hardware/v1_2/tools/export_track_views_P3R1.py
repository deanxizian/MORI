"""Native KiCad views with zone fills omitted from a temporary review copy.

The routed source board is never altered. These are inspection views, not
manufacturing data, and retain the actual pads, tracks and Fab outlines.
"""
import sys,json,subprocess,hashlib
from pathlib import Path
import pcbnew as k
from layout_P3R1 import paths

kind=sys.argv[1];name,d,p,r=paths(kind)
out=d.parents[1]/'layout_P3R1'/('drafts' if '--draft' in sys.argv else 'previews')/name
out.mkdir(parents=True,exist_ok=True)
before=hashlib.sha256(p.read_bytes()).hexdigest();b=k.LoadBoard(str(p))
for z in list(b.Zones()):
 if not z.GetIsRuleArea():b.Delete(z)
tmp=Path('/tmp')/(name+'_TRACK_REVIEW_ONLY.kicad_pcb');k.SaveBoard(str(tmp),b)
cli='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
node='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
sharp='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'
log=[]
for label,side in [('top','F'),('bottom','B')]:
 stem=out/(label+'_tracks');args=[cli,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',side+'.Cu,'+side+'.Silkscreen,'+side+'.Fab,Edge.Cuts','-o',str(stem.with_suffix('.svg'))]
 if side=='B':args+=['--mirror']
 args+=[str(tmp)];run=subprocess.run(args,capture_output=True,text=True,check=True)
 js='const sharp=require('+json.dumps(sharp)+');sharp(process.argv[1],{density:400}).resize({width:2400}).flatten({background:"#10151c"}).png().toFile(process.argv[2]);'
 subprocess.run([node,'-e',js,str(stem.with_suffix('.svg')),str(stem.with_suffix('.png'))],check=True)
 log.append(dict(argv=args,stdout=run.stdout))
assert before==hashlib.sha256(p.read_bytes()).hexdigest()
(r/'track_review_exports.json').write_text(json.dumps(dict(source_pcb_sha256=before,source_modified=False,zone_fills_omitted_in_temporary_copy=True,commands=log),indent=2)+'\n')
print(name,'native track-only views exported')
