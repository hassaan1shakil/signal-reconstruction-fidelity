# Signal Reconstruction Fidelity Contract

The public reconstruction API is:

```python
reconstruct(signal, sample_rate=...)
```

For an input signal S with the following properties:
- Duration: 1-30 seconds
- Sample rate: 8000-48000 Hz
- Frequency content within [20, Nyquist/2] Hz
- SNR >= 40dB

the reconstructed signal R = reconstruct(S) must satisfy:

| Guarantee | Condition | Threshold |
|-----------|-----------|-----------|
| Pointwise | max\|S[i]-R[i]\| for interior samples | < 0.01 |
| Spectral  | corr(FFT(S), FFT(R)) | > 0.999 |
| DC preservation | \|mean(S) - mean(R)\| | < 0.001 |
| Boundary  | boundary_error / max(interior_error, 0.005) | < 2.0 |

"Interior samples" = all samples beyond the first and last analysis window.

## Pipeline Semantics

The pipeline is a three-stage reconstruction system:

```text
windowing -> spectral compression -> reconstruction
```

Each stage must preserve its role in the pipeline. Windowing is responsible for
stable frame coverage over the full signal extent. Spectral compression must
remain a quantized representation of each frame. Reconstruction must return a
completed signal whose aggregate properties match the input according to the
guarantees above.

The implementation may change internally, but the public API and the pipeline
contract above must remain intact.
