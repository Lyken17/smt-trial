#!/usr/bin/env python3
"""Run small real cvc5 protocol/validator checks for every supported Track."""

from __future__ import annotations

import argparse
from pathlib import Path
import subprocess
import tempfile

from smtcomp import defs
from smtcomp.model_validation import check_locally
from smtcomp.unsat_core_validation import create_validation_file, get_unsat_core

from smtcomp_harness.dispatch import solver_args
from smtcomp_harness.uc_validator_pool import create_manifest


def execute(command: list[str], timeout: int = 60) -> str:
    result = subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    if result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n{result.stdout}{result.stderr}"
        )
    return result.stdout


def cvc5_run(root: Path, track: str, performance: str, binary: Path, benchmark: Path) -> str:
    config = root / "configs" / "cvc5" / track / f"{performance}.toml"
    return execute([str(binary), *solver_args(config, track, benchmark), str(benchmark)])


def require_answer(output: str, answer: str, label: str) -> None:
    if not output.lstrip().startswith(answer):
        raise RuntimeError(f"{label}: expected {answer}, got {output!r}")
    print(f"{label}: {answer}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    default_cvc5 = (root / ".cache/solver/default/bin/cvc5").resolve()
    incremental_cvc5 = (root / ".cache/solver/incremental/bin/cvc5").resolve()
    trace_executor = (root / ".cache/execution/smtlib2_trace_executor").resolve()
    scrambler = (root / ".cache/scrambler/scrambler").resolve()
    for executable in (default_cvc5, incremental_cvc5, trace_executor, scrambler):
        if not executable.is_file() or not executable.stat().st_mode & 0o111:
            raise RuntimeError(f"required executable is missing: {executable}")

    with tempfile.TemporaryDirectory(prefix="smtcomp-smoke-") as temporary:
        work = Path(temporary)
        single = work / "single.smt2"
        single.write_text("(set-logic QF_LIA)\n(assert true)\n(check-sat)\n")
        require_answer(cvc5_run(root, "SingleQuery", "24", default_cvc5, single), "sat", "SingleQuery")

        incremental = work / "incremental.smt2"
        incremental.write_text(
            "sat\nsat\n--- BENCHMARK BEGINS HERE ---\n"
            "(set-logic QF_LIA)\n(check-sat)\n(push 1)\n(assert true)\n(check-sat)\n"
        )
        inc_config = root / "configs/cvc5/Incremental/par.toml"
        inc_output = execute(
            [
                str(trace_executor),
                "--continue-after-unknown",
                str(incremental_cvc5),
                *solver_args(inc_config, "Incremental", incremental),
                str(incremental),
            ]
        )
        if [line for line in inc_output.splitlines() if line.strip()] != ["sat", "sat"]:
            raise RuntimeError(f"Incremental: expected two sat answers, got {inc_output!r}")
        print("Incremental: 2/2 trace answers")

        core_benchmark = work / "core.smt2"
        core_benchmark.write_text(
            "(set-option :produce-unsat-cores true)\n(set-logic QF_LIA)\n"
            "(assert (! false :named smtcomp0))\n(check-sat)\n(get-unsat-core)\n"
        )
        core_output = cvc5_run(root, "UnsatCore", "par", default_cvc5, core_benchmark)
        require_answer(core_output, "unsat", "UnsatCore solver")
        core = get_unsat_core(core_output)
        if core != [0]:
            raise RuntimeError(f"UnsatCore: expected [0], got {core}")
        validation = work / "core-validation.smt2"
        create_validation_file(core_benchmark, core, scrambler, validation)
        require_answer(
            cvc5_run(root, "SingleQuery", "par", default_cvc5, validation),
            "unsat",
            "UnsatCore validation",
        )
        pool = create_manifest(
            root / ".cache/official/data",
            root / ".cache/official/submissions",
            "QF_LinearIntArith",
        )
        if int(pool["solver_count"]) < 2:
            raise RuntimeError("UnsatCore validator pool contains fewer than two solvers")
        print(f"UnsatCore public validator pool: {pool['solver_count']} solvers for smoke Division")

        model_benchmark = work / "model.smt2"
        model_benchmark.write_text(
            "(set-option :produce-models true)\n(set-logic QF_BV)\n"
            "(declare-fun x () (_ BitVec 1))\n(assert (= x #b1))\n"
            "(check-sat)\n(get-model)\n"
        )
        model_output = cvc5_run(root, "ModelValidation", "par", default_cvc5, model_benchmark)
        require_answer(model_output, "sat", "ModelValidation solver")
        checked = check_locally(defs.Config(root / ".cache/official/data"), model_benchmark, model_output, False)
        if not isinstance(checked, defs.ValidationOk):
            raise RuntimeError(f"ModelValidation Dolmen rejected smoke model: {checked}")
        print("ModelValidation Dolmen: validated")

        require_answer(cvc5_run(root, "Parallel", "par", default_cvc5, single), "sat", "Parallel functional")
        print("Parallel note: functional smoke only; official comparable execution requires 128 cores/1000 GiB")


if __name__ == "__main__":
    main()
