#!/usr/bin/env python3
"""One guarded 4 s actuator response probe; operator holds the body upright.

This identifies command/response observations, not balance or calibrated
loaded friction. Both wheels receive the same forward FF ramp, then reverse.
Native damping remains explicit in the log. No attitude controller, retries,
service, or self-righting is enabled. Default invocation performs no I/O.
"""
import math

from air_trial import main as trial_main
from attitude import Fault, finite
from ground_trial import ground_command
from ground_hold_trial import HoldTravel
from protocol import RATIO
from two_deck_fused_roll import PLAN as BASE


PLAN = dict(BASE, name='two_deck_actuator_response_probe_v82', duration_s=4.,
            control_phase='two_deck_response_probe',
            feedforward_torque_limit_nm=.09,
            native_wheel_damping_nm_per_rad_s=.025,
            kp_nm_per_rad=0., kd_nm_per_rad_s=0.,
            probe_peak_ff_nm=.09,
            active_message='RESPONSE_PROBE_ACTIVE: 双轮响应检查现在开始，约4秒。请扶住车身防倒，允许轮子小幅前后滚动；结束后两轮停机。')
PLAN.pop('motion_hold_reason')


def waveform(elapsed):
    finite(elapsed)
    if elapsed < 0.:
        raise Fault('negative_probe_time')
    if .3 <= elapsed < .9:
        return 'forward_ramp', (elapsed-.3)/.6
    if .9 <= elapsed < 1.2:
        return 'forward_hold', 1.
    if 1.2 <= elapsed < 1.5:
        return 'forward_release', (1.5-elapsed)/.3
    if 2. <= elapsed < 2.6:
        return 'reverse_ramp', -(elapsed-2.)/.6
    if 2.6 <= elapsed < 2.9:
        return 'reverse_hold', -1.
    if 2.9 <= elapsed < 3.2:
        return 'reverse_release', -(3.2-elapsed)/.3
    return 'zero_ff_native_damping', 0.


class ResponseProbe:
    def __init__(self):
        self.reset()

    def reset(self):
        self.start = self.previous = self.configuration = None

    def validate_arm(self, attitude, speeds, plan):
        ground_command(attitude, speeds, plan)
        if set(speeds) != {0, 1}:
            raise Fault('probe_requires_both_wheels')

    def __call__(self, attitude, speeds, plan=PLAN):
        self.validate_arm(attitude, speeds, plan)
        t = attitude['t']
        dt = attitude['dt'] if self.previous is None else t-self.previous
        finite(t, dt)
        if not .001 <= dt <= plan['loop_gap_s']:
            raise Fault('probe_sample_gap')
        names = ('probe_peak_ff_nm', 'native_wheel_damping_nm_per_rad_s',
                 'feedforward_torque_limit_nm', 'predicted_net_torque_limit_nm')
        config = tuple(plan[n] for n in names)
        finite(*config)
        if not 0. < plan['probe_peak_ff_nm'] <= plan['feedforward_torque_limit_nm'] <= .09:
            raise Fault('probe_ff_budget_invalid')
        if self.start is None:
            self.start, self.configuration = t, config
        elif config != self.configuration:
            raise Fault('probe_parameters_changed')
        stage, fraction = waveform(t-self.start)
        fraction = max(-1., min(1., fraction))
        requested = fraction*plan['probe_peak_ff_nm']
        kd_step = RATIO**2/128000000
        native_kd = math.floor(plan['native_wheel_damping_nm_per_rad_s']/kd_step)*kd_step
        cap = plan['predicted_net_torque_limit_nm']-RATIO/256000
        commands = {}
        for mid, speed in speeds.items():
            damping = native_kd*speed
            low = max(-plan['feedforward_torque_limit_nm'], -cap+damping)
            high = min(plan['feedforward_torque_limit_nm'], cap+damping)
            if low > high:
                raise Fault('native_braking_envelope_unavailable')
            commands[mid] = max(low, min(high, requested))
        attitude['response_probe'] = dict(
            stage=stage, elapsed_s=t-self.start, requested_forward_ff_nm=requested,
            command_forward_ff_nm=commands.copy(),
            native_kd_quantized_nm_per_rad_s=native_kd,
            previous_forward_rate_rad_s=speeds.copy(),
            limited=any(abs(v-requested)>1e-12 for v in commands.values()),
            scope='guarded_response_only_no_attitude_balance_control')
        self.previous = t
        return commands


def main(argv=None):
    return trial_main(argv, plan=PLAN, start_flag='--run-two-deck-response-probe',
                      controller=ResponseProbe(), travel_factory=HoldTravel,
                      description=__doc__)


if __name__ == '__main__':
    raise SystemExit(main())
