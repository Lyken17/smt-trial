"""Starter submission for the cvc5 configuration challenge.

Edit only ``get_config`` while tuning a competition entry. The evaluator calls
it once per benchmark with the SMT-LIB logic and the number of remote workers
available to the cloud harness.
"""

from __future__ import annotations


def get_config(logic: str, workers: int) -> dict[str, object]:
    """Return the cvc5 launcher configuration for one benchmark.

    ``cvc5_args`` contains complete command-line tokens such as
    ``--enum-inst-sum`` or ``--decision=internal``. Prefer ``--option=value``
    for options that take a value.
    """
    del logic, workers
    return {
        "mode": "sequential",
        "jobs_per_node": 1,
        "local_replicas": 1,
        "cvc5_args": (),
    }
