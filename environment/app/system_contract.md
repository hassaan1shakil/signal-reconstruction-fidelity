# Signal Reconstruction Fidelity Contract

The implementation is evaluated on input signals S with the following
properties:
- Duration: 1-30 seconds
- Sample rate: 8000-48000 Hz
- Frequency content within [20, Nyquist/2] Hz
- SNR >= 40dB

For each evaluated signal, the reconstructed signal R = reconstruct(S) must
satisfy:

| Guarantee | Condition | Threshold |
|-----------|-----------|-----------|
| Pointwise | max\|S[i]-R[i]\| for interior samples | < 0.01 |
| Spectral  | corr(FFT(S), FFT(R)) | > 0.999 |
| DC preservation | \|mean(S) - mean(R)\| | < 0.001 |
| Boundary  | boundary_error / max(interior_error, 0.005) | < 2.0 |

"Interior samples" = all samples beyond the first and last analysis window.

The pipeline consists of: windowing -> spectral compression -> reconstruction.
Run with: `python3 -c "from reconstructor import reconstruct; ..."`
