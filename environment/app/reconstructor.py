from dataclasses import dataclass

import numpy as np

from spectral_compressor import SpectralCompressor
from windowing import FrameGrid


DEFAULT_WINDOW_SIZE = 1024
DEFAULT_HOP_SIZE = 256


@dataclass
class ReconstructionConfig:
    window_size: int = DEFAULT_WINDOW_SIZE
    hop_size: int = DEFAULT_HOP_SIZE
    boundary: str = 'stable'


class ReconstructionStats:
    def __init__(self):
        self.source_level = 0.0
        self.working_level = 0.0

    def observe_input(self, signal):
        self.source_level = float(np.mean(signal))

    def observe_working_set(self, frames):
        self.working_level = float(np.mean(frames))

    def align_working_set(self, frames):
        return frames + (self.source_level - self.working_level)


class SignalReconstructor:
    def __init__(self, config=None, compressor=None, stats=None):
        self.config = config or ReconstructionConfig()
        self.grid = FrameGrid(
            self.config.window_size,
            self.config.hop_size,
            self.config.boundary,
        )
        self.compressor = compressor or SpectralCompressor()
        self.stats = stats or ReconstructionStats()

    def reconstruct(self, signal, sample_rate=16000):
        signal = np.asarray(signal, dtype=float)
        self.stats.observe_input(signal)
        package = self.grid.frames(signal)
        processed_frames = np.zeros_like(package.frames)
        for i in range(package.frames.shape[0]):
            compressed = self.compressor.compress(package.frames[i])
            processed_frames[i] = self.compressor.decompress(compressed)
        self.stats.observe_working_set(processed_frames)
        adjusted_frames = self.stats.align_working_set(processed_frames)
        padded = self.grid.synthesize(adjusted_frames, package.buffer_length)
        reconstructed = self.grid.trim(padded, package.original_length)
        return reconstructed


def reconstruct(signal, sample_rate=16000,
                window_size=DEFAULT_WINDOW_SIZE,
                hop_size=DEFAULT_HOP_SIZE):
    config = ReconstructionConfig(window_size=window_size, hop_size=hop_size)
    return SignalReconstructor(config=config).reconstruct(signal, sample_rate)
