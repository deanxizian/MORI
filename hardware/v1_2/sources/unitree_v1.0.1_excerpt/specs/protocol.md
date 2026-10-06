# Unitree J288/S288 Digital Servo — Communication Protocol Specification

## 1. Physical Layer

| Property | Value |
|----------|-------|
| Interface | Half-duplex TTL multi-drop bus |
| Baudrate | 6,000,000 bps (fixed) |
| Frame format | 8N1 (8 data bits, 1 stop bit, no parity) |
| Bus capacity | Up to 16 servos (ID 0–15, ID 15 = broadcast, no response) |
| Gear ratio (RATIO) | `70070.0 / 243.0 ≈ 288.35` |

## 2. Control Packet (Host → Servo) — 20 bytes

```
Offset  Size  Field       Description
────────────────────────────────────────
 0       2    head        0xFE 0xEE (packet start marker)
 2       1    mode_byte   Bitfield: [3:0]=id, [6:4]=mode, [7]=timeout
 3       1    reserved    Always 0x00
 4      12    comd        Control parameters (see below)
16       4    CRC32       CRC-32 checksum (polynomial 0x04C11DB7)
```

### Mode byte structure

| Bits | Field | Values |
|------|-------|--------|
| [3:0] | id | 0–15 (target servo ID) |
| [6:4] | mode | 0 = stop & lock torque; 1 = hybrid closed-loop |
| [7] | timeout | 0 = disable timeout protection; 1 = enable |

### Control parameters (comd, 12 bytes, little-endian)

| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | int16 | tor_des | Target rotor torque (raw) |
| 2 | int16 | spd_des | Target rotor speed (raw) |
| 4 | int32 | pos_des | Target rotor position (raw) |
| 8 | int16 | k_pos | Stiffness proportional gain (raw) |
| 10 | int16 | k_spd | Damping differential gain (raw) |

### Float → Fixed conversion formulas

```
k_pos    = Kp / (RATIO²) × 1_280_000       Range: 0 – 2128.523  → 0..32767
k_spd    = Kd / (RATIO²) × 128_000_000     Range: 0 – 21.285    → 0..32767
pos_des  = outputPos  × RATIO × 32768 / π / 2   Range: ±1428.019 → ±2³¹
spd_des  = outputSpd  × RATIO × 2.560 / π / 2   Range: ±278.901 → ±32767
tor_des  = outputTor  / RATIO × 256_000          Range: ±36.909  → ±32767
```

## 3. Feedback Packet (Servo → Host) — 26 bytes

```
Offset  Size  Field       Description
────────────────────────────────────────
 0       2    head        0xFC 0xEE (packet start marker)
 2       1    mode_byte   Bitfield: same layout as control packet
 3      19    fbk         Feedback data (see below)
22       4    CRC32       CRC-32 checksum (polynomial 0x04C11DB7)
```

### Feedback data (fbk, 19 bytes, little-endian)

| Offset | Type | Name | Description |
|--------|------|------|-------------|
| 0 | int8 | temp | Shell temperature (-128–127 °C) |
| 1 | uint8 | sensor | Winding temperature (0–255 °C) |
| 2 | uint16 | vol | Supply voltage (raw, value/2 = volts) |
| 4 | int16 | torque | Rotor torque (raw) |
| 6 | int16 | speed | Rotor speed (raw) |
| 8 | int32 | pos | Rotor position (raw) |
| 12 | uint32 | MError | Hardware error code |
| 16 | uint16 | OutPos : 13 | Output position (lower 13 bits) |
| 16 | uint16 | ExFlag : 3 | Warning flag (upper 3 bits) |
| 18 | uint8 | ExSensor2 | Reserved |
| 19 | uint8 | ExCom | Extended communication |

### Raw → Physical conversion

```
vol       = raw_vol / 2.0                              (V)
ExPos     = 2π × OutPos / 8192.0                       (rad)
outputSpd = (speed / 2.56) × 2π / RATIO                (rad/s)
outputTor = (torque / 256000.0) × RATIO                 (N·m)
outputPos = 2π × pos / 32768.0 / RATIO                  (rad)
```

## 4. CRC-32

- Polynomial: `0x04C11DB7` (same as IEEE 802.3, but bit-reversed processing)
- Initial value: `0xFFFFFFFF`
- Lookup table (256 entries) is included in both implementations:
  - Python: `CRC32_TABLE` in `servo_demo.py`
  - STM32: `crc32_table[]` in `crc_ccitt.h`

### CRC scope

| Packet | CRC covers |
|--------|------------|
| Control (20 B) | bytes 0–15 (head + mode + reserved + comd) |
| Feedback (26 B) | bytes 2–21 (mode + fbk) — excludes head |

## 5. Parameter Ranges

| Parameter | Min | Max | Description |
|-----------|-----|-----|-------------|
| id | 0 | 15 | Servo bus ID |
| mode | 0 | 1 | 0=stop, 1=hybrid closed-loop |
| timeout | 0 | 1 | Timeout protection |
| outputTor | -36.909 | 36.908 | Target torque (N·m) |
| outputSpd | -278.902 | 278.902 | Target speed (rad/s) |
| outputPos | -1428.019 | 1428.019 | Target position (rad) |
| Kp | 0 | 2128.523 | Stiffness gain |
| Kd | 0 | 21.285 | Damping gain |
