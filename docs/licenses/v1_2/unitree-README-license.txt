# Unitree J288 / S288 Digital Servo — Communication Examples

> [**中文版 README**](./README.zh-CN.md)

> Official communication demos for [Unitree J288/S288 brushless joint servo](https://www.unitree.com/en/DigitalServo).

This repository contains two independent reference implementations built on the same communication protocol, enabling PC-based testing and embedded integration.

## Quick Start

| Platform | Path | Description |
|----------|------|-------------|
| **Python** (PC) | [`python/`](./python/) | Interactive serial terminal for testing / debugging |
| **STM32** (Embedded) | [`stm32/`](./stm32/) | Keil MDK project for STM32F413RGT6 HAL integration |

## Protocol Specification

The servo uses a half-duplex TTL bus (8N1, 6 Mbps). See [`specs/protocol.md`](./specs/protocol.md) for the full packet format, CRC32 algorithm, and float-to-fixed conversion formulas.

| Parameter | Range | Description |
|-----------|-------|-------------|
| Bus ID | 0 – 15 | Up to 16 servos on one bus (15 = broadcast) |
| Baudrate | 6,000,000 bps | Fixed, not configurable |
| Control packet | 20 bytes | `0xFE 0xEE` header + mode + params + CRC32 |
| Feedback packet | 26 bytes | `0xFC 0xEE` header + mode + status + CRC32 |
| Gear ratio | 288.35 : 1 | `70070.0 / 243.0` |

## Repository Structure

```
digital_servo/
├── README.md                # This file — project overview
├── specs/
│   └── protocol.md          # Shared protocol specification
├── python/
│   ├── README.md            # Python demo usage
│   ├── requirements.txt     # pyserial dependency
│   └── servo_demo.py        # Interactive control terminal
└── stm32/
    ├── README.md            # STM32 demo usage
    ├── porting-guide.md     # MCU / UART migration notes
    └── firmware/            # Keil MDK project (STM32F413RGT6)
        ├── App/             # Protocol encapsulation (protocol.c/h, crc_ccitt.h)
        ├── Core/            # HAL-generated code (main, usart, gpio, it)
        ├── Drivers/         # STM32F4xx HAL + CMSIS
        ├── MDK-ARM/         # Keil project files (.uvprojx)
        ├── .mxproject
        └── J288-S288__ComDemo.ioc
```

## License

Provided by Unitree for non-commercial research, education, and DIY development.
For commercial mass-production use, contact Unitree official for formal authorization.
