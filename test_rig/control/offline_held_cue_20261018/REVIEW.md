# v158 held-diagnostic cue repair

User reports releasing the body on red because red has consistently meant
balance compensation active. The held constant-rate diagnostic reused that
cue despite disabling body balance PID. This is an operator-interface defect.
Do not attribute the subsequent fall to a failing balance controller or use
this run to qualify supported loaded wheel smoothness. Motors are stopped.

Trial92 completed9.001515s/1793cycles and final mode0 was verified. Its body
support throughout is UNKNOWN, visual result missed. All four selected
relative-rotor speed plateaus have no low-speed reports, but there is no
external floor/output motion measure. This is not hardware-accuracy proof.
Raw13523346bytes SHA971e07332ca8145b4e615a6eb802159c7ed6618aa7d9a4ba6ee881a4a219e792.
Trial93 stopped on body tilt at2.985252s/594cycles; final mode0 verified.
User then explained red/release behavior, exact contact/release time unknown.
Raw4788275bytes SHAd4c30d2b8562f393f3e6fa55231ad77b305388f2547931eefd72ac1b36e8051f.

Change only cue semantics. CamIndicator defaults retain the original red,
one start/two stop tones and watchdogs for every balance entry. An explicit
boolean operator_held_diagnostic plan flag selects red-off/silent behavior.
The CAM link still handshakes, acknowledges completed OFF frames, checks
450ms ACK freshness and150ms control liveness. A wrong ON ACK faults. It
never emits M or b on this held path; all motor/controller/thermal/travel/
pose/communication gates and existing finite9s native-rate sequence remain.
No CAM firmware change or flash, source/runtime mode change, or auto rearm.
The operator must HOLD throughout, not only guard against falling.

Tests use actual worker threads and fake CAM ACK transport to verify no red
command or balance tone, control expiry, missing/off or unexpected/on ACK
faults, correct entry factory selection, and unchanged default balance cue.
Software passes do not establish physical smoothness or rapid settling.

Source-only deployment backs up the full priorv157 source and manifest.
No motor entry point runs during deployment. Before any new motor trial,
complete display-only OFF verification and confirm onsite body/part state
after release. Balance remains unoptimized; this fixes a prerequisite for
valid actuator isolation. No automatic restart after93 fault.
