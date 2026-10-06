"""P5 routing preparation. Layout acceptance is always separate from ERC/DRC."""
from pathlib import Path
from collections import defaultdict
import pcbnew as k,json,math,sys,subprocess,hashlib
from layout_P5 import paths,xy,pt,mm,F,B,track,via,rect,update
from geometry_guard_P5 import Guard
from functional_schematic import sexpr,encode

def configure(kind):
    name,d,p,r=paths(kind);pro=json.loads((d/(name+'.kicad_pro')).read_text())
    classes=[dict(name='Default',clearance=.2,track_width=.2,via_diameter=.8,via_drill=.3)]
    patterns=[]
    if kind=='power':
        for cn,w,nets in [
          ('Pack',2.,['PACK_FUSED','BAT_IN','BAT_REV','BAT_MON']),
          ('Wheel',1.5,['W9_IN','W_PRE','W_VM']),
          ('Head',1.,['H6_IN','H_PRE','H_VM','W_DUMP_D','H_DUMP_D']),
          ('5V',.8,['+5V_MOTION','+5V_CAM','M5_VIN','C5_VIN']),
          ('Switch',.6,['M5_SW','C5_SW']),
          ('Kelvin',.381,['KELVIN_P','KELVIN_N'])]:
            classes.append(dict(name=cn,clearance=.2,track_width=w,via_diameter=1.,via_drill=.45))
            patterns += [dict(pattern='/'+n,netclass=cn) for n in nets]
    elif kind=='rear':
        classes.append(dict(name='USB_POWER',clearance=.2,track_width=.6,via_diameter=1.,via_drill=.45))
        patterns += [dict(pattern='/'+n,netclass='USB_POWER') for n in ['VBUS_RAW','VBUS_FUSED']]
    elif kind=='motion':
        classes.append(dict(name='SUPPLY',clearance=.2,track_width=.5,via_diameter=.8,via_drill=.3))
        patterns.append(dict(pattern='/+5V_MOTION',netclass='SUPPLY'))
    pro['net_settings']['classes']=classes;pro['net_settings']['netclass_patterns']=patterns
    pro['board']['design_settings']['drc_exclusions']=[]
    (d/(name+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n')
    # Existing translation remains intact. Add the explicit opposite-side
    # body restrictions; changing layer does not create a route exemption.
    f=d/(name+'.kicad_dru');marker='# P5 both outer layers - no automatic opposite-side exemption'
    base=f.read_text().split(marker)[0].rstrip()+'\n\n'+marker+'\n'
    b=k.LoadBoard(str(p))
    for fp in b.GetFootprints():
        ref=fp.GetReference();area_name='NETBODY_'+ref+'_OPPOSITE'
        if not any(z.GetZoneName()==area_name for z in b.Zones()):continue
        nets=sorted({str(q.GetNetname()) for q in fp.Pads() if q.GetNetname()})
        cond="A.intersectsArea('"+area_name+"')"+''.join(" && A.NetName != '"+n+"'" for n in nets)
        base+='(rule '+json.dumps('P5 '+ref+' opposite projection')+'\n (condition '+json.dumps(cond)+')\n (constraint disallow track via)\n)\n'
    f.write_text(base)
    print(kind,'P5 source-rule constraints and current-aware routing classes written',flush=True)

def normal(f,p):
    r=rect(f);x,y=xy(p.GetPosition());cx,cy=(r[0]+r[2])/2,(r[1]+r[3])/2
    dx,dy=x-cx,y-cy
    if abs(dx)/max((r[2]-r[0])/2,.1) >= abs(dy)/max((r[3]-r[1])/2,.1):return (1 if dx>=0 else -1,0)
    return (0,1 if dy>=0 else -1)

def plane_ports(kind):
    if kind!='motion':return
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p));log=[];failed=[]
    assert not list(b.GetTracks()),'Plane ports start only on the zero-copper checkpoint.'
    for f in sorted(b.GetFootprints(),key=lambda f:(not f.GetReference().startswith('U'),f.GetReference())):
        for q in f.Pads():
            net=q.GetNetname()
            if net not in ['/GND','/+3V3'] or q.GetAttribute()!=k.PAD_ATTRIB_SMD:continue
            a=xy(q.GetPosition());nx,ny=normal(f,q);g=Guard(b,net);best=None
            for dist in [1.2,1.45,1.7,2.,2.4,2.8]:
                z=tuple(round(v/.0254)*.0254 for v in (a[0]+nx*dist,a[1]+ny*dist))
                # Align the trace to the globally gridded via at a landing
                # point INSIDE its actual pad, without a visible tiny jog.
                landing=(a[0],z[1]) if nx else (z[0],a[1])
                if not q.GetEffectiveShape(f.GetLayer()).Collide(pt(*landing),0):continue
                if g.via_clear(z) and g.line_clear(landing,z,f.GetLayer(),.2):best=(landing,z);break
            if best is None:
                failed.append(dict(ref=f.GetReference(),pin=q.GetNumber(),net=net,xy=a));continue
            landing,z=best;track(b,net,[landing,z],.2,f.GetLayer());via(b,net,*z,grid=False)
            log.append(dict(ref=f.GetReference(),pin=q.GetNumber(),net=net,landing=landing,via=z,direction=[nx,ny],via_grid_mm=.0254))
    k.SaveBoard(str(p),b);(r/'plane_ports.json').write_text(json.dumps(dict(routes=log,unresolved=failed),indent=2)+'\n')
    print(kind,'outward plane connections',len(log),'unresolved',len(failed),flush=True)

def planes(kind):
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p));W,H=json.loads((d/'connectivity.json').read_text())['size']
    for z in list(b.Zones()):
        if not z.GetIsRuleArea():b.Delete(z)
    for f in b.GetFootprints():
        for q in f.Pads():
            if q.GetAttribute()==k.PAD_ATTRIB_PTH:
                q.SetThermalSpokeAngleDegrees(45);q.SetThermalGap(mm(.254));q.SetLocalThermalSpokeWidthOverride(mm(.2999994))
    layers=[(F,'/GND'),(B,'/GND')]+([(k.In1_Cu,'/GND'),(k.In2_Cu,'/+3V3')] if kind=='motion' else [])
    for layer,net in layers:
        z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.GetNetsByName()[net]);z.SetZoneName('P5_'+net[1:]+'_'+b.GetLayerName(layer))
        z.SetLocalClearance(mm(.3999992 if layer in [k.In1_Cu,k.In2_Cu] else .2999994));z.SetMinThickness(mm(.15));z.SetPadConnection(k.ZONE_CONNECTION_THT_THERMAL)
        z.SetThermalReliefGap(mm(.254));z.SetThermalReliefSpokeWidth(mm(.2999994));z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS)
        z.Outline().NewOutline()
        for x,y in [(0,0),(W,0),(W,H),(0,H)]:z.Outline().Append(mm(x),mm(y))
        b.Add(z)
    k.ZONE_FILLER(b).Fill(b.Zones());k.SaveBoard(str(p),b)

def dsn(kind):
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p))
    for z in list(b.Zones()):
        if not z.GetIsRuleArea() or z.GetZoneName().startswith('NETBODY_') or not (z.IsOnLayer(F) or z.IsOnLayer(B)):
            b.Delete(z);continue
        if z.GetZoneName().startswith('BODY_'):
            # Specctra applies its 0.2 mm copper clearance to a keepout;
            # KiCad's native BODY boundary already defines the forbidden
            # copper area. Compensate ONLY in the temporary router model.
            z.Outline().Deflate(mm(.198),k.CORNER_STRATEGY_CHAMFER_ALL_CORNERS,mm(.002))
            if not z.Outline().OutlineCount():b.Delete(z)
    if kind=='motion':b.SetCopperLayerCount(2) # temporary router model ONLY
    fn=d/(name+'.dsn');assert k.ExportSpecctraDSN(b,str(fn))
    tree=sexpr(fn.read_text());network=next(n for n in tree if isinstance(n,list) and n[0]=='network')
    ignored={'/GND'}|({'/+3V3'} if kind=='motion' else set())
    # Planes connect these nets. They remain real native nets and must still
    # pass the final unconnected check; omitted only from signal autorouting.
    for row in network:
        if isinstance(row,list) and row[0]=='net' and row[1].strip('"') in ignored:
            row[:]=row[:2] # retain net identity for protected native copper
    for x in network:
        if isinstance(x,list) and x[0]=='class':x[:]=[q for q in x if not (isinstance(q,str) and q.strip('"') in ignored)]
    wiring=next((x for x in tree if isinstance(x,list) and x[0]=='wiring'),None)
    if wiring:
        for row in wiring[1:]:
            if not isinstance(row,list):continue
            t=next((n for n in row if isinstance(n,list) and n[0]=='type'),None)
            if t:t[1]='protect'
    fn.write_text(encode(tree).replace('(clearance 50 (type smd_smd))','(clearance 200 (type smd_smd))')+'\n')
    (r/'dsn_scope.json').write_text(json.dumps(dict(native_pcb_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),ignored_router_nets=sorted(ignored),reason='Require actual plane connectivity in final native DRC; no waiver of unconnected pads',routing_layers=['F.Cu','B.Cu'],inner_native_stack_preserved=kind=='motion'),indent=2)+'\n')
    print(kind,'new DSN exported',flush=True)

def import_ses(kind):
    name,d,p,r=paths(kind);b=k.LoadBoard(str(p))
    ignored={'/GND'}|({'/+3V3'} if kind=='motion' else set());saved=[]
    for t in b.GetTracks():
        if t.GetNetname() not in ignored:continue
        if isinstance(t,k.PCB_VIA):saved.append(('via',str(t.GetNetname()),xy(t.GetPosition()),k.ToMM(t.GetWidth(F)),k.ToMM(t.GetDrill())))
        else:saved.append(('track',str(t.GetNetname()),xy(t.GetStart()),xy(t.GetEnd()),k.ToMM(t.GetWidth()),t.GetLayer()))
    assert k.ImportSpecctraSES(b,str(d/(name+'.ses')))
    for t in list(b.GetTracks()):
        if t.GetNetname() in ignored:b.Delete(t)
    for row in saved:
        if row[0]=='via':via(b,row[1],*row[2],vd=row[3],dr=row[4],grid=False)
        else:track(b,row[1],[row[2],row[3]],row[4],row[5])
    k.SaveBoard(str(p),b);planes(kind)

if __name__=='__main__':
    kind,action=sys.argv[1:3];{'configure':configure,'ports':plane_ports,'fill':planes,'dsn':dsn,'import':import_ses}[action](kind)
