# SPDX-License-Identifier: GPL-3.0-or-later
"""Fixed v184 control gains with a stricter boot arming gate; no tuning server."""
from attitude import Fault
from live_tuning import TuningChannel
from live_tuning_policy import gains
from two_deck_remote_drive import PLAN as BASE
from responsive_remote import ResponsiveRemoteController as RemoteDriveController, ResponsiveVelocityReference
from drive_profile import ResponsiveDriveProfile

PLAN = dict(
    BASE,
    name='boot_stand_runtime_0_1_11',
    arm_stable_s=1.5,
    arm_pitch_limit_deg=BASE['arm_pitch_limit_deg'],
    arm_roll_limit_deg=min(5., BASE['arm_roll_limit_deg']),
    arm_pitch_span_deg=1.,
    arm_rate_limit_dps=min(3., BASE.get('arm_rate_limit_dps', 3.)),
    start_on_pose=True,
    handheld_wait=True,
    live_status_window_limit=1,
    wait_upright_message='WAIT_UPRIGHT: 电机禁能。两轮着地，扶正保持 1.5 秒，松开遥控按键。',
    pose_ready_message='ARMING: 扶正计时完成，正在检查平衡接管。',
    active_message='BALANCING: 持续平衡，红点亮、一声后可以松手；方向键行驶，松键减速站立。',
)
# duration_s remains the frozen live-controller admission value. engine.run's
# explicit continuous=True removes the trial deadline; it never restarts PID.


class Controller(RemoteDriveController):
    def reset(self):
        super().reset()
        self.drive_profile = ResponsiveDriveProfile()
        self.speed_reference = ResponsiveVelocityReference()

    def extra_telemetry(self, sample):
        result = super().extra_telemetry(sample)
        velocity = sample['attitude'].get('velocity_hold', {})
        result['drive_response'] = {k:velocity.get(k) for k in (
            'responsive_drive_active', 'selected_speed_gain', 'selected_pitch_slew_dps')}
        return result

    def __init__(self, keys, *, now=None, output_check=lambda: None):
        self.output_check = output_check
        self.stop_combo_since = None
        channel = TuningChannel(gains(PLAN), **({'now': now} if now else {}))
        super().__init__(channel, keys)

    def ready_to_arm(self, now):
        row = self.keys.read(now)
        # An asleep remote is allowed: no movement intent. A connected remote
        # must be released before the continuous dwell can begin.
        return row[3] == 0 and (not row[1] or not row[2])

    def validate_arm(self, attitude, speeds, plan):
        if (abs(attitude['pitch_deg']) > plan['arm_pitch_limit_deg'] or
                abs(attitude['roll_deg']) > plan['arm_roll_limit_deg'] or
                abs(attitude['pitch_rate_dps']) > plan['arm_rate_limit_dps']):
            raise Fault('upright_pose_lost_during_arm')
        return super().validate_arm(attitude, speeds, plan)

    def check_external_stop(self):
        self.output_check()
        super().check_external_stop()

    def __call__(self, attitude, speeds, plan=PLAN):
        row = self.keys.read(attitude['t'])
        # The frozen Keys mask sorts codes: ENTER=bit0, BACK=bit5.
        # Both held for one second are an explicit disarm, not a drive stop.
        combo = row[1] and row[3] & 33 == 33
        self.stop_combo_since = (
            self.stop_combo_since if self.stop_combo_since is not None
            else attitude['t']) if combo else None
        if self.stop_combo_since is not None and attitude['t'] - self.stop_combo_since >= 1.:
            raise Fault('operator_remote_disarm')
        return super().__call__(attitude, speeds, plan)
