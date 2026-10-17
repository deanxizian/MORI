# v159 native execution on the current causal position-return baseline

Goal remains rapid, repeatable support-free quiet including after a light
disturbance. Trial91 had persistent small oscillation across live P/D
comparisons, not goal completion. Actual UART successful20-byte writes
confirm198.6-198.8Hz per servo. These counts do not qualify internal servo
sampling, motor accuracy, backlash, friction or closed-loop delay.

The fixed-speed diagnostic inherited a misleading red/release cue. v158
repairs this and preserves all balance cues and watchdogs. Trial92 completed
9s, but support condition cannot be asserted; visual observation was missed.
User explains releasing on red during93, which stopped on tilt. Trial94
used the repaired red-OFF/silent path, user confirms holding throughout,
but missed seeing start. It stopped on tilt at2.900109s, mode0 verified.
These are NOT supported/unperturbed balance observations or proven smooth
external wheel/floor motion. No more repeated held tests are planned now.

Candidate composes the existing reviewed NativeExecutionController around
the full CausalVelocityLiveController via explicit tested C3 order. Original
position return, timestamped20ms velocity input, integral gate, inner PID,
relative-heading requests, arming/reset/final-stop and bounded tuning API
remain. Freeze current trial91 gains P3.25/I0.60/D0.050/speedP0.25 initially.
Only active actuator allocation/packets change: use existing native NET
allocator, zero position/stiffness, velocity reference near measured rate
plus requestedNET/Kd and tiny FF wire correction. Kd0.040 is experimental,
not vendor tuning or identified plant data; it is between passive0.005 and
the earlier physically exercised native0.40 path. Earlier41-43 had worse
drift and are NOT adopted as successful balance. Current feedback/position
path differs, so this new comparison still requires real verification.

Same0.12Nm FF and sampled predictedNET budgets, actual shaft6rad/s, pitch
+/-30deg,80C and all original IMU/communication/travel/torque protection.
A wire velocity reference capped6rad/s does not bound instantaneous motion.
Sampled predictedNET is NOT a hardware instantaneous torque clamp; internal
rate filtering and actuator dynamics remain unqualified. Keep1800s upper
bound to permit a single standing session, but monitor initial seconds
closely. Default inert; explicit exact start/operator unlock and fresh
checks. No automatic fault rearm, boot service, controller/origin reset.
Red/one-tone balance cue retained; redOFF/two tones means catch.

Frozen raw87 SHA3461a6fdf8ae890d53188bbab7bce2756cb939de061dc675dde4d689c22d5285,
99706counterfactual frames: maxFF0.001126382459Nm, maxsampledNET0.119733027885Nm,
maxvelocityreference3.634477rad/s,2limited frames,6startup warmup frames,
single PID object and one filter reset, exact CRC and polarity/budgets.
Trajectory came from another controller. This check predicts no physical
stability, settling, actual NET torque, friction or floor movement.

Meaningful tests verify one PID/reference path, preserved values against
baseline in unsaturated motion, exact signed packet decoding/CRC/budgets,
raw speed/configuration failure and invalidated allocations, full zero-arm
and fault final-mode0/no-rearm harness, and inert explicit entry.
Before deployment require both-host full checks and preserved prior sources.
No motor I/O occurs during deployment. New physical comparison requires
current upright/catch-only onsite facts after the held diagnostic stop.
