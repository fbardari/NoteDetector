"""
Graphical User Interface (GUI) module built with Tkinter for the Real-Time Note Detector.
"""

import time
import tkinter as tk
from tkinter import ttk

import numpy as np
import sounddevice as sd

from note_detector.config import (
    BLOCK_SIZE,
    BUFFER_SIZE,
    A4_FREQ,
    HOLD_DURATION,
    NOTE_NAMES,
    WHITE_KEYS,
    MIDI_MIN,
    MIDI_MAX,
)
from note_detector.audio import detect_frequency, get_status_color


class App:
    # Virtual piano key dimensions and layout constants
    W, H = 28, 150          # White key width and height
    BW, BH = 18, 92         # Black key width and height
    X0, Y0 = 10, 10

    # Intonation tuning bar dimensions
    BAR_W, BAR_H = 700, 90

    def __init__(self, root):
        """
        Initializes the application window, audio streams, tracking variables, and UI components.
        """
        self.root = root
        root.title("Real-Time Note Detector")
        root.resizable(False, False)

        self.stream = None
        self.sr = 44100
        self.buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)

        self.ultimo_suono = 0.0
        self.ultima_midi = None
        self.cent_smooth = None
        self.tasto_acceso = None

        self._costruisci_ui()
        self._popola_dispositivi()
        self.aggiorna()
        root.protocol("WM_DELETE_WINDOW", self.chiudi)

    # ---------------------------------------------------------------- UI Construction
    def _costruisci_ui(self):
        """Builds and packs all graphical widgets into the main window."""
        pad = {"padx": 12, "pady": 4}

        # Microphone selection dropdown row
        riga = ttk.Frame(self.root)
        riga.pack(fill="x", **pad)
        ttk.Label(riga, text="Microphone:").pack(side="left")
        self.combo = ttk.Combobox(riga, state="readonly", width=60)
        self.combo.pack(side="left", padx=8)
        self.combo.bind("<<ComboboxSelected>>", self._cambio_dispositivo)

        # Primary note display and pitch feedback labels
        self.lbl_nota = tk.Label(self.root, text="--", font=("Helvetica", 56, "bold"), fg="#888")
        self.lbl_nota.pack(pady=(6, 0))
        self.lbl_freq = tk.Label(self.root, text="", font=("Helvetica", 14))
        self.lbl_freq.pack()
        self.lbl_verdetto = tk.Label(self.root, text="", font=("Helvetica", 13, "bold"))
        self.lbl_verdetto.pack(pady=(0, 6))

        # Intonation tuning meter canvas
        self.bar = tk.Canvas(self.root, width=self.BAR_W, height=self.BAR_H,
                             bg="white", highlightthickness=0)
        self.bar.pack(pady=4)
        self._disegna_barra()

        # Virtual piano keyboard canvas
        n_bianchi = sum(1 for m in range(MIDI_MIN, MIDI_MAX + 1) if m % 12 in WHITE_KEYS)
        self.piano = tk.Canvas(self.root, width=n_bianchi * self.W + 2 * self.X0,
                               height=self.H + 2 * self.Y0, bg="#f0f0f0", highlightthickness=0)
        self.piano.pack(padx=12, pady=8)
        self._disegna_pianoforte()

        # Status bar label at the bottom
        self.status = ttk.Label(self.root, text="", foreground="#666")
        self.status.pack(pady=(0, 8))

    def _disegna_pianoforte(self):
        """Draws white and black piano keys onto the virtual keyboard canvas."""
        self.tasti = {}
        self.colore_base = {}
        idx = 0
        posizioni_bianchi = {}
        
        # Render white keys first
        for m in range(MIDI_MIN, MIDI_MAX + 1):
            if m % 12 in WHITE_KEYS:
                x = self.X0 + idx * self.W
                posizioni_bianchi[m] = x
                self.tasti[m] = self.piano.create_rectangle(
                    x, self.Y0, x + self.W, self.Y0 + self.H,
                    fill="white", outline="#333")
                self.colore_base[m] = "white"
                
                # Add octave labels on C notes (Do)
                if m % 12 == 0:
                    octave_num = m // 12 - 1
                    self.piano.create_text(x + self.W / 2, self.Y0 + self.H - 10,
                                           text=f"C{octave_num}", font=("Helvetica", 8), fill="#555")
                idx += 1
                
        # Render black keys on top
        for m in range(MIDI_MIN, MIDI_MAX + 1):
            if m % 12 not in WHITE_KEYS:
                x_prec = posizioni_bianchi[m - 1]
                x = x_prec + self.W - self.BW / 2
                self.tasti[m] = self.piano.create_rectangle(
                    x, self.Y0, x + self.BW, self.Y0 + self.BH,
                    fill="#222", outline="#000")
                self.colore_base[m] = "#222"

    def _disegna_barra(self):
        """Draws the tuning meter scale, tick marks, center green zone, and needle indicator."""
        c, w, h = self.bar, self.BAR_W, self.BAR_H
        self.bar_margine = 40
        self.bar_larghezza = w - 2 * self.bar_margine
        cx = w / 2
        y1, y2 = 30, 60

        c.create_rectangle(self.bar_margine, y1, w - self.bar_margine, y2,
                           fill="#eee", outline="#999")
        
        # In-tune center zone region (±5 cents)
        zona = self._x_cent(5) - self._x_cent(0)
        c.create_rectangle(cx - zona, y1, cx + zona, y2, fill="#b8f0cf", outline="")
        
        # Draw scale tick marks and numerical labels
        for cent in range(-50, 51, 10):
            x = self._x_cent(cent)
            lungo = cent % 50 == 0
            c.create_line(x, y2, x, y2 + (14 if lungo else 8), fill="#555")
            if lungo:
                testo = "0" if cent == 0 else f"{cent:+d}"
                c.create_text(x, y2 + 24, text=testo, font=("Helvetica", 9), fill="#555")
                
        c.create_text(self.bar_margine - 8, (y1 + y2) / 2, text="♭", font=("Helvetica", 16), fill="#555")
        c.create_text(w - self.bar_margine + 8, (y1 + y2) / 2, text="♯", font=("Helvetica", 16), fill="#555")
        c.create_text(cx, 12, text="cents", font=("Helvetica", 9), fill="#888")

        # Movable intonation indicator needle
        self.lancetta = c.create_rectangle(cx - 3, y1 - 6, cx + 3, y2 + 6,
                                           fill="#888", outline="", state="hidden")

    def _x_cent(self, cent):
        """Maps cent deviation value to an X-coordinate position on the tuning meter bar."""
        return self.BAR_W / 2 + (cent / 50.0) * (self.bar_larghezza / 2)

    # ---------------------------------------------------------------- Audio Stream Management
    def _popola_dispositivi(self):
        """Queries and lists available audio input recording devices into the combobox."""
        self.dispositivi = []
        try:
            for i, d in enumerate(sd.query_devices()):
                if d["max_input_channels"] > 0:
                    self.dispositivi.append((i, d["name"]))
        except Exception as e:
            self.status.config(text=f"Error reading audio devices: {e}")
            return

        if not self.dispositivi:
            self.status.config(text="No microphones found.")
            return

        self.combo["values"] = [f"{i}: {n}" for i, n in self.dispositivi]

        try:
            predefinito = sd.default.device[0]
        except Exception:
            predefinito = -1
        indici = [i for i, _ in self.dispositivi]
        scelto = predefinito if predefinito in indici else indici[0]
        self.combo.current(indici.index(scelto))
        self.avvia_stream(scelto)

    def _cambio_dispositivo(self, _evento=None):
        """Handles switching input audio devices from the dropdown menu."""
        i, _ = self.dispositivi[self.combo.current()]
        self.avvia_stream(i)

    def _callback(self, indata, frames, time_info, status):
        """Sounddevice stream input data callback function."""
        self.buffer = np.roll(self.buffer, -frames)
        self.buffer[-frames:] = indata[:, 0]

    def avvia_stream(self, device):
        """Starts the input audio stream capture for the selected microphone device."""
        self.ferma_stream()
        try:
            info = sd.query_devices(device)
            self.sr = int(info["default_samplerate"])
            self.buffer = np.zeros(BUFFER_SIZE, dtype=np.float32)
            self.stream = sd.InputStream(device=device, channels=1, samplerate=self.sr,
                                         blocksize=BLOCK_SIZE, callback=self._callback)
            self.stream.start()
            self.status.config(text=f"Listening: {info['name']} ({self.sr} Hz)")
        except Exception as e:
            self.stream = None
            self.status.config(text=f"Microphone error: {e}")

    def ferma_stream(self):
        """Stops and safely closes the active audio stream."""
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    # ---------------------------------------------------------------- Real-Time Update Loop
    def aggiorna(self):
        """Periodic UI and audio processing loop executing every 50ms."""
        freq = detect_frequency(self.buffer.copy(), self.sr)
        ora = time.time()

        if freq is not None:
            # Calculate corresponding MIDI note number and cent deviation
            midi_f = 69 + 12 * np.log2(freq / A4_FREQ)
            midi = int(round(midi_f))
            cent = (midi_f - midi) * 100

            # Smooth out cent fluctuations when playing the same note consecutively
            if midi == self.ultima_midi and self.cent_smooth is not None:
                self.cent_smooth = 0.6 * self.cent_smooth + 0.4 * cent
            else:
                self.cent_smooth = cent
            self.ultima_midi = midi
            self.ultimo_suono = ora
            self.mostra(midi, freq, self.cent_smooth)
        elif ora - self.ultimo_suono > HOLD_DURATION:
            # Clear display if sound has ceased for longer than hold duration limit
            self.cancella()

        self.root.after(50, self.aggiorna)

    def mostra(self, midi, freq, cent):
        """Updates UI elements with current pitch detection results and visual indicators."""
        colore = get_status_color(cent)
        nome = NOTE_NAMES[midi % 12]
        ottava = midi // 12 - 1

        self.lbl_nota.config(text=f"{nome}{ottava}", fg=colore)
        self.lbl_freq.config(text=f"{freq:.2f} Hz      {cent:+.0f} cents")
        
        # Determine tuning verdict message
        if abs(cent) <= 5:
            verdetto = "In Tune"
        elif cent < 0:
            verdetto = "Flat: pitch up slightly"
        else:
            verdetto = "Sharp: pitch down slightly"
        self.lbl_verdetto.config(text=verdetto, fg=colore)

        # Reposition and color tuning meter needle (clamped between ±50 cents)
        x = self._x_cent(max(-50, min(50, cent)))
        self.bar.coords(self.lancetta, x - 3, 24, x + 3, 66)
        self.bar.itemconfig(self.lancetta, fill=colore, state="normal")

        self.evidenzia(midi, colore)

    def cancella(self):
        """Clears the UI display fields when no sound is detected."""
        self.ultima_midi = None
        self.cent_smooth = None
        self.lbl_nota.config(text="--", fg="#888")
        self.lbl_freq.config(text="")
        self.lbl_verdetto.config(text="")
        self.bar.itemconfig(self.lancetta, state="hidden")
        self.evidenzia(None, None)

    def evidenzia(self, midi, colore):
        """Highlights the active note key on the virtual piano keyboard."""
        if self.tasto_acceso is not None and self.tasto_acceso != midi:
            self.piano.itemconfig(self.tasti[self.tasto_acceso],
                                  fill=self.colore_base[self.tasto_acceso])
            self.tasto_acceso = None
        if midi is not None and midi in self.tasti:
            self.piano.itemconfig(self.tasti[midi], fill=colore)
            self.tasto_acceso = midi

    def chiudi(self):
        """Closes audio streams gracefully and destroys the application window on exit."""
        self.ferma_stream()
        self.root.destroy()