"""
Configuration settings, constants, and color definitions for the Real-Time Note Detector.
"""

# ---------------------------------------------------------------- Parameters
BLOCK_SIZE = 1024
BUFFER_SIZE = 8192          # Analysis window size (~170-190 ms)
FMIN, FMAX = 50.0, 2000.0   # Frequency range in Hz
VOLUME_THRESHOLD = 0.003    # Below this RMS value is treated as silence (increase if background noise is high)
CORRELATION_THRESHOLD = 0.5
A4_FREQ = 440.0
HOLD_DURATION = 0.4         # Note persistence duration in seconds after sound ceases

# ---------------------------------------------------------------- Musical Mapping
# Note names using standard English notation (C instead of Do)
NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F",
              "F#", "G", "G#", "A", "A#", "B"]
WHITE_KEYS = {0, 2, 4, 5, 7, 9, 11}

MIDI_MIN, MIDI_MAX = 36, 95   # Range from C2 to B6 (5 octaves)

# ---------------------------------------------------------------- UI Theme Colors
COLOR_GREEN = "#2ecc71"
COLOR_YELLOW = "#f1c40f"
COLOR_RED = "#e74c3c"