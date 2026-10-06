"""Offset only the forward end of each CAM fixed tail, preserving rear fan clearance."""
from pathlib import Path
W2_SCRIPT=Path(__file__).resolve();W2_ROOT=W2_SCRIPT.parent
W2_HELPER=W2_ROOT/'screen_CAM_pitch_anchor_warp.py'
__file__=str(W2_HELPER)
exec(compile(W2_HELPER.read_text().split('\npw_rows=[];',1)[0],str(W2_HELPER),'exec'),globals())
__file__=str(W2_SCRIPT);PW_SCRIPT=W2_SCRIPT
PW_OUT=W2_ROOT/'cam_pitch_anchor/warp_v2';PW_OUT.mkdir(exist_ok=True)
W2_original_tail=shifted_tails

def shifted_tails(radius,shift,shift_length,end_y):
    offset=1.8875-shift
    # Keep the existing connector departure and rear routing exactly. The
    # second lateral transition is on the forward horizontal straight only.
    _,_,_,_,_=W2_original_tail(radius,1.8875,shift_length,end_y)
    arc_length=math.pi*radius/2
    start_y=-8.;stop_y=4.5
    start_s=5.+arc_length+(start_y-(slots[0,1]+radius))
    stop_s=5.+arc_length+(stop_y-(slots[0,1]+radius))
    end_s=5.+arc_length+(end_y-(slots[0,1]+radius))
    knots=sorted(set([0.,5.,5.+arc_length,5.+shift_length,start_s,stop_s,end_s]))
    assert start_s>5.+shift_length and stop_s<end_s
    s=np.r_[np.concatenate([np.linspace(a,b,max(1,math.ceil((b-a)/.02))+1)[:-1] for a,b in zip(knots,knots[1:])]),end_s]
    u=np.clip(s-5.,0.,arc_length);theta=u/radius
    v=np.zeros((len(s),3));v[:,1]=radius*(1-np.cos(theta))+np.maximum(0.,s-5.-arc_length)
    v[:,2]=-np.minimum(s,5.)-radius*np.sin(theta)
    t=np.clip((s-5.)/shift_length,0.,1.);t2=np.clip((s-start_s)/(stop_s-start_s),0.,1.)
    v[:,0]=1.8875*(10*t**3-15*t**4+6*t**5)-offset*(10*t2**3-15*t2**4+6*t2**5)
    max_xpp=max((10*math.sqrt(3)/3)*1.8875/shift_length**2,(10*math.sqrt(3)/3)*abs(offset)/(stop_s-start_s)**2)
    error=(1/radius+max_xpp)*.02**2/8
    return [v+e for e in slots],[error]*4,0.,s,v

W2_pack=pw_pack
def pw_pack(samples,error,slot,pitch):
    result=W2_pack(samples,error,slot,pitch)
    if result['status']!='PASS':
        indices=result.get('indices',result.get('sample_indices'))
        if indices:
            result['loop_point_mm']=samples[0][indices[0]].tolist()
            other=result.get('other_slot',slot)
            if result['type'] in ['own_fan','other_fan']:result['fan_point_mm']=pw_fans[other][0][indices[1]].tolist()
    return result

# Run the unchanged source/packing/support checks with the altered tail.
body='pw_rows=[];'+W2_HELPER.read_text().split('\npw_rows=[];',1)[1]
body=body.replace('for pw_offset in [1.5,2.,2.5]:','for pw_offset in [2.,2.5,1.5]:')
# The original tail's radius is unchanged behind Y=-8. The forward offset
# lies on a straight, so curvature there is bounded by max |X second derivative|.
body=body.replace("pw_tail_R=1/math.sqrt(1/7.5**2+pw_tail_ddx**2)","pw_tail_R=min(1/math.sqrt(1/7.5**2+((10*math.sqrt(3)/3)*1.8875/16.**2)**2),12.5**2/((10*math.sqrt(3)/3)*pw_offset))")
body=body.replace("'source_tail_helper_sha256':sha(PW_TAIL_HELPER)","'source_tail_helper_sha256':sha(PW_TAIL_HELPER),'source_warp_helper_sha256':sha(W2_HELPER)")
exec(compile(body,str(W2_SCRIPT),'exec'),globals())
