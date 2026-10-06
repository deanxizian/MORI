"""Native P2 connector references and explicitly declared prototype stackup."""
from pathlib import Path
import pcbnew as k
import sys,json,math
from layout_P2 import paths,pt,mm
from functional_schematic import sexpr,encode

def annotate(kind):
    name,d,p=paths(kind);b=k.LoadBoard(str(p));data=json.loads((d/'connectivity.json').read_text());w,h=data['size'];placed=[]
    # Add only connector labels; detailed small-part references stay in Fab.
    for f in sorted(b.GetFootprints(),key=lambda f:f.GetReference()):
        ref=f.GetReference()
        if not ref.startswith('J'):continue
        silk=k.B_SilkS if f.IsFlipped() else k.F_SilkS
        if any(isinstance(t,k.PCB_TEXT) and t.GetText()==ref and t.GetLayer()==silk for t in b.GetDrawings()):continue
        t=k.PCB_TEXT(b);t.SetText(ref);t.SetTextSize(pt(.8,.8));t.SetTextThickness(mm(.12));t.SetLayer(silk);t.SetMirrored(f.IsFlipped());t.SetTextAngle(k.EDA_ANGLE(0,k.DEGREES_T))
        fx,fy=[k.ToMM(v) for v in f.GetPosition()];candidates=[]
        for iy in range(2,int(h*2)-1):
            for ix in range(2,int(w*2)-1):
                x,y=ix/2,iy/2;candidates.append(((x-fx)**2+(y-fy)**2,x,y))
        for _,x,y in sorted(candidates):
            t.SetPosition(pt(x,y));bb=t.GetBoundingBox();bb.Inflate(mm(.15))
            if bb.GetX()<mm(.5) or bb.GetY()<mm(.5) or bb.GetRight()>mm(w-.5) or bb.GetBottom()>mm(h-.5):continue
            # Leave assembled housings and all existing silk visible.
            blocked=False
            for other in b.GetFootprints():
                if other.IsFlipped()==f.IsFlipped() and bb.Intersects(other.GetBoundingBox(False,False)):blocked=True;break
                for pad in other.Pads():
                    mask=k.B_Mask if f.IsFlipped() else k.F_Mask
                    if pad.IsOnLayer(mask) and bb.Intersects(pad.GetBoundingBox()):blocked=True;break
                if blocked:break
            if blocked:continue
            for item in list(b.GetDrawings())+list(b.GetTracks()):
                if (isinstance(item,k.PCB_VIA) or isinstance(item,k.PCB_TEXT) and item.GetLayer()==silk) and bb.Intersects(item.GetBoundingBox()):blocked=True;break
            if blocked:continue
            b.Add(t);placed.append(dict(ref=ref,xy_mm=[x,y],side='B' if f.IsFlipped() else 'F'));break
        else:raise RuntimeError(('no legible connector label position',name,ref))
    k.SaveBoard(str(p),b)
    tree=sexpr(p.read_text());setup=next(x for x in tree if isinstance(x,list) and x[0]=='setup')
    setup[:]=[x for x in setup if not isinstance(x,list) or x[0]!='stackup']
    cu=.07 if kind=='power' else .035;core=round(1.6-.02-2*cu,3)
    stack=f'''(stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness {cu}))
      (layer "dielectric 1" (type "core") (thickness {core}) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness {cu}))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "ENIG") (dielectric_constraints no))'''
    setup.insert(1,sexpr(stack));p.write_text(encode(tree)+'\n')
    # Native parse/save confirms that the declared stackup is valid KiCad data.
    b=k.LoadBoard(str(p));k.SaveBoard(str(p),b)
    (d/'layout_notes.json').write_text(json.dumps(dict(status='PROTOTYPE_NOT_BENCH_VALIDATED',stackup=dict(layers=2,finished_thickness_mm=1.6,copper_nominal_um=round(cu*1000),dielectric_mm=core,finish='ENIG design target; supplier quote pending',material='FR4; Dk/loss nominal modeling values, not a measured laminate'),connector_silkscreen=placed),indent=2)+'\n')
    print(name,'connector labels',len(placed),'declared',round(cu*1000),'um copper')

if __name__=='__main__':annotate(sys.argv[1])
