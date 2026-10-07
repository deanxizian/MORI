# V1.2 source index recovery

The original user-supplied `REFERENCES.md` and its S01–S08 mapping were **not supplied**. This file was added during archive review on 2026-10-07. The table is a contextual cross-reference to the recorded HW12 source catalogue, not a claim that the original mapping was recovered or that any hardware was measured.

| Spec marker | Context in the specification | Recorded reference |
|---|---|---|
| S01 | S288 nominal specifications | [Unitree S288 current Chinese specifications](https://www.unitree.com/cn/DigitalServo/); [Unitree J288/S288 manual](https://www.unitree.com/images/无刷数字舵机J288S288使用手册.pdf) |
| S02 | S288 protocol example | [Unitree digital_servo v1.0.1](https://github.com/unitreerobotics/digital_servo/archive/refs/tags/v1.0.1.zip) |
| S03 | SCS0009 interfaces | [FEETECH SCS0009 A/0 2020-11-23](https://www.feetech.cn/Data/feetechrc/upload/file/20220915/6379883463905538176347522.pdf) |
| S04 | CAM33700 | [Waveshare CAM SKU33700](https://docs.waveshare.com/ESP32-S3-CAM-OVxxxx); [Waveshare CAM schematic](https://files.waveshare.com/wiki/ESP32-S3-CAM-OVxxxx/ESP32-S3-CAM-XXXX-schematic.pdf) |
| S05 | LCD35079 | [Waveshare LCD SKU35079](https://docs.waveshare.com/1.85inch_Touch_LCD_Module) |
| S07 | ICM-42688-P | [TDK DS000347 ICM42688P](https://www.lcsc.com/datasheet/C1850418.pdf) |
| S06 | Not cited in the supplied V1.2 specification | Original meaning unknown; no replacement invented. |
| S08 | Charging architecture / rejection of old 2S design | Original reference unknown; no final 3S charger qualification is implied. See the current electrical contract and procurement blockers. |

[Full source catalogue](hardware/v1_2/sources/index.json) contains access dates, source IDs and original limitations. [Software source lock](software/references_v1_2.lock.json) pins protocol/example code. Manufacturer nominal values and archived reviews do not establish availability, current pricing, physical fit or electrical qualification.
