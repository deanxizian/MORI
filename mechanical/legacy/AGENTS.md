# MORI hardware constraints

- Preserve existing Blender models, params.json, geometry reports and unrelated files. Hardware work lives in hardware/.
- Exactly three motors: two encoded brushed DC wheel drives and one position-controlled head yaw actuator.
- Pure two-wheel active balancing; no runtime third contact, caster, skid or support foot. No promise of power-off standing, self-righting or docking.
- Keep spherical head/body, circular black face, plain wheel hubs, ground clearance and tyre/shell clearance. Never scale real parts to fake fit.
- Use existing structure parameters when supplied. The Blender project is now present: root params.json and reports/derived.json are authoritative. hardware/mechanical_interfaces.json mirrors these coordinates and records actual candidate parts and fit conflicts. Never introduce a competing mechanical definition.
- Modules first, carrier PCB second, integrated electronics only after measured validation. All current CAD is PROTOTYPE / UNVALIDATED.
- Motors disabled on boot/reset/fault. Explicit local unlock and passed checks required. No automatic fault re-arm. Physical emergency stop required.
- Never invent stock, prices, dimensions, ratings, successful builds, measurements or balance logs. Distinguish source data, estimates and measured evidence.
- Status vocabulary: PASS / FAIL / NOT_TESTED / NOT_APPLICABLE. ERC/DRC does not validate dynamics, thermal performance, EMC or battery safety.
- Build and test commands, source dates, assumptions and procurement/PCB/power-on blockers must be recorded. Do not export manufacturing data from an unrouted PCB.
