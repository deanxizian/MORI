"""Before/after visuals from hashed native coordinates; no PCB mutation."""
import json, hashlib, subprocess
import render_review as r
G0=r.G
G1=json.loads((r.HERE/'reports/FINAL_geometry.json').read_text())
NAME='MORI_power_J10_C4_CANDIDATE'
PCB=r.HERE/NAME/(NAME+'.kicad_pcb')
assert hashlib.sha256(PCB.read_bytes()).hexdigest()==G1['sha256']
changes=[
 ('V01','F.Cu',[37,46,42,47],'/CHG_N'),
 ('V07','F.Cu',[18,37,49,55],'/CHG_N'),
 ('V08','B.Cu',[2,6,31,37],'/CHG_N'),
 ('V10','F.Cu',[11,18,24,33],'/+5V_MOTION'),
 ('V11','B.Cu',[40,48,17,23],'/BAT_ADC'),
 ('V12','F.Cu',[42,50,43,48],'/ARM_Q'),
]
for label,layer,bounds,net in changes:
    fig,axs=r.plt.subplots(1,2,figsize=(15,8));fig.patch.set_facecolor(r.BG)
    for ax,g,title in zip(axs,[G0,G1],['C3 BEFORE','C4 AFTER']):
        r.G=g;r.draw(ax,layer,bounds,net,title=label+' '+title+' '+net+' '+layer)
    fig.tight_layout();fig.savefig(r.OUT/(label+'_before_after.png'),dpi=150);r.plt.close(fig)
r.G=G1
for layer in ['F.Cu','B.Cu']:
    fig,ax=r.plt.subplots(figsize=(19,13));fig.patch.set_facecolor(r.BG)
    r.draw(ax,layer,[0,80,0,55],title='C4 '+layer+' / source '+G1['sha256'][:16]+' / copper planes hidden')
    fig.tight_layout();fig.savefig(r.OUT/('C4_'+layer.replace('.','_')+'.png'),dpi=160);r.plt.close(fig)
commands=[];out=r.HERE/'native_review';out.mkdir(exist_ok=True)
for label,layers in [('front','F.Cu,F.Silkscreen,Edge.Cuts'),('back','B.Cu,B.Silkscreen,Edge.Cuts')]:
    args=['/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli','pcb','export','svg','--mode-single','--page-size-mode','2','--exclude-drawing-sheet','--scale','1','--layers',layers,'-o',str(out/(label+'.svg')),str(PCB)]
    run=subprocess.run(args,capture_output=True,text=True);assert run.returncode==0
    commands.append(dict(argv=args,returncode=run.returncode,stdout=run.stdout,stderr=run.stderr,pcb_sha256=G1['sha256']))
    node='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node'
    code="const sharp=require('/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');sharp(process.argv[1],{density:96}).resize({width:3000}).png().toFile(process.argv[2]);"
    subprocess.run([node,'-e',code,str(out/(label+'.svg')),str(out/(label+'.png'))],check=True)
(r.HERE/'reports/visual_sources.json').write_text(json.dumps({'before':G0['sha256'],'after':G1['sha256'],'comparisons':[x[0]for x in changes],'native_svg_commands':commands,'method':'Tracks drawn at actual mm width; simplified pad corners in geometry plots; native SVG supplies exact pad contours and silkscreen. Both sides use top-view coordinates; planes hidden in geometry plots.'},indent=2)+'\n')
print('Rendered six comparisons, two overviews and native SVG/PNG.')
