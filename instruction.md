# Signal Reconstruction Fidelity

The reconstruction pipeline in `/app` violates its fidelity contract for some
valid inputs. Your task is to find and fix the implementation so the public
`reconstruct(signal, sample_rate=...)` API satisfies the guarantees in
`/app/system_contract.md`.

The relevant files are:

- `/app/windowing.py`
- `/app/spectral_compressor.py`
- `/app/reconstructor.py`
- `/app/fidelity_checker.py`
- `/app/system_contract.md`

Do not change the public API. The verifier imports `reconstruct` from
`reconstructor.py` and checks the contract across multiple signal families.
