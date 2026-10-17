# v157 same-window velocity input comparison

Current trial90 v156 remains ACTIVE with P2.75/I0.60/D0.065/speedP0.25.
Initial P2.50 was followed by an operator-confirmed light push, so its early
windows are not an unperturbed comparison. Restored P2.75, tested D0.065,
then D0.080: the latter increased angular-rate RMS without full settling and
was restored to0.065. Two10s zero reported shaft-speed windows occurred near
246-266s. The user then confirmed one actual light push and no later contact;
the current loop has continued oscillating for minutes. No repeatable fast
settling, permanent stillness, or actuator defect is established.

v157 compares only the velocity input against those current four gains.
Forward continuous rotor/gear angle plus interpolated forward body pitch
are differentiated over the SAME PAST20ms window. No future samples or
independent absolute output-angle derivative. Host receive timestamps do
not reveal internal sampling/filter delays; nominal no-slip velocity is not
measured floor speed. The first about6frames explicitly reuse the legacy
input until the window exists. After ready, invalid data faults, never
silently falls back. Bounded history and strict order/age/gap checks.

The complete original arming path uses its original speed reference, then
the existing reset-before-active starts a fresh candidate. This preserves
zero-mode/zero-arm checks rather than weakening them to fit the candidate.
Raw shaft speed, allocation, relative heading, travel and all original
actuator/body/thermal/communication/IMU guards remain authoritative. Outer
speed filtering, pitch-reference limits/slew, inner PID, position origin,
return and integral gate remain unchanged. Same FF/NET0.12Nm,6rad/s,
+/-30deg,80C,1800s maximum. Same explicit local unlock, source verification,
CAM red/on-one-tone and off-two-tones, final mode0 and post-stop observations.
No automatic start, parameter search, controller reset or fault rearm.

Frozen trial87 source1118307192bytes SHA256
3461a6fdf8ae890d53188bbab7bce2756cb939de061dc675dde4d689c22d5285:
estimator99700ready/6warmup/0rejections. New RMS0.0157-0.0192m/s versus old
0.0134-0.0165m/s on selected30s windows, so DO NOT claim lower noise or an
already improved estimator. Difference RMS0.0078-0.0101m/s demonstrates a
material bandwidth/phase difference; it is not identified sensor latency or
proof the old estimate was wrong. Counterfactual full-controller99706frame
check:0limited frames, maxFF0.118270Nm/maxpredictedNET0.116722Nm, exact packets
retain zero velocity/position/stiffness, CRC valid, one startup filter reset
and the same PID object. Recorded inputs came from another controller;
these checks do not predict its resulting physical trajectory or stability.
Reports: logs/trial87-causal-velocity-review.json,
logs/trial87-causal-command-budget.json and source analysis scripts.

Local485tests PASS, including known constant-world motion plus body rotation,
fixed-world rocking with mismatched reported-rate filtering, strict invalid
time/data rejection, bounded history, stationary packet parity, raw speed/
stale-feedback faults and full fake-bus legacy-arm/final-mode0 lifecycle.
FakeBus is not a physical motor model. Pi full-suite verification and fresh
disabled health/power/pose checks are required after supported handover.
Never deploy over an active motor loop. Ask the operator to HOLD the body
before deliberate DISARM of trial90, preserve its raw report and source,
then source-only deploy. Hardware outcome NOT_TESTED. Initial physical
comparison remains no-push, then only a deliberate light-push recovery test.
