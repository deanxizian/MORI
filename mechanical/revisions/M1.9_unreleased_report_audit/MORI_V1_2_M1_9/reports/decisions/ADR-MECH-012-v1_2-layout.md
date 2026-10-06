# ADR-MECH-012 · V1.2 layout and pending cross-domain review

Status: mechanical M1 decision accepted within user task; vendor interfaces and physical fit pending. Date2026-09-22.

V1.2 user specification supersedes A4 proportions and H0.3 candidate layout. Nominal120/160/95, clearance25, mild bodyB shoulder/belly sculpting. Final derived height287. External-two-wheel operation and hidden yaw/pitch retained; no camera/audio deletion.

Head CAM33700 and LCD35079 move together with pitch. Reuse board audio/microphones. S288x2 with separate frame-carried axles/bearings; SCS0009x2. No additionalFOC or duplicate mic/amp. Direct wheel coupling remains trial blank pending vendor output detail, not a finished spline interface.

The rear motion-board allocation is70x35x12mm (inside the spec maximum70x50). Power allocation44x16x10; CAM50x45x12 and battery80x65x30 are assumed limits. Exceeding these means mechanical redesign, never scaling real hardware. Sources partly documented; actual CAM dimension image unavailable. A complete parts database is not invented.

Battery service changes from downward to forward after both shells and hangers are removed; releasing lower shell requires wheel/axle removal. This maintenance cost remains explicit; future dedicated hatch can improve it after real pack selection. Head shell lower opening is -46.5mm from head center to clear the existing rotor at pitch+25. Range unchanged.

Hardware owner: V1.2-H0.1 components.json appeared during this run and was read-only reconciled. Continue filling missing mechanical data; review/acknowledge contracts/mechanical_interfaces.json allocations and missing dimensions, exact3S power/charger compatibility, mass, thermal, speaker and fastening interfaces. Do not use CAM single-cell charge input as3S charger. No changes were made to electrical_interfaces.json.

Software owner: review reports/camera_kinematics.json, head_load_estimate.json and mass_budget.json for simulation. Sameyaw±60/pitch−20..25; no protocol file changes required by this task. These estimates are not measured feedback or balance qualification.

Budget<=1000CNY remains a gate; missing quotes/runtime evidence block procurement/PCB freeze, not modeling. Templates/references/acceptance/seed companions not supplied. M2 manufacturing interface freeze staysBLOCKED until supplier and measured details arrive.

LCD handoff: hardware correctly states55x55 is a bound, not a55mm cylinder. A full55x55x8 assumed-depth keepout is retained and its actual intersections are reported asBLOCKED. The visible round backing is a construction template only. Obtain actual outline before selecting a deeper screen placement or limited cheek reshaping; no supplier-fit claim.
