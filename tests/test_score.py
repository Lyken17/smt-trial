from pathlib import Path
import tempfile
import unittest

import polars as pl
from smtcomp import defs

from smtcomp_harness.matrix import combinations
from smtcomp_harness.score import ALLOWED_KINDS, _require_track_validation, validate_score_coordinates


class ScoreValidationTests(unittest.TestCase):
    def _result_dir(self, root: Path, data: dict[str, list[object]]) -> Path:
        directory = root / "result"
        directory.mkdir()
        pl.DataFrame(data).write_ipc(directory / "parsed.feather")
        return directory

    def test_model_validation_rejects_pending_models(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._result_dir(
                Path(tmp), {"answer": [int(defs.Answer.ModelNotValidated)]}
            )
            with self.assertRaisesRegex(ValueError, "not all been validated"):
                _require_track_validation("ModelValidation", [source])

    def test_unsat_core_rejects_missing_validation_evidence(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = self._result_dir(Path(tmp), {"answer": [int(defs.Answer.Unsat)]})
            with self.assertRaisesRegex(ValueError, "validation evidence"):
                _require_track_validation("UnsatCore", [source])

    def test_finalized_organizer_json_is_accepted(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "official.json.gz"
            source.touch()
            _require_track_validation("UnsatCore", [source])

    def test_official_kinds_are_track_specific(self):
        self.assertEqual(ALLOWED_KINDS["Incremental"], {"par"})
        self.assertEqual(ALLOWED_KINDS["Parallel"], {"par"})
        self.assertEqual(ALLOWED_KINDS["UnsatCore"], {"par", "seq"})
        self.assertIn("24", ALLOWED_KINDS["SingleQuery"])
        self.assertNotIn("24", ALLOWED_KINDS["ModelValidation"])

    def test_score_coordinates_are_track_division_performance_triples(self):
        validate_score_coordinates("SingleQuery", "24", "QF_LinearIntArith")
        validate_score_coordinates("UnsatCore", "seq", "QF_LinearIntArith")
        with self.assertRaisesRegex(ValueError, "not an official"):
            validate_score_coordinates("UnsatCore", "24", "QF_LinearIntArith")
        with self.assertRaisesRegex(ValueError, "not part of Track"):
            validate_score_coordinates("ModelValidation", "par", "QF_Strings")
        with self.assertRaisesRegex(ValueError, "Division is required"):
            validate_score_coordinates("SingleQuery", "par", None)

    def test_official_score_matrix_is_complete(self):
        rows = combinations()
        self.assertEqual(len(rows), 195)
        self.assertEqual(len({(r["track"], r["division"], r["performance"]) for r in rows}), 195)


if __name__ == "__main__":
    unittest.main()
