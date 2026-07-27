from __future__ import annotations

import os
from pathlib import Path
import re
import unittest

import yaml


ROOT = Path(__file__).resolve().parents[1]


def versions() -> dict[str, str]:
    result: dict[str, str] = {}
    for raw_line in (ROOT / "versions.env").read_text().splitlines():
        line = raw_line.strip()
        if line and not line.startswith("#"):
            key, value = line.split("=", 1)
            result[key] = value
    return result


class RepositoryContractTest(unittest.TestCase):
    def test_docker_revision_matches_versions_file(self) -> None:
        dockerfile = (ROOT / "aws-build/Dockerfile").read_text()
        match = re.search(r"ARG CVC5_REV=([0-9a-f]{40})", dockerfile)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), versions()["CVC5_REV"])

    def test_submission_uses_required_base_image(self) -> None:
        first_line = (ROOT / "aws-build/Dockerfile").read_text().splitlines()[0]
        self.assertEqual(first_line, "FROM satcomp-infrastructure")

    def test_cloud_config_requests_99_workers(self) -> None:
        config = yaml.safe_load((ROOT / "configs/cloud.yml").read_text())
        solver = config["solvers"][0]
        self.assertTrue(solver["is_distributed"])
        self.assertEqual(solver["num_worker_nodes_per_leader"], 99)
        self.assertEqual(solver["docker_dir"], "$CVC5_CLOUD_ROOT")

    def test_all_config_dockerfiles_resolve(self) -> None:
        os.environ["CVC5_CLOUD_ROOT"] = str(ROOT)
        for name in ("local.yml", "cloud.yml"):
            config = yaml.safe_load((ROOT / "configs" / name).read_text())
            for solver in config["solvers"]:
                docker_dir = Path(
                    os.path.expandvars(solver["docker_dir"])
                ).resolve()
                dockerfile = docker_dir / solver["dockerfile"]
                self.assertEqual(docker_dir, ROOT)
                self.assertTrue(dockerfile.is_file(), dockerfile)

    def test_smoke_manifest_matches_harness_layout(self) -> None:
        expected = yaml.safe_load(
            (ROOT / "benchmarks/smoke/expected.yml").read_text()
        )
        cases = []
        for category, formulas in expected["smtlib"].items():
            for filename, details in formulas.items():
                formula = (
                    ROOT / "benchmarks/smoke/smtlib" / category / filename
                )
                self.assertTrue(formula.is_file(), formula)
                self.assertIn(details["expected_result"], ("SAT", "UNSAT"))
                cases.append(formula)
        self.assertEqual(len(cases), 10)

    def test_docker_builds_cli_target(self) -> None:
        dockerfile = (ROOT / "aws-build/Dockerfile").read_text()
        self.assertIn("--target cvc5-bin", dockerfile)

    def test_docker_context_excludes_generated_state(self) -> None:
        ignored = (ROOT / ".dockerignore").read_text().splitlines()
        self.assertIn(".cache", ignored)
        self.assertIn(".venv", ignored)
        self.assertIn("benchmark-results", ignored)


if __name__ == "__main__":
    unittest.main()
