"""P2-only vendor land-pattern corrections. No component substitutions."""
from pathlib import Path
import json,re,csv
import pcbnew as k

MM=k.FromMM
V=lambda x,y:k.VECTOR2I(MM(x),MM(y))


def apply(kind,b,d,data):
    if kind not in ['motion','imu']:return
    old_id={'motion':'Package_SO:VSSOP-8_2.3x2mm_P0.5mm','imu':'Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y'}[kind]
    new_name={'motion':'TI_DCU0008A_0p85x0p30','imu':'TDK_ICM42688P_LGA14_3x2p5'}[kind];new_id='MORI_Custom:'+new_name
    lib=d/'footprints/MORI_Custom.pretty';lib.mkdir(exist_ok=True)
    fp=k.FootprintLoad(str(d/('footprints/'+old_id.split(':')[0]+'.pretty')),old_id.split(':')[1])
    assert fp
    fp.SetFPID(k.LIB_ID('MORI_Custom',new_name))
    if kind=='motion':
        fp.SetLibDescription('TI DCU0008A board land pattern, drawing 4225266/A 09/2014; SN74LVC2G125 datasheet PDF p25. Pads 0.85x0.30, row span 3.10, pitch 0.50 mm. Source rule mask/paste expansion remains +0.05 mm.')
        for pad in fp.Pads():
            n=int(pad.GetNumber());x=-1.55 if n<=4 else 1.55;y=(n-2.5)*.5 if n<=4 else (6.5-n)*.5
            pad.SetPosition(V(x,y));pad.SetSize(V(.85,.30));pad.SetRoundRectRadiusRatio(.05/.30)
    else:
        fp.SetLibDescription('TDK ICM-42688-P DS-000347 v1.9 pp54-55 + AN-000393 v2.4 Fig1: PCB lands equal nominal lead 0.475x0.25 mm, pitch0.50. Centres x1.1625/y0.9125. Source +0.05 mask/paste retained; stencil requires separate review.')
        for pad in fp.Pads():
            n=int(pad.GetNumber())
            pad.SetSize(V(.475,.25) if n in [1,2,3,4,8,9,10,11] else V(.25,.475))
            pad.SetShape(k.PAD_SHAPE_RECT)
    k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(lib),fp)
    for c in data['components']:
        if c['footprint']!=old_id:continue
        old=next(f for f in b.GetFootprints() if f.GetReference()==c['ref'])
        nets={p.GetNumber():p.GetNet() for p in old.Pads()};pos=old.GetPosition();rot=old.GetOrientationDegrees();flipped=old.IsFlipped()
        new=k.FootprintLoad(str(lib),new_name);new.SetFPID(k.LIB_ID('MORI_Custom',new_name))
        b.Add(new)
        new.SetReference(old.GetReference());new.SetValue(old.GetValue());new.SetPath(old.GetPath())
        new.SetFields(old.GetFieldsText())
        new.SetPosition(pos)
        if flipped:new.Flip(pos,False)
        new.SetOrientationDegrees(rot);new.Reference().SetVisible(old.Reference().IsVisible());new.Value().SetVisible(old.Value().IsVisible())
        for p in new.Pads():p.SetNet(nets[p.GetNumber()])
        b.Delete(old);c['footprint']=new_id
    for p in [d/(d.name+'.kicad_sch'),d/'MORI.kicad_sym',d/'assembly_bom.csv']:
        p.write_text(p.read_text().replace(old_id,new_id))
    table=d/'fp-lib-table'
    if '(name "MORI_Custom")' not in table.read_text():
        table.write_text(table.read_text().rstrip()[:-1]+'(lib (name "MORI_Custom") (type "KiCad") (uri "${KIPRJMOD}/footprints/MORI_Custom.pretty") (options "") (descr "Vendor land patterns")))\n')
