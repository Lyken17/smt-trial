# SMT-COMP 2025 cvc5 tuning repository rules

## Supported scope

The supported regular competition tracks are `SingleQuery`, `Incremental`,
`UnsatCore`, `ModelValidation`, and `Parallel`. `make smoke-all` is the required
small functional check. A track must not be reported as a full local 2025
reproduction unless its complete selection passes `make check-selection` (or
all five pass `make check-all-selections`) and its validator/execution/scoring
path was run. Cloud was not held in 2025 and ProofExhibition has no regular
score; do not invent results for either.

The organizers did not publish the final UnsatCore validator identity
selection. The repository's public-pool mode is the maximal deterministic pool
of publicly identifiable sound 2025 Single Query solvers and must retain
`exact_organizer_pool=false`. Never describe it as the unknown exact private
organizer selection.

## Immutable official inputs

Do not change the pinned SMT-COMP tool, benchmark metadata, historical results,
raw benchmark archives, selected benchmark membership, selection seed,
scramble IDs, expected statuses, Track/Division/Logic mapping, execution limits,
result parser, or score computation in order to improve a tuning result.

Official references:

- https://smt-comp.github.io/2025/rules.pdf
- https://github.com/SMT-COMP/smt-comp.github.io/tree/smtcomp25
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/selection.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scramble_benchmarks.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py
- https://doi.org/10.5281/zenodo.16740866
- https://doi.org/10.5281/zenodo.15493096

## Tuning boundary

For a tuning experiment, solver options may be changed only in:

- `configs/cvc5/<Track>/<Performance>.toml`

Options may depend on Track, Division, and SMT-LIB Logic. They must not depend
on benchmark name, path, checksum, expected status, execution order, previous
answer, or observed result metadata. Harness code, documentation, dependency
configuration, and tests may be changed only to maintain or audit the harness,
not to manufacture a better score.

Each Track/Performance file contains all official Divisions. The Performance
filename selects an independent candidate before a run;
it must never be exposed to the solver or used to dispatch individual
benchmarks. Every experiment must rerun its complete Division. Scores from
different experiment configurations must not be combined into one claimed
submission result.

Wrong SAT/UNSAT answers are official scoring errors and must never be hidden or
filtered. The `24` performance is the official `walltime_s <= 24` scoring view;
it is not a 24-second execution limit. Formal SingleQuery, Incremental,
UnsatCore, and ModelValidation execution uses the official 1200-second wall
limit, 4 cores, 4800 CPU seconds, and 30 GiB memory. Parallel uses 1200 seconds,
128 cores, 153600 CPU seconds, and 1000 GiB. A smaller-host functional smoke is
not an official-comparable Parallel timing result.

## Required workflow and reporting

Build all tracks with `make setup-all`; use `make setup-single-query` only for
the documented reduced scope. The resumable selection wrapper must call
the pinned official selection and scrambling functions and may skip a task only
when both its generated yml and non-empty scrambled SMT2 already exist. It may
repair a missing YAML from an existing non-empty scrambled file only through
the pinned official YAML generator and identical expected-status semantics.
Complete selections are: SingleQuery 129,361; Incremental 22,942; UnsatCore
70,604; ModelValidation 59,762; Parallel 400. Never round an incomplete cache
up to an official total.

The official Dolmen build's old Debian URLs now return 404. The compatibility
step may activate only the date-pinned Debian snapshot already recorded in the
pinned base image; it must not change the Dolmen commit, base-image digest,
dependency declarations, compile command, or tests. Source:
https://snapshot.debian.org/archive/debian/20240612T000000Z/

Run and score one Division explicitly, for example:

```bash
make run TRACK=SingleQuery DIVISION=QF_LinearIntArith RUN_ID=<run-id>
make score TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  PERFORMANCE=24 RUN_ID=<run-id>
```

Every reported tuning result must include Track, Division, performance kind,
cvc5 configuration/options, cvc5 revision, host CPU/RAM, official-tool revision,
and whether the full official selection passed the documented integrity checks.
Competition rankings are per Division and performance; any cross-Division sum
must be labeled non-official diagnostic output.

## Portability

Do not commit usernames, passwords, home-directory paths, drive letters,
machine names, regional package mirrors, fixed distribution codenames, fixed
CPU architectures, or generated cache symlinks. Host-dependent storage and
parallelism must use `configs/setup-single-query.env`, `configs/setup-all.env`,
environment overrides, or automatic capability detection. Runtime files below
`.cache`, `work`, and `results` are local artifacts and must remain untracked.
