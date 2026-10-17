# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile unmodified pinned upstream function bodies with no-I/O test shims.

This checks numerical port fidelity, not full ArduPilot integration or physics.
AP_Param storage, AHRS pitch input and clock are shims; notch/slew/PD-sum
features are disabled exactly as documented for the Python port.
"""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]/'reference_sources/ardupilot_rover_4_7_2'


def extract(path, signature):
    text=(ROOT/path).read_text()
    start=text.index(signature)
    brace=text.index('{',start)
    depth=1;end=brace+1
    while depth:
        depth+=(text[end]=='{')-(text[end]=='}')
        end+=1
    return text[start:end]+'\n'


SHIM=r'''
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
using std::isfinite;
#define AP_FILTER_ENABLED 0
#define INTERNAL_ERROR(x) ((void)0)
#define M_2PI 6.28318530717958647692f
#define AR_ATTCONTROL_TIMEOUT_MS 200
#define AR_ATTCONTROL_PITCH_RELAX_RATIO 0.5f
#define MAX(a,b) std::max<float>((a),(b))
#define MIN(a,b) std::min<float>((a),(b))
bool is_positive(float v) { return v > 0; }
bool is_negative(float v) { return v < 0; }
bool is_zero(float v) { return std::abs(v) < 1.1920928955078125e-7f; }
float constrain_float(float v,float lo,float hi) { return std::max(lo,std::min(hi,v)); }
float calc_lowpass_alpha_dt(float dt,float cutoff_freq);
uint32_t clock_ms=1000;
namespace AP_HAL { uint32_t millis() { return clock_ms; } }
struct AHRS { float pitch=0; float get_pitch_rad() const { return pitch; } } ahrs_instance;
namespace AP { AHRS &ahrs() { return ahrs_instance; } }
struct PIDInfo {
 float Dmod=1,slew_rate=0,target=0,actual=0,error=0,P=0,D=0,I=0,FF=0,DFF=0;
 bool PD_limit=false,limit=false,I_term_set=false,reset=false;
};
struct DisabledSlew { float modifier(float,float) { return 1; } float get_slew_rate(){return 0;} };
class AC_PID {
public:
 float _target=0,_error=0,_derivative=0,_target_derivative=0,_integrator=0;
 float _kp=0,_ki=0,_kd=0,_kimax=0,_kff=0,_kdff=0;
 float _filt_T_hz=0,_filt_E_hz=0,_filt_D_hz=0,_kpdmax=0,_slew_limit_scale=1;
 struct { bool _reset_filter=true,_I_set=false; } _flags;
 PIDInfo _pid_info;
 DisabledSlew _slew_limiter;
 float update_all(float,float,float,bool,float=1,float=1);
 void update_i(float,bool,float=1);
 float get_ff() const;
 float get_filt_T_alpha(float) const;
 float get_filt_E_alpha(float) const;
 float get_filt_D_alpha(float) const;
 void reset_filter() { _flags._reset_filter=true; }
 void reset_I() { _integrator=0; }
};
class AR_AttitudeControl {
public:
 AC_PID _pitch_to_throttle_pid;
 float _pitch_to_throttle_ff=0,_pitch_limit_tc=0,_pitch_limit_throttle_thresh=0;
 float _pitch_limit_low=0,_pitch_limit_high=0;
 uint32_t _balance_last_ms=0;
 bool _pitch_limited=false;
 float get_throttle_out_from_pitch(float,float,bool,float);
};
'''

MAIN=r'''
int main() {
 AR_AttitudeControl control;
 auto &p=control._pitch_to_throttle_pid;
 float max_pitch;
 if (!(std::cin >> p._kp >> p._ki >> p._kd >> p._kimax >> p._filt_T_hz
       >> p._filt_E_hz >> p._filt_D_hz >> p._kff >> p._kdff
       >> control._pitch_to_throttle_ff >> max_pitch >> control._pitch_limit_tc
       >> control._pitch_limit_throttle_thresh)) return 2;
 float target,measurement,dt; int limit,reset;
 std::cout << std::setprecision(10);
 while (std::cin >> target >> measurement >> dt >> limit >> reset) {
   clock_ms += std::lround(dt*1000);
   if (reset) control._balance_last_ms=0;
   ahrs_instance.pitch=measurement;
   float out=control.get_throttle_out_from_pitch(target,max_pitch,limit,dt);
   const auto &i=p._pid_info;
   std::cout << out << ' ' << i.P << ' ' << i.I << ' ' << i.D << ' '
      << p.get_ff() << ' ' << i.error << ' ' << i.target << ' '
      << control._pitch_limit_low << ' ' << control._pitch_limit_high << '\n';
 }
}
'''


def build(directory):
    metadata=json.loads((ROOT/'source.json').read_text())
    if metadata['commit']!='fb773567896014da007bca58358704d4a0d8516f':
        raise AssertionError('unexpected_upstream_commit')
    for name,digest in metadata['files'].items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
            raise AssertionError('upstream_reference_modified:'+name)
    functions=extract('libraries/AP_Math/AP_Math.cpp','float calc_lowpass_alpha_dt(')
    for signature in ('float AC_PID::update_all(', 'void AC_PID::update_i(',
                      'float AC_PID::get_ff()', 'float AC_PID::get_filt_T_alpha(',
                      'float AC_PID::get_filt_E_alpha(', 'float AC_PID::get_filt_D_alpha('):
        functions+=extract('libraries/AC_PID/AC_PID.cpp',signature)
    functions+=extract('libraries/APM_Control/AR_AttitudeControl.cpp',
                       'float AR_AttitudeControl::get_throttle_out_from_pitch(')
    source=Path(directory)/'upstream_oracle.cpp'
    binary=Path(directory)/'upstream_oracle'
    source.write_text(SHIM+functions+MAIN)
    subprocess.run(['c++','-std=c++17','-O0',str(source),'-o',str(binary)],
                   check=True,capture_output=True,text=True)
    return binary


def calculate(binary,config,rows):
    names=('kp','ki','kd','imax','fltt','flte','fltd','ff','dff','pitch_ff',
           'pitch_max','limit_tc','limit_threshold')
    data=' '.join(str(config[k]) for k in names)+'\n'
    data+=''.join(' '.join(str(int(v)) if isinstance(v,bool) else str(v) for v in row)+'\n' for row in rows)
    result=subprocess.run([str(binary)],input=data,capture_output=True,text=True,check=True)
    return [list(map(float,line.split())) for line in result.stdout.splitlines()]
