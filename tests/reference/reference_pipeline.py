import numpy as np


WINDOW_SIZE = 1024
HOP_SIZE = 256


def _levels_for(magnitude):
    maximum = np.max(magnitude)
    if maximum <= 0:
        return np.full(magnitude.shape, 2 ** 16, dtype=float)
    relative = magnitude / maximum
    effective_bits = np.clip(
        np.round(16 * relative + 4 * (1.0 - relative)),
        4,
        16,
    )
    return 2 ** effective_bits


def _process_frame(frame):
    spectrum = np.fft.rfft(frame)
    magnitude = np.abs(spectrum)
    phase = np.angle(spectrum)
    levels = _levels_for(magnitude)
    phase_quantized = np.round(phase / (2 * np.pi) * levels) / levels * (2 * np.pi)
    return np.fft.irfft(
        magnitude * np.exp(1j * phase_quantized),
        n=len(frame),
    ).real


def reconstruct(signal, sample_rate=16000):
    signal = np.asarray(signal, dtype=float)
    original_mean = np.mean(signal)
    window = np.hanning(WINDOW_SIZE)
    pad_width = WINDOW_SIZE // 2
    padded = np.pad(signal, (pad_width, pad_width), mode='reflect')
    n_frames = int(np.ceil((len(padded) - WINDOW_SIZE) / HOP_SIZE)) + 1
    target_length = (n_frames - 1) * HOP_SIZE + WINDOW_SIZE
    extra = target_length - len(padded)
    if extra > 0:
        padded = np.pad(padded, (0, extra), mode='reflect')

    frames = np.zeros((n_frames, WINDOW_SIZE))
    for i in range(n_frames):
        start = i * HOP_SIZE
        frames[i] = padded[start:start + WINDOW_SIZE] * window

    processed = np.zeros_like(frames)
    for i in range(n_frames):
        processed[i] = _process_frame(frames[i])

    output = np.zeros(len(padded))
    norm = np.zeros(len(padded))
    for i in range(n_frames):
        start = i * HOP_SIZE
        output[start:start + WINDOW_SIZE] += processed[i]
        norm[start:start + WINDOW_SIZE] += window
    norm[norm < 1e-10] = 1.0

    reconstructed = (output / norm)[pad_width:pad_width + len(signal)]
    reconstructed += original_mean - np.mean(reconstructed)
    return reconstructed
