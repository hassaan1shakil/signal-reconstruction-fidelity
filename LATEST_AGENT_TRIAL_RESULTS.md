# Latest Agent Trial Results

This document summarizes the latest clean scored agent trials for
`signal-reconstruction-fidelity`.

The trials were run on July 14, 2026 after the task contract and instructions
were revised to be less prescriptive. The summary below excludes one invalid
setup run where the agent failed before reaching the task.

## Summary

| Metric | Result |
|---|---:|
| Clean scored runs | 9 |
| Full solves | 0 |
| Output metrics passed but behavior failed | 6 |
| Output metrics failed before behavior checks | 3 |
| Reward-file/harness failures among scored runs | 0 |

The main result is that agents continued to fail after the wording update, but
the failures were useful. Several agents improved the pipeline or produced
numerically strong outputs, yet none repaired all intended mechanisms.

## Trial Table

| Trial | Job | Agent | Model | Reward | Result Type | Main Failure |
|---|---|---|---|---:|---|---|
| 001 | `2026-07-14__12-28-23` | Gemini CLI | `gemini-3.5-flash` | 0.0 | Output failure | DC improved and boundary padding changed to edge hold, but spectral compression remained position-driven |
| 002 | `2026-07-14__12-28-27` | Codex | `gpt-5.4-mini` | 0.0 | Behavioral failure | High-resolution rectangular quantization passed metrics, but boundary extension and magnitude-driven precision were still wrong |
| 003 | `2026-07-14__12-41-17` | Codex | `gpt-5.4` | 0.0 | Behavioral failure | Uniform 24-bit phase precision and post-synthesis DC correction passed metrics, but boundary and magnitude behavior were still wrong |
| 004 | `2026-07-14__12-41-42` | Gemini CLI | `gemini-2.5-pro` | 0.0 | Output failure | DC handled through zero-mean reconstruction, but boundary and spectral bugs remained |
| 005 | `2026-07-14__12-54-56` | Gemini CLI | `gemini-3-flash-preview` | 0.0 | Output failure | Partial DC repair only; boundary-sensitive and multi-tone cases still failed |
| 006 | `2026-07-14__12-55-09` | Codex | `gpt-5.5` | 0.0 | Behavioral failure | Near-exact reconstruction through high-bit coefficient storage, but intended pipeline behavior was not repaired |
| 007 | `2026-07-14__13-02-55` | Gemini CLI | `gemini-3.1-flash-lite` | 0.0 | Behavioral failure | Positional tail precision tuned enough for metrics, but not magnitude-driven |
| 008 | `2026-07-14__13-11-36` | Gemini CLI | `gemini-3.1-pro-preview` | 0.0 | Behavioral failure | DC fixed and precision raised, but boundary and magnitude-driven checks failed |
| 009 | `2026-07-18__15-35-10` | terminus-2 | `claude-sonnet-5` | 0.0 | Behavioral failure | Both mechanisms diagnosed correctly and DC alignment fixed structurally, but phase precision was retuned by frequency position rather than made magnitude-driven, and boundary extension still did not preserve edge continuity |
## Verifier Signals

The most common behavioral failures were:

```text
behavior: FAIL boundary extension does not preserve edge continuity
behavior: FAIL phase precision is not driven by spectral magnitude
```

These checks were important because output-only grading would have accepted five
of the eight scored submissions. Those candidates produced good numerical
reconstructions, but they did so through shortcuts or incomplete repairs.

## Per-Trial Notes

### Trial 001: `2026-07-14__12-28-23`

- Agent/model: Gemini CLI, `gemini-3.5-flash`
- Reward: `0.0`
- Result type: output failure
- Output failures:
  - `multi_tone_spectral`: spectral correlation `0.963041071588`
  - `combined`: boundary ratio `3.81665643808`
- Main changes:
  - changed stable boundary padding from constant padding to edge padding
  - made frame alignment a no-op
  - added final DC correction after synthesis
- Interpretation:
  - The agent identified the DC issue and made a plausible boundary change, but
    edge padding was not enough for the expected continuity behavior.
  - The spectral compressor remained driven by bin position, so the multi-tone
    spectral case still failed.

### Trial 002: `2026-07-14__12-28-27`

- Agent/model: Codex, `gpt-5.4-mini`
- Reward: `0.0`
- Result type: behavioral failure after output metrics passed
- Behavioral failures:
  - boundary extension did not preserve edge continuity
  - phase precision was not driven by spectral magnitude
- Main changes:
  - replaced the compressor with uniform high-resolution real/imaginary
    quantization
  - made frame-domain DC alignment a no-op
  - left stable boundary handling as constant padding
- Interpretation:
  - This was a strong output shortcut. The final signals looked good, but the
    boundary and phase-precision mechanisms were not actually repaired.

### Trial 003: `2026-07-14__12-41-17`

- Agent/model: Codex, `gpt-5.4`
- Reward: `0.0`
- Result type: behavioral failure after output metrics passed
- Behavioral failures:
  - boundary extension did not preserve edge continuity
  - phase precision was not driven by spectral magnitude
- Main changes:
  - changed the compressor to uniform `max(phase_bits, 24)` phase precision
  - made frame-domain alignment a no-op
  - added post-synthesis DC correction
  - left constant boundary padding in place
- Interpretation:
  - This run handled DC correctly and made compression nearly lossless, but it
    missed the two harder architectural requirements.

### Trial 004: `2026-07-14__12-41-42`

- Agent/model: Gemini CLI, `gemini-2.5-pro`
- Reward: `0.0`
- Result type: output failure
- Output failures:
  - `boundary_sensitive`: boundary ratio `12.6835844699`
  - `multi_tone_spectral`: spectral correlation `0.963042474079`
  - `combined`: boundary ratio `3.78554514789`
- Main changes:
  - subtracted the source mean before windowing
  - reconstructed a zero-mean signal
  - added the source mean back after synthesis
- Interpretation:
  - DC behavior improved, but the boundary and spectral mechanisms remained
    largely unchanged.

### Trial 005: `2026-07-14__12-54-56`

- Agent/model: Gemini CLI, `gemini-3-flash-preview`
- Reward: `0.0`
- Result type: output failure
- Output failures:
  - `boundary_sensitive`: boundary ratio `12.6835844699`
  - `multi_tone_spectral`: spectral correlation `0.963042474079`
  - `combined`: boundary ratio `4.29279019297`
- Main changes:
  - removed frame-domain DC correction from the active reconstruction path
  - left the original boundary policy and position-driven compressor in place
- Interpretation:
  - This was a partial DC repair. The failed metrics show the two harder bugs
    were still active.

### Trial 006: `2026-07-14__12-55-09`

- Agent/model: Codex, `gpt-5.5`
- Reward: `0.0`
- Result type: behavioral failure after output metrics passed
- Behavioral failures:
  - boundary extension did not preserve edge continuity
  - phase precision was not driven by spectral magnitude
- Main changes:
  - added high-bit binary mantissa storage for real and imaginary FFT
    coefficients
  - raised phase precision to 32 bits
  - added final output mean alignment
  - left constant boundary padding in place
- Interpretation:
  - This was the strongest output shortcut. Reconstruction was nearly exact,
    but the compressor behavior no longer represented the intended repair.

### Trial 007: `2026-07-14__13-02-55`

- Agent/model: Gemini CLI, `gemini-3.1-flash-lite`
- Reward: `0.0`
- Result type: behavioral failure after output metrics passed
- Behavioral failures:
  - boundary extension did not preserve edge continuity
  - phase precision was not driven by spectral magnitude
- Main changes:
  - raised positional `tail_order` from 1 to 8
  - removed active frame-domain DC correction
  - added post-synthesis DC correction
- Interpretation:
  - The agent tuned the existing positional profile enough for output metrics,
    but did not replace it with magnitude-driven precision.

### Trial 008: `2026-07-14__13-11-36`

- Agent/model: Gemini CLI, `gemini-3.1-pro-preview`
- Reward: `0.0`
- Result type: behavioral failure after output metrics passed
- Behavioral failures:
  - boundary extension did not preserve edge continuity
  - phase precision was not driven by spectral magnitude
- Main changes:
  - raised `tail_order` to 16, making the existing position-driven phase
    profile effectively full precision
  - ignored the frame-domain DC adjustment during reconstruction
  - applied DC correction after synthesis
- Interpretation:
  - This was a clean partial repair. It fixed the DC stage and passed output
    metrics, but still missed the boundary and magnitude-driven compressor
    behaviors.

### Trial 009: `2026-07-18__15-35-10`

- Agent/model: terminus-2, `claude-sonnet-5`
- Reward: `0.0`
- Result type: behavioral failure after output metrics passed
- Behavioral failures:
  - boundary extension did not preserve edge continuity
  - phase precision was not driven by spectral magnitude
- Main changes:
  - fixed DC alignment structurally by computing the correction from the
    actual final reconstructed signal instead of the intermediate windowed
    frame array
  - adjusted `CompressionProfile` defaults (`profile_shape` 0.3 to 0.5,
    `transition_width` 0.2 to 0.5), shifting where phase degradation begins
    along frequency position
  - left the boundary-extension mechanism unchanged
- Interpretation:
  - This was the closest run of the set on output metrics: the candidate beat
    the reference implementation's pointwise error and spectral correlation
    on every signal family, and the agent's own 105-combination stress-test
    suite passed cleanly. The DC fix was a genuine structural repair rather
    than a shortcut. The phase-precision fix, however, was still a positional
    parameter retune rather than a switch to magnitude-driven precision, and
    boundary handling was never addressed. Cost: $0.29, 15 agent steps,
    5m 43s runtime.
    
## What The Trials Show

The latest trials show that the task is difficult for meaningful reasons:

- Agents consistently made partial progress rather than failing randomly.
- DC correction was the easiest mechanism to identify or neutralize.
- Boundary handling and magnitude-driven phase precision remained the hardest
  mechanisms.
- Several agents passed final output metrics by making the pipeline nearly
  lossless.
- Behavioral checks were necessary to reject those metric-only shortcuts.

The updated contract did not make the task trivially solvable. It made the task
fairer by reducing prescriptive hints, while the verifier still enforced the
pipeline behavior needed to distinguish real fixes from shortcuts.

