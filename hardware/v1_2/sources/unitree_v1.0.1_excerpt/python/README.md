# Python Serial Communication Demo

> Interactive serial terminal for Unitree J288/S288 digital servo via pyserial.

## Prerequisites

```bash
pip install pyserial
```

## Quick Start

1. Connect PC serial adapter (USB-to-TTL) to the servo bus, power on the servo.
2. Identify your serial port:
   - Windows: `COM3`, `COM4` (check Device Manager)
   - Linux: `/dev/ttyUSB0`, `/dev/ttyACM0`
   - macOS: `/dev/tty.usbserial-xxxx`
3. Edit the `SERIAL_PORT` variable in `servo_demo.py` to match your port.
4. Run:

```bash
python servo_demo.py
```

5. Send commands interactively:

```
> send 0 1 0 0.0 0.5 0.0 0.0 1.0
```

### Command format

```
send <id> <mode> <timeout> <torque> <speed> <position> <Kp> <Kd>
```

### Examples

| Action | Command |
|--------|---------|
| Constant speed (0.5 rad/s) | `send 0 1 0 0.0 0.5 0.0 0.0 1.0` |
| Stop servo | `send 0 0 0 0.0 0.0 0.0 0.0 0.0` |
| Quit | `quit` |

## Timeout Behavior

- `timeout=1`: servo executes command once, keeps state for ~1 s. Requires continuous frame transmission.
- `timeout=0`: servo holds the command persistently.

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| Cannot open port | `sudo chmod 666 /dev/ttyUSB0` (Linux), check port number (Windows) |
| No feedback | Check TX/RX wiring, verify baud rate = 6 Mbps, check power supply |
| Servo stops early | timeout=1 requires continuous command frames |
