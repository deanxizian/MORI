"""Clip actual silkscreen around exposed copper; preserve local library variants.

Only graphical silk changes. No net, copper, pad, pin or BOM MPN changes.
"""
import pcbnew as k
import json,math,csv,sys
from pathlib import Path
from layout_P2 import paths,pt,mm
from functional_schematic import sexpr,encode,q
from close_routes_P2 import snap_via_ends,merge_lines

def polish(kind):
    name,d,pcb=paths(kind);b=k.LoadBoard(str(pcb));mapping={};changes={}
    masks={k.F_SilkS:[],k.B_SilkS:[]}
    for f in b.GetFootprints():
        for p in f.Pads():
            for silk,mask,cu in [(k.F_SilkS,k.F_Mask,k.F_Cu),(k.B_SilkS,k.B_Mask,k.B_Cu)]:
                if p.IsOnLayer(mask):masks[silk].append(p.GetEffectiveShape(cu))
    for t in b.GetTracks():
        if isinstance(t,k.PCB_VIA):masks[k.F_SilkS].append(t.GetEffectiveShape(k.F_Cu))
    lib=d/'footprints/MORI_Custom.pretty';lib.mkdir(exist_ok=True)
    for f in b.GetFootprints():
        count=0
        for g in list(f.GraphicalItems()):
            if not isinstance(g,k.PCB_SHAPE) or g.GetLayer() not in masks:continue
            a,c=g.GetStart(),g.GetEnd();segments=[]
            if g.GetShape()==k.S_SEGMENT:segments=[(a,c)]
            elif g.GetShape()==k.S_RECT:
                vs=[a,k.VECTOR2I(c.x,a.y),c,k.VECTOR2I(a.x,c.y),a];segments=list(zip(vs,vs[1:]))
            elif g.GetShape()==k.S_CIRCLE:
                center=g.GetCenter();radius=g.GetRadius();n=max(24,math.ceil(2*math.pi*k.ToMM(radius)/.15))
                vs=[k.VECTOR2I(round(center.x+radius*math.cos(2*math.pi*i/n)),round(center.y+radius*math.sin(2*math.pi*i/n))) for i in range(n+1)];segments=list(zip(vs,vs[1:]))
            else:continue
            remaining=[];cut=False
            # Circular outlines are tessellated into 0.15 mm chords. Keep
            # those visible chords instead of applying the longer straight-
            # line fragment threshold, which would erase the whole circle.
            min_fragment=mm(.025 if g.GetShape()==k.S_CIRCLE else .20)
            margin=mm(.05+.01+.025)+g.GetWidth()//2
            for a,c in segments:
                length=(c-a).EuclideanNorm();n=max(1,math.ceil(k.ToMM(length)/.025));run=None
                for i in range(n+1):
                    p=k.VECTOR2I(round(a.x+(c.x-a.x)*i/n),round(a.y+(c.y-a.y)*i/n))
                    ok=not any(s.Collide(p,margin) for s in masks[g.GetLayer()])
                    if ok and run is None:run=p
                    if not ok:
                        cut=True
                        if run is not None and (p-run).EuclideanNorm()>min_fragment:
                            end=k.VECTOR2I(round(a.x+(c.x-a.x)*(i-1)/n),round(a.y+(c.y-a.y)*(i-1)/n));remaining.append((run,end))
                        run=None
                    elif i==n and run is not None and (p-run).EuclideanNorm()>min_fragment:remaining.append((run,p))
            if not cut:continue
            count+=1
            for a,c in remaining:
                s=k.PCB_SHAPE(f);s.SetShape(k.S_SEGMENT);s.SetLayer(g.GetLayer());s.SetStart(a);s.SetEnd(c);s.SetWidth(g.GetWidth());f.Add(s)
            f.Remove(g)
        if count:
            ref=f.GetReference();old=str(f.GetFPID().GetLibItemName());new=old.split('__P2_')[0]+'__P2_'+ref
            f.SetFPID(k.LIB_ID('MORI_Custom',new));mapping[ref]='MORI_Custom:'+new;changes[ref]=count
            k.PCB_IO_MGR.FindPlugin(k.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(lib),f)
    # Remove redundant hand-added Fab labels where the library already has one.
    fps={f.GetReference():f for f in b.GetFootprints()}
    for t in list(b.GetDrawings()):
        if isinstance(t,k.PCB_TEXT) and t.GetLayer() in [k.F_Fab,k.B_Fab] and t.GetText() in fps:
            f=fps[t.GetText()]
            if any(hasattr(g,'GetText') and g.GetText()=='${REFERENCE}' for g in f.GraphicalItems()):b.Delete(t)
    if mapping:
        def update(node):
            if not isinstance(node,list):return
            props={json.loads(x[1]):x for x in node if isinstance(x,list) and x and x[0]=='property'}
            if 'Reference' in props and 'Footprint' in props:
                ref=json.loads(props['Reference'][2])
                if ref in mapping:props['Footprint'][2]=q(mapping[ref])
            for x in node:update(x)
        for p in [d/(name+'.kicad_sch'),d/'MORI.kicad_sym']:
            node=sexpr(p.read_text());update(node);p.write_text('('+node[0]+'\n'+'\n'.join(encode(x) if isinstance(x,list) else x for x in node[1:])+'\n)\n')
        data=json.loads((d/'connectivity.json').read_text())
        for c in data['components']:
            if c['ref'] in mapping:c['footprint']=mapping[c['ref']]
        (d/'connectivity.json').write_text(json.dumps(data,indent=2)+'\n')
        p=d/'assembly_bom.csv';rows=list(csv.DictReader(p.open()))
        for row in rows:
            if row['ref'] in mapping:row['footprint']=mapping[row['ref']]
        with p.open('w',newline='') as out:w=csv.DictWriter(out,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
        p=d/'fp-lib-table'
        if '(name "MORI_Custom")' not in p.read_text():p.write_text(p.read_text().rstrip()[:-1]+'(lib (name "MORI_Custom") (type "KiCad") (uri "${KIPRJMOD}/footprints/MORI_Custom.pretty") (options "") (descr "P2 local outline variants")))\n')
    merge_lines(b);snap_via_ends(b);k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(pcb),b)
    print(name,'silk outline portions trimmed',changes,flush=True)

if __name__=='__main__':polish(sys.argv[1])
