"""ASSUMED planar model, not an identified MORI plant or a tuning file.
Input is cart acceleration m/s², NOT S288 torque or PWM. Positive forward lean
needs forward acceleration. A point body plus a fixed-height head give
J*theta'' = g*H*theta - H*a - I_head*head_pitch''.
The head's COM is assumed at its pitch bearing; its orbital mass and spin inertia
are separate. Head COM offsets, motor electrical dynamics and tyre compliance
are not represented. Supply fraction limits available acceleration; it is not
a battery-voltage threshold or a measured voltage/torque transfer function.
"""
import math,random,collections,json,argparse,pathlib

def run(reverse=False,delay_s=.01,deadzone=.03,noise_rad=.0005,slip=1.,seconds=4.,
        supply_fraction=1.,head_mass_kg=0.,head_height_m=.23,
        head_inertia_kg_m2=0.,head_pitch_amplitude_rad=0.,head_pitch_hz=1.,
        initial_pitch_rad=.035):
 values=(delay_s,deadzone,noise_rad,slip,seconds,supply_fraction,head_mass_kg,
         head_height_m,head_inertia_kg_m2,head_pitch_amplitude_rad,head_pitch_hz,initial_pitch_rad)
 if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in values):raise ValueError('finite model parameters required')
 if not (0<=delay_s<=1 and 0<=deadzone<=2 and 0<=noise_rad<=.1 and 0<=slip<=1 and 0<seconds<=60 and 0<=supply_fraction<=1 and 0<=head_mass_kg<=2 and 0<head_height_m<=1 and 0<=head_inertia_kg_m2<=1 and abs(head_pitch_amplitude_rad)<=.5 and 0<=head_pitch_hz<=5 and abs(initial_pitch_rad)<.349):raise ValueError('model parameter outside supported range')
 dt=1/416;length=.15;g=9.80665;wn=5.;damping=.8
 # Body-only nominal model, fixed across stress cases. Desired s²+2ζωs+ω².
 kp=g+length*wn**2;kd=length*2*damping*wn
 body_mass_kg=1.;H=body_mass_kg*length+head_mass_kg*head_height_m
 J=body_mass_kg*length**2+head_mass_kg*head_height_m**2+head_inertia_kg_m2
 available_acceleration=2.*supply_fraction
 theta=initial_pitch_rad;rate=0.;x=v=0.;maximum=abs(theta);saturated=0.;fault=None
 # Linear fractional-sample delay: zero is immediate; exact grid delays use N samples.
 delay_steps=delay_s/dt;whole=int(delay_steps);fraction=delay_steps-whole
 q=collections.deque([0.]*(whole+2),maxlen=whole+2);rng=random.Random(17);samples=[]
 for i in range(int(seconds/dt)):
  measured=theta+rng.gauss(0,noise_rad);raw=(kp*measured+kd*rate)*(-1 if reverse else 1)
  a=max(-available_acceleration,min(available_acceleration,raw));a=0 if abs(a)<deadzone else a-math.copysign(deadzone,a)
  saturated=saturated+dt if abs(raw)>available_acceleration else 0
  if abs(theta)>.349 or saturated>.2:fault='SEVERE_TILT' if abs(theta)>.349 else 'SATURATION';break
  head_rate_frequency=2*math.pi*head_pitch_hz
  head_acceleration=-head_pitch_amplitude_rad*head_rate_frequency**2*math.sin(head_rate_frequency*i*dt)
  head_reaction_nm=-head_inertia_kg_m2*head_acceleration
  q.append(a);applied=((1-fraction)*q[-whole-1]+fraction*q[-whole-2])*slip
  rate+=(g*H*theta-H*applied+head_reaction_nm)/J*dt;theta+=rate*dt;v+=applied*dt;x+=v*dt
  maximum=max(maximum,abs(theta));samples.append({'t_s':i*dt,'pitch_rad':theta,'cart_acceleration_m_s2':applied,'head_reaction_nm':head_reaction_nm,'x_m':x,'v_m_s':v})
 return {'source':'SIMULATION','hardware_qualification':'NOT_TESTED','parameters':'ASSUMED_CART_ACCELERATION_MODEL_NOT_PWM_OR_S288_TORQUE','kp_model_only':kp,'kd_model_only':kd,'pitch_end_rad':theta,'pitch_max_rad':maximum,'fault':fault,'dt_s':dt,'delay_s':delay_s,'delay_model':'linear_fractional_sample','deadzone':deadzone,'noise_rad':noise_rad,'slip':slip,'supply_fraction':supply_fraction,'available_acceleration_m_s2':available_acceleration,'body_mass_kg':body_mass_kg,'body_height_m':length,'head_mass_kg':head_mass_kg,'head_height_m':head_height_m,'head_inertia_kg_m2':head_inertia_kg_m2,'head_pitch_amplitude_rad':head_pitch_amplitude_rad,'head_pitch_hz':head_pitch_hz,'gravity_moment_kg_m':H,'total_inertia_kg_m2':J,'samples':samples}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',default='reports/v1/SIMULATED_dynamics.json');a=ap.parse_args()
 results={name:run(**kw) for name,kw in [('nominal',{}),('reverse',{'reverse':True}),('delay_120ms',{'delay_s':.12}),('wheel_slip',{'slip':.05}),('low_supply',{'supply_fraction':.15}),('head_inertia',{'head_mass_kg':.18,'head_height_m':.26,'head_inertia_kg_m2':.001}),('head_motion',{'head_mass_kg':.18,'head_height_m':.26,'head_inertia_kg_m2':.001,'head_pitch_amplitude_rad':.17}),('combined',{'delay_s':.08,'supply_fraction':.3,'head_mass_kg':.18,'head_height_m':.26,'head_inertia_kg_m2':.001,'head_pitch_amplitude_rad':.17})]}
 pathlib.Path(a.output).write_text(json.dumps(results,indent=2));print(a.output)
if __name__=='__main__':main()
