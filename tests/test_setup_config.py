import subprocess
import unittest
from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]


class SetupConfigTests(unittest.TestCase):
    def test_bootstrap_does_not_force_removed_host_tool_cache(self) -> None:
        for relative in ("Makefile", "scripts/bootstrap.sh"):
            text = (ROOT / relative).read_text()
            self.assertNotIn(".cache/system-deps", text, relative)
            self.assertNotIn("BISON_PKGDATADIR", text, relative)

    def test_dependency_check_enforces_supported_python(self) -> None:
        text = (ROOT / "scripts/install_system_deps.sh").read_text()
        self.assertIn("sys.version_info < (3, 11)", text)

    def test_make_does_not_depend_on_checkout_executable_bits(self) -> None:
        text = (ROOT / "Makefile").read_text()
        self.assertNotIn("\t./scripts/", text)

    def test_single_query_setup_config_is_valid_bash(self) -> None:
        subprocess.run(
            ["bash", "-n", "configs/setup-single-query.env"],
            cwd=ROOT,
            check=True,
        )

    def test_single_query_setup_config_defines_portable_controls(self) -> None:
        command = (
            "source configs/setup-single-query.env; "
            "test \"$CACHE_PLACEMENT\" = auto; "
            "test -z \"$EXTERNAL_CACHE_ROOT\"; "
            "test \"$BENCHMARK_COMPONENT\" = non-incremental-benchmarks; "
            "test \"$SOLVER_COMPONENT\" = default-solver"
        )
        subprocess.run(["bash", "-c", command], cwd=ROOT, check=True)

    def test_environment_overrides_are_preserved(self) -> None:
        command = (
            "source configs/setup-single-query.env; "
            "test \"$CACHE_PLACEMENT\" = external; "
            "test \"$EXTERNAL_CACHE_ROOT\" = /srv/smt-cache; "
            "test \"$SELECTION_JOBS\" = 3"
        )
        subprocess.run(
            ["bash", "-c", command],
            cwd=ROOT,
            env={
                "PATH": "/usr/bin:/bin",
                "CACHE_PLACEMENT": "external",
                "EXTERNAL_CACHE_ROOT": "/srv/smt-cache",
                "SELECTION_JOBS": "3",
            },
            check=True,
        )

    def test_checked_in_setup_has_no_host_specific_path(self) -> None:
        text = (ROOT / "configs/setup-single-query.env").read_text()
        forbidden = (
            r"[A-Za-z]:\\",
            r"/mnt/[A-Za-z]/",
            r"/home/[^ $/{]+",
            r"/var/tmp/",
            r"LOCAL_DEB_(CODENAME|ARCH)",
        )
        for pattern in forbidden:
            self.assertIsNone(re.search(pattern, text), pattern)


if __name__ == "__main__":
    unittest.main()
