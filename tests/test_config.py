from pathlib import Path
import tempfile
import unittest

from smtcomp_harness.config import args_for, load
from smtcomp import defs


ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_checked_in_configs(self):
        files = {
            "SingleQuery": "single-query.toml",
            "Incremental": "incremental.toml",
            "UnsatCore": "unsat-core.toml",
            "ModelValidation": "model-validation.toml",
            "Parallel": "parallel.toml",
        }
        for track_name, filename in files.items():
            data = load(ROOT / "configs/cvc5" / filename, track_name)
            self.assertEqual(
                set(data.get("division", {})),
                {division.name for division in defs.tracks[defs.Track(track_name)]},
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
        data = load(ROOT / "configs/cvc5/single-query.toml")
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


if __name__ == "__main__":
    unittest.main()
