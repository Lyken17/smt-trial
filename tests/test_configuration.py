from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from cvc5_cloud.configuration import (
    SolverConfig,
    load_config,
    read_logic,
    validate_config,
)


class SubmissionConfigurationTest(unittest.TestCase):
    def test_reads_smtlib_logic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            formula = Path(temporary) / "input.smt2"
            formula.write_text("(set-logic QF_NRA)\n(check-sat)\n")
            self.assertEqual(read_logic(formula), "QF_NRA")

    def test_starter_submission_is_sequential(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            formula = Path(temporary) / "input.smt2"
            formula.write_text("(set-logic QF_UF)\n(check-sat)\n")
            self.assertEqual(
                load_config(formula, workers=99),
                SolverConfig(
                    mode="sequential",
                    jobs_per_node=1,
                    local_replicas=1,
                    cvc5_args=(),
                ),
            )

    def test_rejects_unknown_configuration_keys(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown configuration keys"):
            validate_config(
                {
                    "mode": "sequential",
                    "jobs_per_node": 1,
                    "local_replicas": 1,
                    "cvc5_args": (),
                    "answer": "sat",
                }
            )

    def test_rejects_runner_managed_cvc5_arguments(self) -> None:
        with self.assertRaisesRegex(ValueError, "managed"):
            validate_config(
                {
                    "mode": "portfolio",
                    "jobs_per_node": 8,
                    "local_replicas": 1,
                    "cvc5_args": ("--tlimit=1",),
                }
            )


if __name__ == "__main__":
    unittest.main()
