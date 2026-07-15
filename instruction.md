# Signal Reconstruction Fidelity

The reconstruction pipeline in `/app` violates its fidelity contract for valid
inputs. Fix the implementation so the public
`reconstruct(signal, sample_rate=...)` API satisfies `/app/system_contract.md`.

The relevant files are:

- `/app/windowing.py`
- `/app/spectral_compressor.py`
- `/app/reconstructor.py`
- `/app/fidelity_checker.py`
- `/app/system_contract.md`

Keep the pipeline architecture and public API intact. The end result should be
a faithful reconstruction system matching the contract.
