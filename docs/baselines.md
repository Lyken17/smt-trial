# Baselines

Measured on July 26, 2026, using the pinned cvc5 competition build:

- cvc5 `1.3.5.dev`, commit `6f2bc560651b6b739de93519f5cc815c182a0027`
- GCC 13.1.0, static competition build
- host `cpu-00097`, Linux 5.15, 96 logical CPUs
- 10 seconds per benchmark
- 95 non-incremental SMT-LIB 2025 benchmarks

The proxy is a deterministic, status-balanced size-quantile sample from
[SMT-LIB 2025 on Zenodo](https://zenodo.org/records/16740866). Its manifest
SHA-256 is
`7dd9d837beca9ebd7061c5f7ccc97b681abc5467a57501b7055858f03c94f39d`.
ABVFP and QF_NIRA contain fewer than 12 labeled SAT/UNSAT instances in the
source archives, so the final sample has 95 rather than 108 benchmarks.

## Aggregate

| Baseline | Solved | Wrong | Unknown | Total wall (s) | PAR-2 (s) |
|---|---:|---:|---:|---:|---:|
| Sequential | 73/95 | 0 | 22 | 173.107 | 450.906 |
| Portfolio-8 | 83/95 | 0 | 12 | 127.699 | 253.644 |
| Seeded race 4x2 | 83/95 | 0 | 12 | 135.096 | 261.020 |

## By Logic

| Logic | Instances | Sequential | Portfolio-8 | Seeded race 4x2 |
|---|---:|---:|---:|---:|
| ABVFP | 9 | 9 | 9 | 9 |
| ALIA | 12 | 7 | 12 | 12 |
| LIA | 12 | 10 | 10 | 10 |
| NIA | 12 | 12 | 12 | 12 |
| NRA | 12 | 7 | 10 | 10 |
| QF_ALIA | 12 | 6 | 7 | 7 |
| QF_AUFLIA | 12 | 11 | 12 | 12 |
| QF_NIRA | 2 | 1 | 1 | 1 |
| QF_S | 12 | 10 | 10 | 10 |

The local cvc5 portfolio adds 10 solves over sequential, concentrated in ALIA,
NRA, QF_ALIA, and QF_AUFLIA. The seeded race does not add solves on this sample
and is slightly slower on one host, so its value still needs an actual
multi-node AWS measurement. It is retained as the minimum distributed
orchestration baseline.

Reproduce the sample and run:

```bash
make baseline-proxy
```

Generated per-instance data is written to
`benchmark-results/smtlib-2025/{runs.csv,summary.json,REPORT.md}`. The final
SMT-COMP 2026 cloud benchmark selection and hardware are not yet published, so
these measurements are engineering baselines, not predicted competition
scores.
