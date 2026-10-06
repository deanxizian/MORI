"""Shared H0.1 coupled-plant sensitivity model. No hardware qualification.
R is wheel radius in metres; caller must explicitly assign the geometry value.
"""
import math
import numpy as np
from scipy.linalg import solve_continuous_are
G=9.80665
R=0.0475

def plant_terms(p,theta=0):
    m,l=p['body_mass'],p['l']
    return np.array([[p['total_mass']+p['Jwheels']/R**2,m*l*math.cos(theta)],
                     [m*l*math.cos(theta),p['Jbody']+m*l*l]])

def gain(p):
    h=plant_terms(p);ainv=np.linalg.inv(h)
    A=np.zeros((4,4));A[0,1]=1;A[2,3]=1
    A[[1,3],2]=ainv@np.array([0,p['body_mass']*G*p['l']])
    B=np.zeros((4,1));B[[1,3],0]=ainv@np.array([1/R,-1])
    Q=np.diag([2,1,160,3]);RR=np.array([[1.]])
    P=solve_continuous_are(A,B,Q,RR)
    K=np.linalg.solve(RR,B.T@P)
    assert np.max(np.real(np.linalg.eigvals(A-B@K)))<0
    return K[0]

def simulate(p,k,limit_per_wheel,delay_ms,theta0=10,deadband_nm=.008,lag_ms=6):
    dt=.0005;period=.002;steps=int(3/dt);delay=max(0,int(delay_ms/1000/period))
    commands=[0.]*delay;state=np.array([0.,0.,math.radians(theta0),0.]);tau=0.;held=0.
    times=[];data=[];sat=0;cmd_peak=0.;failed=False;fail_reason=None
    def deriv(s,t):
        _,v,th,w=s;m,l=p['body_mass'],p['l']
        force=m*l*w*w*math.sin(th)-.08*math.tanh(v/.015)-.04*v
        rhs=np.array([t/R+force,m*G*l*math.sin(th)-t-.0002*w])
        ac=np.linalg.solve(plant_terms(p,th),rhs)
        return np.array([v,ac[0],w,ac[1]])
    for n in range(steps):
        if n%4==0:
            raw=-float(k@state);cmd_peak=max(cmd_peak,abs(raw)/2)
            lim=2*limit_per_wheel
            sat+=abs(raw)>lim
            cmd=float(np.clip(raw,-lim,lim));commands.append(cmd);held=commands.pop(0)
            # Conservative friction/gear reversal loss model, not a measured FIT0521 deadband.
            held=math.copysign(max(0,abs(held)-2*deadband_nm),held)
        tau+=(held-tau)*min(1,dt/(lag_ms/1000))
        a=deriv(state,tau);b=deriv(state+dt*a/2,tau);c=deriv(state+dt*b/2,tau);d=deriv(state+dt*c,tau)
        state+=dt*(a+2*b+2*c+d)/6
        if n%20==0:times.append(n*dt);data.append(state.copy())
        if abs(state[2])>math.radians(30):failed=True;fail_reason='tilt_over_30deg';break
        if abs(state[1])>.8:failed=True;fail_reason='wheel_speed_over_0.8m_s';break
    data=np.array(data);tail=data[np.array(times)>2]
    recovered=not failed and len(tail)>0 and np.max(np.abs(tail[:,2]))<math.radians(2) and np.max(np.abs(tail[:,1]))<.1
    result=dict(per_wheel_limit_Nm=limit_per_wheel,delay_ms=delay_ms,actuator_lag_ms=lag_ms,
        assumed_deadband_per_wheel_Nm=deadband_nm,initial_tilt_deg=theta0,
        criterion_met=bool(recovered),stopped=failed,stop_reason=fail_reason,
        max_tilt_deg=float(np.max(np.abs(data[:,2]))*180/math.pi),
        max_speed_m_s=float(np.max(np.abs(data[:,1]))),travel_m=float(np.max(np.abs(data[:,0]))),
        saturation_fraction=sat/max(1,(n//4+1)),unlimited_command_peak_per_wheel_Nm=cmd_peak,
        end_tilt_deg=float(state[2]*180/math.pi))
    return result,np.array(times),data

