# v153 pitch-frame reference on the current position-return baseline

Previous goal turn is PROGRESS: trial84 rejected the original AP-slew comparison, and v152/trial85 bounded net encoder drift while still taking259s to settle. Goal remains fast, sustained, support-free standing and re-settling after a light push; no software or occasional-quiet claim completes it. Fresh process/socket check confirms no current motion process after85.

## Evidence for this comparison

`analysis_tools/feedback_phase_audit.py` independently checks lag orientation using a known20ms synthetic delay, Welch phase, centred secant timestamps, constant rejection and fixed-world coordinate algebra. On trials82/83/85, both reported speed fields best correlate with the high-resolution rotor-position symmetric derivative at about+10ms lag; velocity magnitude is also filtered at high frequencies. This is a relation between fields, NOT an identified mechanical delay or sensor-internal clock calibration. Reported torque follows sampled predictedNET at a similar+5ms relation, which likewise is not externally measured shaft torque. Coherence in a closed loop is not plant identification.

A second calculation aligns HOST timestamps and compares the body-relative speed with relative speed plus body pitch. The corrected6–15Hz band is27–34percent of the original relative band across three separate recordings. These are nominal no-slip coordinate estimates, not measured floor speed. The symmetric position derivative is OFFLINE and NONCAUSAL; it is NOT selected as a runtime input. The directly differentiated rotor field plus body-angle secant cancels less at those frequencies because field-internal filtering/timing differs. Do not infer that replacing the reported speed with an unfiltered derivative is safe or better.

| Trial/window | Relative6–15Hz RMS rad/s | Relative+gyro RMS rad/s | Ratio |
|---|---:|---:|---:|
| 82 / [5.0, 100.0] | 0.270478 | 0.075663 | 0.280 |
| 83 / [5.0, 90.0] | 0.248561 | 0.067385 | 0.271 |
| 85 / [5.0, 165.0] | 0.277496 | 0.094528 | 0.341 |

## Actual candidate and provenance

Reuse the EXISTING `PitchCorrectedVelocityReference` / `PitchVelocityProxy`: add interpolated body pitch rate at each previous wheel-feedback HOST timestamp before the existing50ms speed filter. No new estimator, notch, friction model, delay extrapolator or motor PID. First sample has explicit raw warmup; stale/unbracketed data faults, never silently falls back after warmup. Raw shaft rates still own all actuator allocation, heading and speed/travel guards. Position-return remains unchanged and uses original relative-origin proxy; it is not world positioning. Existing PID gainsP3.25/I0.60/D0.070, speedP0.25, positionP0.30/s, returntargetcap0.03m/s remain.

Historicalv105/trial33 used this same algebra but drifted farther and was NOT adopted:30s, final common encoder offset about−13cm, no alignment errors. Its P/D, trim and speed-gain baseline differed; it had no current origin-return layer. This new comparison does not assert that old result succeeded or guarantee the current result. Monitor BOTH gross drift and fine oscillation; do not mask one with the other.

New inert-by-default explicit entry `two_deck_live_position_pitch_frame.py`, max1800s to match the already authorized30minute live-tuning scope. Every original hard guard retained:0.12Nm FF/predictedNET,6rad/s,±30deg,80C,0.30m net/24m cumulative/0.03m differential encoder travel, feedback timing/torque, IMU and CAM. No auto-start/service/fault rearm. Mode0 is not power isolation. Current onsite pose/presence and fresh stopped/UPS health must be checked before any physical enable; battery state is time-specific and no per-cell/SOC claim is made.

Focused checks: zero-pitch-rate exact packet parity to v152; fixed-world/case-rotation cancellation only in the speed reference; unchanged position-return and command budgets; stale/unbracketed data/raw speed fault precedence; live origin/PID/filter/estimator state preservation; finite mode1 run and finalmode0/no rearm after injected stale feedback. Full tests, frozen replay and actual physical evidence must be recorded separately. None proves the final goal until real fast sustained settling and disturbance recovery are observed.

Primary reference for the speed-coordinate expectation is the preserved local no-slip helper and pinned ArduPilot pitch/speed architecture. Current official Balance Bot guide was rechecked2026-10-17: https://ardupilot.org/rover/docs/balance_bot-tuning.html and https://ardupilot.org/rover/docs/balance_bot-issues.html. It separately discusses pitch trim, motor dead zone, backlash and PID gains; it does not claim this candidate is correct for S288 hardware.
