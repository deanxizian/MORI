#!/usr/bin/env python3
"""Finite raw-IMU observation with no motor/serial I/O or attitude filtering."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import signal
import sys
import time

from preflight import RawIMU, CycleGC
from calibration import dot, unit


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture',action='store_true')
    p.add_argument('--seconds',type=int,choices=range(1,121),default=120)
    p.add_argument('--output',type=Path)
    args=p.parse_args(argv)
    if not args.capture:
        print(json.dumps(dict(status='NOT_TESTED',hardware_opened=False,motor_serial_opened=False)))
        return 0
    if not args.output or sys.platform!='linux':p.error('Pi Linux and new output file required')
    report=dict(utc=datetime.now(timezone.utc).isoformat(),status='FAIL',imu={},gc={},samples=[],
                motor_serial_opened=False,motor_commands_sent=0,requested_seconds=args.seconds,
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                timestamp_boundary='host read completion; not sensor hardware timestamp')
    def stop(sig,_):raise KeyboardInterrupt('signal_'+str(sig))
    with args.output.open('x') as output:
        handlers={s:signal.signal(s,stop) for s in (signal.SIGINT,signal.SIGTERM,signal.SIGHUP)}
        try:
            with CycleGC(report['gc'],'defer'),RawIMU(report['imu']) as imu:
                begin=time.monotonic();last_print=begin-5;reference=None
                print('IMU_ONLY_CAPTURE_READY: 已开始原始三轴采集，最长 120 秒；不打开电机串口。',flush=True)
                while time.monotonic()-begin<args.seconds:
                    row=imu.sample();t=time.monotonic()
                    g=unit(row['accel_g'])
                    if reference is None:reference=g
                    change=math.degrees(math.acos(max(-1,min(1,dot(reference,g)))))
                    report['samples'].append(dict(elapsed_s=t-begin,imu=row,gravity_change_deg=change))
                    if t-last_print>=5:
                        print(json.dumps(dict(elapsed_s=round(t-begin,1),gravity_change_deg=round(change,1),
                                              accel_g=[round(v,3) for v in row['accel_g']],
                                              gyro_dps=[round(v,2) for v in row['gyro_dps']])),flush=True)
                        last_print=t
                report.update(status='PASS',elapsed_s=time.monotonic()-begin,completion='duration_completed')
        except KeyboardInterrupt as exc:
            report.update(status='PASS' if report['samples'] else 'FAIL',completion='operator_ended_capture',reason=str(exc))
        except Exception as exc:
            report.update(status='FAIL',reason=str(exc))
        finally:
            if not report['imu'].get('configuration_restored',False):report['status']='FAIL'
            json.dump(report,output,indent=2)
            for s,h in handlers.items():signal.signal(s,h)
    print(json.dumps(dict(status=report['status'],samples=len(report['samples']),
                          reason=report.get('reason'),motor_commands_sent=0,
                          imu_restored=report['imu'].get('configuration_restored'))),flush=True)
    return 0 if report['status']=='PASS' else 2


if __name__=='__main__':raise SystemExit(main())
