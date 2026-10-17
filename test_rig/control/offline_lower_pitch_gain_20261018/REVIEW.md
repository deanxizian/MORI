# v156 one-factor lower pitch gain comparison

Trial87 v154:501.492108s/99706cycles, deliberate operator_disarm_requested
after the operator switched to supporting the body for a diagnostic.
Final mode0 verified; raw1118307192bytes SHA256
3461a6fdf8ae890d53188bbab7bce2756cb939de061dc675dde4d689c22d5285.
Persisted with file and directory fsync, copied and hash-verified locally.
Its10-second windows continued oscillating; speedP0.20 did not improve the
comparison and was restored0.25. Operator reports intermittent floor rolling.

Two v155 fixed native-rate attempts stopped on pitch12deg after0.993/2.825s,
final mode0 verified, no auto-retry. Reverse was never reached. In the second
attempt's0.804-2.816s forward segment, target0.20 quantized0.19577rad/s,
feedback means left0.17527/right0.17407rad/s, no<=0.02rad/s interval lasting
0.1s. Operator missed visual observation. Body pitch changed, and native
speed control is not the balance torque backend, so this is NOT loaded
smoothness, backlash or accuracy qualification, or motor fault exclusion.

Trial87 representative30s windows show pitch P RMS about0.028Nm, I about
0.002-0.003Nm and D about0.010-0.012Nm, with repeated low-speed/burst response.
This motivates testing lower pitch stiffness; it does not identify a cause
or predict a stable plant. Actual COM, friction and actuator transfer remain
unmeasured. Do not infer motor resolution from apparent rolling increments.

v156 changes only initial pitch P2.75 to2.50. Same v154 controller, I0.60,
D0.050, speedP0.25, body-pitch velocity correction, position origin/return,
integral gate, native damping0.005, FF/NET0.12Nm,6rad/s,+/-30deg,80C,
1800s maximum and every IMU/serial/travel/torque guard remain unchanged.
The source-reviewed live policy P lower edge expands2.75 to2.00, preserving
upper3.50, maximum step0.25,1-5s ramp, session/revision/readiness checks and
immutable plan fields. This software envelope is experimental, not a
demonstrated stable-gain or safety rating. Start at2.50, observe comparable
unperturbed windows, then at most one small smooth change at a time; reject
or restore on deterioration. No automatic parameter search or fault rearm.

Tests cover inert default, exact scope/guard invariance, lower-bound and
step rejection,1200-frame same-gain controller/packet parity and budgets,
staged2.50->2.25->2.00 ramps preserving PID/filter/integral/origin lifecycle,
and persistent DISARM. Software/frozen checks do not certify actual balance.
Preserve v155 source backup before source-only deployment. Fresh upright
grounded pose, charger unplugged, onsite catch/power cut and explicit unlock
remain necessary. Red/on one tone means active balance; off/two means catch.
Physical outcome NOT_TESTED. Never automatically restart after a fault.
