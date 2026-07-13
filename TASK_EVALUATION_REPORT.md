# Signal Reconstruction Fidelity Task Evaluation Report

## Executive Summary

The `signal-reconstruction-fidelity` task was evaluated across seven completed
agent trials after reward-file plumbing was fixed. All seven trials were
harness-clean and produced scored verifier results with reward `0.0`; none
failed because of missing reward files or infrastructure exceptions.

The trials indicate that the task is genuinely difficult. Agents made partial
progress in several different ways, but no tested agent fully repaired the
pipeline. The most successful run fixed boundary behavior and DC behavior, then
failed only the hidden behavioral check requiring phase precision to be driven
by spectral magnitude.

The main Terminal Bench 3 design risk is not overall difficulty. The risk is
that the hidden verifier enforces a compressor design property that is only
implicit in the current visible instructions. Agents that make the pipeline
effectively lossless can satisfy all output-fidelity metrics while still being
rejected for not preserving the intended compression architecture. This is a
fair and useful behavioral check if the visible contract explicitly says the
spectral compression stage must remain quantized and magnitude-adaptive.

## Task Under Evaluation

- Task name: `signal-reconstruction-fidelity`
- Category: signal-processing debugging
- Primary modules:
  - `windowing.py`
  - `spectral_compressor.py`
  - `reconstructor.py`
- Contract metrics:
  - pointwise interior error
  - FFT magnitude correlation
  - DC preservation
  - boundary error ratio

The intended repair requires:

1. Using continuity-preserving boundary extension for the default stable
   framing path.
2. Allocating phase quantization precision according to spectral magnitude, not
   FFT-bin position.
3. Restoring DC after overlap-add synthesis and trimming, not by shifting
   intermediate windowed frames.

## Evaluation Method

The task was run through multiple agent trials using Codex and Gemini variants.
For each run, the following were inspected:

- top-level job result
- reward-file status
- verifier stdout
- submitted artifact files
- agent transcript when useful

The separate verifier first evaluates deterministic output-fidelity signal
families, then applies behavioral probes for pipeline structure and mechanism
preservation.

## Trial Summary

| Trial | Job | Agent | Model | Reward | Result Type | Main Failure |
|---|---|---|---|---:|---|---|
| 001 | `jobs/2026-07-13__14-15-28` | Codex | `openai/gpt-5.4` | 0.0 | Behavioral failure | Exact-phase shortcut; boundary and magnitude-adaptive mechanisms unfixed |
| 002 | `jobs/2026-07-13__14-23-18` | Codex | `openai/gpt-5.5` | 0.0 | Behavioral failure | Same output-perfect shortcut as Trial 001 |
| 003 | `jobs/2026-07-13__14-15-24` | Gemini CLI | `gemini/gemini-2.5-pro` | 0.0 | Output failure | Original boundary, spectral, and DC bugs mostly remained |
| 004 | `jobs/2026-07-13__14-30-58` | Gemini CLI | `gemini/gemini-3.5-flash` | 0.0 | Behavioral failure | Uniform full-precision quantization; boundary and magnitude-adaptive mechanisms unfixed |
| 005 | `jobs/2026-07-13__14-36-09` | Gemini CLI | `gemini/gemini-3.1-flash-lite` | 0.0 | Output failure | Spectral-only partial fix; DC bug remained |
| 006 | `jobs/2026-07-13__14-40-39` | Gemini CLI | `gemini/gemini-3-flash-preview` | 0.0 | Behavioral near-miss | Boundary and DC fixed; phase precision remained position-driven |
| 007 | `jobs/2026-07-13__14-44-16` | Gemini CLI | `gemini/gemini-3.1-pro-preview` | 0.0 | Output failure | DC neutralized and boundary frames bypassed; spectral compressor unchanged |

## Observed Failure Patterns

### 1. Output-Perfect Shortcuts

Trials 001, 002, and 004 passed output-fidelity families but failed hidden
behavioral checks. These agents made the spectral stage effectively lossless,
either by preserving exact phase or by setting all phase quantization to high
precision.

This demonstrates that output-only grading would be too weak for this task.
The behavioral checks are necessary to reject solutions that remove the
intended compression behavior rather than repairing it.

### 2. Partial Local Repairs

Trials 005 and 007 each repaired one or two symptoms but left an independent
bug intact.

- Trial 005 improved spectral precision but missed the DC ordering bug.
- Trial 007 neutralized DC and bypassed boundary-frame compression but left the
  spectral compressor unchanged.

These trials show that the task is not solvable with a single local tweak. The
verifier successfully separates independent bug classes.

### 3. Strong Near-Miss

Trial 006 is the strongest evidence that the task has real diagnostic depth.
The agent repaired boundary behavior and DC behavior, and all output-fidelity
families passed. The only remaining failure was:

```text
behavior: FAIL phase precision is not driven by spectral magnitude
```

The submitted compressor still allocated precision by FFT-bin position rather
than spectral magnitude. This distinguishes parameter tuning from conceptual
repair.

## Difficulty Assessment

The task appears genuinely hard for current agents. Evidence:

- Seven scored trials produced no complete solution.
- Agents failed in different ways rather than all making the same simple
  mistake.
- Several agents made meaningful partial progress.
- The best run repaired two of the three intended mechanisms and still missed
  the deeper spectral-compression rule.

The bug architecture is therefore doing useful work. It creates a multi-step
debugging problem in which agents must reason about runtime behavior, signal
families, and cross-module interactions.

## Terminal Bench 3 Fairness Assessment

The task is close to TB3-ready, but one fairness issue should be addressed
before finalizing a more verbose variant.

The current visible instruction says the public reconstruction API must satisfy
the fidelity contract. It does not clearly state that:

- the spectral stage must remain a quantized compression stage,
- exact phase preservation is not an acceptable repair,
- uniform maximum precision is not an acceptable repair, or
- phase precision is expected to be allocated by spectral magnitude.

Because the hidden verifier enforces magnitude-adaptive behavior, agents can
reasonably produce output-valid solutions that fail for architectural reasons
not fully stated in the visible contract.

This does not make the task invalid, but it does mean the next variation should
make the compressor contract explicit. A small visible sentence would be enough:

> The spectral compression stage must remain a quantized compression stage. Do
> not bypass phase quantization or preserve exact phase. Phase precision should
> be allocated according to spectral component magnitude, with stronger
> components receiving at least as much precision as weaker components.

This wording preserves the challenge while making the behavioral verifier fair.

## Recommendations

1. Keep the three-bug architecture.

   The trial data shows independent failures for boundary handling, spectral
   compression, and DC restoration.

2. Keep the behavioral probes.

   They caught output-perfect shortcuts that would otherwise have passed.

3. Add a visible compressor-contract hook in the next variation.

   This reduces the risk that the task feels like an implementation-preference
   test rather than a debugging task.

4. Keep the oracle diagnostic style.

   The updated `solution/solution.sh` now observes the system, probes signal
   classes, prints root-cause diagnostics, and only then patches files.

5. Continue running agent trials after the instruction update.

   The key thing to watch is whether the added compressor-contract language
   makes the task too easy or simply prevents hidden-contract ambiguity.

## Conclusion

The current task is difficult for substantive reasons, not because the harness
is broken. The verifier is functioning correctly and captures multiple classes
of incomplete or shortcut solutions.

For final TB3 alignment, the next iteration should make the compressor behavior
visible in the contract. With that adjustment, failures would be attributable
to diagnostic difficulty rather than an implicit implementation requirement.
