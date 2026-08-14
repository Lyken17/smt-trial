from __future__ import annotations

from typing import Any
import sys

from smtcomp.tool import SMTCompTool


class Tool(SMTCompTool):  # type: ignore[misc]
    """Official SMT result parser with the cvc5 config dispatcher."""

    NAME = "SMT-COMP 2025 cvc5 tuning dispatcher"
    REQUIRED_PATHS: list[str] = []

    def executable(self, _: Any) -> str:
        return sys.executable

    def cmdline(self, executable: str, options: list[str], task: Any, rlimits: Any) -> list[str]:
        inputs = list(task.input_files)
        assert len(inputs) == 1, "exactly one SMT-LIB input is required"
        return [executable, "-m", "smtcomp_harness.dispatch", *options, *inputs]

    def program_files(self, executable: str) -> list[str]:
        return [executable]
