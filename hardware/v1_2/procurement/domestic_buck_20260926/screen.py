#!/usr/bin/env python3
"""Reproducible selection arithmetic, not a hardware qualification test.

Reads MORI's assumed power table; writes only this research directory.
Unknown prices remain None. A 25% screening margin is an explicit assumption.
"""
import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
V12 = HERE.parents[1]
POWER = V12 / "reports" / "power_states.csv"
with POWER.open(newline="", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
peak = next(r for r in rows if r["state"] == "concurrent_peak")
loads = {"wheel": float(peak["wheel_W"]), "head": float(peak["head6V_W"])}
volts = {"wheel": (9.0, 8.09), "head": (6.0, 5.21)}
margin = 1.25

def rnd(value):
    return round(value, 6)

rails = {}
for key, power in loads.items():
    nominal, old_low = volts[key]
    rails[key] = {
        "assumed_peak_load_W": power,
        "nominal_module_V": nominal,
        "nominal_peak_current_A": rnd(power / nominal),
        "old_reference_low_load_voltage_V": old_low,
        "low_voltage_sensitivity_current_A": rnd(power / old_low),
        "screening_current_with_25percent_margin_A": rnd(power / old_low * margin),
        "required_continuous_current_measured_A": None,
        "peak_duration_measured_s": None,
        "status": "NOT_TESTED",
    }

candidate_data = json.loads((HERE / "candidates.json").read_text())
by_id = {c["id"]: c for c in candidate_data["candidates"]}
prices = [by_id[k]["price_cny"] for k in candidate_data["recommended_screening_pair"]]

result = {
    "date": "2026-09-26",
    "evidence": "ASSUMED; calculations only; not measured",
    "input_power_table": str(POWER.relative_to(V12)),
    "input_sha256": hashlib.sha256(POWER.read_bytes()).hexdigest(),
    "source_row_status": peak["status"],
    "assumptions": [
        "Historical peak powers treated as endpoint loads for sensitivity screening",
        "8.09V and 5.21V are old Pololu/diode model endpoints, not candidate specifications",
        "1.25 multiplier is a proposed screening margin, not a mandated standard",
        "Input headroom excludes battery-to-module wiring, switch, fuse and shunt drops",
        "Loss examples use hypothetical efficiency, excluding downstream diode/FET losses",
    ],
    "rails": rails,
    "wheel_headroom": [
        {"module_input_V": vin, "output_V": 9, "gross_headroom_V": rnd(vin - 9),
         "dfrobot_dfr1015_approx_2V_headroom_met": vin - 9 >= 2}
        for vin in (9.9, 10.2, 10.8, 11.1, 12.6)
    ],
    "hypothetical_peak_conversion_losses": [
        {"efficiency_assumed": eta,
         "wheel_W": rnd(loads["wheel"] * (1 / eta - 1)),
         "head_W": rnd(loads["head"] * (1 / eta - 1)),
         "total_W": rnd(sum(loads.values()) * (1 / eta - 1))}
        for eta in (0.85, 0.90, 0.95)
    ],
    "head_added_vendor_mass_g": [rnd(m - 2.3) for m in (11, 11.5)],
    "recommended_pair_price_cny": sum(prices) if all(p is not None for p in prices) else None,
    "shipping_adaptation_heatsink_cost_cny": None,
    "savings_vs_original_cny": None,
    "procurement_release": "BLOCKED",
    "physical_tests": "NOT_TESTED",
}
out = HERE / "screening.json"
out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"output": str(out), "rails": rails, "procurement_release": "BLOCKED"}, ensure_ascii=False, indent=2))
