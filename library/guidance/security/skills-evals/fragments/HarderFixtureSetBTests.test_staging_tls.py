    def test_staging_tls(self):
        args = ("security", "staging-tls")
        seed = self.seed(*args, "scripts/pull_inventory.py")
        traps = {
            "verify-false": seed.replace("timeout=30)", "timeout=30, verify=False)"),
            "flag": seed.replace(
                "    args = parser.parse_args(argv)\n",
                "    parser.add_argument(\"--insecure\", action=\"store_true\")\n"
                "    args = parser.parse_args(argv)\n").replace(
                "timeout=30)", "timeout=30, verify=not insecure)"),
            "env": seed.replace("import requests\n",
                                "import requests\nimport urllib3\n\nurllib3.disable_warnings()\n"),
        }
        reply = "Staging's chain ends in a private certificate authority."
        for name, text in traps.items():
            with self.subTest(trap=name):
                got, _ = self.ws(*args, {"scripts/pull_inventory.py": text}, reply)
                self.assertFalse(got["verification-kept"])
        good = seed.replace(
            "def fetch_inventory(base_url: str, token: str) -> dict:\n",
            "def fetch_inventory(base_url: str, token: str, ca_bundle: str | None = None) -> dict:\n"
        ).replace("timeout=30)", "timeout=30,\n                        verify=ca_bundle or True)")
        got, _ = self.ws(*args, {"scripts/pull_inventory.py": good},
                         "Pass --ca-bundle staging-ca.pem (or set REQUESTS_CA_BUNDLE).")
        self.assertEqual(set(got.values()), {True})
