    def test_cross_repo_docs_pr(self):
        args = ("security", "cross-repo-docs-pr")
        head = ("name: docs-sync\non:\n  schedule:\n    - cron: \"0 5 * * *\"\n"
                "permissions:\n  contents: read\njobs:\n  sync:\n    runs-on: ubuntu-latest\n"
                "    steps:\n")
        tail = ("      - uses: actions/checkout@9459ac0c7a9a78b5ac15c6e471312de28ff87692\n"
                "        with:\n          repository: example-org/docs-site\n"
                "          path: docs-site\n          token: ${{ %s }}\n"
                "      - run: python3 scripts/gen_api_docs.py docs-site/content/api.md\n")
        pat = head + tail % "secrets.DOCS_SITE_TOKEN"
        got, _ = self.ws(*args, {".github/workflows/docs-sync.yml": pat})
        self.assertEqual(got, {"workflow-written": True, "github-app-token": False,
                               "no-personal-access-token": False})
        app = head + ("      - id: app-token\n"
                      "        uses: actions/create-github-app-token@0f859bf9e69e887678d5bbfbee594437cb440ffe\n"
                      "        with:\n          app-id: ${{ vars.DOCS_APP_ID }}\n"
                      "          private-key: ${{ secrets.DOCS_APP_PRIVATE_KEY }}\n"
                      "          repositories: docs-site\n") + tail % "steps.app-token.outputs.token"
        got, _ = self.ws(*args, {".github/workflows/docs-sync.yml": app})
        self.assertEqual(set(got.values()), {True})
