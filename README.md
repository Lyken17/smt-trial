# cvc5 Cloud Configuration Challenge

Tune a pinned [cvc5][cvc5] build to solve as many SMT benchmarks as possible.
The starter is intentionally simple: one sequential cvc5 process with no
extra options. The goal is to improve its pass rate through logic-aware solver
configuration, local portfolios, and cloud worker use.

This is an independent training challenge inspired by
[Anthropic's original performance take-home][anthropic-takehome] and packaged
around the distributed interface prepared for the
[SMT-COMP cloud track][cloud-track]. The official 2026 site states that the
cloud track was not held because suitable execution infrastructure was
unavailable, so this repository is a classroom and research competition, not
an official SMT-COMP 2026 entry.

AI coding and research agents are allowed and encouraged. They must optimize
the real solver configuration, not alter the evaluator or encode benchmark
answers.

## Score

The checked-in training suite contains 95 labeled SMT-LIB 2025 formulas from
nine logics. Every formula has a 10-second wall-clock limit.

1. The primary score is the number of correct `sat` or `unsat` results.
2. `unknown` and timeouts are unsolved cases.
3. A wrong `sat` or `unsat` result fails evaluation.
4. Total wall time and PAR-2 are reported as secondary measurements.

The starter sequential configuration solves **73/95** cases with no wrong
answers. The target is **95/95**. Timing varies by machine, so compare pass
counts first and use timing only under controlled conditions.

## Quick Start

The local build requires Python 3.10+, CMake, Ninja, and GCC 10+ or Clang 12+.
The bootstrap script installs pinned Python build tools and checks out the
exact cvc5 competition revision.

```bash
make setup
make build
make test
make smoke
make score
```

The cvc5 checkout, build, and virtual environment stay under ignored
directories. Scoring prints to the terminal and does not create a results
tree.

For a faster targeted experiment:

```bash
make score SCORE_ARGS="--logic NRA"
make score SCORE_ARGS="--logic QF_ALIA --limit 4 --timeout 3"
```

Run `python tests/submission_tests.py --help` for all evaluator options.

## Submission Surface

Edit [`submission.py`](submission.py). Its only required function is:

```python
def get_config(logic: str, workers: int) -> dict[str, object]:
    return {
        "mode": "sequential",
        "jobs_per_node": 1,
        "local_replicas": 1,
        "cvc5_args": (),
    }
```

The evaluator supplies the uppercase SMT-LIB logic and available remote worker
count. A submission may return different settings per logic.

| Field | Meaning |
|---|---|
| `mode` | `sequential`, `portfolio`, or `distributed` |
| `jobs_per_node` | cvc5 jobs used by each internal portfolio |
| `local_replicas` | seeded local portfolios in distributed mode |
| `cvc5_args` | extra complete cvc5 option tokens |

Use `--option=value` for options that require a value. Language, timeout, and
portfolio-control flags are owned by the runner so every submission is scored
under the same contract.

The same `submission.py` is copied into the AWS image and loaded by
`aws-build/solver_cmd.py`. Local evaluation and cloud packaging therefore use
one source of truth.

## Rules

Treat `tests/`, `benchmarks/`, `cvc5_cloud/`, `aws-build/`, and `configs/` as
frozen challenge infrastructure. The intended submission diff is
`submission.py`.

Allowed:

- use coding agents, search agents, scripts, and automated experiments;
- inspect benchmark syntax, cvc5 help, logs, and timing data;
- select different valid cvc5 options for different SMT-LIB logics;
- use the provided portfolio and distributed modes.

Not allowed:

- modify tests, manifests, benchmark formulas, expected results, or timeouts;
- hardcode answers, benchmark filenames, checksums, or evaluation order;
- make solver decisions by reading expected-status metadata;
- report scores from a modified evaluator.

When using an agent, instruct it to optimize only `submission.py` and verify
with the canonical scorer. Before sharing a result, run:

```bash
git diff origin/main -- tests/ benchmarks/ cvc5_cloud/ aws-build/ configs/
make test
make smoke
make score
```

The first command must be empty for a challenge submission.

## Repository Layout

| Path | Purpose |
|---|---|
| `submission.py` | entrant-controlled cvc5 configuration |
| `tests/submission_tests.py` | canonical scorer |
| `benchmarks/smtlib-2025/` | fixed 95-case training suite |
| `benchmarks/smoke/` | fast 10-case correctness suite |
| `cvc5_cloud/` | validated local and distributed runner |
| `aws-build/` | competition Dockerfile and harness adapter |
| `configs/` | local and distributed infrastructure definitions |
| `scripts/` | reproducible cvc5 and harness setup |
| `versions.env` | pinned source revisions |

See [`docs/architecture.md`](docs/architecture.md) for launcher behavior and
[`docs/submission-checklist.md`](docs/submission-checklist.md) before testing a
cloud entry.

## Pinned Inputs

- cvc5 branch `smtcomp2026`, commit
  `6f2bc560651b6b739de93519f5cc815c182a0027`
- AWS competition infrastructure branch `mainline-2026`, commit
  `e88c32ae6173a1e0713a0e727af424d6298c6949`
- SMT-LIB 2025 non-incremental release, Zenodo record `16740866`

All revisions are centralized in [`versions.env`](versions.env). The
Dockerfile repeats the cvc5 revision because Docker build arguments cannot
import the environment file; a repository test keeps both pins equal.

[anthropic-takehome]: https://github.com/anthropics/original_performance_takehome
[cloud-track]: https://smt-comp.github.io/2026/parallel_track/#cloud-track
[cvc5]: https://github.com/cvc5/cvc5
