from pathlib import Path
import tempfile
import unittest

from smtcomp_harness.dispatch import benchmark_logic, division_for, solver_args


ROOT = Path(__file__).resolve().parents[1]


class DispatchTests(unittest.TestCase):
    def test_logic_and_division(self):
        with tempfile.TemporaryDirectory() as tmp:
            benchmark = Path(tmp) / "x.smt2"
            benchmark.write_text("; comment\n(set-logic QF_LIA)\n(check-sat)\n")
            self.assertEqual(benchmark_logic(benchmark), "QF_LIA")
            self.assertEqual(division_for("SingleQuery", "QF_LIA"), "QF_LinearIntArith")

    def test_parallel_mapping_is_official(self):
        self.assertEqual(division_for("Parallel", "QF_BV"), "QF_Bitvec")

    def test_incremental_protocol_is_harness_owned(self):
        with tempfile.TemporaryDirectory() as tmp:
            benchmark = Path(tmp) / "x.smt2"
            benchmark.write_text("(set-logic QF_LIA)\n(check-sat)\n")
            args = solver_args(ROOT / "configs/cvc5/incremental.toml", "Incremental", benchmark)
            self.assertIn("--incremental", args)
            self.assertIn("--print-success", args)
            self.assertNotIn("--no-incremental", args)


if __name__ == "__main__":
    unittest.main()
