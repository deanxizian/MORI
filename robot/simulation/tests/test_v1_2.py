from contracts.profile import PROFILE
from simulation.harness import Rig
from simulation.vision import Vision, fixture
import struct
import pytest
from simulation.s288_replay import decode, crc32_words, rows
from fastapi.testclient import TestClient
from backend.mori.app import create_app

def test_v1_2_unknown_telemetry_never_looks_measured():
    s=Rig().d.snapshot()
    assert s['software_version']=='1.2.0-dev.1' and s['source']=='SIMULATED'
    assert not s['physical_release'] and not PROFILE['control']['physical_enable']
    assert PROFILE['control']['kp_pitch']==0 and PROFILE['control']['wheel_torque_limit_nm']==0
    for block in [s['sensors']['body_imu'],s['sensors']['head'],s['sensors']['power'],*s['sensors']['wheels']]:
        assert block['valid'] is False
        assert all(value is None for key,value in block.items() if key!='valid')
    assert PROFILE['power']['critical_v'] is None  # never reuse the old 2S cutoff
    assert PROFILE['motion']['inter_mcu_baud'] is None

def test_health_version_matches_telemetry_and_profile(tmp_path):
    with TestClient(create_app(str(tmp_path))) as client:
        assert client.get('/health').json()['version']==PROFILE['software_version']

def test_tracking_before_first_frame_is_pending_not_http_error(tmp_path):
    app=create_app(str(tmp_path));g=app.state.gateway
    # No lifespan producer: exercise the precise interval before first capture.
    client=TestClient(app)
    try:
        identity=client.post('/api/pair',json={'code':g.auth.pair_code}).json()
        headers={'Authorization':'Bearer '+identity['token']}
        g.device.camera='TRACKING'
        pending=client.get('/api/camera/frame',headers=headers)
        assert pending.status_code==204 and pending.content==b''
        g.device.camera='OFF'
        assert client.get('/api/camera/frame',headers=headers).status_code==409
    finally:client.close();g.close()

def test_missing_head_feedback_stops_body_follow_without_disarm():
    r=Rig();r.arm();r.issue('CAMERA_MODE',{'mode':'TRACKING','upload_allowed':False})
    frame=r.d.capture();r.d.observe(frame,Vision().detect(fixture(1)))
    r.issue('SELECT_TARGET',{'target_id':'track-1','confirmed':True})
    assert r.issue('FOLLOW',{'mode':'BODY','supervised':True})['status']=='RUNNING'
    r.d.head_feedback_ok=False;r.tick()
    assert r.d.active is None and r.d.target_v==0 and r.d.enabled
    assert not r.d.observe(r.d.capture(),Vision().detect(fixture(2)))

def test_s288_replay_corruption_units_unsigned_and_provenance():
    p=bytes.fromhex('fcee1019c81800018000008000000000000000100000')
    p+=struct.pack('<I',crc32_words(p[2:]))
    f=decode(p,0)
    assert f['sensor_raw']==200 and f['voltage_v']==12
    assert f['absolute_output_rad']==pytest.approx(3.141592653589793)
    for bad in [p[:-1],p+b'0',p[:-1]+bytes([p[-1]^1])]:
        with pytest.raises(ValueError):decode(bad,0)
    with pytest.raises(ValueError):decode(p,1)
    values=list(rows('simulation/fixtures/SIMULATED_s288.jsonl'))
    assert len(values)==2 and all(r['source']=='SIMULATED' for r in values)
