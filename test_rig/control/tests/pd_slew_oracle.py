# SPDX-License-Identifier: GPL-3.0-or-later
"""Unmodified pinned AC_PID/attitude/SlewLimiter functions with no-I/O shims.

Scalar LPF shim uses the verified upstream alpha and reset-to-zero behavior.
Clock/AP_Param/AHRS are shims, as in ardupilot_oracle. Static-zero storage
models upstream's static control instance. This is not a full firmware build.
"""
import hashlib,json,subprocess
from pathlib import Path
from ardupilot_oracle import ROOT,SHIM,MAIN,extract

REFERENCE=Path(__file__).resolve().parents[1]/'offline_pd_slew_20261017'


def build(directory):
    meta=json.loads((ROOT/'source.json').read_text())
    for name,digest in meta['files'].items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
    meta=json.loads((REFERENCE/'source.json').read_text())
    assert meta['commit']=='fb773567896014da007bca58358704d4a0d8516f'
    for name,row in meta['files'].items():
        assert hashlib.sha256((REFERENCE/'upstream'/name).read_bytes()).hexdigest()==row['sha256'],name
    h=(REFERENCE/'upstream/SlewLimiter.h').read_text().replace('#pragma once','').replace('#include "LowPassFilter.h"','')
    cpp=(REFERENCE/'upstream/SlewLimiter.cpp').read_text().replace('#include "SlewLimiter.h"','')
    lpf=r'''
#define CLASS_NO_COPY(name) name(const name&)=delete;name&operator=(const name&)=delete
class LowPassFilterFloat {
 float output=0,cutoff=0;
public:
 void set_cutoff_frequency(const float&v){cutoff=v;}
 void reset(const float&v){output=v;}
 float apply(const float&s,const float&dt){output+=(s-output)*calc_lowpass_alpha_dt(dt,cutoff);return output;}
};
'''
    old='struct DisabledSlew { float modifier(float,float) { return 1; } float get_slew_rate(){return 0;} };'
    assert old in SHIM
    shim=SHIM.replace(old,lpf+h+cpp).replace('DisabledSlew _slew_limiter;',
            'float _smax=0,_stau=1;SlewLimiter _slew_limiter{_smax,_stau};')
    functions=extract('libraries/AP_Math/AP_Math.cpp','float calc_lowpass_alpha_dt(')
    for signature in ('float AC_PID::update_all(', 'void AC_PID::update_i(',
                      'float AC_PID::get_ff()', 'float AC_PID::get_filt_T_alpha(',
                      'float AC_PID::get_filt_E_alpha(', 'float AC_PID::get_filt_D_alpha('):
        functions+=extract('libraries/AC_PID/AC_PID.cpp',signature)
    functions+=extract('libraries/APM_Control/AR_AttitudeControl.cpp',
                       'float AR_AttitudeControl::get_throttle_out_from_pitch(')
    main=MAIN.replace('AR_AttitudeControl control;','static AR_AttitudeControl control;')
    main=main.replace('>> control._pitch_limit_throttle_thresh)',
                      '>> control._pitch_limit_throttle_thresh >> p._smax >> p._stau)')
    main=main.replace("<< control._pitch_limit_low << ' ' << control._pitch_limit_high << '\\n';",
                      "<< control._pitch_limit_low << ' ' << control._pitch_limit_high << ' ' << i.Dmod << ' ' << i.slew_rate << '\\n';")
    source=Path(directory)/'pd_slew_oracle.cpp';binary=Path(directory)/'pd_slew_oracle'
    source.write_text(shim+functions+main)
    subprocess.run(['c++','-std=c++17','-O0',str(source),'-o',str(binary)],check=True,capture_output=True,text=True)
    return binary


def calculate(binary,config,rows):
    names=('kp','ki','kd','imax','fltt','flte','fltd','ff','dff','pitch_ff',
           'pitch_max','limit_tc','limit_threshold','smax','slew_tau')
    data=' '.join(str(config[k]) for k in names)+'\n'
    data+=''.join(' '.join(str(int(v)) if isinstance(v,bool) else str(v) for v in row)+'\n' for row in rows)
    output=subprocess.run([str(binary)],input=data,capture_output=True,text=True,check=True).stdout
    return [list(map(float,line.split())) for line in output.splitlines()]
