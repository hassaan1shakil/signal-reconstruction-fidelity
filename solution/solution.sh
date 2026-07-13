#!/bin/sh
set -eu

APP_DIR="${APP_DIR:-/app}"
TESTS_DIR="${TESTS_DIR:-/tests}"

if [ ! -d "$APP_DIR" ]; then
    APP_DIR="environment/app"
fi

echo "# PART 1 -- Run visible tests if the task exposes them"
if [ -d "$APP_DIR/visible_tests" ]; then
    python3 -m pytest "$APP_DIR/visible_tests" -q
else
    echo "# No visible_tests directory is present in this task image."
fi

echo "# PART 2 -- Read the fidelity contract"
cat "$APP_DIR/system_contract.md"
echo "# Contract requires: pointwise < 0.01, spectral > 0.999, dc < 0.001"
echo "# Contract also constrains boundary error relative to interior error."
echo "# Must hold for: zero-mean tones, boundary-sensitive signals, multi-tone signals, non-zero-mean signals."

echo "# PART 3 -- Probe the pipeline before modifying source files"
APP_DIR="$APP_DIR" python3 - <<'PY'
import os
import sys

import numpy as np

app_dir = os.environ['APP_DIR']
sys.path.insert(0, app_dir)

from fidelity_checker import run_all_checks
from reconstructor import ReconstructionConfig, SignalReconstructor, reconstruct
from spectral_compressor import CompressionProfile, SpectralCompressor
from windowing import FrameGrid


SAMPLE_RATE = 16000
WINDOW_SIZE = 1024
HOP_SIZE = 256


def report_signal(name, signal):
    reconstructed = reconstruct(signal, sample_rate=SAMPLE_RATE)
    passed, details = run_all_checks(signal, reconstructed, window_size=WINDOW_SIZE)
    print(f"# Probe {name}: {'PASS' if passed else 'FAIL'}")
    for check_name, result in details.items():
        print(f"#   {check_name}: {'PASS' if result[0] else 'FAIL'} value={float(result[1]):.12g}")


n = SAMPLE_RATE * 2
t = np.arange(n) / SAMPLE_RATE
simple = 0.2 * np.sin(2 * np.pi * 440 * t)
boundary = 0.8 * np.cos(2 * np.pi * 440 * t)

spectral = np.zeros_like(t)
for frequency, phase in [
    (1450, 0.2),
    (1880, 0.7),
    (2331, 1.2),
    (3100, 2.0),
    (3817, 0.4),
    (5100, 1.1),
    (6700, 2.5),
]:
    spectral += np.sin(2 * np.pi * frequency * t + phase)
spectral *= 0.03 / max(np.max(np.abs(spectral)), 1e-12)

dc_signal = 0.002 + 0.1 * np.sin(2 * np.pi * 330 * t)

report_signal("simple zero-mean sine", simple)
report_signal("boundary-sensitive cosine", boundary)
report_signal("low-amplitude multi-tone spectrum", spectral)
report_signal("non-zero-mean signal", dc_signal)

grid = FrameGrid(window_size=8, hop_size=2, boundary='stable')
edge_probe = np.array([
    0.80, 0.35, -0.10, 0.55, -0.40, 0.20, 0.65, -0.25,
    0.15, -0.70, 0.45, 0.05, -0.30, 0.75, -0.15, 0.40,
])
padded = grid.analysis_buffer(edge_probe)
expected_left = edge_probe[1:grid.pad_width + 1][::-1]
print(f"# Boundary diagnostic: stable mode maps to {grid.pad_mode()!r}")
print(f"# Boundary diagnostic: left pad observed={padded[:grid.pad_width].tolist()}")
print(f"# Boundary diagnostic: left pad expected continuity reflection={expected_left.tolist()}")

compressor = SpectralCompressor()
frame = spectral[:WINDOW_SIZE] * np.hanning(WINDOW_SIZE)
roundtrip = compressor.decompress(compressor.compress(frame))
frame_corr = np.corrcoef(
    np.abs(np.fft.rfft(frame)),
    np.abs(np.fft.rfft(roundtrip)),
)[0, 1]
print(f"# Spectral loss in compressor: {frame_corr:.12g}")

profile = CompressionProfile()
magnitudes = np.array([
    1.0e-4, 2.0e-4, 1.0e-4, 3.0e-4, 2.0e-4, 1.0e-4,
    2.0e-4, 1.0e-4, 3.0e-4, 2.0e-4, 1.0e-4, 9.0e-1,
])
levels = profile.levels_for(magnitudes)
print(f"# Phase allocation diagnostic: low first-bin levels={levels[0]:.0f}")
print(f"# Phase allocation diagnostic: high late-bin levels={levels[-1]:.0f}")
print("# Phase allocation diagnostic: precision should follow magnitude, not FFT bin position.")

config = ReconstructionConfig(window_size=WINDOW_SIZE, hop_size=HOP_SIZE)
engine = SignalReconstructor(config=config)
engine.stats.observe_input(dc_signal)
package = engine.grid.frames(dc_signal)
processed = np.zeros_like(package.frames)
for i in range(package.frames.shape[0]):
    compressed = engine.compressor.compress(package.frames[i])
    processed[i] = engine.compressor.decompress(compressed)

raw = engine.grid.trim(
    engine.grid.synthesize(processed, package.buffer_length),
    package.original_length,
)
engine.stats.observe_working_set(processed)
adjusted = engine.stats.align_working_set(processed)
pre_corrected = engine.grid.trim(
    engine.grid.synthesize(adjusted, package.buffer_length),
    package.original_length,
)
print(f"# DC after synthesis: {float(np.mean(raw)):.12g}, expected: {float(np.mean(dc_signal)):.12g}")
print(f"# DC after frame-domain correction: {float(np.mean(pre_corrected)):.12g}, expected: {float(np.mean(dc_signal)):.12g}")
print("# DC diagnostic: correction should be applied after synthesis and trimming.")
PY

echo "# PART 4 -- Apply source fixes after diagnostics"
APP_DIR="$APP_DIR" python3 - <<'PY'
import os
from pathlib import Path

app = Path(os.environ['APP_DIR'])

windowing = app / 'windowing.py'
text = windowing.read_text()
old = "'stable': 'constant'"
new = "'stable': 'reflect'"
if old not in text:
    raise SystemExit('windowing.py did not contain the diagnosed stable constant boundary mode')
windowing.write_text(text.replace(old, new, 1))
print("# Applied fix: stable boundary extension now uses reflection.")

spectral = app / 'spectral_compressor.py'
text = spectral.read_text()
old = """    def levels_for(self, magnitude):
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
"""
new = """    def levels_for(self, magnitude):
        if magnitude.size == 0:
            return magnitude.astype(float)
        maximum = np.max(magnitude)
        if maximum <= 0:
            return np.full(magnitude.shape, 2 ** self.phase_bits, dtype=float)
        relative = magnitude / maximum
        floor = 4
        effective_bits = np.clip(
            np.round(self.phase_bits * relative + floor * (1.0 - relative)),
            floor,
            self.phase_bits,
        )
        return 2 ** effective_bits
"""
if old not in text:
    raise SystemExit('spectral_compressor.py did not contain the diagnosed position-driven profile')
spectral.write_text(text.replace(old, new, 1))
print("# Applied fix: phase quantization precision now follows spectral magnitude.")

reconstructor = app / 'reconstructor.py'
text = reconstructor.read_text()
old = """        self.stats.observe_working_set(processed_frames)
        adjusted_frames = self.stats.align_working_set(processed_frames)
        padded = self.grid.synthesize(adjusted_frames, package.buffer_length)
        reconstructed = self.grid.trim(padded, package.original_length)
        return reconstructed
"""
new = """        padded = self.grid.synthesize(processed_frames, package.buffer_length)
        reconstructed = self.grid.trim(padded, package.original_length)
        return reconstructed + (self.stats.source_level - np.mean(reconstructed))
"""
if old not in text:
    raise SystemExit('reconstructor.py did not contain the diagnosed pre-synthesis DC path')
reconstructor.write_text(text.replace(old, new, 1))
print("# Applied fix: DC restoration now occurs after synthesis and trimming.")
PY

echo "# PART 5 -- Verify"
if [ -f "$TESTS_DIR/verifier.py" ]; then
    python3 "$TESTS_DIR/verifier.py"
    if [ -f "${REWARD_DIR:-/logs/verifier}/reward.txt" ]; then
        cat "${REWARD_DIR:-/logs/verifier}/reward.txt"
    fi
else
    echo "# No verifier.py found at $TESTS_DIR; run the task verifier in the harness."
fi
