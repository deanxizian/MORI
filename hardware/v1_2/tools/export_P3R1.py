#!/usr/bin/env python3
"""Export native P3R1 review/assembly views and bare-board STEP, not fabrication.

Run after a current, successful native P3R1 check. Raster images are renderings
of KiCad SVG, not redrawings of the circuits or copper.
"""
from pathlib import Path
import subprocess,json,hashlib,sys
H=Path(__file__).resolve().parents[1]
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
NODE='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
SHARP='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp'

def export(kind):
    name='MORI_'+kind+'_P3R1';d=H/'kicad'/name;p=d/(name+'.kicad_pcb')
    report=H/'layout_P3R1/reports'/name;out=H/'layout_P3R1'/('drafts' if '--draft' in sys.argv else 'previews')/name;out.mkdir(parents=True,exist_ok=True)
    drc=json.loads((report/'drc.json').read_text())
    if '--draft' not in sys.argv and any(drc[x] for x in ['violations','unconnected_items','schematic_parity']):raise RuntimeError('Resolve P3R1 DRC before publishing previews')
    commands=[]
    def run(args):
        r=subprocess.run(args,text=True,capture_output=True,timeout=180)
        commands.append(dict(argv=args,returncode=r.returncode,output=r.stdout+r.stderr))
        if r.returncode:raise RuntimeError(r.stdout+r.stderr)
    for label,side in [('top','F'),('bottom','B')]:
        for assembly in [False,True]:
            stem=label+('_assembly' if assembly else '')
            layers=side+'.Fab,Edge.Cuts' if assembly else ','.join([side+'.Cu',side+'.Silkscreen',side+'.Fab','Edge.Cuts'])
            args=[CLI,'pcb','export','svg','--mode-single','--fit-page-to-board','--exclude-drawing-sheet','--layers',layers,'-o',str(out/(stem+'.svg'))]
            if side=='B':args+=['--mirror']
            if assembly:args+=['--black-and-white','--sketch-pads-on-fab-layers']
            run(args+[str(p)])
            density=600 if kind=='imu' else 300
            js='const sharp=require('+json.dumps(SHARP)+'); sharp(process.argv[1],{density:'+str(density)+'}).resize({width:2200}).flatten({background:process.argv[3]}).png().toFile(process.argv[2]);'
            run([NODE,'-e',js,str(out/(stem+'.svg')),str(out/(stem+'.png')),'white' if assembly else '#10151c'])
    if '--draft' in sys.argv: return
    run([CLI,'pcb','export','pos','--format','csv','--units','mm','--side','both','-o',str(out/'placement_native.csv'),str(p)])
    step=H/'mechanical'/(name+'_BARE_BOARD.step');step.parent.mkdir(exist_ok=True)
    run([CLI,'pcb','export','step','--board-only','--force','-o',str(step),str(p)])
    (report/'exports.json').write_text(json.dumps(dict(source_pcb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),commands=commands,scope='PROTOTYPE review, assembly coordinates and bare PCB STEP. No Gerber/drill/stencil export. STEP is NOT a populated assembly.'),indent=2)+'\n')
    print(name,'native views / placement / bare STEP exported',flush=True)

if __name__=='__main__':export(sys.argv[1])
