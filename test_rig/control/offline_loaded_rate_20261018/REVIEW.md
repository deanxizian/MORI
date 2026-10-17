# v155 operator-held loaded constant-rate diagnostic

Purpose: distinguish loaded low-speed wheel response from host balancing
commands. The user reports visibly intermittent floor rolling, whereas the
three suspended v112 native-rate runs ended disabled and the last was
visually described as basically continuous and smooth. Trial87 v154 still
shows oscillation; reducing speedP0.25 to0.20 did not improve its sampled
10-second windows and was restored to0.25. These observations do not identify
friction, backlash, motor accuracy, or an actuator fault.

The new entry reuses v112 NativeVelocityCommand and exact quantized packet
allocation, and air_trial's explicit unlock, source verification, mode0
prechecks, zero-arm confirmation, raw feedback/IMU guards, CAM cue, final
mode0 verification and post-stop observations. No host balancing PID,
position return, gain tuning, friction compensation or automatic retry.
The body MUST be held upright by the operator throughout while both wheels
remain grounded and free to roll. Catch-only support is insufficient for
this diagnostic. Do not switch from running balance until this changed
physical condition is confirmed, and do not run concurrent motor programs.

Both wheels move in the same vehicle direction (calibrated protocol signs
ID0+ / ID1-). Total9s: forward4s, zero0.5s, reverse4s, zero0.5s. Each4s phase
ramps0.4s up, holds3.2s, ramps0.4s down. Target0.20rad/s quantizes to about
0.19577rad/s; nominal40mm radius gives about8mm/s and2.9cm planned one-way
rolling. Neither is an external measurement of actual floor motion.

Native velocity Kd is at most1.20Nm/(rad/s), reduced using each most recent
sample to keep predicted NET within0.08Nm. FF=0, position target=0, Kp=0.
This is NOT an instantaneous hardware torque clamp. The balancing baseline
has native damping0.005Nm/(rad/s), which is not this velocity-loop Kd.

Stops: raw shaft0.6rad/s, estimated feedback torque0.12Nm (direct strict
health check; inherited dwell-based active guard explicitly disabled),
temperature70C, pitch12deg, roll8deg, pitch-rate80deg/s, inherited rotor
net4cm/cumulative8cm/differential1cm travel limits, independent output net4cm,
or inherited communication/IMU/timing faults. No widening of8ms feedback
deadline,10ms IMU age or25ms loop-gap limits. Independent output samples are
noisy; do not sum their absolute increments as physical travel. A fault
ends the whole sequence, disables both wheels and never rearms itself.

Verification: inert default; exact ramp/pause/reversal; 1801-sample wire
direction, CRC and sampled budget checks; deterministic full-harness finite
sequence and final mode0; speed/temperature/output-travel/error faults;
raw guard precedence and failure latch. FakeBus is not a physical motor
model. Test PASS is not loaded smoothness, balance or hardware qualification.
Before deployment preserve v154 manifest/source backup. Before motion
verify fresh disabled state, power, pose, temperatures below70C and actual
operator support. No autonomous start. Physical outcome NOT_TESTED.
