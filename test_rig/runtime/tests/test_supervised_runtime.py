import copy
import gc
from contextlib import ExitStack, nullcontext
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
import weakref
from unittest.mock import patch
import main
from test_attitude_air import CAL
from test_fall_recovery import stopped_report


class SupervisedRuntimeTests(unittest.TestCase):
    def test_attempt_callbacks_release_controllers_with_gc_disabled_including_exception(self):
        for fail_last in (False,True):
            with self.subTest(fail_last=fail_last):
                refs=[]
                class Output:
                    def __init__(self,*args):self.telemetry={}
                    def __enter__(self):return self
                    def __exit__(self,*args):pass
                    def check(self):pass
                    def __call__(self,message):pass
                class Writer:
                    def __init__(self,*args):pass
                    def open(self,*args):return nullcontext(SimpleNamespace())
                    def audit(self):return {}
                def run(exchanges,imu,cal,report,ack,**kwargs):
                    refs.append(weakref.ref(kwargs['controller']))
                    if len(refs)==5 and fail_last:raise RuntimeError('injected attempt failure')
                    report.update(stopped_report('wheel_speed_stop' if len(refs)<5 else 'signal_15'))
                was_enabled=gc.isenabled()
                gc.disable()
                try:
                    with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
                        root=Path(folder);device=root/'fake-device';device.touch()
                        config=dict(state_directory=str(root/'state'),run_directory=str(root/'run'))
                        replacements={
                            'support.StatusOutput':Output,
                            'support.current_boot_id':lambda:'00000000-0000-0000-0000-000000000001',
                            'preflight.PORT':str(device),'cam_indicator.PORT':str(device),
                            'preflight.RawIMU':lambda *a,**k:nullcontext(object()),
                            'preflight.CycleGC':lambda *a,**k:nullcontext(),
                            'remote_drive_keys.KeyWorker':lambda *a,**k:nullcontext(),
                            'air_trial.display_indicator':lambda *a,**k:nullcontext(object()),
                            'accepted_write.AcceptedPortOpener':Writer,
                            'bench.port_records':lambda:[], 'bench.select_port':lambda *a:{},
                            'engine.run':run,
                        }
                        for name,value in replacements.items():stack.enter_context(patch(name,value))
                        self.assertEqual(main.execute(config,copy.deepcopy(CAL)),2 if fail_last else 0)
                    self.assertEqual(len(refs),5)
                    self.assertFalse(any(ref() is not None for ref in refs))
                finally:
                    if was_enabled:gc.enable()
                    gc.collect()

    def test_main_resets_controller_and_only_authorizes_verified_disabled_handoff_ack(self):
        calls=[];controllers=[];messages=[]
        class Output:
            def __init__(self,*args):self.telemetry={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def check(self):pass
            def __call__(self,message):messages.append((message,self.telemetry.copy()))
        class Writer:
            def __init__(self,*args):pass
            def open(self,*args):return nullcontext(SimpleNamespace())
            def audit(self):return {'test_transport':True}
        def run(exchanges,imu,cal,report,ack,**kwargs):
            c=kwargs['controller'];controllers.append(c)
            calls.append((ack,kwargs['require_reposition']))
            if kwargs['require_reposition']:
                self.assertTrue(report['disabled_idle_timeout_ack_authorized'])
                self.assertTrue(report['previous_stop_archive'])
            self.assertEqual(c.remote_v,0.)
            self.assertEqual(c.remote_turn,0.)
            self.assertEqual(c.speed_reference.remote_speed_integral_rad,0.)
            report['reposition_seen']=False
            kwargs['waiting_observer'](dict(t=1.,pitch_deg=0.,roll_deg=0.,pitch_rate_dps=0.),
                                       {0:0.,1:0.},0.,False,None)
            c.remote_v=.16;c.remote_turn=5.;c.speed_reference.remote_speed_integral_rad=.01
            report.update(stopped_report('wheel_speed_stop' if len(calls)==1 else 'signal_15'))
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            root=Path(folder);device=root/'fake-device';device.touch()
            config=dict(state_directory=str(root/'state'),run_directory=str(root/'run'))
            replacements={
                'support.StatusOutput':Output,
                'support.current_boot_id':lambda:'00000000-0000-0000-0000-000000000001',
                'preflight.PORT':str(device),'cam_indicator.PORT':str(device),
                'preflight.RawIMU':lambda *a,**k:nullcontext(object()),
                'preflight.CycleGC':lambda *a,**k:nullcontext(),
                'remote_drive_keys.KeyWorker':lambda *a,**k:nullcontext(),
                'air_trial.display_indicator':lambda *a,**k:nullcontext(object()),
                'accepted_write.AcceptedPortOpener':Writer,
                'bench.port_records':lambda:[], 'bench.select_port':lambda *a:{},
                'engine.run':run,
            }
            for name,value in replacements.items():stack.enter_context(patch(name,value))
            self.assertEqual(main.execute(config,copy.deepcopy(CAL)),0)
            self.assertEqual(calls,[(True,False),(True,True)])
            self.assertIsNot(controllers[0],controllers[1])
            self.assertEqual(len(list((root/'state/motion-stops').glob('*.json'))),1)
            result=json.loads((root/'state/last-result.json').read_text())
            self.assertEqual(result['stand_cycle'],1)
            self.assertEqual(result['reason'],'signal_15')
            self.assertFalse((root/'state/latch.json').exists())
            self.assertTrue(any(m.startswith('WAIT_REPOSITION:') and t['stand_cycle']==1 for m,t in messages))
