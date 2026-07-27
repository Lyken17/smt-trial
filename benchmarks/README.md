# Benchmarks

Both suites are fixed competition inputs and are covered by SHA-256 checksums
in their manifests:

- `smoke/` contains 10 small correctness cases across five logics.
- `smtlib-2025/` contains 95 training cases across nine logics.

The training suite is a deterministic, status-balanced size sample from the
[SMT-LIB 2025 non-incremental release][smtlib-2025]. It is a public proxy, not
the hidden benchmark selection used by any official competition. Do not modify
the benchmarks or their manifests in a challenge submission.

The provenance of every training formula, its expected status, and its
original checksum are recorded in `smtlib-2025/manifest.json`.

The repository's BSD license covers the challenge code, not these third-party
formulas. Benchmark files retain their upstream license metadata and
provenance; consult the source record before redistributing the corpus.

[smtlib-2025]: https://zenodo.org/records/16740866
