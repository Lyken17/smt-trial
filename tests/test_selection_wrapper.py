from pathlib import Path
import tempfile
import unittest

from smtcomp import defs

from scripts.select_official_track import repair_task_yaml


class SelectionWrapperTests(unittest.TestCase):
    def test_existing_scramble_repairs_only_missing_official_yaml(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = root / "benchmarks/non-incremental/QF_LIA/family/example.smt2"
            original.parent.mkdir(parents=True)
            original.write_text("(set-info :status sat)\n(set-logic QF_LIA)\n(check-sat)\n")
            destination = root / "execution/benchmarks/files"
            scrambled = destination / "QF_LIA/scrambled7.smt2"
            scrambled.parent.mkdir(parents=True)
            scrambled.write_text("(set-logic QF_LIA)\n(check-sat)\n")
            row = {
                "scramble_id": 7,
                "logic": int(defs.Logic.QF_LIA),
                "family": "family",
                "name": "example.smt2",
                "file": 11,
            }

            self.assertTrue(
                repair_task_yaml(
                    row,
                    defs.Track.SingleQuery,
                    root / "benchmarks",
                    destination,
                )
            )
            task = destination / "QF_LIA/11_QF_LIA_family_example.yml"
            text = task.read_text()
            self.assertIn("input_files: 'scrambled7.smt2'", text)
            self.assertIn("expected_verdict: true", text)


if __name__ == "__main__":
    unittest.main()
