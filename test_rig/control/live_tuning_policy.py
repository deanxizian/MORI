"""Small, explicit online-gain envelope; never authorizes motion or guard changes."""
import math

# physical key: plan key, lower, upper, maximum change per transaction
FIELDS={
    # v156 comparison: lower-only extension. This is an experimental tuning
    # range, not a stability guarantee. Output/health guards are immutable.
    'pitch_p':('ap_kp',2.00,3.50,.25),
    'pitch_i':('ap_ki',.15,.60,.15),
    'pitch_d':('ap_kd',.050,.090,.015),
    'speed_p':('speed_kp_rad_per_m_s',.15,.40,.05),
}


def number(value):
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('finite_numeric_value_required')
    return float(value)


def gains(plan):
    scale=number(plan['output_scale_nm'])
    if scale<=0:raise ValueError('invalid_output_scale')
    return {key:number(plan[field])*(1 if key=='speed_p' else scale)
            for key,(field,*_) in FIELDS.items()}


def with_gains(plan,values):
    if set(values)!=set(FIELDS):raise ValueError('exact_gain_fields_required')
    result=plan.copy()
    for key,(field,lo,hi,_) in FIELDS.items():
        value=number(values[key])
        if not lo-1e-12<=value<=hi+1e-12:raise ValueError('gain_outside_envelope_'+key)
        result[field]=value/(1 if key=='speed_p' else plan['output_scale_nm'])
    return result


def validate_plan_change(before,after):
    if before.get('allow_live_tuning') is not True or after.get('allow_live_tuning') is not True:
        raise ValueError('live_tuning_not_enabled')
    allowed={v[0] for v in FIELDS.values()}
    if set(before)!=set(after) or any(before[k]!=after[k] for k in before if k not in allowed):
        raise ValueError('immutable_plan_field_changed')
    a,b=gains(before),gains(after)
    with_gains(before,a);with_gains(after,b)
    if any(abs(b[k]-a[k])>FIELDS[k][3]+1e-12 for k in FIELDS):
        raise ValueError('gain_step_too_large')


def validate_set(request,session,revision,current):
    required={'op','session','expected_revision','request_id','key','value','ramp_s'}
    if type(request) is not dict or set(request)!=required or request.get('op')!='set':
        raise ValueError('exact_set_fields_required')
    if request['session']!=session:raise ValueError('wrong_session')
    if type(request['expected_revision']) is not int or request['expected_revision']!=revision:
        raise ValueError('stale_revision')
    rid=request['request_id']
    if type(rid) is not str or not 1<=len(rid)<=80 or not all(c.isalnum() or c in '-_' for c in rid):
        raise ValueError('invalid_request_id')
    key=request['key']
    if type(key) is not str or key not in FIELDS:raise ValueError('gain_not_allowed')
    value=number(request['value']);ramp=number(request['ramp_s'])
    _,lo,hi,step=FIELDS[key]
    if not lo<=value<=hi:raise ValueError('gain_outside_envelope')
    if abs(value-current[key])>step+1e-12:raise ValueError('gain_step_too_large')
    if abs(value-current[key])<1e-12:raise ValueError('no_change')
    if not 1<=ramp<=5:raise ValueError('ramp_must_be_1_to_5_seconds')
    return key,value,ramp
