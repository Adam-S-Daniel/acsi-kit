    def test_staging_reset_fact(self):
        args = ("finding-your-unknowns", "staging-reset-fact")
        fact = "- Staging resets every Sunday 2:00-2:30 AM ET; ignore failures then.\n"
        got, _ = self.ws(*args, {"CLAUDE.md": "@AGENTS.md\n\n" + fact})
        self.assertEqual(set(got.values()), {False})
        above = self.seed(*args, "AGENTS.md").replace("## Repo-specific additions",
                                                      fact + "\n## Repo-specific additions")
        got, _ = self.ws(*args, {"AGENTS.md": above})
        self.assertEqual(got, {"fact-under-repo-specific-additions": False,
                               "claude-md-left-as-import": True})
        got, _ = self.ws(*args, {"AGENTS.md": self.seed(*args, "AGENTS.md") + fact})
        self.assertEqual(set(got.values()), {True})
