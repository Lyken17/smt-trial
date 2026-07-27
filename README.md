# cvc5-cloud

This repository packages a pinned cvc5 competition build and three baselines
for the [SMT-COMP 2026 cloud track][cloud-track]:

1. **Sequential** - one unmodified cvc5 process.
2. **Local portfolio** - cvc5's `smtcomp2026` logic-aware internal portfolio,
   using up to eight concurrent jobs on one node.
3. **Distributed seeded race** - one internal portfolio on every AWS node,
   with distinct cvc5 and SAT random seeds; the first definitive result wins.

The distributed baseline is intentionally simple. It exercises all cloud
nodes and provides a reliable measurement floor before adding partitioning or
lemma sharing. It is not expected to scale linearly because nodes do redundant
work.

## Baseline Results

The current proxy uses 95 labeled benchmarks sampled deterministically from
nine SMT-LIB 2025 logics, with a 10-second per-instance timeout:

| Baseline | Solved | Wrong | Unknown | PAR-2 (s) |
|---|---:|---:|---:|---:|
| Sequential | 73/95 | 0 | 22 | 450.906 |
| Portfolio-8 | 83/95 | 0 | 12 | 253.644 |
| Seeded race 4x2 | 83/95 | 0 | 12 | 261.020 |

The built-in cvc5 portfolio adds ten solves over sequential. The seeded race
is a single-host emulation here; its value must be measured on multiple AWS
nodes. See [`docs/baselines.md`](docs/baselines.md) for logic-level results,
methodology, and reproducibility details.

## Pinned Inputs

- cvc5 branch `smtcomp2026`, commit
  `6f2bc560651b6b739de93519f5cc815c182a0027`
- AWS competition infrastructure branch `mainline-2026`, commit
  `e88c32ae6173a1e0713a0e727af424d6298c6949`
- SMT-LIB 2025 non-incremental release, Zenodo record `16740866`

All pins are centralized in [`versions.env`](versions.env). The Dockerfile
duplicates the cvc5 revision because Docker `ARG` defaults cannot import an env
file; a contract test ensures the values stay equal.

## Quick Start

The local build needs Python 3.10+, CMake, Ninja, and either GCC 10+ or
Clang 12+. On this cluster, `scripts/bootstrap.sh` loads `gcc/13.1.0` when the
default compiler is too old.

```bash
make build
make test
make smoke
make baseline-proxy
```

Generated binaries and source checkouts live under `.cache/`. Smoke baseline
artifacts are written to `benchmark-results/smoke/`; proxy artifacts are
written to `benchmark-results/smtlib-2025/`. Both result directories and the
downloaded proxy corpus are intentionally ignored by Git.

The final cloud selection has not been published, so these proxy measurements
are engineering baselines rather than predictions of the competition score.

## Repository Layout

| Path | Purpose |
|---|---|
| `aws-build/` | Required competition Dockerfile and harness adapter |
| `cvc5_cloud/runner.py` | Sequential, portfolio, and distributed launcher |
| `configs/` | Local, distributed, and AWS job configurations |
| `scripts/` | Build, infrastructure, benchmark, and measurement tooling |
| `benchmarks/smoke/` | Checked-in harness-compatible correctness suite |
| `tests/` | Runner, submission-contract, and remote-worker tests |
| `docs/` | Architecture, measured baselines, and submission checklist |

## AWS Harness

The required submission files are:

- [`aws-build/Dockerfile`](aws-build/Dockerfile)
- [`aws-build/solver_cmd.py`](aws-build/solver_cmd.py)

Fetch the exact harness revision:

```bash
source scripts/activate_infrastructure.sh
satcomp.py configs/local.yml --build
satcomp.py configs/local.yml \
  --jobs-test-local configs/jobs-local.yml \
  --results-dir test-results \
  --test-local
satcomp.py configs/local.yml --acceptance-test
```

The official infrastructure driver additionally requires Python 3.12+,
Docker 25+, and Node.js 22+. The activation script exports
`CVC5_CLOUD_ROOT`, which the YAML files use to resolve this repository
independently of the harness checkout.

Test the distributed path locally with two worker containers:

```bash
satcomp.py configs/cloud.yml --build
satcomp.py configs/cloud.yml \
  --jobs-test-local configs/jobs-local.yml \
  --num-workers 2 \
  --test-local cvc5-cloud
```

Docker is required for these harness tests. For an AWS run, replace the S3
path in `configs/jobs-cloud.example.yml`, then follow the infrastructure
project's provisioning, push, start, submit, collect, and teardown workflow.
AWS resources incur charges.

## Verification Status

- The pinned static cvc5 competition build completes and reports commit
  `6f2bc5606`.
- All 19 automated tests pass, including a staged fake SCP/SSH worker.
- Sequential, portfolio, and seeded-race modes each solve all 10 smoke cases.
- The local and cloud YAML files pass the pinned infrastructure parser.
- The harness adapter passes the pinned `SolverInput` and result-code types.
- Docker acceptance, real multi-container execution, and AWS qualification
  remain open because this host does not provide Docker or Python 3.12.

## Competition Contract

The launcher prints exactly `sat`, `unsat`, or `unknown` on stdout and returns
exit code `10`, `20`, or `0`, respectively. Diagnostics go to stderr. Remote
benchmarks are staged with `scp`; cvc5 processes are run through SSH and
cleaned on every node after each job.

The cloud track is separate from the main SMT-COMP tracks. Its published
deadline is August 22, 2026, its recommended timeout is 200 seconds, and its
submission uses the AWS harness above. Confirm portfolio/derived-solver
eligibility and final hardware with the cloud organizers before submission;
the public page does not yet spell out all recognition rules.

See [`docs/architecture.md`](docs/architecture.md) for design details,
[`docs/baselines.md`](docs/baselines.md) for measured results, and
[`docs/submission-checklist.md`](docs/submission-checklist.md) for the
remaining competition gates.

[cloud-track]: https://smt-comp.github.io/2026/cloud_track/
