#!/usr/bin/env python3
"""
GUI for controlling Rigol DG800/DG900 generators
Requires: pip install pyvisa pyvisa-py numpy tkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from rigol_dg import RigolDG, wav_to_csv
import numpy as np
import pyvisa as visa

class DeviceSelectionDialog:
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("VISA Device Selection")
        self.dialog.geometry("600x400")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()  # Modal window
        self.dialog.transient(parent)

        # Center the window
        self.dialog.geometry("+{}+{}".format(
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        self.setup_ui()
        self.scan_devices()

    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Title
        title_label = ttk.Label(main_frame, text="Select VISA Device",
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 20))

        # Scan area
        scan_frame = ttk.Frame(main_frame)
        scan_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(scan_frame, text="🔄 Rescan Devices",
                  command=self.scan_devices).pack(side="left")

        self.scan_status = ttk.Label(scan_frame, text="")
        self.scan_status.pack(side="left", padx=(10, 0))

        # Device list
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 20))

        ttk.Label(list_frame, text="Devices found:").pack(anchor="w")

        # Listbox with scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill="both", expand=True, pady=(5, 0))

        self.device_listbox = tk.Listbox(listbox_frame, height=8, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.device_listbox.yview)
        self.device_listbox.configure(yscrollcommand=scrollbar.set)

        self.device_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Info frame
        info_frame = ttk.LabelFrame(main_frame, text="Device Information", padding=10)
        info_frame.pack(fill="x", pady=(0, 20))

        self.device_info = tk.Text(info_frame, height=4, wrap="word", font=("Courier", 8))
        self.device_info.pack(fill="x")

        # Events
        self.device_listbox.bind("<<ListboxSelect>>", self.on_device_select)
        self.device_listbox.bind("<Double-Button-1>", lambda e: self.connect_device())

        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="Cancel",
                  command=self.cancel).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="Connect",
                  command=self.connect_device).pack(side="right")

        # Manual address
        manual_frame = ttk.LabelFrame(main_frame, text="Manual Address", padding=10)
        manual_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(manual_frame, text="VISA Address:").pack(side="left")
        self.manual_entry = ttk.Entry(manual_frame, width=50)
        self.manual_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        ttk.Button(manual_frame, text="Use",
                  command=self.use_manual).pack(side="left", padx=(5, 0))

    def scan_devices(self):
        self.scan_status.config(text="Scanning...")
        self.device_listbox.delete(0, tk.END)
        self.device_info.delete(1.0, tk.END)
        self.dialog.update()

        try:
            rm = visa.ResourceManager('@py')
            resources = rm.list_resources()

            if not resources:
                self.device_listbox.insert(tk.END, "No VISA devices found")
                self.scan_status.config(text="❌ No devices found")
            else:
                for i, res in enumerate(resources):
                    self.device_listbox.insert(tk.END, f"{i}: {res}")
                self.scan_status.config(text=f"✅ Found {len(resources)} devices")

            rm.close()
        except Exception as e:
            self.device_listbox.insert(tk.END, f"Scan error: {str(e)}")
            self.scan_status.config(text="❌ Scan error")

    def on_device_select(self, event):
        selection = self.device_listbox.curselection()
        if not selection:
            return

        line = self.device_listbox.get(selection[0])
        if ":" not in line or "No" in line or "error" in line:
            self.device_info.delete(1.0, tk.END)
            return

        # Extract VISA address
        resource_name = line.split(": ", 1)[1]

        # Show device information
        self.device_info.delete(1.0, tk.END)
        self.device_info.insert(tk.END, f"Address: {resource_name}\n")

        # Try to get device ID
        try:
            rm = visa.ResourceManager('@py')
            instr = rm.open_resource(resource_name)
            instr.timeout = 2000
            idn = instr.query("*IDN?").strip()
            self.device_info.insert(tk.END, f"Identification: {idn}")
            instr.close()
            rm.close()
        except:
            self.device_info.insert(tk.END, "Identification: Not available")

    def connect_device(self):
        selection = self.device_listbox.curselection()
        if not selection:
            messagebox.showwarning("Warning", "Select a device from the list")
            return

        line = self.device_listbox.get(selection[0])
        if ":" not in line or "No" in line or "error" in line:
            messagebox.showwarning("Warning", "Select a valid device")
            return

        self.result = line.split(": ", 1)[1]
        self.dialog.destroy()

    def use_manual(self):
        address = self.manual_entry.get().strip()
        if not address:
            messagebox.showwarning("Warning", "Enter a valid VISA address")
            return
        self.result = address
        self.dialog.destroy()

    def cancel(self):
        self.result = None
        self.dialog.destroy()

class RigolDGGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Rigol DG Controller")
        self.root.geometry("900x700")

        self.gen = None
        self.connected = False

        self.setup_ui()

    def setup_ui(self):
        """Create the graphical interface"""

        # === CONNECTION FRAME ===
        conn_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        conn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ttk.Label(conn_frame, text="VISA Address:").grid(row=0, column=0, sticky="w")
        self.visa_entry = ttk.Entry(conn_frame, width=50)
        self.visa_entry.grid(row=0, column=1, padx=5)
        self.visa_entry.insert(0, "Auto-detect")

        self.connect_btn = ttk.Button(conn_frame, text="Connect", command=self.connect)
        self.connect_btn.grid(row=0, column=2, padx=5)

        self.status_label = ttk.Label(conn_frame, text="Not connected", foreground="red")
        self.status_label.grid(row=0, column=3, padx=10)

        # === NOTEBOOK FOR CHANNELS ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        # Tab Channel 1
        self.channel1_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.channel1_frame, text="Channel 1")
        self.setup_channel_controls(self.channel1_frame, 1)

        # Tab Channel 2
        self.channel2_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.channel2_frame, text="Channel 2")
        self.setup_channel_controls(self.channel2_frame, 2)

        # Tab Arbitrary waveforms
        self.arb_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.arb_frame, text="ARB Waveforms")
        self.setup_arb_controls()

        # Configure resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

    def setup_channel_controls(self, parent, channel):
        """Create controls for a channel"""

        # === WAVEFORM ===
        wave_frame = ttk.LabelFrame(parent, text="Waveform", padding=10)
        wave_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(wave_frame, text="Type:").grid(row=0, column=0, sticky="w")
        func_var = tk.StringVar(value="SIN")
        setattr(self, f"ch{channel}_func", func_var)
        func_combo = ttk.Combobox(wave_frame, textvariable=func_var, width=15,
                                  values=["SIN", "SQU", "RAMP", "PULSE", "NOIS", "DC", "ARB"])
        func_combo.grid(row=0, column=1, padx=5)
        func_combo.bind("<<ComboboxSelected>>", lambda e: self.update_function(channel))

        # === BASIC PARAMETERS ===
        params_frame = ttk.LabelFrame(parent, text="Parameters", padding=10)
        params_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # Frequency
        freq_label = ttk.Label(params_frame, text="Frequency (Hz):")
        freq_label.grid(row=0, column=0, sticky="w")
        setattr(self, f"ch{channel}_freq_label", freq_label)

        freq_var = tk.StringVar(value="1000")
        setattr(self, f"ch{channel}_freq", freq_var)
        freq_entry = ttk.Entry(params_frame, textvariable=freq_var, width=15)
        freq_entry.grid(row=0, column=1, padx=5)

        # Frequency unit
        freq_unit_var = tk.StringVar(value="HZ")
        setattr(self, f"ch{channel}_freq_unit", freq_unit_var)
        freq_unit_combo = ttk.Combobox(params_frame, textvariable=freq_unit_var, width=8,
                                       values=["HZ", "KHZ", "MHZ"], state="readonly")
        freq_unit_combo.grid(row=0, column=2, padx=2)
        freq_unit_combo.bind("<<ComboboxSelected>>", lambda e: self.update_frequency_unit(channel))

        ttk.Button(params_frame, text="Apply",
                  command=lambda: self.set_frequency(channel)).grid(row=0, column=3, padx=5)

        # Amplitude
        ampl_label = ttk.Label(params_frame, text="Amplitude (Vpp):")
        ampl_label.grid(row=1, column=0, sticky="w")
        setattr(self, f"ch{channel}_ampl_label", ampl_label)

        ampl_var = tk.StringVar(value="2")
        setattr(self, f"ch{channel}_ampl", ampl_var)
        ampl_entry = ttk.Entry(params_frame, textvariable=ampl_var, width=15)
        ampl_entry.grid(row=1, column=1, padx=5)

        # Amplitude unit
        unit_var = tk.StringVar(value="VPP")
        setattr(self, f"ch{channel}_ampl_unit", unit_var)
        unit_combo = ttk.Combobox(params_frame, textvariable=unit_var, width=8,
                                  values=["VPP", "VRMS", "DBM"], state="readonly")
        unit_combo.grid(row=1, column=2, padx=2)
        unit_combo.bind("<<ComboboxSelected>>", lambda e: self.update_amplitude_unit(channel))

        ttk.Button(params_frame, text="Apply",
                  command=lambda: self.set_amplitude(channel)).grid(row=1, column=3, padx=5)

        # Offset
        ttk.Label(params_frame, text="Offset (V):").grid(row=2, column=0, sticky="w")
        offset_var = tk.StringVar(value="0")
        setattr(self, f"ch{channel}_offset", offset_var)
        offset_entry = ttk.Entry(params_frame, textvariable=offset_var, width=20)
        offset_entry.grid(row=2, column=1, padx=5)

        ttk.Button(params_frame, text="Apply",
                  command=lambda: self.set_offset(channel)).grid(row=2, column=2, padx=5)

        # Phase
        ttk.Label(params_frame, text="Phase (°):").grid(row=3, column=0, sticky="w")
        phase_var = tk.StringVar(value="0")
        setattr(self, f"ch{channel}_phase", phase_var)
        phase_entry = ttk.Entry(params_frame, textvariable=phase_var, width=20)
        phase_entry.grid(row=3, column=1, padx=5)

        ttk.Button(params_frame, text="Apply",
                  command=lambda: self.set_phase(channel)).grid(row=3, column=2, padx=5)

        # Duty Cycle (for square wave)
        ttk.Label(params_frame, text="Duty Cycle (%):").grid(row=4, column=0, sticky="w")
        duty_var = tk.StringVar(value="50")
        setattr(self, f"ch{channel}_duty", duty_var)
        duty_entry = ttk.Entry(params_frame, textvariable=duty_var, width=20)
        duty_entry.grid(row=4, column=1, padx=5)

        ttk.Button(params_frame, text="Apply",
                  command=lambda: self.set_duty_cycle(channel)).grid(row=4, column=2, padx=5)

        # === MODULATION ===
        mod_frame = ttk.LabelFrame(parent, text="Modulation", padding=10)
        mod_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        # AM
        ttk.Label(mod_frame, text="AM - Depth (%):").grid(row=0, column=0, sticky="w")
        am_depth_var = tk.StringVar(value="50")
        setattr(self, f"ch{channel}_am_depth", am_depth_var)
        ttk.Entry(mod_frame, textvariable=am_depth_var, width=15).grid(row=0, column=1, padx=5)

        ttk.Label(mod_frame, text="Freq (Hz):").grid(row=0, column=2, sticky="w")
        am_freq_var = tk.StringVar(value="10")
        setattr(self, f"ch{channel}_am_freq", am_freq_var)
        ttk.Entry(mod_frame, textvariable=am_freq_var, width=15).grid(row=0, column=3, padx=5)

        ttk.Button(mod_frame, text="Enable AM",
                  command=lambda: self.set_am_modulation(channel)).grid(row=0, column=4, padx=5)

        # FM
        ttk.Label(mod_frame, text="FM - Dev (Hz):").grid(row=1, column=0, sticky="w")
        fm_dev_var = tk.StringVar(value="100")
        setattr(self, f"ch{channel}_fm_dev", fm_dev_var)
        ttk.Entry(mod_frame, textvariable=fm_dev_var, width=15).grid(row=1, column=1, padx=5)

        ttk.Label(mod_frame, text="Freq (Hz):").grid(row=1, column=2, sticky="w")
        fm_freq_var = tk.StringVar(value="10")
        setattr(self, f"ch{channel}_fm_freq", fm_freq_var)
        ttk.Entry(mod_frame, textvariable=fm_freq_var, width=15).grid(row=1, column=3, padx=5)

        ttk.Button(mod_frame, text="Enable FM",
                  command=lambda: self.set_fm_modulation(channel)).grid(row=1, column=4, padx=5)

        # Disable modulation
        ttk.Button(mod_frame, text="Disable Modulation",
                  command=lambda: self.modulation_off(channel)).grid(row=2, column=0, columnspan=5, pady=10)

        # === OUTPUT ===
        output_frame = ttk.LabelFrame(parent, text="Output", padding=10)
        output_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(output_frame, text="Load (Ω):").grid(row=0, column=0, sticky="w")
        load_var = tk.StringVar(value="50")
        setattr(self, f"ch{channel}_load", load_var)
        load_combo = ttk.Combobox(output_frame, textvariable=load_var, width=15,
                                  values=["50", "75", "600", "1000", "INF"])
        load_combo.grid(row=0, column=1, padx=5)

        ttk.Button(output_frame, text="Apply",
                  command=lambda: self.set_output_load(channel)).grid(row=0, column=2, padx=5)

        # ON/OFF buttons
        btn_frame = ttk.Frame(output_frame)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="OUTPUT ON",
                  command=lambda: self.output_on(channel)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="OUTPUT OFF",
                  command=lambda: self.output_off(channel)).pack(side="left", padx=5)

        # Quick RF configuration
        rf_frame = ttk.Frame(output_frame)
        rf_frame.grid(row=2, column=0, columnspan=3, pady=10)

        ttk.Button(rf_frame, text="⚡ Config RF (50Ω + dBm)",
                  command=lambda: self.set_rf_mode(channel)).pack(side="left", padx=5)

        # === STATUS READING ===
        status_frame = ttk.LabelFrame(parent, text="Current Status", padding=10)
        status_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

        status_text = tk.Text(status_frame, height=6, width=70)
        status_text.grid(row=0, column=0, padx=5, pady=5)
        setattr(self, f"ch{channel}_status", status_text)

        ttk.Button(status_frame, text="Update Status",
                  command=lambda: self.read_status(channel)).grid(row=1, column=0, pady=5)

    def setup_arb_controls(self):
        """Create controls for arbitrary waveforms"""

        # === LOAD FROM CSV ===
        csv_frame = ttk.LabelFrame(self.arb_frame, text="Load from CSV", padding=10)
        csv_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(csv_frame, text="Channel:").grid(row=0, column=0, sticky="w")
        self.arb_channel = tk.StringVar(value="1")
        ttk.Combobox(csv_frame, textvariable=self.arb_channel, width=10,
                    values=["1", "2"]).grid(row=0, column=1, padx=5)

        ttk.Label(csv_frame, text="Name:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.arb_name = tk.StringVar(value="CUSTOM")
        ttk.Entry(csv_frame, textvariable=self.arb_name, width=20).grid(row=0, column=3, padx=5)

        self.arb_normalize = tk.BooleanVar(value=True)
        ttk.Checkbutton(csv_frame, text="Normalize",
                       variable=self.arb_normalize).grid(row=0, column=4, padx=10)

        ttk.Button(csv_frame, text="Select CSV File",
                  command=self.load_csv).grid(row=1, column=0, columnspan=5, pady=10)

        self.csv_path_label = ttk.Label(csv_frame, text="No file selected")
        self.csv_path_label.grid(row=2, column=0, columnspan=5)

        # === LOAD FROM WAV ===
        wav_frame = ttk.LabelFrame(self.arb_frame, text="Load from WAV Audio", padding=10)
        wav_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(wav_frame, text="Max points:").grid(row=0, column=0, sticky="w")
        self.wav_max_points = tk.StringVar(value="8192")
        ttk.Combobox(wav_frame, textvariable=self.wav_max_points, width=10,
                    values=["4096", "8192", "16384"]).grid(row=0, column=1, padx=5)

        ttk.Label(wav_frame, text="Channel:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.wav_channel = tk.StringVar(value="0")
        ttk.Combobox(wav_frame, textvariable=self.wav_channel, width=10,
                    values=["0 (Left/Mono)", "1 (Right)"]).grid(row=0, column=3, padx=5)

        ttk.Button(wav_frame, text="Select WAV File",
                  command=self.load_wav).grid(row=1, column=0, columnspan=4, pady=10)

        self.wav_path_label = ttk.Label(wav_frame, text="No file selected")
        self.wav_path_label.grid(row=2, column=0, columnspan=4)

        # === CREATE FROM FUNCTION ===
        func_frame = ttk.LabelFrame(self.arb_frame, text="Generate Waveform", padding=10)
        func_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(func_frame, text="Type:").grid(row=0, column=0, sticky="w")
        self.arb_type = tk.StringVar(value="sinc")
        ttk.Combobox(func_frame, textvariable=self.arb_type, width=15,
                    values=["sinc", "gauss", "exponential", "chirp"]).grid(row=0, column=1, padx=5)

        ttk.Label(func_frame, text="Points:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.arb_points = tk.StringVar(value="1000")
        ttk.Entry(func_frame, textvariable=self.arb_points, width=15).grid(row=0, column=3, padx=5)

        ttk.Button(func_frame, text="Generate and Load",
                  command=self.generate_arb).grid(row=1, column=0, columnspan=4, pady=10)

        # === SAMPLE RATE ===
        srate_frame = ttk.LabelFrame(self.arb_frame, text="Sample Rate", padding=10)
        srate_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(srate_frame, text="Sample Rate (Sa/s):").grid(row=0, column=0, sticky="w")
        self.arb_srate = tk.StringVar(value="1e6")
        ttk.Entry(srate_frame, textvariable=self.arb_srate, width=20).grid(row=0, column=1, padx=5)

        ttk.Button(srate_frame, text="Apply",
                  command=self.set_sample_rate).grid(row=0, column=2, padx=5)

        # === WAVEFORM MANAGEMENT ===
        manage_frame = ttk.LabelFrame(self.arb_frame, text="Waveform Management", padding=10)
        manage_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

        ttk.Button(manage_frame, text="List Waveforms",
                  command=self.list_arb_waveforms).grid(row=0, column=0, padx=5, pady=5)

        ttk.Label(manage_frame, text="Load:").grid(row=1, column=0, sticky="w")
        self.arb_load_name = tk.StringVar()
        ttk.Entry(manage_frame, textvariable=self.arb_load_name, width=20).grid(row=1, column=1, padx=5)
        ttk.Button(manage_frame, text="Load ARB",
                  command=self.load_arb).grid(row=1, column=2, padx=5)

        ttk.Label(manage_frame, text="Delete:").grid(row=2, column=0, sticky="w")
        self.arb_del_name = tk.StringVar()
        ttk.Entry(manage_frame, textvariable=self.arb_del_name, width=20).grid(row=2, column=1, padx=5)
        ttk.Button(manage_frame, text="Delete",
                  command=self.delete_arb).grid(row=2, column=2, padx=5)

        # === INFO AREA ===
        info_frame = ttk.LabelFrame(self.arb_frame, text="Information", padding=10)
        info_frame.grid(row=5, column=0, sticky="ew", padx=10, pady=5)

        self.arb_info = tk.Text(info_frame, height=8, width=70)
        self.arb_info.grid(row=0, column=0, padx=5, pady=5)

    # === CONNECTION METHODS ===

    def connect(self):
        """Connect to the generator"""
        if self.connected:
            messagebox.showinfo("Info", "Already connected")
            return

        visa_addr = self.visa_entry.get()

        # If auto-detect, show selection dialog
        if visa_addr == "Auto-detect" or visa_addr == "":
            dialog = DeviceSelectionDialog(self.root)
            self.root.wait_window(dialog.dialog)

            if dialog.result is None:
                return  # User cancelled

            visa_addr = dialog.result

        def do_connect():
            try:
                # Connect directly with the specified address
                self.gen = RigolDG(visa_addr)

                self.connected = True
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Connected: {self.gen.identify()}", foreground="green"))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Success", "Connected to generator"))

                # Update the address field with the selected one
                self.root.after(0, lambda: self.visa_entry.delete(0, tk.END))
                self.root.after(0, lambda: self.visa_entry.insert(0, visa_addr))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Error", f"Connection error:\n{str(e)}"))

        threading.Thread(target=do_connect, daemon=True).start()

    def check_connection(self):
        """Check active connection"""
        if not self.connected or self.gen is None:
            messagebox.showerror("Error", "Not connected to generator")
            return False
        return True

    # === CHANNEL CONTROL METHODS ===

    def update_function(self, channel):
        """Update waveform"""
        if not self.check_connection():
            return

        try:
            func = getattr(self, f"ch{channel}_func").get()
            self.gen.set_function(channel, func)
            messagebox.showinfo("OK", f"Channel {channel}: waveform → {func}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_frequency(self, channel):
        """Set frequency with current unit"""
        if not self.check_connection():
            return

        try:
            freq_value = float(getattr(self, f"ch{channel}_freq").get())
            freq_unit = getattr(self, f"ch{channel}_freq_unit").get()

            # Use the method with unit
            self.gen.set_frequency_with_unit(channel, freq_value, freq_unit)

            # Message with correct unit
            unit_str = {"HZ": "Hz", "KHZ": "kHz", "MHZ": "MHz"}[freq_unit]
            messagebox.showinfo("OK", f"Channel {channel}: frequency → {freq_value} {unit_str}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_amplitude(self, channel):
        """Set amplitude with current unit"""
        if not self.check_connection():
            return

        try:
            ampl = float(getattr(self, f"ch{channel}_ampl").get())
            unit = getattr(self, f"ch{channel}_ampl_unit").get()

            # Set unit before value
            self.gen.set_amplitude_unit(channel, unit)
            self.gen.set_amplitude(channel, ampl)

            # Message with correct unit
            unit_str = {"VPP": "Vpp", "VRMS": "Vrms", "DBM": "dBm"}[unit]
            messagebox.showinfo("OK", f"Channel {channel}: amplitude → {ampl} {unit_str}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_offset(self, channel):
        """Set offset"""
        if not self.check_connection():
            return

        try:
            offset = float(getattr(self, f"ch{channel}_offset").get())
            self.gen.set_offset(channel, offset)
            messagebox.showinfo("OK", f"Channel {channel}: offset → {offset} V")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_phase(self, channel):
        """Set phase"""
        if not self.check_connection():
            return

        try:
            phase = float(getattr(self, f"ch{channel}_phase").get())
            self.gen.set_phase(channel, phase)
            messagebox.showinfo("OK", f"Channel {channel}: phase → {phase}°")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_duty_cycle(self, channel):
        """Set duty cycle"""
        if not self.check_connection():
            return

        try:
            duty = float(getattr(self, f"ch{channel}_duty").get())
            self.gen.set_duty_cycle(channel, duty)
            messagebox.showinfo("OK", f"Channel {channel}: duty cycle → {duty}%")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_amplitude_unit(self, channel):
        """Update amplitude unit and label"""
        if not self.check_connection():
            return

        try:
            unit = getattr(self, f"ch{channel}_ampl_unit").get()
            self.gen.set_amplitude_unit(channel, unit)

            # Update label
            label = getattr(self, f"ch{channel}_ampl_label")
            if unit == "VPP":
                label.config(text="Amplitude (Vpp):")
            elif unit == "VRMS":
                label.config(text="Amplitude (Vrms):")
            elif unit == "DBM":
                label.config(text="Power (dBm):")

            messagebox.showinfo("OK", f"Channel {channel}: amplitude unit → {unit}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def update_frequency_unit(self, channel):
        """Update frequency unit and label"""
        try:
            unit = getattr(self, f"ch{channel}_freq_unit").get()

            # Update label
            label = getattr(self, f"ch{channel}_freq_label")
            if unit == "HZ":
                label.config(text="Frequency (Hz):")
            elif unit == "KHZ":
                label.config(text="Frequency (kHz):")
            elif unit == "MHZ":
                label.config(text="Frequency (MHz):")

            messagebox.showinfo("OK", f"Channel {channel}: frequency unit → {unit}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_rf_mode(self, channel):
        """Quick configuration for RF measurements (50Ω + dBm)"""
        if not self.check_connection():
            return

        try:
            # Set 50Ω load and dBm unit
            self.gen.set_50ohm_dbm_mode(channel)

            # Update GUI controls
            getattr(self, f"ch{channel}_load").set("50")
            getattr(self, f"ch{channel}_ampl_unit").set("DBM")

            # Update amplitude label
            label = getattr(self, f"ch{channel}_ampl_label")
            label.config(text="Power (dBm):")

            messagebox.showinfo("OK", f"Channel {channel}: configured for RF (50Ω + dBm)")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # === MODULATION METHODS ===

    def set_am_modulation(self, channel):
        """Enable AM modulation"""
        if not self.check_connection():
            return

        try:
            depth = float(getattr(self, f"ch{channel}_am_depth").get())
            freq = float(getattr(self, f"ch{channel}_am_freq").get())
            self.gen.set_am_modulation(channel, depth, freq)
            messagebox.showinfo("OK", f"Channel {channel}: AM enabled (depth={depth}%, freq={freq}Hz)")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_fm_modulation(self, channel):
        """Enable FM modulation"""
        if not self.check_connection():
            return

        try:
            dev = float(getattr(self, f"ch{channel}_fm_dev").get())
            freq = float(getattr(self, f"ch{channel}_fm_freq").get())
            self.gen.set_fm_modulation(channel, dev, freq)
            messagebox.showinfo("OK", f"Channel {channel}: FM enabled (dev={dev}Hz, freq={freq}Hz)")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def modulation_off(self, channel):
        """Disable modulation"""
        if not self.check_connection():
            return

        try:
            self.gen.modulation_off(channel)
            messagebox.showinfo("OK", f"Channel {channel}: modulation disabled")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # === OUTPUT METHODS ===

    def set_output_load(self, channel):
        """Set load impedance"""
        if not self.check_connection():
            return

        try:
            load = getattr(self, f"ch{channel}_load").get()
            self.gen.set_output_load(channel, load)
            messagebox.showinfo("OK", f"Channel {channel}: load → {load} Ω")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def output_on(self, channel):
        """Enable output"""
        if not self.check_connection():
            return

        try:
            self.gen.output_on(channel)
            messagebox.showinfo("OK", f"Channel {channel}: OUTPUT ON")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def output_off(self, channel):
        """Disable output"""
        if not self.check_connection():
            return

        try:
            self.gen.output_off(channel)
            messagebox.showinfo("OK", f"Channel {channel}: OUTPUT OFF")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def read_status(self, channel):
        """Read current channel status"""
        if not self.check_connection():
            return

        try:
            func = self.gen.get_function(channel)
            freq_hz = float(self.gen.get_frequency(channel))
            ampl = self.gen.get_amplitude(channel)
            ampl_unit = self.gen.get_amplitude_unit(channel)
            is_on = self.gen.is_output_on(channel)

            # Format frequency in the most appropriate unit
            if freq_hz >= 1000000:
                freq_display = f"{freq_hz/1000000:.3f} MHz"
                best_unit = "MHZ"
                best_value = freq_hz/1000000
            elif freq_hz >= 1000:
                freq_display = f"{freq_hz/1000:.3f} kHz"
                best_unit = "KHZ"
                best_value = freq_hz/1000
            else:
                freq_display = f"{freq_hz:.1f} Hz"
                best_unit = "HZ"
                best_value = freq_hz

            status_text = getattr(self, f"ch{channel}_status")
            status_text.delete(1.0, tk.END)
            status_text.insert(tk.END, f"=== CHANNEL {channel} ===\n\n")
            status_text.insert(tk.END, f"Waveform: {func}\n")
            status_text.insert(tk.END, f"Frequency: {freq_display}\n")

            # Format amplitude unit
            unit_str = {"VPP": "Vpp", "VRMS": "Vrms", "DBM": "dBm"}.get(ampl_unit, ampl_unit)
            status_text.insert(tk.END, f"Amplitude: {ampl} {unit_str}\n")
            status_text.insert(tk.END, f"Output: {'ON' if is_on else 'OFF'}\n")

            # Also update GUI controls with read values
            getattr(self, f"ch{channel}_ampl_unit").set(ampl_unit)
            getattr(self, f"ch{channel}_freq_unit").set(best_unit)
            getattr(self, f"ch{channel}_freq").set(f"{best_value:.3f}" if best_unit != "HZ" else f"{best_value:.1f}")

            # Update labels
            ampl_label = getattr(self, f"ch{channel}_ampl_label")
            if ampl_unit == "VPP":
                ampl_label.config(text="Amplitude (Vpp):")
            elif ampl_unit == "VRMS":
                ampl_label.config(text="Amplitude (Vrms):")
            elif ampl_unit == "DBM":
                ampl_label.config(text="Power (dBm):")

            freq_label = getattr(self, f"ch{channel}_freq_label")
            if best_unit == "HZ":
                freq_label.config(text="Frequency (Hz):")
            elif best_unit == "KHZ":
                freq_label.config(text="Frequency (kHz):")
            elif best_unit == "MHZ":
                freq_label.config(text="Frequency (MHz):")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # === ARBITRARY WAVEFORM METHODS ===

    def load_csv(self):
        """Load waveform from CSV"""
        if not self.check_connection():
            return

        filename = filedialog.askopenfilename(
            title="Select CSV file",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )

        if not filename:
            return

        self.csv_path_label.config(text=f"File: {filename}")

        try:
            channel = int(self.arb_channel.get())
            name = self.arb_name.get()
            normalize = self.arb_normalize.get()

            num_points = self.gen.load_arb_from_csv(channel, filename, name, normalize)

            self.arb_info.delete(1.0, tk.END)
            self.arb_info.insert(tk.END, f"File loaded: {filename}\n")
            self.arb_info.insert(tk.END, f"Points loaded: {num_points}\n")
            self.arb_info.insert(tk.END, f"Name: {name}\n")
            self.arb_info.insert(tk.END, f"Normalized: {'Yes' if normalize else 'No'}\n")
            self.arb_info.insert(tk.END, f"\nUse 'Load ARB' to activate the waveform")

            messagebox.showinfo("OK", f"Loaded {num_points} points from CSV")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_wav(self):
        """Load waveform from WAV file"""
        if not self.check_connection():
            return

        filename = filedialog.askopenfilename(
            title="Select WAV file",
            filetypes=[("WAV files", "*.wav"), ("All files", "*.*")]
        )

        if not filename:
            return

        self.wav_path_label.config(text=f"File: {filename}")

        try:
            import tempfile
            import os

            channel = int(self.arb_channel.get())
            name = self.arb_name.get()
            max_points = int(self.wav_max_points.get())
            wav_channel = int(self.wav_channel.get().split()[0])  # Extract number from "0 (Left/Mono)"

            # Convert WAV to temporary CSV
            temp_csv = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
            temp_csv.close()

            # Convert WAV to CSV
            info = wav_to_csv(filename, temp_csv.name, max_points=max_points,
                            channel=wav_channel, normalize=True)

            # Load CSV into generator
            num_points = self.gen.load_arb_from_csv(channel, temp_csv.name, name, normalize=False)

            # Set suggested sample rate
            self.arb_srate.set(f"{info['suggested_sample_rate']:.0f}")
            self.gen.set_arb_sample_rate(channel, info['suggested_sample_rate'])

            # Clean up temp file
            os.unlink(temp_csv.name)

            # Update info
            self.arb_info.delete(1.0, tk.END)
            self.arb_info.insert(tk.END, f"WAV file loaded: {os.path.basename(filename)}\n")
            self.arb_info.insert(tk.END, f"Original sample rate: {info['sample_rate']} Hz\n")
            self.arb_info.insert(tk.END, f"Duration: {info['duration']:.3f} seconds\n")
            self.arb_info.insert(tk.END, f"Channels: {info['channels']}\n")
            self.arb_info.insert(tk.END, f"Points exported: {info['num_points']}\n")
            self.arb_info.insert(tk.END, f"Generator sample rate: {info['suggested_sample_rate']:.0f} Sa/s\n")
            self.arb_info.insert(tk.END, f"Downsampled: {'Yes' if info['downsampled'] else 'No'}\n")
            self.arb_info.insert(tk.END, f"Name: {name}\n")
            self.arb_info.insert(tk.END, f"\nUse 'Load ARB' to activate the waveform")

            messagebox.showinfo("OK",
                f"Loaded {num_points} points from WAV\n"
                f"Sample rate set to {info['suggested_sample_rate']:.0f} Sa/s")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def generate_arb(self):
        """Generate mathematical waveform"""
        if not self.check_connection():
            return

        try:
            channel = int(self.arb_channel.get())
            name = self.arb_name.get()
            arb_type = self.arb_type.get()
            points = int(self.arb_points.get())

            # Generate data
            t = np.linspace(-np.pi, np.pi, points)

            if arb_type == "sinc":
                data = np.sinc(t)
            elif arb_type == "gauss":
                data = np.exp(-t**2 / 2)
            elif arb_type == "exponential":
                data = np.exp(-abs(t))
            elif arb_type == "chirp":
                data = np.sin(t**2)
            else:
                raise ValueError(f"Unknown type: {arb_type}")

            # Normalize
            data = data / np.max(np.abs(data))

            self.gen.create_arb_waveform(channel, data.tolist(), name)

            self.arb_info.delete(1.0, tk.END)
            self.arb_info.insert(tk.END, f"Waveform generated: {arb_type}\n")
            self.arb_info.insert(tk.END, f"Points: {points}\n")
            self.arb_info.insert(tk.END, f"Name: {name}\n")
            self.arb_info.insert(tk.END, f"\nUse 'Load ARB' to activate the waveform")

            messagebox.showinfo("OK", f"Waveform '{arb_type}' generated ({points} points)")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def set_sample_rate(self):
        """Set sample rate"""
        if not self.check_connection():
            return

        try:
            channel = int(self.arb_channel.get())
            rate = float(eval(self.arb_srate.get()))  # Allows scientific notation
            self.gen.set_arb_sample_rate(channel, rate)
            messagebox.showinfo("OK", f"Sample rate → {rate} Sa/s")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def list_arb_waveforms(self):
        """List saved waveforms"""
        if not self.check_connection():
            return

        try:
            waveforms = self.gen.get_arb_list()

            self.arb_info.delete(1.0, tk.END)
            self.arb_info.insert(tk.END, "=== SAVED WAVEFORMS ===\n\n")

            if waveforms:
                for wf in waveforms:
                    self.arb_info.insert(tk.END, f"- {wf}\n")
            else:
                self.arb_info.insert(tk.END, "No saved waveforms\n")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def load_arb(self):
        """Load ARB waveform"""
        if not self.check_connection():
            return

        try:
            channel = int(self.arb_channel.get())
            name = self.arb_load_name.get()

            if not name:
                messagebox.showwarning("Warning", "Enter waveform name")
                return

            self.gen.load_arb_waveform(channel, name)
            messagebox.showinfo("OK", f"Channel {channel}: loaded waveform '{name}'")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_arb(self):
        """Delete waveform"""
        if not self.check_connection():
            return

        try:
            name = self.arb_del_name.get()

            if not name:
                messagebox.showwarning("Warning", "Enter waveform name")
                return

            if messagebox.askyesno("Confirm", f"Delete '{name}'?"):
                self.gen.delete_arb_waveform(name)
                messagebox.showinfo("OK", f"Waveform '{name}' deleted")
        except Exception as e:
            messagebox.showerror("Error", str(e))


def main():
    root = tk.Tk()
    app = RigolDGGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
