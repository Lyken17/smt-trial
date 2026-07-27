# Challenge Agent Instructions

These instructions apply when working on a challenge submission. Repository
maintainers may edit infrastructure while developing the challenge itself.

## Objective

Maximize the number of correct SMT results reported by `make score`. The
starter score is 73/95. Wrong `sat` or `unsat` answers are invalid; prefer
`unknown` when cvc5 cannot decide a case safely.

## Allowed Edit

Edit `submission.py` only. Use its `logic` and `workers` inputs to select valid
cvc5 modes, job counts, replicas, and command-line options.

Do not modify:

- `tests/` or `tests/submission_tests.py`;
- `benchmarks/`, manifests, expected statuses, or checksums;
- `cvc5_cloud/`, `aws-build/`, `configs/`, or timeout handling;
- repository integrity checks or result parsing.

Do not hardcode answers, benchmark identities, checksums, or evaluation order.
Do not infer answers from expected-status metadata.

## Workflow

1. Read `submission.py` and cvc5's option help.
2. Form a solver-configuration hypothesis.
3. Run a targeted logic with
   `make score SCORE_ARGS="--logic LOGIC"`.
4. Run `make smoke` after every configuration family change.
5. Run the complete `make score` before reporting an improvement.
6. Report solved, wrong, unknown, wall time, and PAR-2.

Agent-assisted search, web research, and automated experiments are allowed.
Keep experimental logs and generated files out of Git.
