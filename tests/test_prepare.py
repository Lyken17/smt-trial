from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET

from smtcomp_harness.prepare import prepare


ROOT = Path(__file__).resolve().parents[1]


class PrepareTests(unittest.TestCase):
    def test_every_supported_track_uses_official_resources(self):
        cases = {
            "SingleQuery": ("24", "QF_LIA", 4, 30720),
            "UnsatCore": ("par", "QF_LIA", 4, 30720),
            "ModelValidation": ("par", "QF_LIA", 4, 30720),
            "Parallel": ("par", "QF_LIA", 128, 1024000),
        }
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cvc5 = root / "cvc5"
            cvc5.write_text("#!/bin/sh\n")
            cvc5.chmod(0o755)
            for track, (performance, logic, cores, memory) in cases.items():
                selection = root / track / logic
                selection.mkdir(parents=True)
                (selection / f"0_{logic}_x.yml").write_text("format_version: '2.0'\n")
                output = root / f"{track}.xml"
                prepare(
                    track,
                    ROOT / "configs/cvc5" / track / f"{performance}.toml",
                    cvc5,
                    selection.parent,
                    output,
                    performance=performance,
                )
                xml = ET.parse(output).getroot()
                self.assertEqual(xml.attrib["walltimelimit"], "1200s")
                self.assertEqual(xml.attrib["cpuCores"], str(cores))
                self.assertEqual(xml.attrib["timelimit"], f"{1200 * cores}s")
                self.assertEqual(xml.attrib["memlimit"], f"{memory} MB")

    def test_official_single_query_limits_in_xml(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cvc5 = root / "cvc5"
            cvc5.write_text("#!/bin/sh\n")
            cvc5.chmod(0o755)
            selection = root / "selection" / "QF_LIA"
            selection.mkdir(parents=True)
            (selection / "0_QF_LIA_x.yml").write_text("format_version: '2.0'\n")
            output = root / "run.xml"
            prepare(
                "SingleQuery",
                ROOT / "configs/cvc5/SingleQuery/24.toml",
                cvc5,
                selection.parent,
                output,
                performance="24",
            )
            xml = ET.parse(output).getroot()
            self.assertEqual(xml.attrib["walltimelimit"], "1200s")
            self.assertEqual(xml.attrib["timelimit"], "4800s")
            self.assertEqual(xml.attrib["memlimit"], "30720 MB")
            self.assertEqual(xml.attrib["cpuCores"], "4")
            includes = [node.text for node in xml.findall(".//include")]
            self.assertEqual(len(includes), 1)
            self.assertTrue(includes[0].endswith("*/*.yml"))

    def test_division_filters_task_logics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cvc5 = root / "cvc5"
            cvc5.write_text("#!/bin/sh\n")
            cvc5.chmod(0o755)
            for logic in ("QF_LIA", "QF_BV"):
                directory = root / "selection" / logic
                directory.mkdir(parents=True)
                (directory / f"0_{logic}_x.yml").write_text("format_version: '2.0'\n")
            output = root / "run.xml"
            prepare(
                "SingleQuery",
                ROOT / "configs/cvc5/SingleQuery/24.toml",
                cvc5,
                root / "selection",
                output,
                division="QF_LinearIntArith",
                performance="24",
            )
            includes = [node.text for node in ET.parse(output).findall(".//include")]
            self.assertTrue(any("QF_LIA" in value for value in includes))
            self.assertFalse(any("QF_BV" in value for value in includes))

    def test_performance_config_supports_division_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cvc5 = root / "cvc5"
            cvc5.write_text("#!/bin/sh\n")
            cvc5.chmod(0o755)
            selection = root / "selection" / "QF_LIA"
            selection.mkdir(parents=True)
            (selection / "0_QF_LIA_x.yml").write_text("format_version: '2.0'\n")
            output = root / "run.xml"
            prepare(
                "SingleQuery",
                ROOT / "configs/cvc5/SingleQuery/24.toml",
                cvc5,
                selection.parent,
                output,
                division="QF_LinearIntArith",
                performance="24",
            )
            self.assertTrue(output.is_file())

    def test_incremental_uses_official_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cvc5 = root / "cvc5"
            trace = root / "smtlib2_trace_executor"
            for executable in (cvc5, trace):
                executable.write_text("#!/bin/sh\n")
                executable.chmod(0o755)
            selection = root / "selection" / "QF_LIA"
            selection.mkdir(parents=True)
            (selection / "0_QF_LIA_x.yml").write_text("format_version: '2.0'\n")
            output = root / "run.xml"
            prepare(
                "Incremental",
                ROOT / "configs/cvc5/Incremental/par.toml",
                cvc5,
                selection.parent,
                output,
                trace_executor=trace,
                performance="par",
            )
            xml = ET.parse(output).getroot()
            self.assertEqual(xml.attrib["tool"], "smtcomp_harness.benchexec_tool_incremental")
            self.assertEqual(xml.attrib["cpuCores"], "4")
            self.assertEqual(xml.attrib["memlimit"], "30720 MB")
            self.assertIn(str(trace.resolve()), [node.text for node in xml.findall(".//option")])

    def test_unsat_core_validation_uses_official_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            cvc5 = root / "cvc5"
            cvc5.write_text("#!/bin/sh\n")
            cvc5.chmod(0o755)
            selection = root / "selection" / "QF_LIA"
            selection.mkdir(parents=True)
            (selection / "scrambled1_0.smt2").write_text("(set-logic QF_LIA)\n")
            output = root / "run.xml"
            prepare(
                "UnsatCoreValidation",
                ROOT / "configs/cvc5/SingleQuery/par.toml",
                cvc5,
                selection.parent,
                output,
                division="QF_LinearIntArith",
                performance="par",
            )
            xml = ET.parse(output).getroot()
            self.assertEqual(xml.attrib["walltimelimit"], "1200s")
            self.assertEqual(xml.attrib["timelimit"], "4800s")
            self.assertEqual(xml.attrib["memlimit"], "15360 MB")
            self.assertEqual(xml.attrib["cpuCores"], "4")
            self.assertIn(
                "UnsatCoreValidation",
                xml.find("rundefinition").attrib["name"],
            )


if __name__ == "__main__":
    unittest.main()
