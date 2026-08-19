from __future__ import annotations

from pathlib import Path
from typing import Any
import sys

from smtcomp.incremental_tool import IncrementalSMTCompTool

from .dispatch import solver_args


def _value(options: list[str], name: str) -> str:
    try:
        return options[options.index(name) + 1]
    except (ValueError, IndexError) as error:
        raise ValueError(f"missing BenchExec option {name}") from error


class Tool(IncrementalSMTCompTool):  # type: ignore[misc]
    """Official incremental result parser and trace executor with tuned cvc5 args."""

    NAME = "SMT-COMP 2025 incremental cvc5 tuning dispatcher"
    REQUIRED_PATHS: list[str] = []

    def executable(self, _: Any) -> str:
        return sys.executable

    def cmdline(self, executable: str, options: list[str], task: Any, rlimits: Any) -> list[str]:
        inputs = list(task.input_files)
        assert len(inputs) == 1, "exactly one SMT-LIB input is required"
        benchmark = Path(inputs[0])
        config = Path(_value(options, "--config"))
        cvc5 = str(Path(_value(options, "--cvc5")).resolve())
        trace_executor = str(Path(_value(options, "--trace-executor")).resolve())
        return [
            trace_executor,
            "--continue-after-unknown",
            cvc5,
            *solver_args(config, "Incremental", benchmark),
            str(benchmark),
        ]

    def program_files(self, executable: str) -> list[str]:
        return [executable]
