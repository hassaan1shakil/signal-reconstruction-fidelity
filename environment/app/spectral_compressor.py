from dataclasses import dataclass

import numpy as np


@dataclass
class CompressionProfile:
    phase_bits: int = 16
    profile_shape: float = 0.3
    transition_width: float = 0.2
    tail_order: int = 1

    def levels_for(self, magnitude):
        if magnitude.size == 0:
            return magnitude.astype(float)
        if np.max(magnitude) <= 0:
            return np.full(magnitude.shape, 2 ** self.phase_bits, dtype=float)
        position = np.linspace(0.0, 1.0, magnitude.size)
        mix = np.clip(
            (position - self.profile_shape) / self.transition_width,
            0.0,
            1.0,
        )
        effective_bits = np.clip(
            np.round(self.phase_bits * (1.0 - mix) + self.tail_order * mix),
            self.tail_order,
            self.phase_bits,
        )
        return 2 ** effective_bits


class SpectralCompressor:
    def __init__(self, profile=None):
        self.profile = profile or CompressionProfile()

    def compress(self, frame):
        spectrum = np.fft.rfft(frame)
        magnitude = np.abs(spectrum)
        phase = np.angle(spectrum)
        levels = self.profile.levels_for(magnitude)
        phase_quantized = np.round(phase / (2 * np.pi) * levels) / levels * (2 * np.pi)
        return {
            'magnitude': magnitude,
            'phase_quantized': phase_quantized,
            'n_fft': len(frame),
        }

    def decompress(self, compressed):
        spectrum = compressed['magnitude'] * np.exp(
            1j * compressed['phase_quantized']
        )
        return np.fft.irfft(spectrum, n=compressed['n_fft']).real


def compress_frame(frame):
    return SpectralCompressor().compress(frame)


def decompress_frame(compressed):
    return SpectralCompressor().decompress(compressed)
