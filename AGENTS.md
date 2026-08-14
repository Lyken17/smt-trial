# SMT-COMP 2025 cvc5 tuning repository rules

## Supported scope

The only currently supported and end-to-end tested competition track is
`SingleQuery`. Incremental, UnsatCore, ModelValidation, and Parallel files are
reserved scaffolding and must not be reported as reproduced 2025 results until
their data, validation, execution, and scoring paths have been separately
completed and tested.

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

## Tuning boundary

For a Single Query tuning experiment, solver options may be changed only in:

- `configs/cvc5/single-query.toml`

Options may depend on Track, Division, and SMT-LIB Logic. They must not depend
on benchmark name, path, checksum, expected status, execution order, previous
answer, or observed result metadata. Harness code, documentation, dependency
configuration, and tests may be changed only to maintain or audit the harness,
not to manufacture a better score.

Wrong SAT/UNSAT answers are official scoring errors and must never be hidden or
filtered. The `24` performance is the official `walltime_s <= 24` scoring view;
it is not a 24-second execution limit. Formal Single Query execution uses the
official 1200-second wall limit, 4 cores, 4800 CPU seconds, and 30 GiB memory.

## Required workflow and reporting

Build with `make setup-single-query`. The resumable selection wrapper must call
the pinned official selection and scrambling functions and may skip a task only
when both its generated yml and scrambled SMT2 already exist. A complete
selection has 129,361 yml files and 129,361 scrambled SMT2 files; never round an
incomplete cache up to the official total.

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
parallelism must use `configs/setup-single-query.env`, environment overrides,
or automatic capability detection. Runtime files below `.cache`, `work`, and
`results` are local artifacts and must remain untracked.
