#!/usr/bin/env python3
"""
GUI per controllo generatori Rigol DG800/DG900
Richiede: pip install pyvisa pyvisa-py numpy tkinter
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
from rigol_dg import RigolDG
import numpy as np
import pyvisa as visa

class DeviceSelectionDialog:
    def __init__(self, parent):
        self.result = None
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Selezione Dispositivo VISA")
        self.dialog.geometry("600x400")
        self.dialog.resizable(False, False)
        self.dialog.grab_set()  # Finestra modale
        self.dialog.transient(parent)

        # Centra la finestra
        self.dialog.geometry("+{}+{}".format(
            parent.winfo_rootx() + 50,
            parent.winfo_rooty() + 50
        ))

        self.setup_ui()
        self.scan_devices()

    def setup_ui(self):
        # Frame principale
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)

        # Titolo
        title_label = ttk.Label(main_frame, text="Seleziona Dispositivo VISA",
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 20))

        # Area di scansione
        scan_frame = ttk.Frame(main_frame)
        scan_frame.pack(fill="x", pady=(0, 10))

        ttk.Button(scan_frame, text="🔄 Rianalizza Dispositivi",
                  command=self.scan_devices).pack(side="left")

        self.scan_status = ttk.Label(scan_frame, text="")
        self.scan_status.pack(side="left", padx=(10, 0))

        # Lista dispositivi
        list_frame = ttk.Frame(main_frame)
        list_frame.pack(fill="both", expand=True, pady=(0, 20))

        ttk.Label(list_frame, text="Dispositivi trovati:").pack(anchor="w")

        # Listbox con scrollbar
        listbox_frame = ttk.Frame(list_frame)
        listbox_frame.pack(fill="both", expand=True, pady=(5, 0))

        self.device_listbox = tk.Listbox(listbox_frame, height=8, font=("Courier", 9))
        scrollbar = ttk.Scrollbar(listbox_frame, orient="vertical", command=self.device_listbox.yview)
        self.device_listbox.configure(yscrollcommand=scrollbar.set)

        self.device_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Frame info
        info_frame = ttk.LabelFrame(main_frame, text="Informazioni Dispositivo", padding=10)
        info_frame.pack(fill="x", pady=(0, 20))

        self.device_info = tk.Text(info_frame, height=4, wrap="word", font=("Courier", 8))
        self.device_info.pack(fill="x")

        # Eventi
        self.device_listbox.bind("<<ListboxSelect>>", self.on_device_select)
        self.device_listbox.bind("<Double-Button-1>", lambda e: self.connect_device())

        # Pulsanti
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")

        ttk.Button(button_frame, text="Annulla",
                  command=self.cancel).pack(side="right", padx=(10, 0))
        ttk.Button(button_frame, text="Connetti",
                  command=self.connect_device).pack(side="right")

        # Indirizzo manuale
        manual_frame = ttk.LabelFrame(main_frame, text="Indirizzo Manuale", padding=10)
        manual_frame.pack(fill="x", pady=(10, 0))

        ttk.Label(manual_frame, text="Indirizzo VISA:").pack(side="left")
        self.manual_entry = ttk.Entry(manual_frame, width=50)
        self.manual_entry.pack(side="left", padx=(5, 0), fill="x", expand=True)
        ttk.Button(manual_frame, text="Usa",
                  command=self.use_manual).pack(side="left", padx=(5, 0))

    def scan_devices(self):
        self.scan_status.config(text="Scansione in corso...")
        self.device_listbox.delete(0, tk.END)
        self.device_info.delete(1.0, tk.END)
        self.dialog.update()

        try:
            rm = visa.ResourceManager('@py')
            resources = rm.list_resources()

            if not resources:
                self.device_listbox.insert(tk.END, "Nessun dispositivo VISA trovato")
                self.scan_status.config(text="❌ Nessun dispositivo trovato")
            else:
                for i, res in enumerate(resources):
                    self.device_listbox.insert(tk.END, f"{i}: {res}")
                self.scan_status.config(text=f"✅ Trovati {len(resources)} dispositivi")

            rm.close()
        except Exception as e:
            self.device_listbox.insert(tk.END, f"Errore di scansione: {str(e)}")
            self.scan_status.config(text="❌ Errore scansione")

    def on_device_select(self, event):
        selection = self.device_listbox.curselection()
        if not selection:
            return

        line = self.device_listbox.get(selection[0])
        if ":" not in line or "Nessun" in line or "Errore" in line:
            self.device_info.delete(1.0, tk.END)
            return

        # Estrae l'indirizzo VISA
        resource_name = line.split(": ", 1)[1]

        # Mostra informazioni del dispositivo
        self.device_info.delete(1.0, tk.END)
        self.device_info.insert(tk.END, f"Indirizzo: {resource_name}\n")

        # Tenta di ottenere ID del dispositivo
        try:
            rm = visa.ResourceManager('@py')
            instr = rm.open_resource(resource_name)
            instr.timeout = 2000
            idn = instr.query("*IDN?").strip()
            self.device_info.insert(tk.END, f"Identificazione: {idn}")
            instr.close()
            rm.close()
        except:
            self.device_info.insert(tk.END, "Identificazione: Non disponibile")

    def connect_device(self):
        selection = self.device_listbox.curselection()
        if not selection:
            messagebox.showwarning("Attenzione", "Seleziona un dispositivo dalla lista")
            return

        line = self.device_listbox.get(selection[0])
        if ":" not in line or "Nessun" in line or "Errore" in line:
            messagebox.showwarning("Attenzione", "Seleziona un dispositivo valido")
            return

        self.result = line.split(": ", 1)[1]
        self.dialog.destroy()

    def use_manual(self):
        address = self.manual_entry.get().strip()
        if not address:
            messagebox.showwarning("Attenzione", "Inserisci un indirizzo VISA valido")
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
        """Crea l'interfaccia grafica"""

        # === FRAME CONNESSIONE ===
        conn_frame = ttk.LabelFrame(self.root, text="Connessione", padding=10)
        conn_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=5)

        ttk.Label(conn_frame, text="Indirizzo VISA:").grid(row=0, column=0, sticky="w")
        self.visa_entry = ttk.Entry(conn_frame, width=50)
        self.visa_entry.grid(row=0, column=1, padx=5)
        self.visa_entry.insert(0, "Auto-detect")

        self.connect_btn = ttk.Button(conn_frame, text="Connetti", command=self.connect)
        self.connect_btn.grid(row=0, column=2, padx=5)

        self.status_label = ttk.Label(conn_frame, text="Non connesso", foreground="red")
        self.status_label.grid(row=0, column=3, padx=10)

        # === NOTEBOOK PER CANALI ===
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=5)

        # Tab Canale 1
        self.channel1_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.channel1_frame, text="Canale 1")
        self.setup_channel_controls(self.channel1_frame, 1)

        # Tab Canale 2
        self.channel2_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.channel2_frame, text="Canale 2")
        self.setup_channel_controls(self.channel2_frame, 2)

        # Tab Forme d'onda arbitrarie
        self.arb_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.arb_frame, text="Forme d'onda ARB")
        self.setup_arb_controls()

        # Configura ridimensionamento
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

    def setup_channel_controls(self, parent, channel):
        """Crea i controlli per un canale"""

        # === FORMA D'ONDA ===
        wave_frame = ttk.LabelFrame(parent, text="Forma d'onda", padding=10)
        wave_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(wave_frame, text="Tipo:").grid(row=0, column=0, sticky="w")
        func_var = tk.StringVar(value="SIN")
        setattr(self, f"ch{channel}_func", func_var)
        func_combo = ttk.Combobox(wave_frame, textvariable=func_var, width=15,
                                  values=["SIN", "SQU", "RAMP", "PULSE", "NOIS", "DC", "ARB"])
        func_combo.grid(row=0, column=1, padx=5)
        func_combo.bind("<<ComboboxSelected>>", lambda e: self.update_function(channel))

        # === PARAMETRI BASE ===
        params_frame = ttk.LabelFrame(parent, text="Parametri", padding=10)
        params_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        # Frequenza
        freq_label = ttk.Label(params_frame, text="Frequenza (Hz):")
        freq_label.grid(row=0, column=0, sticky="w")
        setattr(self, f"ch{channel}_freq_label", freq_label)

        freq_var = tk.StringVar(value="1000")
        setattr(self, f"ch{channel}_freq", freq_var)
        freq_entry = ttk.Entry(params_frame, textvariable=freq_var, width=15)
        freq_entry.grid(row=0, column=1, padx=5)

        # Unità frequenza
        freq_unit_var = tk.StringVar(value="HZ")
        setattr(self, f"ch{channel}_freq_unit", freq_unit_var)
        freq_unit_combo = ttk.Combobox(params_frame, textvariable=freq_unit_var, width=8,
                                       values=["HZ", "KHZ", "MHZ"], state="readonly")
        freq_unit_combo.grid(row=0, column=2, padx=2)
        freq_unit_combo.bind("<<ComboboxSelected>>", lambda e: self.update_frequency_unit(channel))

        ttk.Button(params_frame, text="Applica",
                  command=lambda: self.set_frequency(channel)).grid(row=0, column=3, padx=5)

        # Ampiezza
        ampl_label = ttk.Label(params_frame, text="Ampiezza (Vpp):")
        ampl_label.grid(row=1, column=0, sticky="w")
        setattr(self, f"ch{channel}_ampl_label", ampl_label)

        ampl_var = tk.StringVar(value="2")
        setattr(self, f"ch{channel}_ampl", ampl_var)
        ampl_entry = ttk.Entry(params_frame, textvariable=ampl_var, width=15)
        ampl_entry.grid(row=1, column=1, padx=5)

        # Unità ampiezza
        unit_var = tk.StringVar(value="VPP")
        setattr(self, f"ch{channel}_ampl_unit", unit_var)
        unit_combo = ttk.Combobox(params_frame, textvariable=unit_var, width=8,
                                  values=["VPP", "VRMS", "DBM"], state="readonly")
        unit_combo.grid(row=1, column=2, padx=2)
        unit_combo.bind("<<ComboboxSelected>>", lambda e: self.update_amplitude_unit(channel))

        ttk.Button(params_frame, text="Applica",
                  command=lambda: self.set_amplitude(channel)).grid(row=1, column=3, padx=5)

        # Offset
        ttk.Label(params_frame, text="Offset (V):").grid(row=2, column=0, sticky="w")
        offset_var = tk.StringVar(value="0")
        setattr(self, f"ch{channel}_offset", offset_var)
        offset_entry = ttk.Entry(params_frame, textvariable=offset_var, width=20)
        offset_entry.grid(row=2, column=1, padx=5)

        ttk.Button(params_frame, text="Applica",
                  command=lambda: self.set_offset(channel)).grid(row=2, column=2, padx=5)

        # Fase
        ttk.Label(params_frame, text="Fase (°):").grid(row=3, column=0, sticky="w")
        phase_var = tk.StringVar(value="0")
        setattr(self, f"ch{channel}_phase", phase_var)
        phase_entry = ttk.Entry(params_frame, textvariable=phase_var, width=20)
        phase_entry.grid(row=3, column=1, padx=5)

        ttk.Button(params_frame, text="Applica",
                  command=lambda: self.set_phase(channel)).grid(row=3, column=2, padx=5)

        # Duty Cycle (per onda quadra)
        ttk.Label(params_frame, text="Duty Cycle (%):").grid(row=4, column=0, sticky="w")
        duty_var = tk.StringVar(value="50")
        setattr(self, f"ch{channel}_duty", duty_var)
        duty_entry = ttk.Entry(params_frame, textvariable=duty_var, width=20)
        duty_entry.grid(row=4, column=1, padx=5)

        ttk.Button(params_frame, text="Applica",
                  command=lambda: self.set_duty_cycle(channel)).grid(row=4, column=2, padx=5)

        # === MODULAZIONE ===
        mod_frame = ttk.LabelFrame(parent, text="Modulazione", padding=10)
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

        ttk.Button(mod_frame, text="Attiva AM",
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

        ttk.Button(mod_frame, text="Attiva FM",
                  command=lambda: self.set_fm_modulation(channel)).grid(row=1, column=4, padx=5)

        # Disattiva modulazione
        ttk.Button(mod_frame, text="Disattiva Modulazione",
                  command=lambda: self.modulation_off(channel)).grid(row=2, column=0, columnspan=5, pady=10)

        # === OUTPUT ===
        output_frame = ttk.LabelFrame(parent, text="Output", padding=10)
        output_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(output_frame, text="Carico (Ω):").grid(row=0, column=0, sticky="w")
        load_var = tk.StringVar(value="50")
        setattr(self, f"ch{channel}_load", load_var)
        load_combo = ttk.Combobox(output_frame, textvariable=load_var, width=15,
                                  values=["50", "75", "600", "1000", "INF"])
        load_combo.grid(row=0, column=1, padx=5)

        ttk.Button(output_frame, text="Applica",
                  command=lambda: self.set_output_load(channel)).grid(row=0, column=2, padx=5)

        # Pulsanti ON/OFF
        btn_frame = ttk.Frame(output_frame)
        btn_frame.grid(row=1, column=0, columnspan=3, pady=10)

        ttk.Button(btn_frame, text="OUTPUT ON",
                  command=lambda: self.output_on(channel)).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="OUTPUT OFF",
                  command=lambda: self.output_off(channel)).pack(side="left", padx=5)

        # Configurazione rapida RF
        rf_frame = ttk.Frame(output_frame)
        rf_frame.grid(row=2, column=0, columnspan=3, pady=10)

        ttk.Button(rf_frame, text="⚡ Config RF (50Ω + dBm)",
                  command=lambda: self.set_rf_mode(channel)).pack(side="left", padx=5)

        # === LETTURA STATO ===
        status_frame = ttk.LabelFrame(parent, text="Stato Corrente", padding=10)
        status_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

        status_text = tk.Text(status_frame, height=6, width=70)
        status_text.grid(row=0, column=0, padx=5, pady=5)
        setattr(self, f"ch{channel}_status", status_text)

        ttk.Button(status_frame, text="Aggiorna Stato",
                  command=lambda: self.read_status(channel)).grid(row=1, column=0, pady=5)

    def setup_arb_controls(self):
        """Crea i controlli per forme d'onda arbitrarie"""

        # === CARICA DA CSV ===
        csv_frame = ttk.LabelFrame(self.arb_frame, text="Carica da CSV", padding=10)
        csv_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(csv_frame, text="Canale:").grid(row=0, column=0, sticky="w")
        self.arb_channel = tk.StringVar(value="1")
        ttk.Combobox(csv_frame, textvariable=self.arb_channel, width=10,
                    values=["1", "2"]).grid(row=0, column=1, padx=5)

        ttk.Label(csv_frame, text="Nome:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.arb_name = tk.StringVar(value="CUSTOM")
        ttk.Entry(csv_frame, textvariable=self.arb_name, width=20).grid(row=0, column=3, padx=5)

        self.arb_normalize = tk.BooleanVar(value=True)
        ttk.Checkbutton(csv_frame, text="Normalizza",
                       variable=self.arb_normalize).grid(row=0, column=4, padx=10)

        ttk.Button(csv_frame, text="Seleziona File CSV",
                  command=self.load_csv).grid(row=1, column=0, columnspan=5, pady=10)

        self.csv_path_label = ttk.Label(csv_frame, text="Nessun file selezionato")
        self.csv_path_label.grid(row=2, column=0, columnspan=5)

        # === CREA DA FUNZIONE ===
        func_frame = ttk.LabelFrame(self.arb_frame, text="Genera Forma d'Onda", padding=10)
        func_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(func_frame, text="Tipo:").grid(row=0, column=0, sticky="w")
        self.arb_type = tk.StringVar(value="sinc")
        ttk.Combobox(func_frame, textvariable=self.arb_type, width=15,
                    values=["sinc", "gauss", "exponential", "chirp"]).grid(row=0, column=1, padx=5)

        ttk.Label(func_frame, text="Punti:").grid(row=0, column=2, sticky="w", padx=(20,0))
        self.arb_points = tk.StringVar(value="1000")
        ttk.Entry(func_frame, textvariable=self.arb_points, width=15).grid(row=0, column=3, padx=5)

        ttk.Button(func_frame, text="Genera e Carica",
                  command=self.generate_arb).grid(row=1, column=0, columnspan=4, pady=10)

        # === SAMPLE RATE ===
        srate_frame = ttk.LabelFrame(self.arb_frame, text="Sample Rate", padding=10)
        srate_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=5)

        ttk.Label(srate_frame, text="Sample Rate (Sa/s):").grid(row=0, column=0, sticky="w")
        self.arb_srate = tk.StringVar(value="1e6")
        ttk.Entry(srate_frame, textvariable=self.arb_srate, width=20).grid(row=0, column=1, padx=5)

        ttk.Button(srate_frame, text="Applica",
                  command=self.set_sample_rate).grid(row=0, column=2, padx=5)

        # === GESTIONE FORME D'ONDA ===
        manage_frame = ttk.LabelFrame(self.arb_frame, text="Gestione Forme d'Onda", padding=10)
        manage_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=5)

        ttk.Button(manage_frame, text="Lista Forme d'Onda",
                  command=self.list_arb_waveforms).grid(row=0, column=0, padx=5, pady=5)

        ttk.Label(manage_frame, text="Carica:").grid(row=1, column=0, sticky="w")
        self.arb_load_name = tk.StringVar()
        ttk.Entry(manage_frame, textvariable=self.arb_load_name, width=20).grid(row=1, column=1, padx=5)
        ttk.Button(manage_frame, text="Carica ARB",
                  command=self.load_arb).grid(row=1, column=2, padx=5)

        ttk.Label(manage_frame, text="Elimina:").grid(row=2, column=0, sticky="w")
        self.arb_del_name = tk.StringVar()
        ttk.Entry(manage_frame, textvariable=self.arb_del_name, width=20).grid(row=2, column=1, padx=5)
        ttk.Button(manage_frame, text="Elimina",
                  command=self.delete_arb).grid(row=2, column=2, padx=5)

        # === AREA INFO ===
        info_frame = ttk.LabelFrame(self.arb_frame, text="Informazioni", padding=10)
        info_frame.grid(row=4, column=0, sticky="ew", padx=10, pady=5)

        self.arb_info = tk.Text(info_frame, height=8, width=70)
        self.arb_info.grid(row=0, column=0, padx=5, pady=5)

    # === METODI CONNESSIONE ===

    def connect(self):
        """Connette al generatore"""
        if self.connected:
            messagebox.showinfo("Info", "Già connesso")
            return

        visa_addr = self.visa_entry.get()

        # Se è auto-detect, mostra dialog di selezione
        if visa_addr == "Auto-detect" or visa_addr == "":
            dialog = DeviceSelectionDialog(self.root)
            self.root.wait_window(dialog.dialog)

            if dialog.result is None:
                return  # Utente ha annullato

            visa_addr = dialog.result

        def do_connect():
            try:
                # Connette direttamente con l'indirizzo specificato
                self.gen = RigolDG(visa_addr)

                self.connected = True
                self.root.after(0, lambda: self.status_label.config(
                    text=f"Connesso: {self.gen.identify()}", foreground="green"))
                self.root.after(0, lambda: messagebox.showinfo(
                    "Successo", "Connesso al generatore"))

                # Aggiorna il campo indirizzo con quello selezionato
                self.root.after(0, lambda: self.visa_entry.delete(0, tk.END))
                self.root.after(0, lambda: self.visa_entry.insert(0, visa_addr))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror(
                    "Errore", f"Errore di connessione:\n{str(e)}"))

        threading.Thread(target=do_connect, daemon=True).start()

    def check_connection(self):
        """Verifica connessione attiva"""
        if not self.connected or self.gen is None:
            messagebox.showerror("Errore", "Non connesso al generatore")
            return False
        return True

    # === METODI CONTROLLO CANALE ===

    def update_function(self, channel):
        """Aggiorna forma d'onda"""
        if not self.check_connection():
            return

        try:
            func = getattr(self, f"ch{channel}_func").get()
            self.gen.set_function(channel, func)
            messagebox.showinfo("OK", f"Canale {channel}: forma d'onda → {func}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_frequency(self, channel):
        """Imposta frequenza con unità corrente"""
        if not self.check_connection():
            return

        try:
            freq_value = float(getattr(self, f"ch{channel}_freq").get())
            freq_unit = getattr(self, f"ch{channel}_freq_unit").get()

            # Usa il metodo con unità
            self.gen.set_frequency_with_unit(channel, freq_value, freq_unit)

            # Messaggio con unità corretta
            unit_str = {"HZ": "Hz", "KHZ": "kHz", "MHZ": "MHz"}[freq_unit]
            messagebox.showinfo("OK", f"Canale {channel}: frequenza → {freq_value} {unit_str}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_amplitude(self, channel):
        """Imposta ampiezza con unità corrente"""
        if not self.check_connection():
            return

        try:
            ampl = float(getattr(self, f"ch{channel}_ampl").get())
            unit = getattr(self, f"ch{channel}_ampl_unit").get()

            # Imposta l'unità prima del valore
            self.gen.set_amplitude_unit(channel, unit)
            self.gen.set_amplitude(channel, ampl)

            # Messaggio con unità corretta
            unit_str = {"VPP": "Vpp", "VRMS": "Vrms", "DBM": "dBm"}[unit]
            messagebox.showinfo("OK", f"Canale {channel}: ampiezza → {ampl} {unit_str}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_offset(self, channel):
        """Imposta offset"""
        if not self.check_connection():
            return

        try:
            offset = float(getattr(self, f"ch{channel}_offset").get())
            self.gen.set_offset(channel, offset)
            messagebox.showinfo("OK", f"Canale {channel}: offset → {offset} V")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_phase(self, channel):
        """Imposta fase"""
        if not self.check_connection():
            return

        try:
            phase = float(getattr(self, f"ch{channel}_phase").get())
            self.gen.set_phase(channel, phase)
            messagebox.showinfo("OK", f"Canale {channel}: fase → {phase}°")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_duty_cycle(self, channel):
        """Imposta duty cycle"""
        if not self.check_connection():
            return

        try:
            duty = float(getattr(self, f"ch{channel}_duty").get())
            self.gen.set_duty_cycle(channel, duty)
            messagebox.showinfo("OK", f"Canale {channel}: duty cycle → {duty}%")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def update_amplitude_unit(self, channel):
        """Aggiorna l'unità di ampiezza e l'etichetta"""
        if not self.check_connection():
            return

        try:
            unit = getattr(self, f"ch{channel}_ampl_unit").get()
            self.gen.set_amplitude_unit(channel, unit)

            # Aggiorna l'etichetta
            label = getattr(self, f"ch{channel}_ampl_label")
            if unit == "VPP":
                label.config(text="Ampiezza (Vpp):")
            elif unit == "VRMS":
                label.config(text="Ampiezza (Vrms):")
            elif unit == "DBM":
                label.config(text="Potenza (dBm):")

            messagebox.showinfo("OK", f"Canale {channel}: unità ampiezza → {unit}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def update_frequency_unit(self, channel):
        """Aggiorna l'unità di frequenza e l'etichetta"""
        try:
            unit = getattr(self, f"ch{channel}_freq_unit").get()

            # Aggiorna l'etichetta
            label = getattr(self, f"ch{channel}_freq_label")
            if unit == "HZ":
                label.config(text="Frequenza (Hz):")
            elif unit == "KHZ":
                label.config(text="Frequenza (kHz):")
            elif unit == "MHZ":
                label.config(text="Frequenza (MHz):")

            messagebox.showinfo("OK", f"Canale {channel}: unità frequenza → {unit}")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_rf_mode(self, channel):
        """Configura rapidamente per misure RF (50Ω + dBm)"""
        if not self.check_connection():
            return

        try:
            # Imposta carico 50Ω e unità dBm
            self.gen.set_50ohm_dbm_mode(channel)

            # Aggiorna i controlli GUI
            getattr(self, f"ch{channel}_load").set("50")
            getattr(self, f"ch{channel}_ampl_unit").set("DBM")

            # Aggiorna l'etichetta ampiezza
            label = getattr(self, f"ch{channel}_ampl_label")
            label.config(text="Potenza (dBm):")

            messagebox.showinfo("OK", f"Canale {channel}: configurato per RF (50Ω + dBm)")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    # === METODI MODULAZIONE ===

    def set_am_modulation(self, channel):
        """Attiva modulazione AM"""
        if not self.check_connection():
            return

        try:
            depth = float(getattr(self, f"ch{channel}_am_depth").get())
            freq = float(getattr(self, f"ch{channel}_am_freq").get())
            self.gen.set_am_modulation(channel, depth, freq)
            messagebox.showinfo("OK", f"Canale {channel}: AM attivata (depth={depth}%, freq={freq}Hz)")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_fm_modulation(self, channel):
        """Attiva modulazione FM"""
        if not self.check_connection():
            return

        try:
            dev = float(getattr(self, f"ch{channel}_fm_dev").get())
            freq = float(getattr(self, f"ch{channel}_fm_freq").get())
            self.gen.set_fm_modulation(channel, dev, freq)
            messagebox.showinfo("OK", f"Canale {channel}: FM attivata (dev={dev}Hz, freq={freq}Hz)")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def modulation_off(self, channel):
        """Disattiva modulazione"""
        if not self.check_connection():
            return

        try:
            self.gen.modulation_off(channel)
            messagebox.showinfo("OK", f"Canale {channel}: modulazione disattivata")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    # === METODI OUTPUT ===

    def set_output_load(self, channel):
        """Imposta impedenza di carico"""
        if not self.check_connection():
            return

        try:
            load = getattr(self, f"ch{channel}_load").get()
            self.gen.set_output_load(channel, load)
            messagebox.showinfo("OK", f"Canale {channel}: carico → {load} Ω")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def output_on(self, channel):
        """Attiva output"""
        if not self.check_connection():
            return

        try:
            self.gen.output_on(channel)
            messagebox.showinfo("OK", f"Canale {channel}: OUTPUT ON")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def output_off(self, channel):
        """Disattiva output"""
        if not self.check_connection():
            return

        try:
            self.gen.output_off(channel)
            messagebox.showinfo("OK", f"Canale {channel}: OUTPUT OFF")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def read_status(self, channel):
        """Legge stato corrente del canale"""
        if not self.check_connection():
            return

        try:
            func = self.gen.get_function(channel)
            freq_hz = float(self.gen.get_frequency(channel))
            ampl = self.gen.get_amplitude(channel)
            ampl_unit = self.gen.get_amplitude_unit(channel)
            is_on = self.gen.is_output_on(channel)

            # Formatta frequenza nell'unità più appropriata
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
            status_text.insert(tk.END, f"=== CANALE {channel} ===\n\n")
            status_text.insert(tk.END, f"Forma d'onda: {func}\n")
            status_text.insert(tk.END, f"Frequenza: {freq_display}\n")

            # Formatta unità ampiezza
            unit_str = {"VPP": "Vpp", "VRMS": "Vrms", "DBM": "dBm"}.get(ampl_unit, ampl_unit)
            status_text.insert(tk.END, f"Ampiezza: {ampl} {unit_str}\n")
            status_text.insert(tk.END, f"Output: {'ON' if is_on else 'OFF'}\n")

            # Aggiorna anche i controlli GUI con i valori letti
            getattr(self, f"ch{channel}_ampl_unit").set(ampl_unit)
            getattr(self, f"ch{channel}_freq_unit").set(best_unit)
            getattr(self, f"ch{channel}_freq").set(f"{best_value:.3f}" if best_unit != "HZ" else f"{best_value:.1f}")

            # Aggiorna le etichette
            ampl_label = getattr(self, f"ch{channel}_ampl_label")
            if ampl_unit == "VPP":
                ampl_label.config(text="Ampiezza (Vpp):")
            elif ampl_unit == "VRMS":
                ampl_label.config(text="Ampiezza (Vrms):")
            elif ampl_unit == "DBM":
                ampl_label.config(text="Potenza (dBm):")

            freq_label = getattr(self, f"ch{channel}_freq_label")
            if best_unit == "HZ":
                freq_label.config(text="Frequenza (Hz):")
            elif best_unit == "KHZ":
                freq_label.config(text="Frequenza (kHz):")
            elif best_unit == "MHZ":
                freq_label.config(text="Frequenza (MHz):")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    # === METODI FORME D'ONDA ARBITRARIE ===

    def load_csv(self):
        """Carica forma d'onda da CSV"""
        if not self.check_connection():
            return

        filename = filedialog.askopenfilename(
            title="Seleziona file CSV",
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
            self.arb_info.insert(tk.END, f"File caricato: {filename}\n")
            self.arb_info.insert(tk.END, f"Punti caricati: {num_points}\n")
            self.arb_info.insert(tk.END, f"Nome: {name}\n")
            self.arb_info.insert(tk.END, f"Normalizzato: {'Sì' if normalize else 'No'}\n")
            self.arb_info.insert(tk.END, f"\nUsa 'Carica ARB' per attivare la forma d'onda")

            messagebox.showinfo("OK", f"Caricati {num_points} punti da CSV")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def generate_arb(self):
        """Genera forma d'onda matematica"""
        if not self.check_connection():
            return

        try:
            channel = int(self.arb_channel.get())
            name = self.arb_name.get()
            arb_type = self.arb_type.get()
            points = int(self.arb_points.get())

            # Genera dati
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
                raise ValueError(f"Tipo sconosciuto: {arb_type}")

            # Normalizza
            data = data / np.max(np.abs(data))

            self.gen.create_arb_waveform(channel, data.tolist(), name)

            self.arb_info.delete(1.0, tk.END)
            self.arb_info.insert(tk.END, f"Forma d'onda generata: {arb_type}\n")
            self.arb_info.insert(tk.END, f"Punti: {points}\n")
            self.arb_info.insert(tk.END, f"Nome: {name}\n")
            self.arb_info.insert(tk.END, f"\nUsa 'Carica ARB' per attivare la forma d'onda")

            messagebox.showinfo("OK", f"Forma d'onda '{arb_type}' generata ({points} punti)")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def set_sample_rate(self):
        """Imposta sample rate"""
        if not self.check_connection():
            return

        try:
            channel = int(self.arb_channel.get())
            rate = float(eval(self.arb_srate.get()))  # Permette notazione scientifica
            self.gen.set_arb_sample_rate(channel, rate)
            messagebox.showinfo("OK", f"Sample rate → {rate} Sa/s")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def list_arb_waveforms(self):
        """Lista forme d'onda salvate"""
        if not self.check_connection():
            return

        try:
            waveforms = self.gen.get_arb_list()

            self.arb_info.delete(1.0, tk.END)
            self.arb_info.insert(tk.END, "=== FORME D'ONDA SALVATE ===\n\n")

            if waveforms:
                for wf in waveforms:
                    self.arb_info.insert(tk.END, f"- {wf}\n")
            else:
                self.arb_info.insert(tk.END, "Nessuna forma d'onda salvata\n")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def load_arb(self):
        """Carica forma d'onda ARB"""
        if not self.check_connection():
            return

        try:
            channel = int(self.arb_channel.get())
            name = self.arb_load_name.get()

            if not name:
                messagebox.showwarning("Attenzione", "Inserisci nome forma d'onda")
                return

            self.gen.load_arb_waveform(channel, name)
            messagebox.showinfo("OK", f"Canale {channel}: caricata forma d'onda '{name}'")
        except Exception as e:
            messagebox.showerror("Errore", str(e))

    def delete_arb(self):
        """Elimina forma d'onda"""
        if not self.check_connection():
            return

        try:
            name = self.arb_del_name.get()

            if not name:
                messagebox.showwarning("Attenzione", "Inserisci nome forma d'onda")
                return

            if messagebox.askyesno("Conferma", f"Eliminare '{name}'?"):
                self.gen.delete_arb_waveform(name)
                messagebox.showinfo("OK", f"Forma d'onda '{name}' eliminata")
        except Exception as e:
            messagebox.showerror("Errore", str(e))


def main():
    root = tk.Tk()
    app = RigolDGGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
