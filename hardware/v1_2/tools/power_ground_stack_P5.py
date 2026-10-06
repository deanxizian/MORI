"""P5 power: dedicated ground return planes, no inner-layer signal routing.

The two-layer trial had five electrically isolated ground regions after local
ground escapes. This changes the stack-up, not a DRC exclusion. All existing
outer-layer body restrictions and actual component pin assignments remain.
Nominal stack dimensions are design intent and require a board-shop quote.
"""
import json, math
import pcbnew as k
from layout_P5 import *
from close_P5 import connected
from functional_schematic import sexpr, encode

name,d,p,r=paths('power');b=k.LoadBoard(str(p));connected(b)
k.SaveBoard(str(r/'two_layer_return_review.kicad_pcb'),b)
assert b.GetCopperLayerCount()==2, 'One-time stack transition; already applied'
b.SetCopperLayerCount(4)
enabled=b.GetEnabledLayers();enabled.AddLayer(k.In1_Cu);enabled.AddLayer(k.In2_Cu);b.SetEnabledLayers(enabled)
for layer in [k.In1_Cu,k.In2_Cu]:
    z=k.ZONE(b);z.SetLayer(layer);z.SetNet(b.GetNetsByName()['/GND'])
    z.SetZoneName('P5_GND_'+b.GetLayerName(layer));z.SetLocalClearance(mm(.3999992))
    z.SetMinThickness(mm(.15));z.SetPadConnection(k.ZONE_CONNECTION_THT_THERMAL)
    z.SetThermalReliefGap(mm(.254));z.SetThermalReliefSpokeWidth(mm(.2999994))
    z.SetIslandRemovalMode(k.ISLAND_REMOVAL_MODE_ALWAYS);z.Outline().NewOutline()
    for x,y in [(0,0),(80,0),(80,55),(0,55)]:z.Outline().Append(mm(x),mm(y))
    b.Add(z)
    # Preserve the magnetic-component no-copper projection on added layers.
    for ref in ['L60','L70','U60','U70']:
        f=next(f for f in b.GetFootprints()if f.GetReference()==ref);x1,y1,x2,y2=rect(f)
        keep=k.ZONE(b);keep.SetLayer(layer);keep.SetIsRuleArea(True)
        keep.SetZoneName('P5_BUCK_RETURN_AVOID_'+ref+'_'+b.GetLayerName(layer))
        keep.SetDoNotAllowTracks(True);keep.SetDoNotAllowVias(True)
        keep.SetDoNotAllowPads(False);keep.SetDoNotAllowFootprints(False);keep.SetDoNotAllowZoneFills(True)
        keep.Outline().NewOutline()
        for x,y in [(x1,y1),(x2,y1),(x2,y2),(x1,y2)]:keep.Outline().Append(mm(x),mm(y))
        b.Add(keep)
# JP70 ground is carried by its through barrel into both ground planes and B.
# Eliminate a partially obstructed *additional* top pour connection without
# reducing the required four thermal spokes on layers where it connects.
f=next(f for f in b.GetFootprints()if f.GetReference()=='JP70');q=next(q for q in f.Pads()if q.GetNumber()=='2');x,y=xy(q.GetPosition())
z=k.ZONE(b);z.SetIsRuleArea(True);z.SetLayer(F);z.SetZoneName('P5_JP70_GND_INNER_RETURN')
z.SetDoNotAllowTracks(False);z.SetDoNotAllowVias(False);z.SetDoNotAllowPads(False);z.SetDoNotAllowFootprints(False);z.SetDoNotAllowZoneFills(True);z.Outline().NewOutline()
for i in range(64):z.Outline().Append(mm(x+1.5*math.cos(i*math.pi/32)),mm(y+1.5*math.sin(i*math.pi/32)))
b.Add(z);k.SaveBoard(str(p),b)
# A symmetric nominal 1.6-mm stack, including 0.01-mm solder mask per face.
node=sexpr(p.read_text());setup=next(x for x in node if isinstance(x,list)and x[0]=='setup')
setup[:]=[x for x in setup if not isinstance(x,list)or x[0]!='stackup']
setup.insert(1,sexpr('''(stackup
 (layer "F.SilkS" (type "Top Silk Screen"))
 (layer "F.Paste" (type "Top Solder Paste"))
 (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
 (layer "F.Cu" (type "copper") (thickness 0.07))
 (layer "dielectric 1" (type "prepreg") (thickness 0.18) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
 (layer "In1.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 2" (type "core") (thickness 1.01) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
 (layer "In2.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 3" (type "prepreg") (thickness 0.18) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
 (layer "B.Cu" (type "copper") (thickness 0.07))
 (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
 (layer "B.Paste" (type "Bottom Solder Paste"))
 (layer "B.SilkS" (type "Bottom Silk Screen"))
 (copper_finish "None") (dielectric_constraints no))'''))
p.write_text(encode(node)+'\n')
dru=d/(name+'.kicad_dru');s=dru.read_text()
for layer in ['In1.Cu','In2.Cu']:
    s+=f'''\n(rule "P5 R17 {layer} plane clearance" (layer {layer}) (condition "A.Type == 'Zone' || B.Type == 'Zone'") (constraint clearance (min 0.3999992mm)))
(rule "P5 R10 {layer} connection" (layer {layer}) (constraint zone_connection thermal_reliefs) (constraint thermal_relief_gap (opt 0.254mm)) (constraint thermal_spoke_width (opt 0.2999994mm)) (constraint min_resolved_spokes 4))
(rule "P5 R13 {layer} no tracks" (layer {layer}) (condition "A.Type == 'Track' || A.Type == 'Arc'") (constraint disallow track))
'''
dru.write_text(s)
mapping=json.loads((d/'rule_mapping.json').read_text())
for row in mapping['rules']:
    if row['id']in['R10','R17']:row.update(implementation='IMPLEMENTED',note='P5 four-layer power: source plane clearance and four-spoke thermal connections on both internal GND planes.')
    if row['id']=='R13':row.update(implementation='IMPLEMENTED',note='Tracks/arcs allowed on F/B only; internal layers are GND zones, not hidden signal routes.')
(d/'rule_mapping.json').write_text(json.dumps(mapping,ensure_ascii=False,indent=2)+'\n')
com=json.loads((d/'connectivity.json').read_text());com['layers']=4;(d/'connectivity.json').write_text(json.dumps(com,ensure_ascii=False,indent=2)+'\n')
record=dict(previous_layers=2,layers=4,outline_mm=[80,55],thickness_mm=1.6,copper_um=[70,35,35,70],signal_layers=['F.Cu','B.Cu'],inner_nets=['/GND','/GND'],reason='Five separated local ground regions in the two-layer trial; continuous common return is required for switching converters and protection/measurement circuitry.',source='TI TPS54302 RevC section7.4.1, local archive; user source R10/R13/R17/R25',cost='NOT_QUOTED; no fabrication authorization',validation='Native DRC pending; thermal/transient/EMC NOT_TESTED',JP70=dict(pin='2',top_pour_pullback_radius_mm=1.5,connected_layers=['B.Cu','In1.Cu','In2.Cu'],required_spokes_per_connection=4))
(r/'ground_stack_decision.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
print('P5 power four-layer ground stack applied')
