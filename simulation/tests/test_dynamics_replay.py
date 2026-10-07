import json,pathlib
import pytest
from simulation.dynamics import run
from simulation.replay import replay

def test_model_sign_delay_noise_deadzone_slip():
 good=run();assert good['fault'] is None;assert abs(good['pitch_end_rad'])<.01
 assert run(reverse=True)['fault'] is not None
 assert run(delay_s=.2)['fault'] is not None
 assert run(slip=.05)['fault'] is not None
 assert good['kp_model_only']==9.80665+.15*25

def test_replay_keeps_balance_after_stop_and_expiry():
 data=[json.loads(x) for x in pathlib.Path('simulation/fixtures/SIMULATED_session.jsonl').read_text().splitlines()][1:]
 rows=replay(data);assert rows[-1]['state']['enabled'] and rows[-1]['state']['target_v_m_s']==0
 assert rows[-1]['state']['owner'] is None

def test_low_supply_loses_authority_and_trips_without_claiming_a_battery_threshold():
 weak=run(supply_fraction=.15);assert weak['fault'] in ('SEVERE_TILT','SATURATION')
 assert max(abs(s['cart_acceleration_m_s2']) for s in weak['samples'])<=.30
 unpowered=run(supply_fraction=0,noise_rad=0)
 assert unpowered['fault'] is not None
 assert all(s['cart_acceleration_m_s2']==0 for s in unpowered['samples'])
 assert unpowered['pitch_end_rad']>.035
 assert weak['hardware_qualification']=='NOT_TESTED'

def test_head_inertia_and_motion_reaction_are_distinct_from_screen_gaze():
 params=dict(head_mass_kg=.18,head_height_m=.26,head_inertia_kg_m2=.001,initial_pitch_rad=0,noise_rad=0,deadzone=0)
 quiet=run(**params);moving=run(**params,head_pitch_amplitude_rad=.17)
 assert quiet['pitch_max_rad']==0
 assert moving['pitch_max_rad']>0
 assert max(s['head_reaction_nm'] for s in moving['samples'])>0
 assert min(s['head_reaction_nm'] for s in moving['samples'])<0
 assert moving==run(**params,head_pitch_amplitude_rad=.17)
 # Same initial lean and zero actuation: a higher head changes passive dynamics.
 body=run(supply_fraction=0,noise_rad=0)
 head=run(supply_fraction=0,noise_rad=0,head_mass_kg=.18,head_height_m=.26,head_inertia_kg_m2=.001)
 assert abs(body['pitch_end_rad']-head['pitch_end_rad'])>.001

@pytest.mark.parametrize('params',[{'supply_fraction':float('nan')},{'head_mass_kg':-1},{'head_inertia_kg_m2':float('inf')},{'delay_s':-1}])
def test_dynamics_rejects_nonphysical_or_nonfinite_parameters(params):
 with pytest.raises(ValueError):run(**params)

def test_zero_and_fractional_delay_reach_the_actuator_at_declared_times():
 dt=1/416;params=dict(seconds=.02,deadzone=0,noise_rad=0)
 immediate=run(delay_s=0,**params)['samples'][0]['cart_acceleration_m_s2']
 assert immediate>0
 assert run(delay_s=dt,**params)['samples'][0]['cart_acceleration_m_s2']==0
 delayed=run(delay_s=dt,**params)['samples']
 assert delayed[1]['cart_acceleration_m_s2']==pytest.approx(immediate)
 assert run(delay_s=dt/2,**params)['samples'][0]['cart_acceleration_m_s2']==pytest.approx(immediate/2)

def test_replay_unknown_scenario_fails_explicitly():
 with pytest.raises(ValueError,match='scenario'):replay([{'scenario':'singel'}])
