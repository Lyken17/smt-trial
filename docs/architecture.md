# Architecture

## Execution

The AWS harness invokes `aws-build/solver_cmd.py` on the leader. The shim
selects a baseline from `SOLVER_NAME`, passes the benchmark timeout and worker
IP list to `cvc5_cloud/runner.py`, and parses the launcher's final stdout.

For distributed runs, the launcher:

1. copies the leader's downloaded `.smt2` file to every reachable worker;
2. starts a cvc5 internal portfolio locally and through SSH on each worker;
3. assigns each node a distinct `--seed` and `--sat-random-seed`;
4. returns the first exact `sat` or `unsat` result;
5. terminates local SSH clients, after which the harness broadcasts the
   cleanup command to every node.

Each cvc5 process receives an internal wall-clock limit shorter than the
harness limit. Three seconds remain for orchestration and cleanup. The harness
still provides the authoritative outer timeout.

## Why This Baseline

The cvc5 `smtcomp2026` branch contains a built-in portfolio with strategies for
linear and nonlinear arithmetic, quantified logics, bit-vectors, arrays, and
strings. Reusing those strategies establishes a strong baseline with a small
amount of noncritical orchestration code.

Forking inside cvc5 also initially shares parsed assertions through
copy-on-write memory. Eight jobs per 16-vCPU node matches the infrastructure
guidance to prefer physical cores over hardware threads.

The scaling limitation is deliberate: all nodes solve the complete formula.
Seeds diversify SAT decisions and other randomized behavior, but deterministic
theory-heavy problems may receive little benefit from additional nodes.

## Next Experimental Baselines

The next meaningful implementation should divide work instead of adding more
seeds:

- use cvc5 partition generation (`--compute-partitions`) to create cubes;
- schedule cubes dynamically across workers;
- stop globally after a SAT cube or after every cube is UNSAT;
- add cube rebalancing when a worker finishes early;
- compare partition generation overhead against the seeded race under the
  200-second budget.

That design has a larger correctness surface. In particular, an UNSAT answer
is valid only after all exhaustive partitions return UNSAT.

