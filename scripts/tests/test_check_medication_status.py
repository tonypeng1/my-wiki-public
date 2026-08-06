from __future__ import annotations

import contextlib
import importlib.util
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "check-medication-status.py"
SPEC = importlib.util.spec_from_file_location("check_medication_status", SCRIPT)
assert SPEC and SPEC.loader
checker = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = checker
SPEC.loader.exec_module(checker)


class MedicationStatusCheckerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.occasional_med = checker.Med(
            "alprazolam",
            "occasional",
            (("alprazolam", checker.term_pattern("alprazolam", False)),),
            (),
        )

    def test_body_claim_status_accepts_common_occasional_wording(self) -> None:
        for phrase in (
            "used occasionally",
            "taken intermittently",
            "taken as needed",
            "used PRN",
            "taken some nights",
            "not taken daily",
        ):
            with self.subTest(phrase=phrase):
                self.assertEqual(checker.body_claim_status(phrase), "occasional")

        self.assertEqual(checker.body_claim_status("taken every night"), "active")
        self.assertEqual(
            checker.body_claim_status("active but occasionally misses a dose"),
            "active",
        )
        self.assertEqual(checker.body_claim_status("no longer taken"), "stopped")

    def test_regular_use_excerpt_ignores_neutral_occasional_and_past_text(self) -> None:
        self.assertIsNone(checker.regular_use_excerpt("May cause drowsiness."))
        self.assertIsNone(checker.regular_use_excerpt("Taken as needed for sleep."))
        self.assertIsNone(checker.regular_use_excerpt("Previously taken nightly."))
        self.assertIsNone(checker.regular_use_excerpt("Not taken daily."))
        self.assertEqual(
            checker.regular_use_excerpt(
                "Taken nightly before bed as of 2026-08-05."
            ),
            "Taken nightly before bed as of 2026-08-05.",
        )
        self.assertEqual(
            checker.regular_use_excerpt("Taken every night for sleep."),
            "Taken every night for sleep.",
        )
        self.assertEqual(
            checker.regular_use_excerpt("Taken nightly; occasionally causes nausea."),
            "Taken nightly; occasionally causes nausea.",
        )

    def test_occasional_frequency_hit_uses_mirror_subject_or_direct_name(self) -> None:
        subject_hit = checker.occasional_frequency_hit(
            "- [[alprazolam]] — Taken nightly for sleep.", self.occasional_med
        )
        self.assertEqual(subject_hit, ("alprazolam", "- — Taken nightly for sleep."))

        direct_hit = checker.occasional_frequency_hit(
            "- [[sleep-aid]] — Alprazolam is taken every night.", self.occasional_med
        )
        self.assertEqual(
            direct_hit, ("alprazolam", "- — Alprazolam is taken every night.")
        )

        self.assertIsNone(
            checker.occasional_frequency_hit(
                "- [[alprazolam]] — Used as needed for sleep.", self.occasional_med
            )
        )
        self.assertIsNone(
            checker.occasional_frequency_hit(
                "- [[alprazolam]] — Previously taken nightly.", self.occasional_med
            )
        )
        self.assertIsNone(
            checker.occasional_frequency_hit(
                "- [[sleep-aid]] — Taken nightly.", self.occasional_med
            )
        )
        self.assertIsNone(
            checker.occasional_frequency_hit(
                "- [[sleep-aid]] — Alprazolam may cause drowsiness. "
                "Another medicine is taken nightly.",
                self.occasional_med,
            )
        )

    def test_occasional_frontmatter_requires_matching_explicit_status_line(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root).resolve()
            concepts = root / "wiki" / "concepts"
            concepts.mkdir(parents=True)
            article = concepts / "alprazolam.md"

            def write(body: str) -> None:
                article.write_text(
                    "---\n"
                    "title: Alprazolam\n"
                    "tags: [medication]\n"
                    "status: occasional\n"
                    "---\n\n"
                    "# Alprazolam\n\n"
                    f"{body}\n",
                    encoding="utf-8",
                )

            with mock.patch.multiple(checker, ROOT=root, CONCEPTS=concepts):
                write("- **Current status:** **Active, taken as needed**")
                _, findings = checker.load_medications()
                self.assertEqual(findings, [])

                write("- **Current status:** **Active, taken nightly**")
                _, findings = checker.load_medications()
                self.assertEqual([finding.kind for finding in findings], ["STATUS MISMATCH"])

                write("No explicit current-status statement.")
                _, findings = checker.load_medications()
                self.assertEqual([finding.kind for finding in findings], ["STATUS MISMATCH"])

    def test_main_reports_regular_use_only_in_mirrors(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root).resolve()
            wiki = root / "wiki"
            concepts = wiki / "concepts"
            mocs = wiki / "mocs"
            concepts.mkdir(parents=True)
            mocs.mkdir()
            index = wiki / "index.md"

            (concepts / "alprazolam.md").write_text(
                "---\n"
                "title: Alprazolam\n"
                "tags: [medication]\n"
                "status: occasional\n"
                "---\n\n"
                "# Alprazolam\n\n"
                "- **Current status:** **Active, taken as needed**\n",
                encoding="utf-8",
            )
            index.write_text(
                "# Index\n\n"
                "## alprazolam.md\n"
                "- **Type:** concept\n"
                "- **Summary:** Alprazolam is taken every night.\n",
                encoding="utf-8",
            )
            (mocs / "moc-medication.md").write_text(
                "# Medication\n\n"
                "## Concepts\n"
                "- [[alprazolam]] — Used as needed.\n",
                encoding="utf-8",
            )

            output = io.StringIO()
            with mock.patch.multiple(
                checker,
                ROOT=root,
                WIKI=wiki,
                CONCEPTS=concepts,
                MOCS=mocs,
                INDEX=index,
            ):
                with mock.patch.object(sys, "argv", [str(SCRIPT)]):
                    with contextlib.redirect_stdout(output):
                        checker.main()

            report = output.getvalue()
            self.assertIn("FREQUENCY MISMATCH", report)
            self.assertIn("wiki/index.md:3  alprazolam", report)
            self.assertIn("TOTAL: 1 finding(s)", report)


if __name__ == "__main__":
    unittest.main()
