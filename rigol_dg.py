#!/usr/bin/env python3
"""
Controller per generatori Rigol DG800/DG900
Richiede: pip install pyvisa pyvisa-py
"""

import pyvisa as visa
import numpy as np

class RigolDG:
    def __init__(self, resource_name=None):
        """
        Inizializza connessione al generatore Rigol DG800/DG900

        Args:
            resource_name: Stringa identificativa VISA del dispositivo
                          Es: 'USB0::0x1AB1::0x0642::DG9A12345678::INSTR'
                          Es: 'TCPIP0::192.168.1.100::INSTR'
                          Se None, mostra lista dispositivi disponibili
        """
        # Inizializza ResourceManager VISA con backend PyVISA-py
        self.rm = visa.ResourceManager('@py')

        # Se non specificato, rileva automaticamente i dispositivi
        if resource_name is None:
            resources = self.rm.list_resources()
            print("Dispositivi trovati:")
            for i, res in enumerate(resources):
                print(f"{i}: {res}")

            if not resources:
                raise Exception("Nessun dispositivo VISA trovato")

            idx = int(input("Seleziona dispositivo (numero): "))
            resource_name = resources[idx]

        # Apre connessione con timeout di 5 secondi
        self.instr = self.rm.open_resource(resource_name)
        self.instr.timeout = 5000
        print(f"Connesso: {self.identify()}")

    def identify(self):
        """
        Identifica lo strumento tramite comando SCPI *IDN?

        Returns:
            str: Stringa identificativa (produttore, modello, seriale, firmware)
        """
        return self.instr.query("*IDN?").strip()

    def reset(self):
        """
        Esegue reset dello strumento ai valori di fabbrica
        Comando SCPI: *RST
        """
        self.instr.write("*RST")

    # === CONTROLLO CANALE ===

    def set_function(self, channel, func):
        """
        Imposta la forma d'onda per il canale specificato

        Args:
            channel: Numero canale (1 o 2)
            func: Tipo di forma d'onda - valori ammessi:
                  'SIN'   - Sinusoide
                  'SQU'   - Onda quadra
                  'RAMP'  - Rampa/triangolare
                  'PULSE' - Impulso
                  'NOIS'  - Rumore
                  'ARB'   - Arbitraria
                  'DC'    - Continua
        """
        self.instr.write(f"SOUR{channel}:FUNC {func}")

    def set_frequency(self, channel, freq):
        """
        Imposta la frequenza del segnale

        Args:
            channel: Numero canale (1 o 2)
            freq: Frequenza in Hz (range dipende dal modello e dalla forma d'onda)
        """
        self.instr.write(f"SOUR{channel}:FREQ {freq}")

    def set_frequency_khz(self, channel, freq_khz):
        """
        Imposta la frequenza del segnale in kHz

        Args:
            channel: Numero canale (1 o 2)
            freq_khz: Frequenza in kHz
        """
        freq_hz = freq_khz * 1000
        self.instr.write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_frequency_mhz(self, channel, freq_mhz):
        """
        Imposta la frequenza del segnale in MHz

        Args:
            channel: Numero canale (1 o 2)
            freq_mhz: Frequenza in MHz
        """
        freq_hz = freq_mhz * 1000000
        self.instr.write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_frequency_with_unit(self, channel, value, unit):
        """
        Imposta la frequenza con unità specificata

        Args:
            channel: Numero canale (1 o 2)
            value: Valore numerico della frequenza
            unit: Unità di misura ('HZ', 'KHZ', 'MHZ')
        """
        if unit.upper() == 'HZ':
            freq_hz = value
        elif unit.upper() == 'KHZ':
            freq_hz = value * 1000
        elif unit.upper() == 'MHZ':
            freq_hz = value * 1000000
        else:
            raise ValueError(f"Unità non supportata: {unit}. Usa 'HZ', 'KHZ', o 'MHZ'")

        self.instr.write(f"SOUR{channel}:FREQ {freq_hz}")

    def set_amplitude(self, channel, ampl):
        """
        Imposta l'ampiezza del segnale

        Args:
            channel: Numero canale (1 o 2)
            ampl: Ampiezza in Vpp (Volt picco-picco)
                  Range tipico: 1mVpp - 10Vpp (dipende dal carico)
        """
        self.instr.write(f"SOUR{channel}:VOLT {ampl}")

    def set_amplitude_dbm(self, channel, dbm_value):
        """
        Imposta l'ampiezza del segnale in dBm (per carico 50Ω)

        Args:
            channel: Numero canale (1 o 2)
            dbm_value: Potenza in dBm
                      Range tipico: -40 dBm a +20 dBm (dipende dal modello)
        """
        self.instr.write(f"SOUR{channel}:VOLT:UNIT DBM")
        self.instr.write(f"SOUR{channel}:VOLT {dbm_value}")

    def set_amplitude_unit(self, channel, unit):
        """
        Imposta l'unità di misura per l'ampiezza

        Args:
            channel: Numero canale (1 o 2)
            unit: Unità di misura
                  'VPP' - Volt picco-picco
                  'VRMS' - Volt RMS
                  'DBM' - dBm (per carico 50Ω)
        """
        self.instr.write(f"SOUR{channel}:VOLT:UNIT {unit}")

    def get_amplitude_unit(self, channel):
        """
        Ottiene l'unità di misura corrente per l'ampiezza

        Args:
            channel: Numero canale (1 o 2)

        Returns:
            str: Unità corrente ('VPP', 'VRMS', 'DBM')
        """
        return self.instr.query(f"SOUR{channel}:VOLT:UNIT?").strip()

    def set_offset(self, channel, offset):
        """
        Imposta l'offset DC del segnale

        Args:
            channel: Numero canale (1 o 2)
            offset: Offset in Volt (può essere positivo o negativo)
        """
        self.instr.write(f"SOUR{channel}:VOLT:OFFS {offset}")

    def set_phase(self, channel, phase):
        """
        Imposta la fase del segnale

        Args:
            channel: Numero canale (1 o 2)
            phase: Fase in gradi (0-360°)
        """
        self.instr.write(f"SOUR{channel}:PHAS {phase}")

    def set_duty_cycle(self, channel, duty):
        """
        Imposta il duty cycle per onda quadra

        Args:
            channel: Numero canale (1 o 2)
            duty: Duty cycle in percentuale (tipicamente 0.01% - 99.99%)
                  50% = onda quadra simmetrica
        """
        self.instr.write(f"SOUR{channel}:FUNC:SQU:DCYC {duty}")

    # === CONTROLLO OUTPUT ===

    def output_on(self, channel):
        """
        Attiva l'output del canale specificato

        Args:
            channel: Numero canale (1 o 2)
        """
        self.instr.write(f"OUTP{channel} ON")

    def output_off(self, channel):
        """
        Disattiva l'output del canale specificato

        Args:
            channel: Numero canale (1 o 2)
        """
        self.instr.write(f"OUTP{channel} OFF")

    def set_output_load(self, channel, load):
        """
        Imposta l'impedenza di carico dell'output

        Args:
            channel: Numero canale (1 o 2)
            load: Impedenza in Ohm (es: 50) o 'INF' per alta impedenza
                  Il carico influenza l'ampiezza reale del segnale
        """
        self.instr.write(f"OUTP{channel}:LOAD {load}")

    def set_50ohm_dbm_mode(self, channel):
        """
        Configura rapidamente il canale per misure RF:
        - Impedenza di carico 50Ω
        - Unità di ampiezza in dBm

        Args:
            channel: Numero canale (1 o 2)
        """
        self.set_output_load(channel, "50")
        self.set_amplitude_unit(channel, "DBM")

    # === QUERY (LETTURA STATO) ===

    def get_frequency(self, channel):
        """
        Legge la frequenza attuale del canale

        Args:
            channel: Numero canale (1 o 2)

        Returns:
            float: Frequenza in Hz
        """
        return float(self.instr.query(f"SOUR{channel}:FREQ?"))

    def get_amplitude(self, channel):
        """
        Legge l'ampiezza attuale del canale

        Args:
            channel: Numero canale (1 o 2)

        Returns:
            float: Ampiezza in Vpp
        """
        return float(self.instr.query(f"SOUR{channel}:VOLT?"))

    def get_function(self, channel):
        """
        Legge la forma d'onda attuale del canale

        Args:
            channel: Numero canale (1 o 2)

        Returns:
            str: Tipo di forma d'onda (SIN, SQU, RAMP, ecc.)
        """
        return self.instr.query(f"SOUR{channel}:FUNC?").strip()

    def is_output_on(self, channel):
        """
        Verifica se l'output è attivo

        Args:
            channel: Numero canale (1 o 2)

        Returns:
            bool: True se attivo, False se disattivo
        """
        return self.instr.query(f"OUTP{channel}?").strip() == "ON"

    # === MODULAZIONE ===

    def set_am_modulation(self, channel, depth, freq):
        """
        Attiva modulazione di ampiezza (AM)

        Args:
            channel: Numero canale (1 o 2)
            depth: Profondità di modulazione in % (0-120)
            freq: Frequenza modulante in Hz
        """
        self.instr.write(f"SOUR{channel}:AM:STAT ON")
        self.instr.write(f"SOUR{channel}:AM:DEPT {depth}")
        self.instr.write(f"SOUR{channel}:AM:INT:FREQ {freq}")

    def set_fm_modulation(self, channel, deviation, freq):
        """
        Attiva modulazione di frequenza (FM)

        Args:
            channel: Numero canale (1 o 2)
            deviation: Deviazione di frequenza in Hz
            freq: Frequenza modulante in Hz
        """
        self.instr.write(f"SOUR{channel}:FM:STAT ON")
        self.instr.write(f"SOUR{channel}:FM:DEV {deviation}")
        self.instr.write(f"SOUR{channel}:FM:INT:FREQ {freq}")

    def modulation_off(self, channel):
        """
        Disattiva tutte le modulazioni (AM, FM, PM)

        Args:
            channel: Numero canale (1 o 2)
        """
        self.instr.write(f"SOUR{channel}:AM:STAT OFF")
        self.instr.write(f"SOUR{channel}:FM:STAT OFF")
        self.instr.write(f"SOUR{channel}:PM:STAT OFF")

    # === FORME D'ONDA ARBITRARIE ===

    def create_arb_waveform(self, channel, data, name=None):
        """
        Crea una forma d'onda arbitraria personalizzata

        Args:
            channel: Numero canale (1 o 2)
            data: Lista di valori normalizzati tra -1.0 e +1.0
                  Es: [0, 0.5, 1.0, 0.5, 0, -0.5, -1.0, -0.5]
            name: Nome da assegnare alla forma d'onda (opzionale)
                  Se None, carica direttamente nella memoria volatile
        """
        # Converte i dati in formato stringa CSV per comando SCPI
        data_str = ",".join([str(v) for v in data])

        if name:
            # Salva con nome in memoria non volatile
            self.instr.write(f"DATA:DAC VOLATILE,{data_str}")
            self.instr.write(f"DATA:COPY {name},VOLATILE")
        else:
            # Carica direttamente in memoria volatile
            self.instr.write(f"SOUR{channel}:DATA VOLATILE,{data_str}")

    def load_arb_waveform(self, channel, name):
        """
        Carica una forma d'onda arbitraria precedentemente salvata

        Args:
            channel: Numero canale (1 o 2)
            name: Nome della forma d'onda da caricare
        """
        self.instr.write(f"SOUR{channel}:FUNC ARB")
        self.instr.write(f"SOUR{channel}:FUNC:ARB {name}")

    def get_arb_list(self):
        """
        Restituisce lista delle forme d'onda arbitrarie salvate in memoria

        Returns:
            list: Lista dei nomi delle forme d'onda disponibili
        """
        return self.instr.query("DATA:CAT?").strip().split(',')

    def delete_arb_waveform(self, name):
        """
        Elimina una forma d'onda arbitraria dalla memoria

        Args:
            name: Nome della forma d'onda da eliminare
        """
        self.instr.write(f"DATA:DEL {name}")

    def set_arb_sample_rate(self, channel, rate):
        """
        Imposta il sample rate per la forma d'onda arbitraria

        Args:
            channel: Numero canale (1 o 2)
            rate: Sample rate in Sa/s (Samples per second)
                  Range tipico: 1 µSa/s - 200 MSa/s (dipende dal modello)
        """
        self.instr.write(f"SOUR{channel}:FUNC:ARB:SRAT {rate}")

    def get_arb_sample_rate(self, channel):
        """
        Legge il sample rate attuale della forma d'onda arbitraria

        Args:
            channel: Numero canale (1 o 2)

        Returns:
            float: Sample rate in Sa/s
        """
        return float(self.instr.query(f"SOUR{channel}:FUNC:ARB:SRAT?"))

    def load_arb_from_csv(self, channel, csv_file, name=None, normalize=True):
        """
        Carica forma d'onda arbitraria da file CSV

        Args:
            channel: Numero canale (1 o 2)
            csv_file: Percorso del file CSV da caricare
            name: Nome da assegnare alla forma d'onda (opzionale)
            normalize: Normalizza automaticamente i valori tra -1 e +1 (default: True)

        Returns:
            int: Numero di punti caricati

        FORMATI CSV SUPPORTATI:

        1) Una colonna con solo valori di ampiezza:
           0.0
           0.309
           0.588
           0.809
           0.951
           1.0
           ...

        2) Due colonne (tempo, ampiezza) - la colonna tempo viene ignorata:
           0.000, 0.0
           0.001, 0.309
           0.002, 0.588
           0.003, 0.809
           ...

        3) Con intestazione (viene automaticamente rilevata e ignorata):
           time,voltage
           0.000, 0.0
           0.001, 0.309
           ...

        NOTE:
        - I valori devono essere numerici
        - Se normalize=False, i valori devono essere già tra -1 e +1
        - Numero massimo punti: dipende dal modello (tipicamente 8k-16k)
        - Il separatore può essere virgola o punto e virgola
        - Righe non valide vengono automaticamente ignorate
        """
        import csv

        data = []

        with open(csv_file, 'r') as f:
            reader = csv.reader(f, delimiter=',')

            # Prova a rilevare e gestire intestazione
            first_row = next(reader)
            try:
                # Se la prima riga è numerica, usala come dato
                if len(first_row) == 1:
                    data.append(float(first_row[0]))
                else:
                    data.append(float(first_row[-1]))  # Prende ultima colonna
            except ValueError:
                # Prima riga è intestazione testuale, ignorala
                pass

            # Leggi tutti i dati rimanenti
            for row in reader:
                if len(row) == 0:
                    continue
                try:
                    # Prende l'ultima colonna (assume sia l'ampiezza)
                    value = float(row[-1].strip())
                    data.append(value)
                except ValueError:
                    continue  # Salta righe non valide

        if not data:
            raise ValueError("Nessun dato valido trovato nel file CSV")

        # Normalizza i valori tra -1 e +1 se richiesto
        if normalize:
            data_array = np.array(data)
            data_min = data_array.min()
            data_max = data_array.max()

            if data_max != data_min:
                # Formula normalizzazione: y = 2*(x-min)/(max-min) - 1
                data_array = 2 * (data_array - data_min) / (data_max - data_min) - 1
            else:
                # Se tutti i valori sono uguali, imposta a zero
                data_array = np.zeros_like(data_array)

            data = data_array.tolist()

        # Carica la forma d'onda nello strumento
        self.create_arb_waveform(channel, data, name)

        return len(data)

    # === FUNZIONI PREDEFINITE AVANZATE ===

    def create_sine_burst(self, channel, cycles, freq, ampl):
        """
        Crea un burst sinusoidale (pacchetto di cicli)

        Args:
            channel: Numero canale (1 o 2)
            cycles: Numero di cicli per burst
            freq: Frequenza della sinusoide in Hz
            ampl: Ampiezza in Vpp
        """
        self.set_function(channel, "SIN")
        self.set_frequency(channel, freq)
        self.set_amplitude(channel, ampl)
        self.instr.write(f"SOUR{channel}:BURS:STAT ON")
        self.instr.write(f"SOUR{channel}:BURS:NCYC {cycles}")

    def create_custom_pulse(self, channel, width, period, edge_time):
        """
        Crea un impulso con parametri personalizzati

        Args:
            channel: Numero canale (1 o 2)
            width: Larghezza dell'impulso in secondi (es: 1e-3 = 1ms)
            period: Periodo di ripetizione in secondi (es: 10e-3 = 10ms)
            edge_time: Tempo di salita/discesa in secondi (es: 10e-9 = 10ns)
        """
        self.set_function(channel, "PULSE")
        self.instr.write(f"SOUR{channel}:FUNC:PULS:WIDT {width}")
        self.instr.write(f"SOUR{channel}:FUNC:PULS:PER {period}")
        self.instr.write(f"SOUR{channel}:FUNC:PULS:TRAN {edge_time}")

    def create_ramp(self, channel, freq, symmetry):
        """
        Crea una rampa (dente di sega) con simmetria personalizzata

        Args:
            channel: Numero canale (1 o 2)
            freq: Frequenza in Hz
            symmetry: Simmetria in % (0-100)
                      0%   = rampa discendente (\)
                      50%  = triangolare (/\)
                      100% = rampa ascendente (/)
        """
        self.set_function(channel, "RAMP")
        self.set_frequency(channel, freq)
        self.instr.write(f"SOUR{channel}:FUNC:RAMP:SYMM {symmetry}")

    def close(self):
        """
        Chiude la connessione VISA con lo strumento

        Importante: chiamare sempre questo metodo alla fine della sessione
        """
        self.instr.close()
        self.rm.close()


# === ESEMPIO D'USO ===

if __name__ == "__main__":
    # Connessione (rileverà automaticamente il dispositivo)
    gen = RigolDG()

    # Oppure specifica l'indirizzo direttamente:
    # gen = RigolDG('TCPIP0::192.168.1.100::INSTR')

    try:
        # Configura canale 1: sinusoide 1kHz, 2Vpp
        gen.set_function(1, "SIN")
        gen.set_frequency(1, 1000)
        gen.set_amplitude(1, 2)
        gen.set_offset(1, 0)

        # Attiva output
        gen.output_on(1)

        # Leggi configurazione
        print(f"\nCanale 1:")
        print(f"  Funzione: {gen.get_function(1)}")
        print(f"  Frequenza: {gen.get_frequency(1)} Hz")
        print(f"  Ampiezza: {gen.get_amplitude(1)} Vpp")
        print(f"  Output: {'ON' if gen.is_output_on(1) else 'OFF'}")

        # Esempio modulazione AM
        # gen.set_am_modulation(1, depth=50, freq=100)

        # Esempio forma d'onda arbitraria: sinc
        # t = np.linspace(-np.pi, np.pi, 1000)
        # sinc_wave = np.sinc(t)
        # gen.create_arb_waveform(1, sinc_wave.tolist(), "SINC")
        # gen.load_arb_waveform(1, "SINC")

        # Esempio caricamento da CSV
        # num_points = gen.load_arb_from_csv(1, "waveform.csv", name="MY_WAVE")
        # print(f"Caricati {num_points} punti da CSV")
        # gen.load_arb_waveform(1, "MY_WAVE")

    finally:
        gen.close()
