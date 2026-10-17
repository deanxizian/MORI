"""Passive IMU evidence during/after a motor lock; owns no motor interface."""
import math


class StopIMURecorder:
    def __init__(self, imu, report, duration_s, now, sleep):
        if not math.isfinite(duration_s) or not 0 < duration_s <= 3:
            raise ValueError('invalid_passive_stop_observation_duration')
        self.imu,self.report,self.duration,self.now,self.sleep=imu,report,duration_s,now,sleep
        self.data=dict(status='NOT_TESTED',samples=[],errors=[],
            requested_after_stop_s=duration_s,motor_commands_sent=0,
            scope='Raw IMU evidence only; no controller, pose correction, retry or rearm')
        report['stop_imu_observation']=self.data

    def poll(self, phase):
        try:
            row=self.imu.sample_nowait()
            if row is not None:
                self.data['samples'].append(dict(phase=phase,imu=row,
                    since_stop_request_s=row['t_read_complete']-self.report['stop_request_monotonic']))
        except Exception as exc:
            if len(self.data['errors'])<32:
                self.data['errors'].append(dict(t=self.now(),phase=phase,
                    reason=str(exc) or type(exc).__name__,
                    rejected_raw=getattr(self.imu,'last_rejected_sample',None)))

    def finish(self):
        if not self.report.get('final_disabled_verified'):
            self.data['reason']='Stop unconfirmed; do not delay physical cutoff report'
            return
        start=self.now()
        for _ in range(601):
            if self.now()-start>=self.duration:
                break
            self.poll('after_lock_verified')
            self.sleep(.005)
        self.data.update(elapsed_after_stop_s=self.now()-start,
            status='PASS' if self.data['samples'] and not self.data['errors'] else 'FAIL')
