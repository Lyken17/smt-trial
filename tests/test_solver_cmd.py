from __future__ import annotations

import enum
import importlib.util
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
        config = {
            "mode": "distributed",
            "jobs_per_node": 4,
            "local_replicas": 2,
            "cvc5_args": ("--decision=internal",),
        }
        with (
            mock.patch(
                "cvc5_cloud.configuration.read_logic",
                return_value="QF_UF",
            ),
            mock.patch("submission.get_config", return_value=config),
        ):
            command = self.module.get_run_command(solver_input)
        self.assertIn("distributed", command)
        self.assertEqual(command.count("--host"), 2)
        self.assertIn("10.0.0.2", command)
        self.assertIn("--jobs-per-node", command)
        self.assertEqual(command[command.index("--jobs-per-node") + 1], "4")
        self.assertIn("--local-replicas", command)
        self.assertEqual(command[command.index("--local-replicas") + 1], "2")
        self.assertIn("--cvc5-arg=--decision=internal", command)
        self.assertEqual(command[-1], "/tmp/formula.smt2")

    def test_starter_submission_selects_sequential_mode(self) -> None:
        solver_input = types.SimpleNamespace(
            formula_file=Path("/tmp/formula.smt2"),
            timeout_seconds=10,
            worker_node_ips=[],
            solver_argument_list=[],
        )
        with mock.patch(
            "cvc5_cloud.configuration.read_logic",
            return_value="QF_UF",
        ):
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
