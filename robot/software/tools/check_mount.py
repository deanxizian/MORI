#!/usr/bin/env python3
"""Validate an offline measurement record; never changes firmware or verification gates."""
import argparse,json,math,pathlib

def check(record):
    def vector(v):
        if not isinstance(v,list) or len(v)!=3 or any(not isinstance(x,(float,int)) or not math.isfinite(x) for x in v):
            raise ValueError('three measured finite components required')
        return v
    r=[vector(v) for v in record['rotation_raw_to_control']]
    if len(r)!=3:raise ValueError('matrix must be 3x3')
    for i in range(3):
        for j in range(3):
            if abs(sum(r[i][k]*r[j][k] for k in range(3))-(1 if i==j else 0))>1e-4:
                raise ValueError('matrix is not orthonormal')
    det=sum(r[0][i]*(r[1][(i+1)%3]*r[2][(i+2)%3]-r[1][(i+2)%3]*r[2][(i+1)%3]) for i in range(3))
    if abs(det-1)>1e-4:raise ValueError('matrix reflects instead of rotating')
    transform=lambda v:[sum(a*b for a,b in zip(row,vector(v))) for row in r]
    errors={}
    for axis in ('+x','-x','+y','-y','+z','-z'):
        value=transform(record['six_faces_raw_accel_m_s2'][axis])
        expected=[0,0,0];expected['xyz'.index(axis[1])]=9.80665*(1 if axis[0]=='+' else -1)
        error=math.sqrt(sum((a-b)**2 for a,b in zip(value,expected)));errors[axis]=error
        if error>.35:raise ValueError(f'{axis} vector error {error:.4f} exceeds provisional 0.35 m/s2 tolerance')
    gyro=transform(record['forward_lean_raw_gyro_rad_s'])
    if gyro[1]<=.05 or abs(gyro[0])>abs(gyro[1])*.25 or abs(gyro[2])>abs(gyro[1])*.25:
        raise ValueError('forward lean must be positive control gyro-y with small cross-axis motion')
    for i in range(2):
        enc=record['encoder_sign'][i];motor=record['motor_sign'][i]
        count=record['forward_handwheel_raw_count_delta'][i]
        if enc not in (-1,1) or motor not in (-1,1) or not isinstance(count,(float,int)) or not math.isfinite(count) or enc*count<=0:
            raise ValueError('wheel encoder forward sign not verified')
        if record['positive_output_causes_forward_rotation'][i] is not True:
            raise ValueError('positive output forward rotation not recorded')
    return {'source':record.get('source','UNKNOWN'),'numeric_consistency':'PASS','physical_validation':'NOT_TESTED',
            'face_vector_errors_m_s2':errors,'forward_lean_control_gyro_rad_s':gyro,
            'note':'Numeric checks only; operator evidence/signature review required. No configuration flag is enabled.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('record',type=pathlib.Path);a=p.parse_args()
    try:result=check(json.loads(a.record.read_text()))
    except (ValueError,KeyError,TypeError) as e:p.exit(2,'FAIL: '+str(e)+'\n')
    print(json.dumps(result,indent=2))
