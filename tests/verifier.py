import importlib.util
import os
import sys
from pathlib import Path

import numpy as np


SAMPLE_RATE = 16000
DURATION_SECONDS = 2.0
WINDOW_SIZE = 1024
BOUNDARY_FLOOR = 0.005


def _load_reference():
    path = Path(__file__).resolve().parent / 'reference' / 'reference_pipeline.py'
    spec = importlib.util.spec_from_file_location('reference_pipeline', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_candidate_modules():
    app_dir = Path('/app')
    if not app_dir.exists():
        app_dir = Path(__file__).resolve().parents[1] / 'environment' / 'app'
    sys.path.insert(0, str(app_dir))

    for name in ['windowing', 'spectral_compressor', 'reconstructor']:
        sys.modules.pop(name, None)

    import windowing
    import spectral_compressor
    import reconstructor

    return windowing, spectral_compressor, reconstructor


def signal_families():
    n_samples = int(SAMPLE_RATE * DURATION_SECONDS)
    t = np.arange(n_samples) / SAMPLE_RATE

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

    dc = 0.002 + 0.1 * np.sin(2 * np.pi * 330 * t)

    combined = spectral + 0.25
    combined = combined.copy()
    combined[20] += 0.15
    combined[-20] -= 0.15

    return {
        'simple_sine': simple,
        'boundary_sensitive': boundary,
        'multi_tone_spectral': spectral,
        'nonzero_mean': dc,
        'combined': combined,
    }


def check_all(original, reconstructed):
    interior = slice(WINDOW_SIZE, len(original) - WINDOW_SIZE)
    pointwise = np.max(np.abs(original[interior] - reconstructed[interior]))

    fft_orig = np.abs(np.fft.rfft(original))
    fft_recon = np.abs(np.fft.rfft(reconstructed))
    spectral = np.corrcoef(fft_orig, fft_recon)[0, 1]

    dc = abs(np.mean(original) - np.mean(reconstructed))

    boundary_left = slice(0, WINDOW_SIZE)
    boundary_right = slice(len(original) - WINDOW_SIZE, len(original))
    boundary_err = max(
        np.max(np.abs(original[boundary_left] - reconstructed[boundary_left])),
        np.max(np.abs(original[boundary_right] - reconstructed[boundary_right])),
    )
    boundary = boundary_err / max(pointwise, BOUNDARY_FLOOR)

    return {
        'pointwise': (pointwise < 0.01, float(pointwise)),
        'spectral': (spectral > 0.999, float(spectral)),
        'dc': (dc < 0.001, float(dc)),
        'boundary': (boundary < 2.0, float(boundary)),
    }


def run_suite(name, reconstruct):
    failures = []
    for family_name, signal in signal_families().items():
        reconstructed = reconstruct(signal, sample_rate=SAMPLE_RATE)
        results = check_all(signal, reconstructed)
        passed = all(result[0] for result in results.values())
        print(f'{name}:{family_name}: {"PASS" if passed else "FAIL"}')
        for metric, (metric_passed, value) in results.items():
            print(f'  {metric:10s} {"PASS" if metric_passed else "FAIL":4s} {value:.12g}')
        if not passed:
            failures.append((family_name, results))
    return failures


class CountingCompressor:
    def __init__(self):
        self.compress_count = 0
        self.decompress_count = 0

    def compress(self, frame):
        self.compress_count += 1
        return {'frame': np.asarray(frame, dtype=float).copy()}

    def decompress(self, compressed):
        self.decompress_count += 1
        return compressed['frame'].copy()


class ZeroingCompressor:
    def __init__(self):
        self.compress_count = 0
        self.decompress_count = 0

    def compress(self, frame):
        self.compress_count += 1
        return {'n_fft': len(frame)}

    def decompress(self, compressed):
        self.decompress_count += 1
        return np.zeros(compressed['n_fft'])


def run_behavioral_checks(windowing, spectral_compressor, reconstructor):
    failures = []

    signal = np.array([
        0.80, 0.35, -0.10, 0.55, -0.40, 0.20, 0.65, -0.25,
        0.15, -0.70, 0.45, 0.05, -0.30, 0.75, -0.15, 0.40,
    ])
    grid = windowing.FrameGrid(window_size=8, hop_size=2, boundary='stable')
    padded = grid.analysis_buffer(signal)
    expected_left = signal[1:grid.pad_width + 1][::-1]
    expected_right = signal[-2:-grid.pad_width - 2:-1]
    if not (
        np.allclose(padded[:grid.pad_width], expected_left)
        and np.allclose(
            padded[grid.pad_width + len(signal):grid.pad_width + len(signal) + grid.pad_width],
            expected_right,
        )
    ):
        failures.append('boundary extension does not preserve edge continuity')

    profile = spectral_compressor.CompressionProfile()
    magnitudes = np.array([
        1.0e-4, 2.0e-4, 1.0e-4, 3.0e-4, 2.0e-4, 1.0e-4,
        2.0e-4, 1.0e-4, 3.0e-4, 2.0e-4, 1.0e-4, 9.0e-1,
    ])
    levels = profile.levels_for(magnitudes)
    if not (levels[-1] > levels[0] * 8 and levels[-1] >= 2 ** 12):
        failures.append('phase precision is not driven by spectral magnitude')

    sample_rate = SAMPLE_RATE
    t = np.arange(sample_rate) / sample_rate
    pipeline_signal = 0.11 * np.sin(2 * np.pi * 440 * t + 0.1)
    counter = CountingCompressor()
    config = reconstructor.ReconstructionConfig(window_size=256, hop_size=64)
    engine = reconstructor.SignalReconstructor(config=config, compressor=counter)
    engine.reconstruct(pipeline_signal, sample_rate=sample_rate)
    expected_frames = engine.grid.frame_count(
        len(engine.grid.analysis_buffer(pipeline_signal))
    )
    if counter.compress_count != expected_frames or counter.decompress_count != expected_frames:
        failures.append('reconstruction pipeline does not process every frame')

    zeroing = ZeroingCompressor()
    config = reconstructor.ReconstructionConfig(window_size=256, hop_size=64)
    engine = reconstructor.SignalReconstructor(config=config, compressor=zeroing)
    zeroed = engine.reconstruct(pipeline_signal, sample_rate=sample_rate)
    expected_frames = engine.grid.frame_count(
        len(engine.grid.analysis_buffer(pipeline_signal))
    )
    if (
        zeroing.compress_count != expected_frames
        or zeroing.decompress_count != expected_frames
        or np.max(np.abs(zeroed - np.mean(pipeline_signal))) >= 0.01
    ):
        failures.append('reconstruction output does not depend on compressor output')

    original_engine = reconstructor.SignalReconstructor
    probe_calls = []

    class ProbeReconstructor:
        def __init__(self, config=None):
            self.config = config
            probe_calls.append(config)

        def reconstruct(self, signal, sample_rate=16000):
            return np.full_like(np.asarray(signal, dtype=float), 0.12345)

    try:
        reconstructor.SignalReconstructor = ProbeReconstructor
        probe_signal = np.linspace(-0.2, 0.2, 64)
        probe_output = reconstructor.reconstruct(
            probe_signal,
            sample_rate=8000,
            window_size=32,
            hop_size=8,
        )
    finally:
        reconstructor.SignalReconstructor = original_engine

    if not (
        probe_calls
        and np.allclose(probe_output, np.full_like(probe_signal, 0.12345))
        and probe_calls[0].window_size == 32
        and probe_calls[0].hop_size == 8
    ):
        failures.append('public reconstruct does not route through the reconstruction engine')

    original_default_compressor = reconstructor.SpectralCompressor
    try:
        reconstructor.SpectralCompressor = ZeroingCompressor
        zeroed_public = reconstructor.reconstruct(
            pipeline_signal,
            sample_rate=sample_rate,
            window_size=256,
            hop_size=64,
        )
    finally:
        reconstructor.SpectralCompressor = original_default_compressor

    if np.max(np.abs(zeroed_public - np.mean(pipeline_signal))) >= 0.01:
        failures.append('public reconstruct does not use the default compressor dependency')

    dc_signal = 0.004 + 0.08 * np.sin(2 * np.pi * 330 * t + 0.3)
    counter = CountingCompressor()
    config = reconstructor.ReconstructionConfig(window_size=256, hop_size=64)
    engine = reconstructor.SignalReconstructor(config=config, compressor=counter)
    reconstructed = engine.reconstruct(dc_signal, sample_rate=sample_rate)
    dc_error = abs(float(np.mean(dc_signal) - np.mean(reconstructed)))
    if dc_error >= 0.001:
        failures.append(f'DC restoration is not applied after synthesis ({dc_error:.12g})')

    for failure in failures:
        print(f'behavior: FAIL {failure}')
    if not failures:
        print('behavior: PASS')
    return failures


def main():
    reference = _load_reference()
    reference_failures = run_suite('reference', reference.reconstruct)
    if reference_failures:
        raise AssertionError(f'reference failed: {reference_failures!r}')

    modules = _load_candidate_modules()
    candidate_failures = run_suite('candidate', modules[2].reconstruct)
    if candidate_failures:
        raise AssertionError(f'candidate failed: {candidate_failures!r}')

    behavior_failures = run_behavioral_checks(*modules)
    if behavior_failures:
        raise AssertionError(f'behavioral checks failed: {behavior_failures!r}')


def write_reward(value):
    reward_dir = Path(os.environ.get('REWARD_DIR', '/logs/verifier'))
    try:
        reward_dir.mkdir(parents=True, exist_ok=True)
        (reward_dir / 'reward.txt').write_text(f'{value}\n')
    except OSError:
        pass


if __name__ == '__main__':
    try:
        main()
    except Exception:
        write_reward(0.0)
        raise
    else:
        write_reward(1.0)
