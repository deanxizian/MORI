# STM32 HAL Communication Demo

> Official communication demo for Unitree J288/S288 digital servo, based on STM32F413RGT6 HAL library.

## Hardware Requirements

- **MCU**: STM32F413RGT6 (Cortex-M4 with FPU required)
- **UART**: Must support 6 Mbps baud rate
- **Bus mode**: Half-duplex (TTL-to-single-wire adapter required)
- **Wiring**:

| Adapter Pin | STM32 IO | Description |
|-------------|----------|-------------|
| TX/RX | PA9 | Shared half-duplex data line |
| GND | GND | Common ground (mandatory) |

> **Important**: All servos and MCU must share the same GND to avoid packet loss.

## Project Structure

```
firmware/
├── App/
│   ├── protocol.h         # Data structures (MotorCmd_t, MotorData_t, etc.)
│   ├── protocol.c         # modify_data() / extract_data() — float↔fixed conversion
│   └── crc_ccitt.h        # CRC32 lookup-table implementation
├── Core/
│   ├── Inc/               # HAL configuration headers
│   └── Src/
│       ├── main.c              # Main loop: send command → receive feedback
│       ├── usart.c             # USART1 6 Mbps half-duplex init
│       ├── stm32f4xx_it.c      # Interrupt handlers
│       ├── gpio.c              # GPIO init
│       └── stm32f4xx_hal_msp.c # HAL MSP init
├── Drivers/
│   ├── STM32F4xx_HAL_Driver/  # Official HAL library
│   └── CMSIS/                  # CMSIS core headers
├── MDK-ARM/                    # Keil MDK project files
├── .mxproject                  # CubeMX project marker
└── J288-S288__ComDemo.ioc      # CubeMX project config
```

## Build & Flash

1. Open `firmware/MDK-ARM/J288-S288__ComDemo.uvprojx` in Keil MDK.
2. Click **Build** to compile.
3. Connect ST-Link/J-Link debugger.
4. Click **Download** to flash.

## Debugging

Enter Debug mode, open **Watch 1** window (`View → Watch Windows → Watch 1`) and add:

- `cmd` — Motor command struct (to see what you send)
- `data` — Servo feedback struct (to see what you receive)

### Communication health

- `data.timeout == 0` → Normal connection, values refresh.
- `data.timeout` keeps increasing → Wiring issue or servo not responding.

## Control Example

Modify `cmd` fields in Watch window:

1. **Constant speed**: `cmd.mode=1`, `cmd.Kd=1`, `cmd.outputSpd=0.5`
2. **Stop**: `cmd.mode=0`
