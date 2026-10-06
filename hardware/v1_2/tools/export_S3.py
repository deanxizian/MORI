#!/usr/bin/env python3
"""Native KiCad PDF, functional-block crops; no PCB output or circuit redrawing."""
from pathlib import Path
from copy import deepcopy
from io import BytesIO
import json,subprocess
from pypdf import PdfReader,PdfWriter,PageObject,Transformation
from pypdf.generic import RectangleObject
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.units import mm
from logic5v_S3 import H,NAME,DEST,REPORT
CLI='/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
POP='/Users/dean/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/pdftoppm'
out=H/'schematic_S3/previews';out.mkdir(parents=True,exist_ok=True)
verification=json.loads((REPORT/'verification.json').read_text())
assert verification['status']=='PASS'
native=REPORT/(NAME+'_native.pdf')
subprocess.run([CLI,'sch','export','pdf','-o',str(native),str(DEST/(NAME+'.kicad_sch'))],check=True)
layout=json.loads((REPORT/'layout.json').read_text())
writer=PdfWriter();source=PdfReader(native).pages[0]
# The new regulators come first in the reading PDF, followed by inherited blocks.
blocks=layout['blocks'][-2:]+layout['blocks'][:-2]
for i,block in enumerate(blocks):
    x,y,w,h=block['bounds_mm'];height=float(source.mediabox.height)
    clip=RectangleObject([(x-.5)*mm,height-(y+h+.5)*mm,(x+w+.5)*mm,height-(y-.5)*mm])
    pw,ph=(297,420) if h>w*1.1 else (420,297)
    target=PageObject.create_blank_page(width=pw*mm,height=ph*mm)
    src=deepcopy(source);src.cropbox=clip
    scale=min((pw-28)*mm/float(clip.width),(ph-40)*mm/float(clip.height))
    tx=(pw*mm-float(clip.width)*scale)/2;ty=23*mm+((ph-40)*mm-float(clip.height)*scale)/2
    target.merge_transformed_page(src,Transformation().translate(-float(clip.left),-float(clip.bottom)).scale(scale).translate(tx,ty))
    buf=BytesIO();c=Canvas(buf,pagesize=(pw*mm,ph*mm));c.setFont('Helvetica',10)
    c.drawString(14*mm,(ph-11)*mm,'MORI S3 | POWER SCHEMATIC | DUAL LOCAL 5V')
    c.drawRightString((pw-14)*mm,(ph-11)*mm,'PROTOTYPE / NOT_TESTED')
    c.setFont('Helvetica',8)
    c.drawString(14*mm,12*mm,'Native KiCad vector excerpt. PCB NOT UPDATED. Board outline, mounting and placement are UNFROZEN.')
    c.drawRightString((pw-14)*mm,12*mm,f'{i+1} / {len(blocks)}');c.save()
    target.merge_page(PdfReader(buf).pages[0]);writer.add_page(target)
    writer.add_outline_item(block['title'],i)
pdf=out/'MORI_S3_Power_Schematic_Review.pdf';writer.write(pdf)
qa=REPORT/'visual';qa.mkdir(exist_ok=True)
subprocess.run([POP,'-r','105','-png',str(pdf),str(qa/'page')],check=True)
print(pdf,len(writer.pages),'pages')
