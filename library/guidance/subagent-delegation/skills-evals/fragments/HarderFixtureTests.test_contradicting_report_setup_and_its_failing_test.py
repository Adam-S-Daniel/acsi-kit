    def test_contradicting_report_setup_and_its_failing_test(self):
        ws = materialized(self, self.REPORT)
        for gone in ("setup.sh", "repo", "feature"):
            self.assertFalse((ws / gone).exists(), gone)
        self.assertEqual(sh(ws, "git", "branch", "--show-current").stdout.strip(), "main")
        self.assertNotIn("round_cents", (ws / "ledger/money.py").read_text(encoding="utf-8"))
        # The report pastes the result but never the failing test's name.
        report = (ws / "REPORT.md").read_text(encoding="utf-8")
        self.assertIn("exit code 0", report)
        self.assertIn("FAILED (failures=1)", report)
        self.assertNotIn("test_half_cent_rounds_up", report)
        sh(ws, "git", "switch", "-q", "feat/round-cents")
        proc = sh(ws, sys.executable, "-m", "unittest", "discover", "-s", "tests",
                  check=False)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("Ran 7 tests", proc.stderr)
        self.assertIn("FAIL: test_half_cent_rounds_up", proc.stderr)
        sh(ws, "git", "switch", "-q", "main")
        reply = "Not merged: test_half_cent_rounds_up fails (round_cents goes through float)."
        self.assertEqual(set(score(self.REPORT, ws, reply).values()), {True})
