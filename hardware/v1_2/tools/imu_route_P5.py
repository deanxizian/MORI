"""Build the new IMU routing with ground returns reserved before SPI."""
import json,sys
import pcbnew as k
from layout_P5 import paths,xy,pt,F,B,track,via
from body_P5 import create
from geometry_guard_P5 import Guard

def run():
    name,d,p,r=paths('imu');b=k.LoadBoard(str(r/'placement_only.kicad_pcb'));b.SetFileName(str(p));create(b,'imu')
    pads={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
    g=Guard(b,'/GND');vias=[(7.7978,9.6012),(12.1158,9.1948),(10.668,11.5824)]
    for z in vias:assert g.via_clear(z),('GND via',z)
    ground=[]
    for pin in ['2','3']:
        a=xy(pads['U1',pin].GetPosition());ground.append([a,(vias[0][0],a[1]),vias[0]])
    for pin in ['9','10','11']:
        a=xy(pads['U1',pin].GetPosition());ground.append([a,(vias[1][0],a[1]),vias[1]])
    for pin in ['6','7']:
        a=xy(pads['U1',pin].GetPosition());ground.append([a,(a[0],vias[2][1]),vias[2]])
    for points in ground:
        assert all(g.line_clear(a,z,F) for a,z in zip(points,points[1:])),points
        track(b,'/GND',points,.2,F)
    for z in vias:via(b,'/GND',*z,grid=False)
    # Reserve the two adjacent SPI arrivals before branches from MISO/CS
    # can obstruct them. One deliberate bottom-layer crossing for SCK.
    mosi=[(9,3.5),(9,7.4),(9.5,7.9),(9.5,8.6875)]
    gm=Guard(b,'/MOSI');assert all(gm.line_clear(a,z,F) for a,z in zip(mosi,mosi[1:]));track(b,'/MOSI',mosi,.2,F)
    sv=[(7.5946,7.0104),(10.0076,7.0104)];gs=Guard(b,'/SCK')
    for z in sv:assert gs.via_clear(z),('SCK via',z)
    sp=[[(7.0946,3.5),(7.0946,6.5104),sv[0]],[(10.0076,8.6875),sv[1]]]
    for points in sp:
        assert all(gs.line_clear(a,z,F) for a,z in zip(points,points[1:])),points
        track(b,'/SCK',points,.2,F)
    assert gs.line_clear(sv[0],sv[1],B);track(b,'/SCK',sv,.2,B)
    for z in sv:via(b,'/SCK',*z,grid=False)
    k.SaveBoard(str(p),b)
    (r/'imu_ground_first.json').write_text(json.dumps(dict(ground_routes=ground,vias=vias,local_rule_review='R14: adjacent LGA ground pins use compact orthogonal T junctions outside the body; no transit track below the die. Exact 0.499999 mm setback is not claimed for these return junctions.'),indent=2)+'\n')
if __name__=='__main__':run()
