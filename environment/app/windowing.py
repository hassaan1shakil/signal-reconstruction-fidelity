from dataclasses import dataclass

import numpy as np


@dataclass
class WindowedBuffer:
    frames: np.ndarray
    window: np.ndarray
    original_length: int
    buffer_length: int
    trim_start: int


class FrameGrid:
    def __init__(self, window_size=1024, hop_size=256, boundary='stable'):
        self.window_size = window_size
        self.hop_size = hop_size
        self.boundary = boundary
        self.window = np.hanning(window_size)
        self.pad_width = window_size // 2
        self.boundary_modes = {
            'stable': 'constant',
            'mirror': 'reflect',
            'hold': 'edge',
        }

    def pad_mode(self):
        return self.boundary_modes.get(self.boundary, self.boundary)

    def analysis_buffer(self, signal):
        mode = self.pad_mode()
        padded = np.pad(signal, (self.pad_width, self.pad_width), mode=mode)
        n_frames = self.frame_count(len(padded))
        target_length = (n_frames - 1) * self.hop_size + self.window_size
        extra = target_length - len(padded)
        if extra > 0:
            padded = np.pad(padded, (0, extra), mode=mode)
        return padded

    def frame_count(self, buffer_length):
        if buffer_length <= self.window_size:
            return 1
        return int(np.ceil((buffer_length - self.window_size) / self.hop_size)) + 1

    def frames(self, signal):
        signal = np.asarray(signal, dtype=float)
        padded = self.analysis_buffer(signal)
        n_frames = self.frame_count(len(padded))
        frames = np.zeros((n_frames, self.window_size))
        for i in range(n_frames):
            start = i * self.hop_size
            frames[i] = padded[start:start + self.window_size] * self.window
        return WindowedBuffer(
            frames=frames,
            window=self.window,
            original_length=len(signal),
            buffer_length=len(padded),
            trim_start=self.pad_width,
        )

    def synthesize(self, frames, output_length):
        output = np.zeros(output_length)
        norm = np.zeros(output_length)
        for i in range(frames.shape[0]):
            start = i * self.hop_size
            end = min(start + self.window_size, output_length)
            span = end - start
            output[start:end] += frames[i, :span]
            norm[start:end] += self.window[:span]
        norm[norm < 1e-10] = 1.0
        return output / norm

    def trim(self, buffer, original_length):
        start = self.pad_width
        end = start + original_length
        return buffer[start:end]


def create_window(window_size, window_type='hann'):
    if window_type == 'hann':
        return np.hanning(window_size)
    raise ValueError(f"Unknown window type: {window_type}")


def apply_windows(signal, window_size, hop_size):
    window = create_window(window_size)
    n_frames = (len(signal) - window_size) // hop_size + 1
    frames = np.zeros((n_frames, window_size))
    for i in range(n_frames):
        start = i * hop_size
        frames[i] = signal[start:start + window_size] * window
    return frames, window


def reconstruct_from_frames(frames, window, hop_size, output_length):
    output = np.zeros(output_length)
    norm = np.zeros(output_length)
    window_size = frames.shape[1]
    for i in range(frames.shape[0]):
        start = i * hop_size
        end = min(start + window_size, output_length)
        span = end - start
        output[start:end] += frames[i, :span]
        norm[start:end] += window[:span]
    norm[norm < 1e-10] = 1.0
    return output / norm
