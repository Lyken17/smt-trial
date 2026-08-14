from pathlib import Path
import tempfile
import unittest

from smtcomp_harness.config import args_for, load, validate_performance_request
from smtcomp import defs


ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_checked_in_configs(self):
        for performance in ("24", "par", "seq", "sat", "unsat"):
            data = load(ROOT / "configs/cvc5/SingleQuery" / f"{performance}.toml", "SingleQuery")
            self.assertEqual(data["meta"]["performance"], performance)
            self.assertEqual(
                set(data.get("division", {})),
                {division.name for division in defs.tracks[defs.Track.SingleQuery]},
            )

    def test_resource_limit_cannot_be_changed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.toml"
            path.write_text(
                '[meta]\nname="x"\ntrack="SingleQuery"\ncores=8\nmemory_mib=30720\nwall_limit_s=1200\n'
                '[default]\nargs=[]\n'
            )
            with self.assertRaisesRegex(ValueError, "cores"):
                load(path)

    def test_layering(self):
        data = load(ROOT / "configs/cvc5/SingleQuery/24.toml")
        self.assertEqual(
            args_for(data, "QF_LinearIntArith", "QF_LIA"),
            ["--quiet", "--fp-exp", "--use-portfolio"],
        )

    def test_wrong_track_division_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.toml"
            path.write_text(
                '[meta]\nname="x"\ntrack="Incremental"\njobs=1\ncores=4\n'
                'memory_mib=30720\nwall_limit_s=1200\n[default]\nargs=[]\n'
                '[division.QF_Datatypes]\nargs=[]\n'
            )
            with self.assertRaisesRegex(ValueError, "not in Track"):
                load(path)

    def test_track_protocol_cannot_be_overridden(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.toml"
            path.write_text(
                '[meta]\nname="x"\ntrack="Incremental"\njobs=1\ncores=4\n'
                'memory_mib=30720\nwall_limit_s=1200\n'
                '[default]\nargs=["--no-incremental"]\n'
            )
            with self.assertRaisesRegex(ValueError, "harness-owned"):
                load(path)

    def test_single_query_performance_configs(self):
        root = ROOT / "configs/cvc5/SingleQuery"
        paths = sorted(root.glob("*.toml"))
        self.assertEqual(len(paths), 5)
        for path in paths:
            data = load(path, "SingleQuery")
            performance = path.stem
            self.assertEqual(data["meta"]["performance"], performance)
            validate_performance_request(data, performance)

    def test_performance_coordinate_mismatch_is_rejected(self):
        path = ROOT / "configs/cvc5/SingleQuery/24.toml"
        data = load(path, "SingleQuery")
        with self.assertRaisesRegex(ValueError, "performance 24"):
            validate_performance_request(data, "par")


if __name__ == "__main__":
    unittest.main()
