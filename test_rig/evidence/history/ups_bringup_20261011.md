# Waveshare UPS Module 3S feedback bring-up

Bench work started 2026-10-11 Asia/Shanghai and the final sample window ran
2026-10-12 00:00:46–00:01:16. This is an actual Pi4 bench check, not a
production power-system qualification. The user reports the Pi is powered
through the UPS and the 12.6 V charger is also connected.

## Result

| Check | Status | Evidence |
| --- | --- | --- |
| UPS feedback on I²C-6, address `0x41` | PASS | 60/60 samples, 29.500 s, no read errors; INA219-compatible configuration `0x399f` |
| Voltage measurement readout | PASS | Mean **11.5519 V**, range 11.536–11.560 V |
| Current conversion with the fitted nominal shunt | PASS | User identified **R010**, hence 0.01 Ω; mean **+1.4279 A**, range +1.370–+1.463 A |
| Calculated signed power at the monitored battery path | PASS | Mean **+16.4955 W**, range +15.8043–+16.9123 W |
| IMU communication regression on I²C-1, `0x69` | PASS | Ten ID reads `0x1143` and ten error-register reads `0`; no sensor configuration writes |
| Persistent bus setting saved | PASS | Backed up boot config, appended one overlay, verified file contents |
| Bus available after reboot | NOT_TESTED | Enabled live without reboot; boot setting is saved |
| Meter calibration / measured shunt resistance | NOT_TESTED | R010 is a user-observed component marking, not a resistance measurement |
| Charge/discharge transition and supply interruption | NOT_TESTED | Charger remained connected throughout this test |
| Calibrated state of charge, runtime, automatic shutdown | NOT_TESTED | No SOC model or shutdown service installed |
| Physical J1 level-selection / actual I²C voltage measurement | NOT_TESTED | Earlier wiring instructions specify 3.3 V; successful communication is not a voltage measurement |

The INA219 has no unique identification register. The board identity comes
from the selected hardware and user confirmation; address and register
responses are consistent with its INA219. Positive current here means
`IN+ → IN−`. On the published 2023 schematic that is the battery-charging
direction. With the charger connected and voltage increasing, the readings
are consistent with charging; no unplug/replug direction test was performed.
These current and power values describe the monitored battery path, **not**
the Pi's 5 V input current or Pi-only power. Sequential voltage/shunt reads
are not atomic ADC snapshots.

## Current wiring and Pi configuration

| UPS silkscreen | Pi physical pin | GPIO / function |
| --- | --- | --- |
| SDA | 15 | GPIO22 / SDA6 |
| SCL | 16 | GPIO23 / SCL6 |
| GND | 14 | Ground |

This is the user's confirmed alternate-bus wiring; the earlier optional
I²C-1 branch in `hardware/test_rig/system_diagram_R1` is not the live UPS
connection. The BMI323 remains on I²C-1 and has not been moved.

Live command, executed successfully on `PI4`:

```sh
dtoverlay i2c6 pins_22_23 baudrate=100000
```

Appended under the existing `[all]` section in `/boot/firmware/config.txt`:

```ini
# MORI bench UPS Module 3S: physical 15 SDA / 16 SCL / 14 GND
dtoverlay=i2c6,pins_22_23,baudrate=100000
```

Backup on the Pi:
`/root/mori-bringup/ups3s-20261011/config.txt.before-i2c6-20261011T155502Z`.
The prior complete config, before/after hashes and actual commands are in
`01_enable_i2c6_execution.json` and `04_persist_execution.json`.

## Read again

The standalone reader is deployed at
`/root/mori-bringup/ups3s-20261011/read_ups.py`:

```sh
ssh PI4 python3 /root/mori-bringup/ups3s-20261011/read_ups.py --shunt-ohm 0.01 --samples 20
```

It reads raw registers without changing INA219 configuration or calibration.
The calibration register remains `0x0000`; current/power hardware registers
therefore must not be interpreted as valid measurements. Instead:

- `Vshunt = signed16(register 1) × 10 µV`.
- `Vbus = (register 2 >> 3) × 4 mV`.
- `I = Vshunt / 0.01 Ω`; `P = Vbus × I`.

The reader requires an explicit `--shunt-ohm` to calculate current/power.
Without it, voltage can still be read, but current conversion is `BLOCKED`.
No persistent polling process or service is left running.

Actual runtime: Pi4, kernel `6.18.50+rpt-rpi-v8`, Python 3.13.5,
`smbus2` 0.4.3. Source hash and execution command are in
`07_final_execution.json`; all 60 final samples are in `07_final_read.json`.
Final GPIO, bus listing, uptime and throttling flags are in
`08_final_system.json`.

## Correction of the first current estimate

The archived first script used **0.1 Ω**, as shown for R27 in the older
official schematic. It returned about **0.148 A / 1.68 W**. The current
official V2 example instead uses **0.01 Ω**. The user then inspected the
highlighted resistor on the actual unit and confirmed **R010**.

Consequently, the initial current/power figures are **FAIL / superseded**:
they were ten times too small. The original raw register/voltage samples
remain valid and are retained unchanged in `02_read.json`; do not use its
derived current/power as the final result. The exact historical script is
in `history/read_ups_initial_0p1_assumption.py`. The discrepancy and physical
confirmation are in `05_shunt_discrepancy.json` and
`06_physical_confirmation.json`. No exact PCB revision is inferred from the
resistor marking alone.

## Sources

- [TI INA219 datasheet, SBOS448G](https://www.ti.com/lit/ds/symlink/ina219.pdf),
  sections 8.5.6 and 8.6.3: register format and voltage scaling.
- Official schematic retained at
  `hardware/test_rig/specifications/03_Waveshare_UPS_3S/UPS_3S_schematic.pdf`:
  R27 = 0.1 Ω in that document. SHA256
  `ea654047e0c8ae1b8128ecf878ae69e976646ea504c1e6619432751eb452a3b2`.
- [Official V2 example archive](https://files.waveshare.com/wiki/UPS%20Module%203S/UPS_Module_3S_V2%20%281%29.zip):
  `set_calibration_16V_5A` uses 0.01 Ω. Retrieved source is kept in
  `vendor_reference/INA219.py`; archive provenance/hash is in `source.txt`.
  This vendor example was inspected only and was not executed.
- [Official component photograph](https://www.waveshare.com/img/devkit/accBoard/UPS-Module-3S/UPS-Module-3S-details-7.jpg)
  was used to guide the user to the resistor. It is not a photograph of the
  user's particular board. The annotated illustration is a locator only.

This task changed only its bring-up artifacts and the documented Pi overlay
setting. Production electronics, mechanical files, contracts and motor
controls were not modified.
