"""Four same-length socket screws and a catalogue extra-short L-key candidate.

Independent, unapproved mechanical selection. Preserve the four bore axes,
inserts, board, all prints and actuator poses. Model no tool-access cuts.
"""
from pathlib import Path
SK_SCRIPT=Path(__file__).resolve();SK_ROOT=SK_SCRIPT.parent
SK_HELPER=SK_ROOT/'check_CAM_board_last.py';__file__=str(SK_HELPER)
exec(compile(SK_HELPER.read_text().split("\nif __name__=='__main__':",1)[0],str(SK_HELPER),'exec'),globals())
__file__=str(SK_SCRIPT)
from interface_completion import axial
SK_OUT=SK_ROOT/'cam_socket_tool';SK_OUT.mkdir(exist_ok=True)
sk_rows=[r for r in P['interface_completion']['inserts'] if r.get('screw','').startswith('CAM_Mount_Screw_')]
sk_screws={};sk_faces={};sk_started=time.time()
for r in sk_rows:
    n=r['screw'];a=np.array(r['outward'],float);b=np.array(r['screw_head_bearing_mm'])
    assert np.allclose(a,[0,1,0]) and r['screw_length_mm']==5.
    head=axial(1.9,2.,b+a,a);shank=axial(1.,5.01,b-a*2.495,a)
    # Nominal unthreaded major-diameter envelope; mating threads aren't cut.
    socket=manifold.Manifold.cylinder(1.1,1.5/math.sqrt(3),1.5/math.sqrt(3),6)
    socket=socket.rotate([-90,0,0]).translate((b+a).tolist())
    m=(head+shank)-socket
    assert m.status()==manifold.Error.NoError and len(m.decompose())==1
    sk_screws[n]=m;sk_faces[n]=b+a*2.;cache(SK_OUT/(n+'.npz'),m)
sk_stage=bl_fixture|bl_board|{'CAM_catalogue_housing':bl_plug}|sk_screws
sk_core,sk_tails,sk_meta=bl_curves(0.,0.)
sk_wires=[(f'core_{i}',sk_core+[xx[i]-xx[0],0.,0.],sk_meta['core_error_mm']) for i in range(4)]
sk_wires += [(f'tail_{i}',sk_tails[i],sk_meta['tail_error_mm']) for i in range(4)]
sk_wires += [(f'fan_{i}',pw_fans[i][0],pw_fan_errors[i]) for i in range(4)]
sk_wires += [(f'body_{i}',body_samples[i+1,0][0],body_error) for i in range(4)]

def sk_hits(m,targets,threshold=1e-4):
    out=[]
    for n,t in targets.items():
        if not overlap_boxes(m,t,.001):continue
        v=max(0.,float((m^t).volume()))
        if v>threshold:out.append({'object':n,'intersection_mm3':v})
    return out

def sk_wire_hits(m):
    t=pw_obstacle('key','tool',m);hits=[]
    for n,p,e in sk_wires:
        hit=check_one(p,e,t[3],t[4],m,t[5])
        if hit:hits.append({'wire':n,**hit})
    return hits

def sk_tool_parts(face,angle,extra=0.):
    # The catalogue length convention/bend contour are not exact CAD. Enclose
    # both legs with round envelopes and a filled bend block. 90/4.5 are used
    # as centreline extents, making the outer extents larger, not smaller.
    p=np.array(face)+[0.,-.8+extra,0.];rad=1.5/math.sqrt(3)+.01
    pieces=[axial(rad,4.5,p+[0.,2.25,0.],[0,1,0]),
            axial(rad,90.,p+[0.,4.5,45.],[0,0,1]),
            manifold.Manifold.cube([2*rad,2*rad,2*rad],center=True).translate((p+[0,4.5,0]).tolist())]
    return [m.translate((-p).tolist()).rotate([0.,angle,0.]).translate(p.tolist()) for m in pieces]

def sk_tool(face,angle,extra=0.):
    return manifold.Manifold.batch_boolean(sk_tool_parts(face,angle,extra),manifold.OpType.Add)

def sk_tool_axial_sweep(face,angle,travel=6.):
    return manifold.Manifold.batch_boolean([manifold.Manifold.batch_hull([m,m.translate([0.,travel,0.])])
        for m in sk_tool_parts(face,angle)],manifold.OpType.Add)

if __name__=='__main__':
    results=[]
    for r in sk_rows:
        n=r['screw'];targets={k:m for k,m in sk_stage.items() if k!=n}
        angles=[]
        for angle in range(-90,91,5):
            # Convex hull covers the key's complete 5mm screw advance plus
            # 1mm disengagement, at each sampled arm orientation.
            sweep=sk_tool_axial_sweep(sk_faces[n],angle)
            hit=sk_hits(sweep,targets);wh=sk_wire_hits(sweep) if not hit else []
            angles.append({'angle_deg':angle,'status':'PASS' if not hit and not wh else 'BLOCKED','solid_hits':hit,'wire_hits':wh})
        ok=[r['angle_deg'] for r in angles if r['status']=='PASS']
        runs=[];run=[]
        for angle in range(-90,91,5):
            if angle in ok:run.append(angle)
            elif run:runs.append(run);run=[]
        if run:runs.append(run)
        best=max(runs,key=len) if runs else []
        rows={'screw':n,'status':'PASS' if len(best)>=13 else 'BLOCKED','arm_angles':angles,
              'longest_sampled_run_deg':best,'sampled_span_deg':best[-1]-best[0] if best else 0}
        results.append(rows)
        print('SOCKET_TOOL',n,rows['status'],best,flush=True)
    # Preserve the existing thread-interface exclusion ONLY for that screw's
    # own insert. All PCB, print and neighbouring components stay checked.
    screw_paths=[]
    for r in sk_rows:
        n=r['screw'];m=sk_screws[n]
        b=np.array(r['screw_head_bearing_mm']);a=np.array(r['outward'])
        # Union of individual cylindrical sweeps avoids a fictitious conical
        # fill between the head and tip inside the PCB clearance hole.
        sweep=axial(1.9,7.,b+a*3.5,a)+axial(1.,10.01,b+a*.005,a)
        fixture={k:q for k,q in sk_stage.items() if k not in [n,r['id']]}
        hs=sk_hits(sweep,fixture);ws=sk_wire_hits(sweep)
        screw_paths.append({'screw':n,'status':'PASS' if not hs and not ws else 'BLOCKED','solid_hits':hs,'wire_hits':ws,
           'continuous_translation_mm':5.,'excluded_intended_thread_pair':r['id']})
        print('SOCKET_SCREW_PATH',n,screw_paths[-1],flush=True)
    result={'status':'PASS' if all(r['status']=='PASS' for r in results+screw_paths) else 'BLOCKED',
        'source_main_sha256':source_hash,'script_sha256':sha(SK_SCRIPT),'helper_sha256':sha(SK_HELPER),
        'scope':'Independent socket screw selection and sampled key arm directions with continuous axial outer hulls; no angular or entry-path qualification yet',
        'catalogue_tool':{'manufacturer':'Wera','model':'950 PKLS','sku':'05022040001','hex_AF_mm':1.5,'long_leg_mm':90.,'short_leg_mm':4.5,
            'url':'https://www.wera.de/en/tools/950-pkls-l-key-metric-chrome-plated','shape_evidence':'Documented length/AF, conservative assumed bend and outer envelope'},
        'screw':{'candidate':'Bossard BN610 1420569, A2, DIN912/ISO4762 M2x5','major_diameter_mm':2.,'length_mm':5.,'head_diameter_mm':3.8,'head_height_mm':2.,'socket_AF_mm':1.5,'socket_depth_mm':1.,'thread_pitch_mm':.4,
            'url':'https://bossard.partcommunity.com/3d-cad-models/?info=bossard%2F01%2F01_100%2F01_100_100%2F01_100_100_10%2Fbn_610_612_31101%2Fbn_610.prj&languageIso=de',
            'thread_model':'Nominal major-diameter cylinder; not a helical thread or physical engagement qualification'},
        'changes':{'proposed_replacements':list(sk_screws),'quantity_change':0,'printed_changes':[],'axis_changes':[]},
        'driver':results,'screw_paths':screw_paths,'continuous_angular_sweep':'NOT_TESTED','tool_insertion_from_outside':'NOT_TESTED',
        'full_130_poses':'NOT_TESTED','main_applied':False,'approval':'NOT_REQUESTED','whole_harness':'BLOCKED','manufacturing_release':False,'elapsed_s':time.time()-sk_started}
    (SK_OUT/'screen.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    assert sha(source)==source_hash
    print('SOCKET_TOOL_DONE',result['status'],round(time.time()-sk_started,1),flush=True)
