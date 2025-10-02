# Rigol DG800/DG900 Controller (with a gui, eventually)

Python library for remote control of Rigol DG800 and DG900 series arbitrary function generators via VISA interface.

## Requirements

```bash
pip install pyvisa pyvisa-py numpy
```

## Connection

### Auto-detect device
```python
from rigol_dg import RigolDG

gen = RigolDG()  # Shows list of available devices
```

### Direct connection
```python
# USB connection
gen = RigolDG('USB0::0x1AB1::0x0642::DG9A12345678::INSTR')

# LAN connection
gen = RigolDG('TCPIP0::192.168.1.100::INSTR')
```

## Basic Functions

### Standard waveforms
```python
# Sine wave 1 kHz, 2 Vpp
gen.set_function(1, "SIN")
gen.set_frequency(1, 1000)
gen.set_amplitude(1, 2)
gen.set_offset(1, 0)
gen.output_on(1)

# Square wave 50% duty cycle
gen.set_function(1, "SQU")
gen.set_duty_cycle(1, 50)

# Triangular ramp
gen.create_ramp(1, freq=100, symmetry=50)
```

### Available waveforms
- `SIN` - Sine wave
- `SQU` - Square wave
- `RAMP` - Ramp/triangular
- `PULSE` - Pulse
- `NOIS` - Noise
- `ARB` - Arbitrary
- `DC` - DC

## Modulation

### Amplitude Modulation (AM)
```python
gen.set_am_modulation(1, depth=50, freq=100)
```

### Frequency Modulation (FM)
```python
gen.set_fm_modulation(1, deviation=1000, freq=10)
```

### Disable modulation
```python
gen.modulation_off(1)
```

## Arbitrary Waveforms

### Create from Python array
```python
import numpy as np

# Create sinc waveform
t = np.linspace(-np.pi, np.pi, 1000)
sinc_wave = np.sinc(t)
gen.create_arb_waveform(1, sinc_wave.tolist(), name="SINC")
gen.load_arb_waveform(1, "SINC")

# Custom waveform
data = [0, 0.5, 1.0, 0.5, 0, -0.5, -1.0, -0.5]
gen.create_arb_waveform(1, data, name="CUSTOM")
gen.set_arb_sample_rate(1, 1e6)  # 1 MSa/s
```

### Load from CSV file

```python
# Load with automatic normalization
num_points = gen.load_arb_from_csv(1, "waveform.csv", name="MY_WAVE")
print(f"Loaded {num_points} points")
gen.load_arb_waveform(1, "MY_WAVE")
```

### Convert WAV audio to CSV

```python
from rigol_dg import wav_to_csv

# Convert WAV file to CSV (with automatic downsampling to 8k points)
info = wav_to_csv("audio.wav", "waveform.csv", max_points=8192)

print(f"Exported: {info['num_points']} points")
print(f"Duration: {info['duration']:.3f} seconds")
print(f"Suggested sample rate: {info['suggested_sample_rate']:.0f} Sa/s")

# Load the converted waveform into generator
gen.load_arb_from_csv(1, "waveform.csv", name="AUDIO", normalize=False)
gen.set_arb_sample_rate(1, info['suggested_sample_rate'])
gen.load_arb_waveform(1, "AUDIO")
```

**WAV conversion options:**
- `max_points`: Limit output points (e.g., 8192, 16384) - automatically downsamples
- `channel`: Select audio channel (0=left/mono, 1=right) for stereo files
- `normalize`: Normalize amplitude to ±1 (default: True)

**Supported WAV formats:**
- 8-bit, 16-bit, 24-bit, 32-bit PCM
- Mono or stereo (multi-channel)
- Any sample rate

#### Supported CSV formats

**1. One column (amplitude only)**
```csv
0.0
0.309
0.588
0.809
1.0
```

**2. Two columns (time, amplitude)**
```csv
0.000, 0.0
0.001, 0.309
0.002, 0.588
0.003, 0.809
0.004, 1.0
```

**3. With header**
```csv
time,voltage
0.000, 0.0
0.001, 0.309
0.002, 0.588
```

**Notes:**
- Automatic normalization scales values between -1 and +1
- Maximum points: 8k-16k (depends on model)
- Supported separators: comma, semicolon

### Manage saved waveforms
```python
# List waveforms in memory
waveforms = gen.get_arb_list()
print(waveforms)

# Delete waveform
gen.delete_arb_waveform("OLD_WAVE")
```

## Advanced Functions

### Burst
```python
# Burst of 10 sine cycles at 1 kHz
gen.create_sine_burst(1, cycles=10, freq=1000, ampl=2)
```

### Custom pulses
```python
# 1ms pulse, 10ms period, 10ns edge time
gen.create_custom_pulse(1, width=1e-3, period=10e-3, edge_time=10e-9)
```

## Read Status

```python
# Read current parameters
freq = gen.get_frequency(1)
ampl = gen.get_amplitude(1)
func = gen.get_function(1)
is_on = gen.is_output_on(1)

print(f"Frequency: {freq} Hz")
print(f"Amplitude: {ampl} Vpp")
print(f"Function: {func}")
print(f"Output: {'ON' if is_on else 'OFF'}")
```

## Output Configuration

```python
# Set load impedance
gen.set_output_load(1, 50)      # 50 Ω
gen.set_output_load(1, 'INF')   # High impedance
```

## Units of Measurement

| Parameter | Unit | Example |
|-----------|------|---------|
| Frequency | Hz | `1000` = 1 kHz |
| Amplitude | Vpp (Volt peak-to-peak) | `2` = 2 Vpp |
| Offset | V (Volt) | `0.5` = +0.5V DC |
| Phase | Degrees | `90` = 90° |
| Duty cycle | % | `50` = 50% |
| Time | Seconds | `1e-3` = 1 ms |
| Sample rate | Sa/s | `1e6` = 1 MSa/s |
| Impedance | Ω (Ohm) | `50` = 50Ω |

## Complete Example

```python
from rigol_dg import RigolDG

# Connection
gen = RigolDG()

try:
    # Reset instrument
    gen.reset()

    # Channel 1: 1 kHz sine wave with AM modulation
    gen.set_function(1, "SIN")
    gen.set_frequency(1, 1000)
    gen.set_amplitude(1, 2)
    gen.set_offset(1, 0)
    gen.set_am_modulation(1, depth=50, freq=10)
    gen.output_on(1)

    # Channel 2: Arbitrary waveform from CSV
    points = gen.load_arb_from_csv(2, "my_waveform.csv", name="CUSTOM")
    gen.load_arb_waveform(2, "CUSTOM")
    gen.set_arb_sample_rate(2, 1e6)
    gen.set_amplitude(2, 3)
    gen.output_on(2)

    # Verify configuration
    print(f"\nChannel 1: {gen.get_function(1)}, {gen.get_frequency(1)} Hz")
    print(f"Channel 2: {gen.get_function(2)}, {points} points loaded")

    input("\nPress ENTER to exit...")

finally:
    # Close connection
    gen.close()
```

## References

- **Supported models:** Rigol DG800, DG900, DG1000Z, DG4000, DG5000
- **Protocol:** SCPI (Standard Commands for Programmable Instruments)
- **Interfaces:** USB, LAN (Ethernet), GPIB (with adapter)

## Notes

- Always call `gen.close()` at the end of the session
- Arbitrary waveforms must have values between -1 and +1
- Check your model's limits (max frequency, ARB points, etc.)
- For complex waveforms, use adequate sample rate to avoid aliasing

## License

Code provided "as-is" for educational and laboratory use.
