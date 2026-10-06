# MORI V1.2 mechanical candidate release

Open mechanical/index.html for the actual Blender gallery and all parts. Editable model: mechanical/mori_v1_2.blend. Report: reports/mechanical_v1_2.md. Rebuild: python3 mechanical/scripts/run_all.py; see mechanical/README.md for platform dependencies.

M1 complete, M2 partially complete and vendor interfaces blocked, M3 candidate files generated. The full vendor LCD STEP is imported1:1; CAM board outline is documented, populated height remains unknown. Two connector tessellations require conservative collision proxies; exact complete hardware fit remains BLOCKED. Unknown purchased modules remain allocations. Shared inputs: config/geometry.json and contracts/mechanical_interfaces.json. The hardware-owned components.json is an unchanged read-only snapshot; new dimensional facts are handed off through ADR-MECH-013.

This package contains current mechanical evidence only. Previous A4 revisions and unrelated software/hardware stay in the original MORI project. No purchase, PCB freeze or balance validation is claimed.

M1.9 rotates the two wheel motors90deg about unchanged grounded axes, lowers battery/deck12mm and places the inverted yaw CASE inside the yaw-only head frame. A removable D-key reaction link restrains the output/horn to the body; the independent bearing and open bridge carry the head weight. A separate power carrier supports an80x40x18mm capacity allocation, NOT a measured S3 PCB. Read belly_relayout_validation.json and ADR-MECH-021 for checks, servicing and changed servo sign/IMU orientation. Actual horn, PCB fixation, connectors, printed strength and balancing remain unqualified. Prior M1.8 is included as immutable comparison evidence. Original outer geometry, centred LCD and independent forehead camera remain. Nominal282mm height meets300mm product ceiling.

