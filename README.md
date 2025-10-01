# Rigol DG800/DG900 Controller

Libreria Python per il controllo remoto dei generatori di funzioni arbitrarie Rigol serie DG800 e DG900 tramite interfaccia VISA.

## Requisiti

```bash
pip install pyvisa pyvisa-py numpy
```

## Connessione

### Auto-rilevamento dispositivo
```python
from rigol_dg import RigolDG

gen = RigolDG()  # Mostra lista dispositivi disponibili
```

### Connessione diretta
```python
# Connessione USB
gen = RigolDG('USB0::0x1AB1::0x0642::DG9A12345678::INSTR')

# Connessione LAN
gen = RigolDG('TCPIP0::192.168.1.100::INSTR')
```

## Funzioni Base

### Forme d'onda standard
```python
# Sinusoide 1 kHz, 2 Vpp
gen.set_function(1, "SIN")
gen.set_frequency(1, 1000)
gen.set_amplitude(1, 2)
gen.set_offset(1, 0)
gen.output_on(1)

# Onda quadra 50% duty cycle
gen.set_function(1, "SQU")
gen.set_duty_cycle(1, 50)

# Rampa triangolare
gen.create_ramp(1, freq=100, symmetry=50)
```

### Forme d'onda disponibili
- `SIN` - Sinusoide
- `SQU` - Onda quadra
- `RAMP` - Rampa/triangolare
- `PULSE` - Impulso
- `NOIS` - Rumore
- `ARB` - Arbitraria
- `DC` - Continua

## Modulazione

### Modulazione di Ampiezza (AM)
```python
gen.set_am_modulation(1, depth=50, freq=100)
```

### Modulazione di Frequenza (FM)
```python
gen.set_fm_modulation(1, deviation=1000, freq=10)
```

### Disattiva modulazione
```python
gen.modulation_off(1)
```

## Forme d'Onda Arbitrarie

### Creazione da array Python
```python
import numpy as np

# Crea forma d'onda sinc
t = np.linspace(-np.pi, np.pi, 1000)
sinc_wave = np.sinc(t)
gen.create_arb_waveform(1, sinc_wave.tolist(), name="SINC")
gen.load_arb_waveform(1, "SINC")

# Forma d'onda custom
data = [0, 0.5, 1.0, 0.5, 0, -0.5, -1.0, -0.5]
gen.create_arb_waveform(1, data, name="CUSTOM")
gen.set_arb_sample_rate(1, 1e6)  # 1 MSa/s
```

### Caricamento da file CSV

```python
# Carica con normalizzazione automatica
num_points = gen.load_arb_from_csv(1, "waveform.csv", name="MY_WAVE")
print(f"Caricati {num_points} punti")
gen.load_arb_waveform(1, "MY_WAVE")
```

#### Formati CSV supportati

**1. Una colonna (solo ampiezza)**
```csv
0.0
0.309
0.588
0.809
1.0
```

**2. Due colonne (tempo, ampiezza)**
```csv
0.000, 0.0
0.001, 0.309
0.002, 0.588
0.003, 0.809
0.004, 1.0
```

**3. Con intestazione**
```csv
time,voltage
0.000, 0.0
0.001, 0.309
0.002, 0.588
```

**Note:**
- La normalizzazione automatica scala i valori tra -1 e +1
- Numero massimo punti: 8k-16k (dipende dal modello)
- Separatori supportati: virgola, punto e virgola

### Gestione forme d'onda salvate
```python
# Lista forme d'onda in memoria
waveforms = gen.get_arb_list()
print(waveforms)

# Elimina forma d'onda
gen.delete_arb_waveform("OLD_WAVE")
```

## Funzioni Avanzate

### Burst
```python
# Burst di 10 cicli sinusoidali a 1 kHz
gen.create_sine_burst(1, cycles=10, freq=1000, ampl=2)
```

### Impulsi personalizzati
```python
# Impulso 1ms, periodo 10ms, edge time 10ns
gen.create_custom_pulse(1, width=1e-3, period=10e-3, edge_time=10e-9)
```

## Lettura Stato

```python
# Leggi parametri attuali
freq = gen.get_frequency(1)
ampl = gen.get_amplitude(1)
func = gen.get_function(1)
is_on = gen.is_output_on(1)

print(f"Frequenza: {freq} Hz")
print(f"Ampiezza: {ampl} Vpp")
print(f"Funzione: {func}")
print(f"Output: {'ON' if is_on else 'OFF'}")
```

## Configurazione Output

```python
# Imposta impedenza di carico
gen.set_output_load(1, 50)      # 50 Ω
gen.set_output_load(1, 'INF')   # Alta impedenza
```

## Unità di Misura

| Parametro | Unità | Esempio |
|-----------|-------|---------|
| Frequenza | Hz | `1000` = 1 kHz |
| Ampiezza | Vpp (Volt picco-picco) | `2` = 2 Vpp |
| Offset | V (Volt) | `0.5` = +0.5V DC |
| Fase | Gradi | `90` = 90° |
| Duty cycle | % | `50` = 50% |
| Tempo | Secondi | `1e-3` = 1 ms |
| Sample rate | Sa/s | `1e6` = 1 MSa/s |
| Impedenza | Ω (Ohm) | `50` = 50Ω |

## Esempio Completo

```python
from rigol_dg import RigolDG

# Connessione
gen = RigolDG()

try:
    # Reset strumento
    gen.reset()

    # Canale 1: Sinusoide 1 kHz modulata AM
    gen.set_function(1, "SIN")
    gen.set_frequency(1, 1000)
    gen.set_amplitude(1, 2)
    gen.set_offset(1, 0)
    gen.set_am_modulation(1, depth=50, freq=10)
    gen.output_on(1)

    # Canale 2: Forma d'onda arbitraria da CSV
    points = gen.load_arb_from_csv(2, "my_waveform.csv", name="CUSTOM")
    gen.load_arb_waveform(2, "CUSTOM")
    gen.set_arb_sample_rate(2, 1e6)
    gen.set_amplitude(2, 3)
    gen.output_on(2)

    # Verifica configurazione
    print(f"\nCanale 1: {gen.get_function(1)}, {gen.get_frequency(1)} Hz")
    print(f"Canale 2: {gen.get_function(2)}, {points} punti caricati")

    input("\nPremi ENTER per terminare...")

finally:
    # Chiudi connessione
    gen.close()
```

## Riferimenti

- **Modelli supportati:** Rigol DG800, DG900, DG1000Z, DG4000, DG5000
- **Protocollo:** SCPI (Standard Commands for Programmable Instruments)
- **Interfacce:** USB, LAN (Ethernet), GPIB (con adattatore)

## Note

- Chiamare sempre `gen.close()` alla fine della sessione
- Le forme d'onda arbitrarie devono avere valori tra -1 e +1
- Verificare i limiti del proprio modello (frequenza max, punti ARB, ecc.)
- Per forme d'onda complesse, usare sample rate adeguato per evitare aliasing

## Licenza

Codice fornito "as-is" per uso educativo e di laboratorio.
