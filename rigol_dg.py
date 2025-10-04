#!/usr/bin/env python3
"""
Controller for Rigol DG800/DG900 generators
Requires: pip install pyvisa pyvisa-py
"""

import pyvisa as visa
import numpy as np
import logging
import time
from datetime import datetime

class RigolDG:
    def __init__(self, resource_name=None, debug=False):
        """
        Initialize connection to Rigol DG800/DG900 generator

        Args:
            resource_name: VISA device identification string
                          Ex: 'USB0::0x1AB1::0x0642::DG9A12345678::INSTR'
                          Ex: 'TCPIP0::192.168.1.100::INSTR'
                          If None, shows list of available devices
            debug: Enable debug logging (default: False)
        """
        # Debug mode
        self.debug = debug
        self.debug_log = []

        # Setup logging if debug enabled
        if self.debug:
            logging.basicConfig(level=logging.DEBUG)
            # Enable pyvisa logging
            visa.log_to_screen()

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

        # Open connection with proper configuration
        self.instr = self.rm.open_resource(resource_name)
        self.instr.timeout = 5000  # 5 seconds

        # Configure terminators for SCPI communication
        self.instr.read_termination = '\n'
        self.instr.write_termination = '\n'

        # For TCP/IP connections, set chunk size and add delay
        if 'TCPIP' in resource_name:
            self.instr.chunk_size = 4096  # 4KB chunks (more reliable for slow devices)
            time.sleep(0.5)  # Give device time to stabilize TCP connection
            # Disable delay between chunks for faster transfer
            try:
                self.instr.write_delay = 0
            except:
                pass

        self._log_debug(f"Connected to {resource_name}")
        self._log_debug(f"Timeout: {self.instr.timeout} ms")
        self._log_debug(f"Read termination: {repr(self.instr.read_termination)}")
        self._log_debug(f"Write termination: {repr(self.instr.write_termination)}")
        if 'TCPIP' in resource_name:
            self._log_debug(f"Chunk size: {self.instr.chunk_size} bytes")

        # Try to identify the device
        try:
            idn = self.identify()
            print(f"Connected: {idn}")
        except Exception as e:
            # If \n doesn't work, try \r\n
            self._log_debug(f"Connection test failed with \\n, trying \\r\\n", is_error=True)
            self.instr.read_termination = '\r\n'
            self.instr.write_termination = '\r\n'
            self._log_debug(f"Read termination: {repr(self.instr.read_termination)}")
            self._log_debug(f"Write termination: {repr(self.instr.write_termination)}")

            try:
                idn = self.identify()
                print(f"Connected: {idn}")
            except Exception as e2:
                # Last resort: try clearing the device and sending *CLS
                self._log_debug(f"Connection test failed with \\r\\n, trying device clear", is_error=True)
                try:
                    self.instr.clear()
                    self.instr.write("*CLS")
                    idn = self.identify()
                    print(f"Connected: {idn}")
                except:
                    raise Exception(f"Cannot communicate with device: {str(e2)}")

    def _log_debug(self, message, is_error=False):
        """Log debug message with timestamp"""
        if self.debug:
            timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            log_entry = f"[{timestamp}] {message}"
            self.debug_log.append(log_entry)
            if is_error:
                print(f"ERROR: {log_entry}")
            else:
                print(log_entry)

    def _write(self, command):
        """Wrapper for write with debug logging"""
        # Truncate very long commands in debug log
        if len(command) > 200:
            log_cmd = command[:100] + f"...({len(command)} chars)..." + command[-50:]
        else:
            log_cmd = command

        self._log_debug(f"TX: {log_cmd}")
        try:
            self.instr.write(command)
            self._log_debug(f"TX OK")
        except Exception as e:
            self._log_debug(f"TX ERROR: {str(e)}", is_error=True)
            raise

    def _query(self, command):
        """Wrapper for query with debug logging"""
        self._log_debug(f"TX: {command}")
        try:
            response = self.instr.query(command).strip()
            self._log_debug(f"RX: {response}")
            return response
        except Exception as e:
            self._log_debug(f"RX ERROR: {str(e)}", is_error=True)
            raise

    def get_debug_log(self):
        """Return debug log as list of strings"""
        return self.debug_log.copy()

    def clear_debug_log(self):
        """Clear debug log"""
        self.debug_log.clear()

    def identify(self):
        """
        Identify the instrument via SCPI command *IDN?

        Returns:
            str: Identification string (manufacturer, model, serial, firmware)
        """
        return self._query("*IDN?")

    def reset(self):
        """
        Resets the instrument to factory defaults
        SCPI command: *RST
        """
        self._write("*RST")

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
        self._write(f"SOUR{channel}:FUNC {func}")

    def set_frequency(self, channel, freq):
        """
        Sets the signal frequency

        Args:
            channel: Channel number (1 or 2)
            freq: Frequency in Hz (range depends on model and waveform)
        """
        self._write(f"SOUR{channel}:FREQ {freq}")

    def set_frequency_khz(self, channel, freq_khz):
        """
        Sets the signal frequency in kHz

        Args:
            channel: Channel number (1 or 2)
            freq_khz: Frequency in kHz
        """
        freq_hz = freq_khz * 1000
        self._write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_frequency_mhz(self, channel, freq_mhz):
        """
        Sets the signal frequency in MHz

        Args:
            channel: Channel number (1 or 2)
            freq_mhz: Frequency in MHz
        """
        freq_hz = freq_mhz * 1000000
        self._write(f"SOUR{channel}:FREQ {freq_hz}")

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

        self._write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_amplitude(self, channel, ampl):
        """
        Sets the signal amplitude

        Args:
            channel: Channel number (1 or 2)
            ampl: Amplitude in Vpp (Volt peak-to-peak)
                  Typical range: 1mVpp - 10Vpp (depends on load)
        """
        self._write(f"SOUR{channel}:VOLT {ampl}")

    def set_amplitude_dbm(self, channel, dbm_value):
        """
        Sets the signal amplitude in dBm (for 50Ω load)

        Args:
            channel: Channel number (1 or 2)
            dbm_value: Power in dBm
                      Typical range: -40 dBm to +20 dBm (depends on model)
        """
        self._write(f"SOUR{channel}:VOLT:UNIT DBM")
        self._write(f"SOUR{channel}:VOLT {dbm_value}")

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
        self._write(f"SOUR{channel}:VOLT:UNIT {unit}")

    def get_amplitude_unit(self, channel):
        """
        Gets the current unit of measurement for amplitude

        Args:
            channel: Channel number (1 or 2)

        Returns:
            str: Current unit ('VPP', 'VRMS', 'DBM')
        """
        return self._query(f"SOUR{channel}:VOLT:UNIT?")

    def set_offset(self, channel, offset):
        """
        Sets the DC offset of the signal

        Args:
            channel: Channel number (1 or 2)
            offset: Offset in Volts (can be positive or negative)
        """
        self._write(f"SOUR{channel}:VOLT:OFFS {offset}")

    def set_phase(self, channel, phase):
        """
        Sets the signal phase

        Args:
            channel: Channel number (1 or 2)
            phase: Phase in degrees (0-360°)
        """
        self._write(f"SOUR{channel}:PHAS {phase}")

    def set_duty_cycle(self, channel, duty):
        """
        Sets the duty cycle for square wave

        Args:
            channel: Channel number (1 or 2)
            duty: Duty cycle in percentage (typically 0.01% - 99.99%)
                  50% = symmetric square wave
        """
        self._write(f"SOUR{channel}:FUNC:SQU:DCYC {duty}")

    # === OUTPUT CONTROL ===

    def output_on(self, channel):
        """
        Enables the output of the specified channel

        Args:
            channel: Channel number (1 or 2)
        """
        self._write(f"OUTP{channel} ON")

    def output_off(self, channel):
        """
        Disables the output of the specified channel

        Args:
            channel: Channel number (1 or 2)
        """
        self._write(f"OUTP{channel} OFF")

    def set_output_load(self, channel, load):
        """
        Sets the output load impedance

        Args:
            channel: Channel number (1 or 2)
            load: Impedance in Ohms (e.g. 50) or 'INF' for high impedance
                  The load affects the actual signal amplitude
        """
        self._write(f"OUTP{channel}:LOAD {load}")

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
        return float(self._query(f"SOUR{channel}:FREQ?"))

    def get_amplitude(self, channel):
        """
        Reads the current amplitude of the channel

        Args:
            channel: Channel number (1 or 2)

        Returns:
            float: Amplitude in Vpp
        """
        return float(self._query(f"SOUR{channel}:VOLT?"))

    def get_function(self, channel):
        """
        Reads the current waveform of the channel

        Args:
            channel: Channel number (1 or 2)

        Returns:
            str: Waveform type (SIN, SQU, RAMP, etc.)
        """
        return self._query(f"SOUR{channel}:FUNC?")

    def is_output_on(self, channel):
        """
        Checks if the output is active

        Args:
            channel: Channel number (1 or 2)

        Returns:
            bool: True if active, False if inactive
        """
        return self._query(f"OUTP{channel}?") == "ON"

    # === MODULATION ===

    def set_am_modulation(self, channel, depth, freq):
        """
        Enables amplitude modulation (AM)

        Args:
            channel: Channel number (1 or 2)
            depth: Modulation depth in % (0-120)
            freq: Modulating frequency in Hz
        """
        self._write(f"SOUR{channel}:AM:STAT ON")
        self._write(f"SOUR{channel}:AM:DEPT {depth}")
        self._write(f"SOUR{channel}:AM:INT:FREQ {freq}")

    def set_fm_modulation(self, channel, deviation, freq):
        """
        Enables frequency modulation (FM)

        Args:
            channel: Channel number (1 or 2)
            deviation: Frequency deviation in Hz
            freq: Modulating frequency in Hz
        """
        self._write(f"SOUR{channel}:FM:STAT ON")
        self._write(f"SOUR{channel}:FM:DEV {deviation}")
        self._write(f"SOUR{channel}:FM:INT:FREQ {freq}")

    def modulation_off(self, channel):
        """
        Disables all modulations (AM, FM, PM)

        Args:
            channel: Channel number (1 or 2)
        """
        self._write(f"SOUR{channel}:AM:STAT OFF")
        self._write(f"SOUR{channel}:FM:STAT OFF")
        self._write(f"SOUR{channel}:PM:STAT OFF")

    # === ARBITRARY WAVEFORMS ===

    def create_arb_waveform(self, channel, data, name=None, use_binary=True):
        """
        Creates a custom arbitrary waveform

        Args:
            channel: Channel number (1 or 2)
            data: List of normalized values between -1.0 and +1.0
                  Ex: [0, 0.5, 1.0, 0.5, 0, -0.5, -1.0, -0.5]
            name: Name to assign to the waveform (optional)
                  If None, loads directly into volatile memory
            use_binary: Use binary format for faster transfer (default: True)
                       Set to False to use ASCII/CSV format
        """
        import struct

        data_size = len(data)

        # Save original timeout and increase it for large transfers
        original_timeout = self.instr.timeout
        if data_size > 1000:
            # Increase timeout based on data size
            self.instr.timeout = max(10000, int(data_size * 0.5))
            self._log_debug(f"Large waveform ({data_size} points), timeout increased to {self.instr.timeout} ms")

        try:
            # For large waveforms, use binary format (much faster and more reliable)
            if use_binary and data_size > 100:
                self._log_debug(f"Using binary format for {data_size} points...")

                # Convert to 16-bit unsigned integers (0 to 16383 / 0x0000 to 0x3FFF)
                # According to DG900 manual, DATA:DAC16 expects values from 0x0000 to 0x3FFF
                data_array = np.array(data, dtype=np.float64)
                # Scale from [-1.0, +1.0] to [0, 16383]
                data_uint16 = np.clip((data_array + 1.0) * 8191.5, 0, 16383).astype(np.uint16)

                # Convert to binary (little-endian, 2 bytes per point)
                binary_data = data_uint16.tobytes()

                # IEEE 488.2 binary block format: #<num_digits><num_bytes><data>
                num_bytes = len(binary_data)
                num_bytes_str = str(num_bytes)
                num_digits = len(num_bytes_str)
                header = f"#{num_digits}{num_bytes_str}".encode('ascii')

                # Build complete command - use DATA:DAC16 with END flag (manual section 2.6.2)
                # When flag is END, the instrument automatically switches to arbitrary waveform output
                cmd = f"SOUR{channel}:TRAC:DATA:DAC16 VOLATILE,END,".encode('ascii') + header + binary_data

                self._log_debug(f"Binary transfer: {num_bytes} bytes ({data_size} points)")
                self._log_debug(f"Sending to channel {channel} VOLATILE memory with END flag...")
                self._log_debug(f"Data range: 0x0000 to 0x3FFF (0 to 16383)")

                # Send binary data
                self.instr.write_raw(cmd + b'\n')
                self._log_debug(f"Binary data sent successfully")
                self._log_debug(f"Note: END flag automatically activates ARB waveform output")

                time.sleep(0.3 if data_size < 5000 else 0.6)

                # Verify ARB mode was activated (should happen automatically with END flag)
                try:
                    current_func = self._query(f"SOUR{channel}:FUNC?")
                    self._log_debug(f"Current function: {current_func}")
                    if "ARB" in current_func.strip().upper():
                        self._log_debug(f"SUCCESS: ARB waveform activated automatically!")
                    else:
                        self._log_debug(f"Warning: Function is {current_func}, expected ARB", is_error=True)
                        self._log_debug(f"Trying manual activation...", is_error=True)
                        # Manual fallback
                        self._write(f"SOUR{channel}:FUNC ARB")
                        time.sleep(0.3)
                        current_func = self._query(f"SOUR{channel}:FUNC?")
                        self._log_debug(f"After manual activation: {current_func}")
                except Exception as e:
                    self._log_debug(f"Verification failed: {str(e)}", is_error=True)
            else:
                # ASCII format not supported by DG900 - fallback to binary
                self._log_debug(f"ASCII format requested but not supported by DG900")
                self._log_debug(f"Converting to binary format...")

                # Convert to 16-bit unsigned integers (0 to 16383 / 0x0000 to 0x3FFF)
                data_array = np.array(data, dtype=np.float64)
                # Scale from [-1.0, +1.0] to [0, 16383]
                data_uint16 = np.clip((data_array + 1.0) * 8191.5, 0, 16383).astype(np.uint16)

                # Convert to binary
                binary_data = data_uint16.tobytes()

                # IEEE 488.2 binary block format
                num_bytes = len(binary_data)
                num_bytes_str = str(num_bytes)
                num_digits = len(num_bytes_str)
                header = f"#{num_digits}{num_bytes_str}".encode('ascii')

                # Build complete command with END flag
                cmd = f"SOUR{channel}:TRAC:DATA:DAC16 VOLATILE,END,".encode('ascii') + header + binary_data

                self._log_debug(f"Sending {data_size} points to channel {channel}...")

                # Send binary data
                self.instr.write_raw(cmd + b'\n')
                self._log_debug(f"Binary data sent successfully")
                time.sleep(0.3)

                # Verify
                current_func = self._query(f"SOUR{channel}:FUNC?")
                self._log_debug(f"Current function: {current_func}")

                if "ARB" in current_func.strip().upper():
                    self._log_debug(f"SUCCESS: ARB waveform activated!")
                else:
                    self._log_debug(f"Warning: Function is {current_func}, expected ARB", is_error=True)

            self._log_debug("Waveform transfer complete")
        finally:
            # Restore original timeout
            self.instr.timeout = original_timeout
            if data_size > 1000:
                self._log_debug(f"Timeout restored to {original_timeout} ms")

    def load_arb_waveform(self, channel, name):
        """
        Loads a previously saved arbitrary waveform

        Args:
            channel: Channel number (1 or 2)
            name: Name of the waveform to load
        """
        self._write(f"SOUR{channel}:FUNC ARB")
        self._write(f"SOUR{channel}:FUNC:ARB {name}")

    def get_arb_list(self):
        """
        Returns list of arbitrary waveforms saved in memory

        Returns:
            list: List of available waveform names
        """
        return self._query("DATA:CAT?").split(',')

    def delete_arb_waveform(self, name):
        """
        Deletes an arbitrary waveform from memory

        Args:
            name: Name of the waveform to delete
        """
        self._write(f"DATA:DEL {name}")

    def set_arb_sample_rate(self, channel, rate):
        """
        Sets the sample rate for the arbitrary waveform

        Args:
            channel: Channel number (1 or 2)
            rate: Sample rate in Sa/s (Samples per second)
                  Typical range: 1 µSa/s - 200 MSa/s (depends on model)
        """
        self._write(f"SOUR{channel}:FUNC:ARB:SRAT {rate}")

    def get_arb_sample_rate(self, channel):
        """
        Reads the current sample rate of the arbitrary waveform

        Args:
            channel: Channel number (1 or 2)

        Returns:
            float: Sample rate in Sa/s
        """
        return float(self._query(f"SOUR{channel}:FUNC:ARB:SRAT?"))

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
        self._write(f"SOUR{channel}:BURS:STAT ON")
        self._write(f"SOUR{channel}:BURS:NCYC {cycles}")

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
        self._write(f"SOUR{channel}:FUNC:PULS:WIDT {width}")
        self._write(f"SOUR{channel}:FUNC:PULS:PER {period}")
        self._write(f"SOUR{channel}:FUNC:PULS:TRAN {edge_time}")

    def create_ramp(self, channel, freq, symmetry):
        """
        Creates a ramp (sawtooth) with custom symmetry

        Args:
            channel: Channel number (1 or 2)
            freq: Frequency in Hz
            symmetry: Symmetry in % (0-100)
                      0%   = falling ramp (\\)
                      50%  = triangular (/\\)
                      100% = rising ramp (/)
        """
        self.set_function(channel, "RAMP")
        self.set_frequency(channel, freq)
        self._write(f"SOUR{channel}:FUNC:RAMP:SYMM {symmetry}")

    def set_dual_tone(self, channel, freq1, freq2, amplitude=1.0):
        """
        Sets the built-in dual-tone waveform

        Args:
            channel: Channel number (1 or 2)
            freq1: First frequency in Hz
            freq2: Second frequency in Hz
            amplitude: Output amplitude in Vpp (default: 1.0)
        """
        self._log_debug(f"Setting dual-tone on channel {channel}: f1={freq1}Hz, f2={freq2}Hz")

        # Set function to DUALTone (correct command from manual)
        self._log_debug(f"Setting function to DUALTone...")
        self._write(f"SOUR{channel}:FUNC DUALTone")
        time.sleep(0.2)

        # Set the two frequencies using FUNC:DUALTone:FREQ1 and FREQ2
        self._log_debug(f"Setting FREQ1 to {freq1} Hz...")
        self._write(f"SOUR{channel}:FUNC:DUALTone:FREQ1 {freq1}")
        time.sleep(0.1)

        self._log_debug(f"Setting FREQ2 to {freq2} Hz...")
        self._write(f"SOUR{channel}:FUNC:DUALTone:FREQ2 {freq2}")
        time.sleep(0.1)

        # Set amplitude
        self._log_debug(f"Setting amplitude to {amplitude} Vpp...")
        self._write(f"SOUR{channel}:VOLT {amplitude}")
        time.sleep(0.1)

        # Verify
        current_func = self._query(f"SOUR{channel}:FUNC?")
        self._log_debug(f"Current function: {current_func}")

        func_upper = current_func.strip().upper()
        if "DUAL" in func_upper:  # Accept both "DUAL" and "DUALTONE"
            self._log_debug(f"SUCCESS: Dual-tone activated!")
            # Read back the frequencies to confirm
            try:
                f1_actual = self._query(f"SOUR{channel}:FUNC:DUALTone:FREQ1?")
                f2_actual = self._query(f"SOUR{channel}:FUNC:DUALTone:FREQ2?")
                self._log_debug(f"Frequencies set: F1={f1_actual}Hz, F2={f2_actual}Hz")
            except:
                pass
        else:
            self._log_debug(f"Warning: Function is {current_func}, expected DUALTONE", is_error=True)

    def close(self):
        """
        Closes the VISA connection to the instrument

        Important: always call this method at the end of the session
        """
        try:
            # Return control to local (front panel) before closing
            self._log_debug("Returning control to local (front panel)...")
            self._write("SYSTem:LOCal")
            time.sleep(0.1)
        except:
            # Ignore errors during close
            pass

        self.instr.close()
        self.rm.close()
        self._log_debug("Connection closed")


# === UTILITY FUNCTIONS ===

def wav_to_csv(wav_file, csv_file, max_points=None, channel=0, normalize=True):
    """
    Converts a WAV audio file to CSV format for arbitrary waveform generation

    Args:
        wav_file: Path to input WAV file
        csv_file: Path to output CSV file
        max_points: Maximum number of points to export (None = use all)
                   Typical limits: 8k-16k depending on generator model
        channel: Audio channel to extract (0=left/mono, 1=right)
        normalize: Normalize values between -1 and +1 (default: True)

    Returns:
        dict: Information about the conversion including:
              - sample_rate: Original sample rate in Hz
              - duration: Duration in seconds
              - channels: Number of audio channels
              - num_points: Number of points exported
              - suggested_sample_rate: Recommended generator sample rate

    Example:
        >>> info = wav_to_csv("audio.wav", "waveform.csv", max_points=8192)
        >>> print(f"Exported {info['num_points']} points")
        >>> print(f"Suggested sample rate: {info['suggested_sample_rate']} Sa/s")
    """
    import wave
    import struct

    # Open and read WAV file
    with wave.open(wav_file, 'rb') as wav:
        # Get WAV parameters
        n_channels = wav.getnchannels()
        sample_width = wav.getsampwidth()
        sample_rate = wav.getframerate()
        n_frames = wav.getnframes()

        # Check requested channel exists
        if channel >= n_channels:
            raise ValueError(f"Channel {channel} not available. File has {n_channels} channel(s)")

        # Read all frames
        frames = wav.readframes(n_frames)

    # Parse audio data based on sample width
    if sample_width == 1:  # 8-bit unsigned
        fmt = f'{n_frames * n_channels}B'
        data = struct.unpack(fmt, frames)
        # Convert to signed and normalize
        data = np.array(data, dtype=np.float64)
        data = (data - 128) / 128.0
    elif sample_width == 2:  # 16-bit signed
        fmt = f'{n_frames * n_channels}h'
        data = struct.unpack(fmt, frames)
        data = np.array(data, dtype=np.float64) / 32768.0
    elif sample_width == 3:  # 24-bit signed (rare)
        # 24-bit needs special handling
        data = []
        for i in range(0, len(frames), 3 * n_channels):
            for ch in range(n_channels):
                offset = i + ch * 3
                # Convert 3 bytes to signed int
                val = int.from_bytes(frames[offset:offset+3], byteorder='little', signed=True)
                data.append(val / 8388608.0)
        data = np.array(data)
    elif sample_width == 4:  # 32-bit signed
        fmt = f'{n_frames * n_channels}i'
        data = struct.unpack(fmt, frames)
        data = np.array(data, dtype=np.float64) / 2147483648.0
    else:
        raise ValueError(f"Unsupported sample width: {sample_width} bytes")

    # Reshape for multi-channel and extract requested channel
    if n_channels > 1:
        data = data.reshape(-1, n_channels)
        data = data[:, channel]

    # Downsample if max_points is specified
    if max_points and len(data) > max_points:
        # Use linear interpolation for downsampling
        indices = np.linspace(0, len(data) - 1, max_points)
        data = np.interp(indices, np.arange(len(data)), data)

    # Normalize if requested
    if normalize:
        data_max = np.abs(data).max()
        if data_max > 0:
            data = data / data_max

    # Write to CSV file
    np.savetxt(csv_file, data, fmt='%.6f', delimiter=',',
               header='amplitude', comments='')

    # Calculate suggested sample rate for the generator
    duration = n_frames / sample_rate
    num_points = len(data)
    suggested_sample_rate = num_points / duration

    return {
        'sample_rate': sample_rate,
        'duration': duration,
        'channels': n_channels,
        'num_points': num_points,
        'suggested_sample_rate': suggested_sample_rate,
        'normalized': normalize,
        'downsampled': max_points is not None and n_frames > max_points
    }


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

        # WAV to CSV conversion example
        # info = wav_to_csv("audio.wav", "waveform.csv", max_points=8192)
        # print(f"\nWAV conversion:")
        # print(f"  Exported: {info['num_points']} points")
        # print(f"  Duration: {info['duration']:.3f} seconds")
        # print(f"  Suggested sample rate: {info['suggested_sample_rate']:.0f} Sa/s")
        # gen.load_arb_from_csv(1, "waveform.csv", name="AUDIO", normalize=False)
        # gen.set_arb_sample_rate(1, info['suggested_sample_rate'])

    finally:
        gen.close()
