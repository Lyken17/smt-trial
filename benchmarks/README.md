# Benchmarks

`smoke/` is a checked-in correctness suite spanning bit-vectors, linear and
nonlinear integer arithmetic, strings, and quantified uninterpreted functions.
It is intentionally too small and easy for performance conclusions.

Run `make benchmarks` to create `smtlib-2025/`, a deterministic sampled proxy
from the official SMT-LIB 2025 Zenodo release. The cloud organizers have not
published the final 2026 benchmark selection, so proxy results are engineering
baselines rather than predicted competition scores.

