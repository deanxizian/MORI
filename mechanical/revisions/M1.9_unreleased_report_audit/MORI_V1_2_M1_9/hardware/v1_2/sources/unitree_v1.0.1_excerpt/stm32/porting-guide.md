# Porting Guide — STM32 to Other MCUs

## 1. MCU Requirements

- **FPU mandatory**: Hardware floating-point unit is required. Floating-point control loops will lag severely without it (F4/F7/H7 series recommended).
- **UART clock**: Must support 6 Mbps baud rate. Verify your UART peripheral clock can generate this rate with acceptable error (< 2%).

## 2. UART Migration

- Replace initialization code in `usart.c` / `usart_it.c` with your target UART.
- Half-duplex mode (`HAL_HalfDuplex_Init` equivalent) is required — do not connect TX and RX independently to the servo bus.
- Data format: 8N1, 6 Mbps.

## 3. Bus Wiring

```
MCU TX/RX ──── TTL-to-Single-Wire Adapter ──── Servo Bus
MCU GND  ───────────────────────────────────── Servo GND
```

You **cannot** connect MCU TX/RX pins directly to the servo — a half-duplex transceiver adapter is required.

## 4. Multi-Servo Control

Cycle `cmd.id` in a loop (0..14) to control multiple servos on the same bus. ID 15 is a broadcast address (no feedback).

```c
for (int id = 0; id < 15; id++) {
    cmd.id = id;
    modify_data(&cmd);
    transmit(...);
    receive(...);
    extract_data(&data);
}
```

## 5. Common Issues

| Symptom | Likely Cause |
|---------|-------------|
| `data.timeout` keeps increasing | GND not shared, TX/RX reversed, baud rate wrong |
| Servo does not respond | `cmd.mode` not set to 1, or voltage mismatch (J288 needs 25.2 V) |
| Feedback values jitter | Increase `Kd`, add shielding, reduce power ripple |
