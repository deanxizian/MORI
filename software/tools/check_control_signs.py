#!/usr/bin/env python3
"""SIMULATED sign proof only; generic pendulum, not identified MORI dynamics."""
import argparse,json,math,pathlib

def probe():
    # Hypothetical length only sets units. No torque/mass/belt model is asserted.
    g=9.80665;length=.15;lean=.02;forward_accel=1.0
    natural=g*lean/length
    catch=natural-forward_accel/length
    reversed_sign=natural+forward_accel/length
    assert catch < natural < reversed_sign
    # Sensor specific force for +pitch about control +y (top leans forward).
    ax=-g*math.sin(lean);az=g*math.cos(lean)
    assert abs(math.atan2(-ax,az)-lean)<1e-10
    return dict(source='SIMULATED',physical_validation='NOT_TESTED',status='PASS',
                model='theta_ddot = g/l * theta - wheel_acceleration/l',
                assumptions={'hypothetical_length_m':length,'small_lean_rad':lean,'imposed_forward_acceleration_m_s2':forward_accel},
                predicted_angular_acceleration_rad_s2={'unforced':natural,'forward_catch':catch,'reversed_output':reversed_sign},
                conclusion='Positive forward lean needs positive forward wheel torque; reversed output amplifies lean. Positive speed error requests positive lean; initial negative torque initiates lean. This is not tuning or a balance demonstration.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=pathlib.Path);a=p.parse_args();result=probe()
    if a.output:
        if 'SIMULATED' not in a.output.name:p.error('output filename must contain SIMULATED')
        a.output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
