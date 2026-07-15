# Signal Reconstruction Fidelity

This repository contains a Terminal Bench 3 task for debugging a small signal
reconstruction pipeline.

The task asks an agent to repair a public reconstruction API:

```python
reconstruct(signal, sample_rate=...)
```

The implementation must satisfy the fidelity contract in
`environment/app/system_contract.md` while preserving the three-stage pipeline:

```text
windowing -> spectral compression -> reconstruction
```

## Task Structure

```text
.
├── task.toml
├── instruction.md
├── environment/
│   ├── Dockerfile
│   └── app/
│       ├── fidelity_checker.py
│       ├── reconstructor.py
│       ├── requirements.txt
│       ├── spectral_compressor.py
│       ├── system_contract.md
│       └── windowing.py
├── tests/
│   ├── Dockerfile
│   ├── reference/
│   │   └── reference_pipeline.py
│   ├── test.sh
│   └── verifier.py
└── solution/
    └── solution.sh
```

## What The Task Tests

The verifier evaluates reconstruction quality across several signal families,
including simple tones, boundary-sensitive signals, low-amplitude multi-tone
signals, non-zero-mean signals, and combined stress cases.

It checks:

- pointwise reconstruction error
- spectral magnitude correlation
- DC preservation
- boundary behavior
- preservation of the pipeline structure

The task is designed so a simple smoke test is not enough. A correct solution
has to diagnose interactions across windowing, spectral compression, and final
reconstruction.

## Prerequisites

- Python 3.11
- NumPy and SciPy for direct local verifier runs
- Docker for containerized verifier/oracle runs
- Harbor for agent trial runs

## Latest Agent Trial Results

The latest trial set was run on July 14, 2026 after the contract and task
instructions were revised to be less prescriptive.

Summary:

- 8 clean scored July 14 verifier runs were inspected
- 0 agents fully solved the task

| Category | Count | What It Means |
|---|---:|---|
| Clean scored verifier runs | 8 | Agent reached the task and produced a candidate judged by the verifier |
| Full solves | 0 | No scored agent satisfied both output and behavioral checks |
| Output metrics passed, behavior failed | 5 | Candidate looked numerically good but violated pipeline behavior |
| Output metrics failed | 3 | Candidate still failed one or more fidelity signal families |

| Job | Agent / Model | Reward | Result Type | Main Failure |
|---|---|---:|---|---|
| `2026-07-14__12-28-23` | Gemini CLI / `gemini-3.5-flash` | 0.0 | Output failure | DC improved and boundary padding changed to edge hold, but spectral compression remained position-driven |
| `2026-07-14__12-28-27` | Codex / `gpt-5.4-mini` | 0.0 | Behavioral failure | High-resolution rectangular quantization passed metrics, but boundary and magnitude-driven precision stayed wrong |
| `2026-07-14__12-41-17` | Codex / `gpt-5.4` | 0.0 | Behavioral failure | Uniform 24-bit phase precision and DC correction passed metrics, but missed boundary and magnitude behavior |
| `2026-07-14__12-41-42` | Gemini CLI / `gemini-2.5-pro` | 0.0 | Output failure | DC handled through zero-mean reconstruction, but boundary and spectral bugs remained |
| `2026-07-14__12-54-56` | Gemini CLI / `gemini-3-flash-preview` | 0.0 | Output failure | Partial DC repair only; boundary-sensitive and multi-tone cases still failed |
| `2026-07-14__12-55-09` | Codex / `gpt-5.5` | 0.0 | Behavioral failure | Near-exact reconstruction through high-bit coefficient storage, but intended pipeline behavior was not repaired |
| `2026-07-14__13-02-55` | Gemini CLI / `gemini-3.1-flash-lite` | 0.0 | Behavioral failure | Positional tail precision tuned enough for metrics, but not magnitude-driven |
| `2026-07-14__13-11-36` | Gemini CLI / `gemini-3.1-pro-preview` | 0.0 | Behavioral failure | DC fixed and precision raised, but boundary and magnitude-driven checks failed |

Note: Claude models were not included in this trial set because I did not have access to them at the time this task was created and evaluated.

The strongest pattern was not random failure. Agents generally found partial
repairs or shortcuts:

- several agents fixed or neutralized the DC restoration issue
- several agents made the reconstruction numerically accurate by using very
  high precision or near-lossless spectral representations
- no scored July 14 run repaired both the boundary-extension behavior and the
  magnitude-driven phase precision behavior
- output-only grading would have accepted several incorrect submissions

This trial set supports the current verifier design. The behavioral checks were
necessary because multiple agents produced excellent final output metrics while
still violating the intended pipeline behavior. The detailed trial writeup is in
`LATEST_AGENT_TRIAL_RESULTS.md`.

## Local Verification

To run the verifier directly from the repository:

```bash
python3 tests/verifier.py
```

The test entrypoint is intended for the verifier container, where the test
directory is mounted at `/tests`:

```bash
/tests/test.sh
```

The verifier writes the reward file to `/logs/verifier/reward.txt` by default,
or to `$REWARD_DIR/reward.txt` when `REWARD_DIR` is set.

## Running Agent Trials With Harbor

Run these commands from the repository root.

### Gemini CLI

```bash
harbor run -p . \
  --agent gemini-cli \
  --model gemini/gemini-3.1-pro-preview \
  --env docker \
  --yes \
  --ae GEMINI_API_KEY="<YOUR_GEMINI_API_KEY>"
```

### Codex

Log in to Codex first, then run:

```bash
harbor run -p . \
  --agent codex \
  --model openai/gpt-5.5 \
  --env docker \
  --yes \
  --ae CODEX_FORCE_AUTH_JSON=1 \
  --ak reasoning_effort=xhigh
```

### Claude Code

Run `claude setup-token` first to get the OAuth token, then run:

```bash
harbor run -p . \
  --agent claude-code \
  --model anthropic/claude-opus-4-8 \
  --env docker \
  --yes \
  --ae CLAUDE_FORCE_OAUTH=1 \
  --ae CLAUDE_CODE_OAUTH_TOKEN=<YOUR_OAUTH_TOKEN> \
  --ak reasoning_effort=max
```

## Oracle Check

The oracle solution is in `solution/solution.sh`. It is intentionally diagnostic:
it observes the visible behavior, reads the contract, probes signal classes, then
applies the repair and runs the verifier.

If Docker access is available, the oracle can be tested with:

```bash
docker build -t signal-reconstruction-fidelity-oracle environment
docker run --rm \
  -v "$PWD/tests:/tests:ro" \
  -v "$PWD/solution:/solution:ro" \
  -e REWARD_DIR=/logs/verifier \
  signal-reconstruction-fidelity-oracle \
  /bin/sh /solution/solution.sh
```

The expected final reward is `1.0`.

## Acknowledgements

This task was developed using the official Terminal Bench repository and tooling
as the benchmark framework.

The task design and wording were also informed by Ivan Bercovich's article,
[Writing a Good Terminal Bench Task](https://ivanbercovich.com/2026/writing-a-good-terminal-bench-task),
which was especially useful for refining the instructions, verifier philosophy,
and avoiding overly prescriptive task descriptions.
