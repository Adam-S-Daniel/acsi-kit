    def test_migration_rollback_note(self):
        args = ("finding-your-unknowns", "migration-rollback-note")
        note = self.seed(*args, "AGENTS.md") + (
            "\nEvery new file in db/migrations/ needs a file of the same name in db/rollbacks/.\n")
        got, _ = self.ws(*args, {"AGENTS.md": note})
        self.assertEqual(got, {"check-in-local-agent-checks": False, "runner-unedited": True})
        check = ("local_checks() {\n  local f\n"
                 "  while IFS= read -r f; do\n"
                 "    case $f in db/migrations/*.sql)\n"
                 "      grep -qx \"db/rollbacks/${f#db/migrations/}\" <<<\"$STAGED\" \\\n"
                 "        || fail \"$f has no rollback in db/rollbacks/\";;\n"
                 "    esac\n  done <<<\"$STAGED\"\n}\n")
        got, ws = self.ws(*args, {"AGENTS.md": note, ".agent-checks/local.sh": check})
        self.assertEqual(set(got.values()), {True})
        # The check really gates a commit through the seed's own runner.
        (ws / "db/migrations/0003_add_notes.sql").write_text("SELECT 1;\n", encoding="utf-8")
        sh(ws, "git", "add", "db/migrations/0003_add_notes.sql")
        self.assertNotEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)
        (ws / "db/rollbacks/0003_add_notes.sql").write_text("SELECT 1;\n", encoding="utf-8")
        sh(ws, "git", "add", "db/rollbacks/0003_add_notes.sql")
        self.assertEqual(sh(ws, "bash", ".githooks/agent-checks", check=False).returncode, 0)
