#!/usr/bin/env python3
"""Export the native S2 sheets and vector block-by-block review PDF.

Run with the bundled Python (pypdf/reportlab/Pillow). Circuit data always
comes from KiCad's PDF export; this script never redraws electrical content.
"""
from pathlib import Path
from io import BytesIO
from copy import deepcopy
import hashlib
import json
import subprocess
from pypdf import PdfReader, PdfWriter, Transformation, PageObject
from pypdf.generic import RectangleObject
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import mm

H=Path(__file__).resolve().parents[1]
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
POPPLER='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm'
LAYOUT=json.loads((H/'reports/functional_schematic/layout.json').read_text())


def main(pcb_revision='P1'):
    if pcb_revision not in ['P1','P2']:raise ValueError(pcb_revision)
    qa=H/('reports/readability_S2' if pcb_revision=='P1' else 'layout_P2/reports/schematic_review');qa.mkdir(parents=True,exist_ok=True)
    writer=PdfWriter();commands=[];pages=[];native_hashes={}
    def run(argv):
        p=subprocess.run(argv,capture_output=True,text=True,timeout=180)
        commands.append(dict(argv=argv,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr))
        if p.returncode:raise RuntimeError(p.stderr or p.stdout)
    for original_name in ['MORI_motion_P1','MORI_power_P1','MORI_imu_P1']:
        name=original_name.replace('_P1','_'+pcb_revision)
        layout=next(v for v in LAYOUT if v['project']==original_name)
        folder=H/'kicad'/name;out=qa/name;out.mkdir(exist_ok=True)
        sch=folder/(name+'.kicad_sch');pdf=out/(name+'.pdf')
        run([CLI,'sch','export','pdf','-o',str(pdf),str(sch)])
        run([POPPLER,'-scale-to','3500','-png','-singlefile',str(pdf),str(out/'overview')])
        reader=PdfReader(pdf);source=reader.pages[0]
        native_hashes[name]=hashlib.sha256(sch.read_bytes()).hexdigest()
        writer.add_outline_item(name,len(pages))
        for block in layout['blocks']:
            # IMU is already a compact A4 circuit with just two mounting holes.
            if original_name=='MORI_imu_P1' and block is not layout['blocks'][0]:continue
            if original_name=='MORI_imu_P1':
                clip=RectangleObject([0,0,float(source.mediabox.width),float(source.mediabox.height)])
            else:
                x,y,w,h=block['bounds_mm'];height=float(source.mediabox.height)
                clip=RectangleObject([(x-.5)*mm,height-(y+h+.5)*mm,(x+w+.5)*mm,height-(y-.5)*mm])
            pw,ph=(297,420) if float(clip.height)>float(clip.width)*1.1 else (420,297)
            target=PageObject.create_blank_page(width=pw*mm,height=ph*mm)
            src=deepcopy(source);src.cropbox=clip
            s=min((pw-28)*mm/float(clip.width),(ph-40)*mm/float(clip.height))
            tx=(pw*mm-float(clip.width)*s)/2;ty=23*mm+((ph-40)*mm-float(clip.height)*s)/2
            transform=Transformation().translate(-float(clip.left),-float(clip.bottom)).scale(s).translate(tx,ty)
            target.merge_transformed_page(src,transform)
            overlay=BytesIO();c=Canvas(overlay,pagesize=(pw*mm,ph*mm))
            c.setFont('Helvetica',9);c.drawString(14*mm,(ph-11)*mm,f'{name}  |  S2 FUNCTIONAL SCHEMATIC')
            c.drawRightString((pw-14)*mm,(ph-11)*mm,'PROTOTYPE / UNVALIDATED')
            c.setStrokeColorRGB(.7,.75,.8);c.line(14*mm,(ph-15)*mm,(pw-14)*mm,(ph-15)*mm)
            c.setFont('Helvetica',8);c.drawString(14*mm,12*mm,'Vector crop of the native KiCad sheet. Matching net names connect blocks; terminal numbers are unchanged.')
            c.drawRightString((pw-14)*mm,12*mm,str(len(pages)+1));c.save()
            target.merge_page(PdfReader(overlay).pages[0]);writer.add_page(target)
            writer.add_outline_item(block['title'],len(pages))
            pages.append(dict(page=len(pages)+1,project=name,title=block['title'],references=block['references']))
    dest=H/('previews/MORI_S2_Schematic_Review.pdf' if pcb_revision=='P1' else 'layout_P2/previews/MORI_P2_Schematic_Review.pdf')
    dest.parent.mkdir(parents=True,exist_ok=True)
    writer.add_metadata({'/Title':'MORI S2 Functional Schematics','/Subject':'Native KiCad vector excerpts; PROTOTYPE / UNVALIDATED'})
    writer.write(dest)
    check=PdfReader(dest);assert len(check.pages)==len(pages)
    run([POPPLER,'-r','90','-png',str(dest),str(qa/'page')])
    (qa/'export.json').write_text(json.dumps(dict(pdf=str(dest.relative_to(H)),pages=pages,source_schematic_sha256=native_hashes,pdf_sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),commands=commands),indent=2)+'\n')
    print(dest,'pages:',len(pages))


if __name__=='__main__':
    import sys
    main(sys.argv[1] if len(sys.argv)>1 else 'P1')
