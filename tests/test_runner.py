from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest import mock

from cvc5_cloud.runner import (
    Mode,
    RaceConfig,
    Result,
    build_cvc5_command,
    parse_solver_result,
    run_race,
)


class RunnerUnitTest(unittest.TestCase):
    def test_parse_last_exact_result(self) -> None:
        self.assertEqual(parse_solver_result("noise\nsat\n"), Result.SAT)
        self.assertEqual(parse_solver_result("sat\nunsat\n"), Result.UNSAT)
        self.assertEqual(parse_solver_result("not sat\n"), Result.UNKNOWN)

    def test_build_portfolio_command(self) -> None:
        command = build_cvc5_command(
            Path("/solver/cvc5"),
            Path("/tmp/input.smt2"),
            2.5,
            portfolio=True,
            jobs=8,
            seed=17,
            extra_args=("--safe-mode=stable",),
        )
        self.assertIn("--use-portfolio", command)
        self.assertIn("--portfolio-jobs=8", command)
        self.assertIn("--tlimit=2500", command)
        self.assertIn("--seed=17", command)
        self.assertEqual(command[-1], "/tmp/input.smt2")

    def test_local_race_accepts_competition_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            solver = root / "fake-cvc5"
            solver.write_text("#!/bin/sh\necho sat\nexit 10\n")
            solver.chmod(solver.stat().st_mode | stat.S_IXUSR)
            formula = root / "input.smt2"
            formula.write_text("(set-logic QF_UF)\n(check-sat)\n")

            result = run_race(
                RaceConfig(
                    cvc5=solver,
                    formula=formula,
                    timeout_seconds=2,
                    mode=Mode.SEQUENTIAL,
                    shutdown_grace_seconds=0.1,
                )
            )
            self.assertEqual(result, Result.SAT)

    def test_distributed_mode_can_emulate_seeded_local_replicas(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            solver = root / "fake-cvc5"
            solver.write_text(
                "#!/bin/sh\n"
                "case \" $* \" in\n"
                "  *' --seed=2 '*) echo unsat; exit 20 ;;\n"
                "  *) sleep 0.2; echo unknown; exit 0 ;;\n"
                "esac\n"
            )
            solver.chmod(solver.stat().st_mode | stat.S_IXUSR)
            formula = root / "input.smt2"
            formula.write_text("(set-logic QF_UF)\n(check-sat)\n")

            result = run_race(
                RaceConfig(
                    cvc5=solver,
                    formula=formula,
                    timeout_seconds=2,
                    mode=Mode.DISTRIBUTED,
                    jobs_per_node=1,
                    local_replicas=2,
                    shutdown_grace_seconds=0.1,
                )
            )
            self.assertEqual(result, Result.UNSAT)

    def test_distributed_mode_stages_and_runs_remote_worker(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tools = root / "bin"
            tools.mkdir()
            solver = root / "fake-cvc5"
            solver.write_text(
                "#!/bin/sh\n"
                "case \" $* \" in\n"
                "  *' --seed=2 '*) echo unsat; exit 20 ;;\n"
                "  *) sleep 0.2; echo unknown; exit 0 ;;\n"
                "esac\n"
            )
            solver.chmod(solver.stat().st_mode | stat.S_IXUSR)
            scp = tools / "scp"
            scp.write_text(
                "#!/usr/bin/env python3\n"
                "import pathlib, shutil, sys\n"
                "source = pathlib.Path(sys.argv[-2])\n"
                "destination = pathlib.Path(sys.argv[-1].split(':', 1)[1])\n"
                "shutil.copyfile(source, destination)\n"
            )
            scp.chmod(scp.stat().st_mode | stat.S_IXUSR)
            ssh = tools / "ssh"
            ssh.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "os.execl('/bin/sh', 'sh', '-c', sys.argv[-1])\n"
            )
            ssh.chmod(ssh.stat().st_mode | stat.S_IXUSR)
            formula = root / "input.smt2"
            formula.write_text("(set-logic QF_UF)\n(check-sat)\n")
            remote_formula = root / "remote input.smt2"

            with (
                mock.patch.dict(
                    os.environ,
                    {"PATH": f"{tools}:{os.environ['PATH']}"},
                ),
                mock.patch(
                    "cvc5_cloud.runner._remote_formula_path",
                    return_value=str(remote_formula),
                ),
            ):
                result = run_race(
                    RaceConfig(
                        cvc5=solver,
                        formula=formula,
                        timeout_seconds=2,
                        mode=Mode.DISTRIBUTED,
                        jobs_per_node=1,
                        local_replicas=1,
                        hosts=("worker-a",),
                        shutdown_grace_seconds=0.1,
                    )
                )
            self.assertEqual(result, Result.UNSAT)
            self.assertEqual(remote_formula.read_text(), formula.read_text())

    def test_result_does_not_wait_for_descendant_inheriting_output(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            solver = root / "fake-cvc5"
            solver.write_text("#!/bin/sh\nsleep 5 &\necho sat\nexit 10\n")
            solver.chmod(solver.stat().st_mode | stat.S_IXUSR)
            formula = root / "input.smt2"
            formula.write_text("(set-logic QF_UF)\n(check-sat)\n")

            started = time.monotonic()
            result = run_race(
                RaceConfig(
                    cvc5=solver,
                    formula=formula,
                    timeout_seconds=1,
                    mode=Mode.SEQUENTIAL,
                    shutdown_grace_seconds=0.1,
                )
            )
            self.assertEqual(result, Result.SAT)
            self.assertLess(time.monotonic() - started, 0.5)

    def test_rejects_missing_formula(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            solver = root / "fake-cvc5"
            solver.write_text("#!/bin/sh\necho unknown\n")
            solver.chmod(solver.stat().st_mode | stat.S_IXUSR)
            with self.assertRaises(FileNotFoundError):
                run_race(
                    RaceConfig(
                        cvc5=solver,
                        formula=root / "missing.smt2",
                        timeout_seconds=1,
                    )
                )

    def test_rejects_negative_shutdown_grace(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            solver = root / "fake-cvc5"
            solver.write_text("#!/bin/sh\necho unknown\n")
            solver.chmod(solver.stat().st_mode | stat.S_IXUSR)
            formula = root / "input.smt2"
            formula.write_text("(set-logic QF_UF)\n(check-sat)\n")
            with self.assertRaises(ValueError):
                run_race(
                    RaceConfig(
                        cvc5=solver,
                        formula=formula,
                        timeout_seconds=1,
                        shutdown_grace_seconds=-0.1,
                    )
                )


if __name__ == "__main__":
    unittest.main()
