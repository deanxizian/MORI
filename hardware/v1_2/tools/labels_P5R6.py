"""Printed P5R6 labels, with explicit pin functions. No copper changes."""
from review_P5R6 import *
from layout_P5 import rect
from functional_schematic import sexpr, encode, q
import csv


def bb(item):
    b = item.GetBoundingBox()
    return tuple(k.ToMM(v) for v in [b.GetX(),b.GetY(),b.GetRight(),b.GetBottom()])


def overlap(a,b,g=.10):
    return a[0]<b[2]+g and a[2]>b[0]-g and a[1]<b[3]+g and a[3]>b[1]-g


def run(kind):
    e = Edit(kind)
    b = e.b
    for group in list(b.Groups()):
        if group.GetName() == 'P5R6_LOCAL_MARKINGS':
            for item in list(group.GetItems()):
                group.RemoveItem(item)
                b.Delete(item)
            b.Delete(group)
    group = k.PCB_GROUP(b)
    group.SetName('P5R6_LOCAL_MARKINGS')
    b.Add(group)
    changed=[]
    remove={'J6 H-BUCK IN','J15 CHG','J15 1:CHG 2:GND','TP71 GND'} if kind=='power' else set()
    for t in list(b.GetDrawings()):
        if not isinstance(t,k.PCB_TEXT):
            continue
        if t.GetText() in remove:
            for gg in b.Groups():
                if any(x.m_Uuid.AsString()==t.m_Uuid.AsString() for x in gg.GetItems()):
                    gg.RemoveItem(t)
            b.Delete(t)
        elif 'P5R5' in t.GetText() or 'P5R4' in t.GetText():
            before=t.GetText()
            t.SetText(before.replace('P5R5','P5R6').replace('P5R4','P5R6'))
            changed.append({'before':before,'after':t.GetText()})
    occupied={k.F_SilkS:[],k.B_SilkS:[]}
    for f in b.GetFootprints():
        for p in f.Pads():
            for layer,mask in [(k.F_SilkS,k.F_Mask),(k.B_SilkS,k.B_Mask)]:
                if p.IsOnLayer(mask):
                    occupied[layer].append(bb(p))
        for g in [*f.GraphicalItems(),f.Reference(),f.Value()]:
            if g.GetLayer() in occupied and (not hasattr(g,'IsVisible') or g.IsVisible()):
                occupied[g.GetLayer()].append(bb(g))
        body=rect(f)
        if body:
            occupied[k.B_SilkS if f.IsFlipped() else k.F_SilkS].append(body)
    for v in b.GetTracks():
        if isinstance(v,k.PCB_VIA):
            for layer in occupied:
                occupied[layer].append(bb(v))
    for g in b.GetDrawings():
        if g.GetLayer() in occupied:
            occupied[g.GetLayer()].append(bb(g))
    size={'power':(80,55),'motion':(70,35),'rear':(24,25)}[kind]
    placed=[]
    missing=[]

    def label(text,pos,layer=k.F_SilkS,fs=.8,angle=0,radius=1,condition=None):
        t=k.PCB_TEXT(b)
        t.SetText(text)
        t.SetLayer(layer)
        t.SetTextSize(pt(fs,fs))
        t.SetTextThickness(mm(.12))
        t.SetTextAngle(k.EDA_ANGLE(angle,k.DEGREES_T))
        t.SetMirrored(layer==k.B_SilkS)
        steps=int(radius*10)
        offsets=sorted((i*i+j*j,abs(i),i/10,j/10) for i in range(-steps,steps+1) for j in range(-steps,steps+1))
        for _,__,dx,dy in offsets:
            point=(pos[0]+dx,pos[1]+dy)
            if condition and not condition(point):
                continue
            t.SetPosition(pt(*point))
            box=bb(t)
            if box[0]<.3 or box[1]<.3 or box[2]>size[0]-.3 or box[3]>size[1]-.3:
                continue
            if any(overlap(box,x) for x in occupied[layer]):
                continue
            b.Add(t)
            group.AddItem(t)
            occupied[layer].append(box)
            placed.append({'text':text,'layer':b.GetLayerName(layer),'xy_mm':point,'size_mm':fs,'angle':angle})
            return True
        missing.append({'text':text,'requested':pos,'layer':b.GetLayerName(layer)})
        return False

    if kind=='power':
        label('J6 BAT_MON\nSERVICE DNP',(50.5,10.0),k.B_SilkS,radius=3)
        label('J15 CHG_N',(1.0,31.2),angle=90,radius=.4)
        label('J15 1:CHG_N 2:GND',(14,27),k.B_SilkS,radius=3)
        label('INTERLOCK',(13,24.7),k.B_SilkS,radius=3)
        label('TP71 GND',(32.0,45.8),k.B_SilkS,radius=2,
              condition=lambda p:p[1]<=48 and math.dist(p,(34.5,48))<math.dist(p,(35,51)))
        e.f['J6'].SetValue('BAT_MON SERVICE / DNP')
        for path in [e.d/(e.name+'.kicad_sch'),e.d/'MORI.kicad_sym',e.d/'connectivity.json',e.d/'assembly_bom.csv']:
            text=path.read_text()
            text=text.replace('RAW BAT SERVICE / DNP','BAT_MON SERVICE / DNP')
            text=text.replace('J2 -> wheel buck; J4 -> head buck; J6 -> two independent 5 V converters.',
                              'J2: wheel buck. J4: head buck. J6: BAT_MON SERVICE / DNP.')
            path.write_text(text)
    elif kind=='rear':
        label('MORI',(12,1.1),radius=.2)
        label('REAR P5R6',(21,5.5),angle=90,radius=.5)
        label('J2 1:FUSED',(4.0,3.4),angle=90,radius=2)
        label('5:RAW',(3,8.5),radius=1)
        label('J2',(21.8,13.5),radius=.3)
        for i,text in enumerate(['1 F','2 G','CC1','CC2','5 R']):
            label(text,(21.8,15.7+i*2),radius=.65,condition=lambda p,y=15.7+i*2:abs(p[1]-y)<.31)
        label('J3 INTERLOCK',(11.5,17.8),k.B_SilkS,radius=.8)
        label('1RET',(7.8,21.5),k.B_SilkS,radius=.4)
        label('2GND',(14.3,21.5),k.B_SilkS,radius=.4)
        label('3LOOP',(7.8,23.5),k.B_SilkS,radius=.4)
        label('4CLR',(14.6,23.5),k.B_SilkS,radius=.4)
        # Vendor drawing defines contact states, but does not explicitly tie lever
        # direction to state A. Mark the verified electrical state, not a guessed arrow.
        label('ON',(11.5,11.6),k.B_SilkS,radius=.3)
        label('1-2+4-5',(12,14.25),k.B_SilkS,radius=.3)
    e.save()
    dump(e.r/'silkscreen_labels.json',{'changed':changed,'labels':placed,'unplaced':missing,
         'minimum_text_mm':.8,'stroke_mm':.12,'printed_physical_sample':'NOT_TESTED',
         'switch_ON':'Contacts 1-2 and 4-5 closed; lever direction NOT_TESTED. No guessed physical arrow.' if kind=='rear' else None})
    print(kind,'placed',len(placed),'unplaced',missing,flush=True)


if __name__=='__main__':
    for kind in sys.argv[1:] or KINDS:
        run(kind)
