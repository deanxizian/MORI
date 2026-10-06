"""Screen a real-thickness temporary tie tail, not a 6x110 work box.

The strip is an ASSUMED planar shape.  Catalogue upper width/thickness are
retained.  Bend radii are project hypotheses, not manufacturer bend ratings.
No robot geometry, wires, fastening location or official hardware is edited.
"""
from pathlib import Path
TR_SCRIPT=Path(__file__).resolve();TR_ROOT=TR_SCRIPT.parent
TR_HELPER=TR_ROOT/'check_CAM_sequence_tools.py';__file__=str(TR_HELPER)
exec(compile(TR_HELPER.read_text().split('\nst_rows=[];',1)[0],str(TR_HELPER),'exec'),globals())
__file__=str(TR_SCRIPT)
TR_OUT=TR_ROOT/'cam_tail_ribbon';TR_OUT.mkdir(exist_ok=True)
tr_targets=wi_fixed|wi_moving
tr_matrix=np.array([[-1.,0.,0.,float(slots[:,0].mean()+xx.mean())],
                    [0.,1.,0.,float(slots[0,1]+1.5)],[0.,0.,1.,-20.]])
tr_start=(tr_matrix[:,:3]@np.array([st_pivot[0],.14,232.]))+tr_matrix[:,3]
tr_thickness=1.3;tr_width=2.7

def tr_shape(first,radius,column,tail_length=110.):
    """+Y, tangent quarter bend toward -X, left run, bend back toward +Y.

    All possible shorter tails are prefixes of this strip.  Total 110mm is
    deliberately kept from the previous work allocation, not a cut length.
    """
    x,y,z=tr_start;pts=[];tangents=[];lengths=[]
    def emit(p,t):
        if pts and np.linalg.norm(p-pts[-1])<1e-10:return
        pts.append(p);tangents.append(t)
    def line(a,b):
        a=np.array(a,float);b=np.array(b,float);d=np.linalg.norm(b-a)
        assert d>=0.
        if d<1e-9:return
        t=(b-a)/d
        for u in np.linspace(0.,1.,max(2,math.ceil(d/.05)+1)):emit(a+u*(b-a),t)
        lengths.append(float(d))
    def arc(center,a,b):
        center=np.array(center,float);sign=1 if b>a else -1
        for theta in np.linspace(a,b,129):
            emit(center+radius*np.array([math.cos(theta),math.sin(theta)]),
                 sign*np.array([-math.sin(theta),math.cos(theta)]))
        lengths.append(abs(b-a)*radius)
    line([x,y],[x,y+first])
    arc([x-radius,y+first],0.,math.pi/2)
    line([x-radius,y+first+radius],[column+radius,y+first+radius])
    arc([column+radius,y+first+2*radius],-math.pi/2,-math.pi)
    remain=tail_length-sum(lengths);assert remain>0.
    line([column,y+first+2*radius],[column,y+first+2*radius+remain])
    p=np.array(pts);t=np.array(tangents);n=np.c_[-t[:,1],t[:,0]]
    poly=np.vstack([p+tr_thickness/2*n,(p-tr_thickness/2*n)[::-1]])
    area=.5*np.sum(poly[:,0]*np.roll(poly[:,1],-1)-poly[:,1]*np.roll(poly[:,0],-1))
    if area<0:poly=poly[::-1]
    m=manifold.CrossSection([poly.tolist()]).extrude(tr_width).translate([0,0,z-tr_width/2])
    assert m.status()==manifold.Error.NoError and len(m.decompose())==1
    assert abs(float(m.volume())-tail_length*tr_width*tr_thickness)<.025
    return m,np.c_[p,np.full(len(p),z)],{
        'initial_straight_mm':first,'bend_centre_radius_mm':radius,'column_x_mm':column,
        'allocated_length_mm':sum(lengths),'inner_radius_mm':radius-tr_thickness/2,
        'bend_evidence':'ASSUMED easy-axis curvature, not documented allowable radius',
        'maximum_polygon_sagitta_mm':radius*(1-math.cos(math.pi/512))}

tr_rows=[];tr_shapes={};tr_start_time=time.time();tr_ok=[]
for radius,first,column in itertools.product([3.,4.,5.],[1.,2.,3.,4.],[-38.,-40.,-42.,-44.]):
    m,p,meta=tr_shape(first,radius,column)
    fixture=st_hits(m,tr_targets)
    wire=st_wire_hits(m,0.) if fixture['status']=='PASS' else {'status':'NOT_TESTED'}
    i=len(tr_rows)
    row={'candidate':i,**meta,'fixture':fixture,'wires':wire,
         'status':'PASS' if fixture['status']==wire['status']=='PASS' else 'BLOCKED'}
    tr_rows.append(row)
    if row['status']=='PASS':
        tr_ok.append(i);cache(TR_OUT/f'tail_{i}.npz',m);tr_shapes[f'tail_{i}']=p
    print('TAIL_RIBBON',i,row['status'],radius,first,column,
          [h['object'] for h in fixture['hits']],wire,flush=True)
np.savez_compressed(TR_OUT/'centerlines.npz',**tr_shapes)
tr_report={'status':'PASS' if tr_ok else 'BLOCKED',
    'scope':'Temporary CAM-side tie free tail at the seated zero-pose four-wire assembly; full servos retained, optics/head shells not fitted',
    'source_main_sha256':source_hash,'script_sha256':sha(TR_SCRIPT),'helper_sha256':sha(TR_HELPER),
    'start_mm':tr_start.tolist(),'band_width_upper_mm':tr_width,'band_thickness_upper_mm':tr_thickness,
    'tail_length_allocation_mm':110.,'tail_geometry_evidence':'ASSUMED route with documented upper cross-section',
    'actual_tie_oriented_latch_model':'NOT_TESTED','shapes':tr_rows,'passed':tr_ok,
    'fixture_ids':list(tr_targets),'not_yet_fitted':wi_excluded,
    'tightening_force_grip_hands':'NOT_TESTED','initial_threading':'NOT_TESTED',
    'cutting_jaw_mating_with_tail':'NOT_TESTED','whole_CAM_installation':'BLOCKED',
    'full_harness':'BLOCKED','main_applied':False,'manufacturing_release':False,
    'elapsed_s':time.time()-tr_start_time}
(TR_OUT/'screen.json').write_text(json.dumps(tr_report,ensure_ascii=False,indent=2)+'\n')
assert sha(source)==source_hash
print('TAIL_RIBBON_DONE',tr_report['status'],tr_ok,flush=True)
