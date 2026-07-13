import numpy as np


def check_pointwise_error(original, reconstructed, window_size, threshold=0.01):
    interior = slice(window_size, len(original) - window_size)
    max_err = np.max(np.abs(original[interior] - reconstructed[interior]))
    return max_err < threshold, max_err


def check_spectral_fidelity(original, reconstructed, threshold=0.999):
    fft_orig = np.abs(np.fft.rfft(original))
    fft_recon = np.abs(np.fft.rfft(reconstructed))
    corr = np.corrcoef(fft_orig, fft_recon)[0, 1]
    return corr > threshold, corr


def check_dc_preservation(original, reconstructed, threshold=0.001):
    dc_err = abs(np.mean(original) - np.mean(reconstructed))
    return dc_err < threshold, dc_err


def check_boundary_condition(original, reconstructed, window_size, factor=2.0):
    interior = slice(window_size, len(original) - window_size)
    interior_err = np.max(np.abs(
        original[interior] - reconstructed[interior]
    ))
    if interior_err < 0.005:
        interior_err = 0.005

    boundary_left = slice(0, window_size)
    boundary_right = slice(len(original) - window_size, len(original))
    boundary_err = max(
        np.max(np.abs(original[boundary_left] - reconstructed[boundary_left])),
        np.max(np.abs(original[boundary_right] - reconstructed[boundary_right])),
    )
    return boundary_err < factor * interior_err, boundary_err / interior_err


def run_all_checks(original, reconstructed, window_size=1024):
    results = {}
    results['pointwise'] = check_pointwise_error(original, reconstructed, window_size)
    results['spectral'] = check_spectral_fidelity(original, reconstructed)
    results['dc'] = check_dc_preservation(original, reconstructed)
    results['boundary'] = check_boundary_condition(original, reconstructed, window_size)
    all_pass = all(r[0] for r in results.values())
    return all_pass, results
