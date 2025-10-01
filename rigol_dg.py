#!/usr/bin/env python3
"""
Controller for Rigol DG800/DG900 generators
Requires: pip install pyvisa pyvisa-py
"""

import pyvisa as visa
import numpy as np

class RigolDG:
    def __init__(self, resource_name=None):
        """
        Initialize connection to Rigol DG800/DG900 generator

        Args:
            resource_name: VISA device identification string
                          Ex: 'USB0::0x1AB1::0x0642::DG9A12345678::INSTR'
                          Ex: 'TCPIP0::192.168.1.100::INSTR'
                          If None, shows list of available devices
        """
        # Initialize VISA ResourceManager with PyVISA-py backend
        self.rm = visa.ResourceManager('@py')

        # If not specified, auto-detect devices
        if resource_name is None:
            resources = self.rm.list_resources()
            print("Devices found:")
            for i, res in enumerate(resources):
                print(f"{i}: {res}")

            if not resources:
                raise Exception("No VISA devices found")

            idx = int(input("Select device (number): "))
            resource_name = resources[idx]

        # Open connection with 5 second timeout
        self.instr = self.rm.open_resource(resource_name)
        self.instr.timeout = 5000
        print(f"Connected: {self.identify()}")

    def identify(self):
        """
        Identify the instrument via SCPI command *IDN?

        Returns:
            str: Identification string (manufacturer, model, serial, firmware)
        """
        return self.instr.query("*IDN?").strip()

    def reset(self):
        """
        Resets the instrument to factory defaults
        SCPI command: *RST
        """
        self.instr.write("*RST")

    # === CHANNEL CONTROL ===

    def set_function(self, channel, func):
        """
        Sets the waveform type for the specified channel

        Args:
            channel: Channel number (1 or 2)
            func: Waveform type - allowed values:
                  'SIN'   - Sine wave
                  'SQU'   - Square wave
                  'RAMP'  - Ramp/triangular
                  'PULSE' - Pulse
                  'NOIS'  - Noise
                  'ARB'   - Arbitrary
                  'DC'    - DC
        """
        self.instr.write(f"SOUR{channel}:FUNC {func}")

    def set_frequency(self, channel, freq):
        """
        Sets the signal frequency

        Args:
            channel: Channel number (1 or 2)
            freq: Frequency in Hz (range depends on model and waveform)
        """
        self.instr.write(f"SOUR{channel}:FREQ {freq}")

    def set_frequency_khz(self, channel, freq_khz):
        """
        Sets the signal frequency in kHz

        Args:
            channel: Channel number (1 or 2)
            freq_khz: Frequency in kHz
        """
        freq_hz = freq_khz * 1000
        self.instr.write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_frequency_mhz(self, channel, freq_mhz):
        """
        Sets the signal frequency in MHz

        Args:
            channel: Channel number (1 or 2)
            freq_mhz: Frequency in MHz
        """
        freq_hz = freq_mhz * 1000000
        self.instr.write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_frequency_with_unit(self, channel, value, unit):
        """
        Sets frequency with specified unit

        Args:
            channel: Channel number (1 or 2)
            value: Numeric frequency value
            unit: Unit of measurement ('HZ', 'KHZ', 'MHZ')
        """
        if unit.upper() == 'HZ':
            freq_hz = value
        elif unit.upper() == 'KHZ':
            freq_hz = value * 1000
        elif unit.upper() == 'MHZ':
            freq_hz = value * 1000000
        else:
            raise ValueError(f"Unsupported unit: {unit}. Use 'HZ', 'KHZ', or 'MHZ'")

        self.instr.write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_amplitude(self, channel, ampl):
        """
        Sets the signal amplitude

        Args:
            channel: Channel number (1 or 2)
            ampl: Amplitude in Vpp (Volt peak-to-peak)
                  Typical range: 1mVpp - 10Vpp (depends on load)
        """
        self.instr.write(f"SOUR{channel}:VOLT {ampl}")

    def set_amplitude_dbm(self, channel, dbm_value):
        """
        Sets the signal amplitude in dBm (for 50Ω load)

        Args:
            channel: Channel number (1 or 2)
            dbm_value: Power in dBm
                      Typical range: -40 dBm to +20 dBm (depends on model)
        """
        self.instr.write(f"SOUR{channel}:VOLT:UNIT DBM")
        self.instr.write(f"SOUR{channel}:VOLT {dbm_value}")

    def set_amplitude_unit(self, channel, unit):
        """
        Sets the unit of measurement for amplitude

        Args:
            channel: Channel number (1 or 2)
            unit: Unit of measurement
                  'VPP' - Volt peak-to-peak
                  'VRMS' - Volt RMS
                  'DBM' - dBm (for 50Ω load)
        """
        self.instr.write(f"SOUR{channel}:VOLT:UNIT {unit}")

    def get_amplitude_unit(self, channel):
        """
        Gets the current unit of measurement for amplitude

        Args:
            channel: Channel number (1 or 2)

        Returns:
            str: Current unit ('VPP', 'VRMS', 'DBM')
        """
        return self.instr.query(f"SOUR{channel}:VOLT:UNIT?").strip()

    def set_offset(self, channel, offset):
        """
        Sets the DC offset of the signal

        Args:
            channel: Channel number (1 or 2)
            offset: Offset in Volts (can be positive or negative)
        """
        self.instr.write(f"SOUR{channel}:VOLT:OFFS {offset}")

    def set_phase(self, channel, phase):
        """
        Sets the signal phase

        Args:
            channel: Channel number (1 or 2)
            phase: Phase in degrees (0-360°)
        """
        self.instr.write(f"SOUR{channel}:PHAS {phase}")

    def set_duty_cycle(self, channel, duty):
        """
        Sets the duty cycle for square wave

        Args:
            channel: Channel number (1 or 2)
            duty: Duty cycle in percentage (typically 0.01% - 99.99%)
                  50% = symmetric square wave
        """
        self.instr.write(f"SOUR{channel}:FUNC:SQU:DCYC {duty}")

    # === OUTPUT CONTROL ===

    def output_on(self, channel):
        """
        Enables the output of the specified channel

        Args:
            channel: Channel number (1 or 2)
        """
        self.instr.write(f"OUTP{channel} ON")

    def output_off(self, channel):
        """
        Disables the output of the specified channel

        Args:
            channel: Channel number (1 or 2)
        """
        self.instr.write(f"OUTP{channel} OFF")

    def set_output_load(self, channel, load):
        """
        Sets the output load impedance

        Args:
            channel: Channel number (1 or 2)
            load: Impedance in Ohms (e.g. 50) or 'INF' for high impedance
                  The load affects the actual signal amplitude
        """
        self.instr.write(f"OUTP{channel}:LOAD {load}")

    def set_50ohm_dbm_mode(self, channel):
        """
        Quickly configures the channel for RF measurements:
        - Load impedance 50Ω
        - Amplitude unit in dBm

        Args:
            channel: Channel number (1 or 2)
        """
        self.set_output_load(channel, "50")
        self.set_amplitude_unit(channel, "DBM")

    # === QUERY (STATUS READING) ===

    def get_frequency(self, channel):
        """
        Reads the current frequency of the channel

        Args:
            channel: Channel number (1 or 2)

        Returns:
            float: Frequency in Hz
        """
        return float(self.instr.query(f"SOUR{channel}:FREQ?"))

    def get_amplitude(self, channel):
        """
        Reads the current amplitude of the channel

        Args:
            channel: Channel number (1 or 2)

        Returns:
            float: Amplitude in Vpp
        """
        return float(self.instr.query(f"SOUR{channel}:VOLT?"))

    def get_function(self, channel):
        """
        Reads the current waveform of the channel

        Args:
            channel: Channel number (1 or 2)

        Returns:
            str: Waveform type (SIN, SQU, RAMP, etc.)
        """
        return self.instr.query(f"SOUR{channel}:FUNC?").strip()

    def is_output_on(self, channel):
        """
        Checks if the output is active

        Args:
            channel: Channel number (1 or 2)

        Returns:
            bool: True if active, False if inactive
        """
        return self.instr.query(f"OUTP{channel}?").strip() == "ON"

    # === MODULATION ===

    def set_am_modulation(self, channel, depth, freq):
        """
        Enables amplitude modulation (AM)

        Args:
            channel: Channel number (1 or 2)
            depth: Modulation depth in % (0-120)
            freq: Modulating frequency in Hz
        """
        self.instr.write(f"SOUR{channel}:AM:STAT ON")
        self.instr.write(f"SOUR{channel}:AM:DEPT {depth}")
        self.instr.write(f"SOUR{channel}:AM:INT:FREQ {freq}")

    def set_fm_modulation(self, channel, deviation, freq):
        """
        Enables frequency modulation (FM)

        Args:
            channel: Channel number (1 or 2)
            deviation: Frequency deviation in Hz
            freq: Modulating frequency in Hz
        """
        self.instr.write(f"SOUR{channel}:FM:STAT ON")
        self.instr.write(f"SOUR{channel}:FM:DEV {deviation}")
        self.instr.write(f"SOUR{channel}:FM:INT:FREQ {freq}")

    def modulation_off(self, channel):
        """
        Disables all modulations (AM, FM, PM)

        Args:
            channel: Channel number (1 or 2)
        """
        self.instr.write(f"SOUR{channel}:AM:STAT OFF")
        self.instr.write(f"SOUR{channel}:FM:STAT OFF")
        self.instr.write(f"SOUR{channel}:PM:STAT OFF")

    # === ARBITRARY WAVEFORMS ===

    def create_arb_waveform(self, channel, data, name=None):
        """
        Creates a custom arbitrary waveform

        Args:
            channel: Channel number (1 or 2)
            data: List of normalized values between -1.0 and +1.0
                  Ex: [0, 0.5, 1.0, 0.5, 0, -0.5, -1.0, -0.5]
            name: Name to assign to the waveform (optional)
                  If None, loads directly into volatile memory
        """
        # Convert data to CSV string format for SCPI command
        data_str = ",".join([str(v) for v in data])

        if name:
            # Save with name in non-volatile memory
            self.instr.write(f"DATA:DAC VOLATILE,{data_str}")
            self.instr.write(f"DATA:COPY {name},VOLATILE")
        else:
            # Load directly into volatile memory
            self.instr.write(f"SOUR{channel}:DATA VOLATILE,{data_str}")

    def load_arb_waveform(self, channel, name):
        """
        Loads a previously saved arbitrary waveform

        Args:
            channel: Channel number (1 or 2)
            name: Name of the waveform to load
        """
        self.instr.write(f"SOUR{channel}:FUNC ARB")
        self.instr.write(f"SOUR{channel}:FUNC:ARB {name}")

    def get_arb_list(self):
        """
        Returns list of arbitrary waveforms saved in memory

        Returns:
            list: List of available waveform names
        """
        return self.instr.query("DATA:CAT?").strip().split(',')

    def delete_arb_waveform(self, name):
        """
        Deletes an arbitrary waveform from memory

        Args:
            name: Name of the waveform to delete
        """
        self.instr.write(f"DATA:DEL {name}")

    def set_arb_sample_rate(self, channel, rate):
        """
        Sets the sample rate for the arbitrary waveform

        Args:
            channel: Channel number (1 or 2)
            rate: Sample rate in Sa/s (Samples per second)
                  Typical range: 1 µSa/s - 200 MSa/s (depends on model)
        """
        self.instr.write(f"SOUR{channel}:FUNC:ARB:SRAT {rate}")

    def get_arb_sample_rate(self, channel):
        """
        Reads the current sample rate of the arbitrary waveform

        Args:
            channel: Channel number (1 or 2)

        Returns:
            float: Sample rate in Sa/s
        """
        return float(self.instr.query(f"SOUR{channel}:FUNC:ARB:SRAT?"))

    def load_arb_from_csv(self, channel, csv_file, name=None, normalize=True):
        """
        Loads arbitrary waveform from CSV file

        Args:
            channel: Channel number (1 or 2)
            csv_file: Path to the CSV file to load
            name: Name to assign to the waveform (optional)
            normalize: Automatically normalize values between -1 and +1 (default: True)

        Returns:
            int: Number of loaded points

        SUPPORTED CSV FORMATS:

        1) One column with amplitude values only:
           0.0
           0.309
           0.588
           0.809
           0.951
           1.0
           ...

        2) Two columns (time, amplitude) - time column is ignored:
           0.000, 0.0
           0.001, 0.309
           0.002, 0.588
           0.003, 0.809
           ...

        3) With header (automatically detected and ignored):
           time,voltage
           0.000, 0.0
           0.001, 0.309
           ...

        NOTES:
        - Values must be numeric
        - If normalize=False, values must already be between -1 and +1
        - Maximum points: depends on model (typically 8k-16k)
        - Separator can be comma or semicolon
        - Invalid rows are automatically ignored
        """
        import csv

        data = []

        with open(csv_file, 'r') as f:
            reader = csv.reader(f, delimiter=',')

            # Try to detect and handle header
            first_row = next(reader)
            try:
                # If first row is numeric, use it as data
                if len(first_row) == 1:
                    data.append(float(first_row[0]))
                else:
                    data.append(float(first_row[-1]))  # Take last column
            except ValueError:
                # First row is text header, ignore it
                pass

            # Read all remaining data
            for row in reader:
                if len(row) == 0:
                    continue
                try:
                    # Take the last column (assume it's the amplitude)
                    value = float(row[-1].strip())
                    data.append(value)
                except ValueError:
                    continue  # Skip invalid rows

        if not data:
            raise ValueError("No valid data found in CSV file")

        # Normalize values between -1 and +1 if requested
        if normalize:
            data_array = np.array(data)
            data_min = data_array.min()
            data_max = data_array.max()

            if data_max != data_min:
                # Normalization formula: y = 2*(x-min)/(max-min) - 1
                data_array = 2 * (data_array - data_min) / (data_max - data_min) - 1
            else:
                # If all values are equal, set to zero
                data_array = np.zeros_like(data_array)

            data = data_array.tolist()

        # Load the waveform into the instrument
        self.create_arb_waveform(channel, data, name)

        return len(data)

    # === ADVANCED PREDEFINED FUNCTIONS ===

    def create_sine_burst(self, channel, cycles, freq, ampl):
        """
        Creates a sine burst (packet of cycles)

        Args:
            channel: Channel number (1 or 2)
            cycles: Number of cycles per burst
            freq: Sine frequency in Hz
            ampl: Amplitude in Vpp
        """
        self.set_function(channel, "SIN")
        self.set_frequency(channel, freq)
        self.set_amplitude(channel, ampl)
        self.instr.write(f"SOUR{channel}:BURS:STAT ON")
        self.instr.write(f"SOUR{channel}:BURS:NCYC {cycles}")

    def create_custom_pulse(self, channel, width, period, edge_time):
        """
        Creates a pulse with custom parameters

        Args:
            channel: Channel number (1 or 2)
            width: Pulse width in seconds (e.g. 1e-3 = 1ms)
            period: Repetition period in seconds (e.g. 10e-3 = 10ms)
            edge_time: Rise/fall time in seconds (e.g. 10e-9 = 10ns)
        """
        self.set_function(channel, "PULSE")
        self.instr.write(f"SOUR{channel}:FUNC:PULS:WIDT {width}")
        self.instr.write(f"SOUR{channel}:FUNC:PULS:PER {period}")
        self.instr.write(f"SOUR{channel}:FUNC:PULS:TRAN {edge_time}")

    def create_ramp(self, channel, freq, symmetry):
        """
        Creates a ramp (sawtooth) with custom symmetry

        Args:
            channel: Channel number (1 or 2)
            freq: Frequency in Hz
            symmetry: Symmetry in % (0-100)
                      0%   = falling ramp (\)
                      50%  = triangular (/\)
                      100% = rising ramp (/)
        """
        self.set_function(channel, "RAMP")
        self.set_frequency(channel, freq)
        self.instr.write(f"SOUR{channel}:FUNC:RAMP:SYMM {symmetry}")

    def close(self):
        """
        Closes the VISA connection to the instrument

        Important: always call this method at the end of the session
        """
        self.instr.close()
        self.rm.close()


# === USAGE EXAMPLE ===

if __name__ == "__main__":
    # Connection (will auto-detect the device)
    gen = RigolDG()

    # Or specify the address directly:
    # gen = RigolDG('TCPIP0::192.168.1.100::INSTR')

    try:
        # Configure channel 1: sine wave 1kHz, 2Vpp
        gen.set_function(1, "SIN")
        gen.set_frequency(1, 1000)
        gen.set_amplitude(1, 2)
        gen.set_offset(1, 0)

        # Enable output
        gen.output_on(1)

        # Read configuration
        print(f"\nChannel 1:")
        print(f"  Function: {gen.get_function(1)}")
        print(f"  Frequency: {gen.get_frequency(1)} Hz")
        print(f"  Amplitude: {gen.get_amplitude(1)} Vpp")
        print(f"  Output: {'ON' if gen.is_output_on(1) else 'OFF'}")

        # AM modulation example
        # gen.set_am_modulation(1, depth=50, freq=100)

        # Arbitrary waveform example: sinc
        # t = np.linspace(-np.pi, np.pi, 1000)
        # sinc_wave = np.sinc(t)
        # gen.create_arb_waveform(1, sinc_wave.tolist(), "SINC")
        # gen.load_arb_waveform(1, "SINC")

        # CSV loading example
        # num_points = gen.load_arb_from_csv(1, "waveform.csv", name="MY_WAVE")
        # print(f"Loaded {num_points} points from CSV")
        # gen.load_arb_waveform(1, "MY_WAVE")

    finally:
        gen.close()
