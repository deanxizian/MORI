# MORI V1 project rules

- MORI_SPEC_V1.md (user-supplied 2026-09-21 V1) supersedes conflicting A0 instructions. Exactly FOUR actuators: two wheel drives and two head yaw/pitch servos. A real head-mounted camera is mandatory.
- Stage A geometry has one source: config/geometry.json. Allocation envelopes and mounting requirements: contracts/mechanical_interfaces.json. Results and runnable bpy scripts: mechanical/. Hardware work stays in hardware/; preserve unrelated files and other work.
- Root params.json, scripts/, models/, renders/, exports/, hardware/mechanical_interfaces.json and old reports are LEGACY A0, retained for reproducibility. They do not define V1. AGENTS and params snapshots are in mechanical/legacy/.
- Mechanical units are mm. +X right, +Y forward, +Z up. Head yaw +Z turns left; head pitch +X raises the face. Body forward lean is separately defined as -X. Never silently reuse legacy -Y-front transforms.
- Pure two-wheel active balancing; no runtime third contact, caster, skid or support foot. No claim of power-off standing, self-righting or automatic docking. A separate passive maintenance cradle is required; wheels disabled while supported/plugged in.
- Preserve true spherical mother geometry, black circular face with two eyes, plain warm-white wheel hubs, actual belly clearance and tyre/shell gaps. Never scale real hardware to fake fit. No decorative anatomy or obvious neck.
- The head yaw bearing and bilateral pitch bearings carry loads; servos provide torque. Joint samples must include combined yaw/pitch. No infinite rotation or slipring. Provide strain relief and finite service loops.
- Mark every part PRINTABLE / PURCHASED_REFERENCE / PLACEHOLDER and ASSUMED / VENDOR_VERIFIED / MEASURED. Unknown model/hole dimensions remain unknown. Only trial printed-interface holes may be drawn before vendor confirmation.
- Modules first, carrier PCB second, integrated electronics only after measured validation. CAD is PROTOTYPE / UNVALIDATED until its stated checks are completed. A geometry PASS is not hardware qualification.
- Motors disabled on boot/reset/fault. Explicit local unlock and passed checks required. No automatic fault re-arm. Preserve the physical emergency-stop requirement; power-cut actuator/interface and implementation must be confirmed by hardware work. STOP_MOTION differs from DISARM/FAULT_STOP.
- Never invent stock, prices, dimensions, ratings, builds, measurements, balanced operation, 60-minute runtime or <=1000 CNY compliance. Record source data, assumptions and measured evidence separately.
- Status vocabulary: PASS / FAIL / NOT_TESTED / BLOCKED / NOT_APPLICABLE. ERC/DRC does not validate dynamics, thermal performance, EMC or battery safety.
- Record actual commands, tool versions, logs, assumptions and procurement/PCB/power-on blockers. Do not export manufacturing data from an unrouted PCB.
- Scripts may replace only their own tagged generated namespace; preserve unowned scene objects. Render views and STL exports use the same geometry. Explosion transforms are presentation-only.
- AGENTS_MORI_TEMPLATE.md was not supplied/found. The user authorized continuing from task text and then supplied MORI_SPEC_V1.md. No claim that an absent template was read or merged; nonconflicting existing rules above have been retained.
