from __future__ import annotations

import enum
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


class FakeResultCode(enum.Enum):
    UNKNOWN = 0
    SAT = 10
    UNSAT = 20
    INDETERMINATE = -6


def load_solver_cmd():
    common = types.ModuleType("common")
    solver_io = types.ModuleType("common.solver_io")
    solver_io.SolverInput = object
    solver_io.SolverResultCode = FakeResultCode
    common.solver_io = solver_io
    sys.modules["common"] = common
    sys.modules["common.solver_io"] = solver_io
    path = Path(__file__).resolve().parents[1] / "aws-build/solver_cmd.py"
    spec = importlib.util.spec_from_file_location("aws_solver_cmd", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SolverCommandTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_solver_cmd()

    def test_cloud_command_contains_all_workers(self) -> None:
        solver_input = types.SimpleNamespace(
            formula_file=Path("/tmp/formula.smt2"),
            timeout_seconds=200,
            worker_node_ips=["10.0.0.2", "10.0.0.3"],
            solver_argument_list=[],
        )
        with mock.patch.dict(os.environ, {"SOLVER_NAME": "cvc5-cloud"}):
            command = self.module.get_run_command(solver_input)
        self.assertIn("distributed", command)
        self.assertEqual(command.count("--host"), 2)
        self.assertIn("10.0.0.2", command)
        self.assertEqual(command[-1], "/tmp/formula.smt2")

    def test_solver_name_selects_sequential_baseline(self) -> None:
        solver_input = types.SimpleNamespace(
            formula_file=Path("/tmp/formula.smt2"),
            timeout_seconds=10,
            worker_node_ips=[],
            solver_argument_list=[],
        )
        with mock.patch.dict(os.environ, {"SOLVER_NAME": "cvc5-sequential"}):
            command = self.module.get_run_command(solver_input)
        mode_index = command.index("--mode")
        self.assertEqual(command[mode_index + 1], "sequential")

    def test_result_parser_uses_last_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "stdout.txt"
            output.write_text("sat\nunsat\n")
            self.assertEqual(
                self.module.get_solver_result(output),
                FakeResultCode.UNSAT,
            )

    def test_result_parser_rejects_substrings(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "stdout.txt"
            output.write_text("solver says not sat\n")
            self.assertEqual(
                self.module.get_solver_result(output),
                FakeResultCode.INDETERMINATE,
            )


if __name__ == "__main__":
    unittest.main()

