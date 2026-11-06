"""
Audio acquisition module using sounddevice and pitch detection using FFT autocorrelation.
"""

import numpy as np
import sounddevice as sd
from note_detector.config import (
    FMIN,
    FMAX,
    VOLUME_THRESHOLD,
    CORRELATION_THRESHOLD,
    A4_FREQ,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_RED,
)


def detect_frequency(segnale, sr):
    """
    Extracts the fundamental frequency of an audio signal using autocorrelation (via FFT).
    
    Args:
        segnale (numpy.ndarray): Raw audio samples buffer.
        sr (int): Sampling rate in Hz.
        
    Returns:
        float or None: Detected fundamental frequency in Hz, or None if signal is silent/unstable.
    """
    # Remove DC offset to center the signal around zero
    segnale = segnale - segnale.mean()
    
    # Check volume threshold; return None if signal is too quiet (silence)
    if np.sqrt(np.mean(segnale ** 2)) < VOLUME_THRESHOLD:
        return None

    n = len(segnale)
    # Apply Hanning window and compute Real Fast Fourier Transform (RFFT)
    spettro = np.fft.rfft(segnale * np.hanning(n), 2 * n)
    
    # Inverse FFT of the power spectrum to obtain the autocorrelation function
    ac = np.fft.irfft(np.abs(spettro) ** 2)[:n]
    
    # Normalize autocorrelation with respect to the zero lag value
    ac /= ac[0] + 1e-12

    # Restrict lag search range based on configured frequency boundaries (FMIN and FMAX)
    lag_min = int(sr / FMAX)
    lag_max = min(int(sr / FMIN), n - 2)
    seg = ac[lag_min:lag_max]
    
    if len(seg) < 3:
        return None

    # Find peaks within the filtered autocorrelation segment
    soglia = 0.9 * seg.max()
    picco = None
    for i in range(1, len(seg) - 1):
        if seg[i] >= soglia and seg[i] > seg[i - 1] and seg[i] >= seg[i + 1]:
            picco = i + lag_min
            break
            
    # Reject peaks that fail to satisfy the correlation quality threshold
    if picco is None or ac[picco] < CORRELATION_THRESHOLD:
        return None

    # Quadratic interpolation around the peak for sub-sample frequency precision
    a, b, c = ac[picco - 1], ac[picco], ac[picco + 1]
    denom = a - 2 * b + c
    if denom != 0:
        picco = picco + 0.5 * (a - c) / denom
        
    return sr / picco


def get_status_color(cent):
    """
    Determines UI feedback color based on intonation deviation in cents.
    
    Args:
        cent (float): Deviation from exact note pitch in cents.
        
    Returns:
        str: Hex color code representing tuning status (Green, Yellow, Red).
    """
    c = abs(cent)
    if c <= 5:
        return COLOR_GREEN
    if c <= 15:
        return COLOR_YELLOW
    return COLOR_RED