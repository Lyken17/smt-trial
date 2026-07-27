# Architecture

## Configuration Boundary

`submission.py` is the entrant-controlled file. Its `get_config(logic,
workers)` function selects the launcher mode, jobs per node, local replicas,
and extra cvc5 options. `cvc5_cloud/configuration.py` reads the formula logic
and validates this dictionary before any solver process starts.

The local scorer and the AWS harness both use this loader. A configuration
therefore has the same meaning during development and cloud execution.

## Execution

The AWS harness invokes `aws-build/solver_cmd.py` on the leader. The adapter
passes the validated submission, benchmark timeout, and worker addresses to
`cvc5_cloud/runner.py`. In distributed mode, the runner:

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

Sequential mode starts one unmodified cvc5 process. Portfolio mode starts one
cvc5 internal portfolio. Distributed mode starts seeded internal portfolios on
the leader and available workers; the first definitive result wins.

The launcher prints exactly `sat`, `unsat`, or `unknown` on stdout and returns
exit code 10, 20, or 0. Diagnostics are isolated on stderr. Residual cvc5
processes and staged formulas are cleaned after every harness job.
