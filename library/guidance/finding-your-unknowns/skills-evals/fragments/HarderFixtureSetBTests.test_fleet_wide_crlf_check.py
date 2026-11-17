    def test_fleet_wide_crlf_check(self):
        args = ("finding-your-unknowns", "fleet-wide-crlf-check")
        check = ("local_checks() {\n  local f\n  while IFS= read -r f; do\n"
                 "    case $f in *.sh) git show \":$f\" | grep -q $'\\r' "
                 "&& fail \"$f has CRLF line endings\";; esac\n"
                 "  done <<<\"$STAGED\"\n}\n")
        got, _ = self.ws(*args, {".agent-checks/local.sh": check,
                                 ".gitattributes": "*.sh text eol=lf\n"})
        self.assertEqual(set(got.values()), {False})
        runner = self.seed(*args, "templates/agent-checks/agent-checks").replace(
            "\nif [ -f .agent-checks/local.sh ]",
            "\n# Fleet check: shell scripts use LF line endings.\n"
            "while IFS= read -r f; do\n  case $f in *.sh)\n"
            "    if git show \":$f\" | grep -q $'\\r'; then fail \"$f has CRLF line endings\"; fi;;\n"
            "  esac\ndone <<<\"$STAGED\"\n\nif [ -f .agent-checks/local.sh ]")
        got, ws = self.ws(*args, {"templates/agent-checks/agent-checks": runner})
        self.assertEqual(set(got.values()), {True})
        (ws / "run.sh").write_bytes(b"#!/bin/sh\r\necho hi\r\n")
        sh(ws, "git", "add", "run.sh")
        self.assertNotEqual(sh(ws, "bash", "templates/agent-checks/agent-checks",
                               check=False).returncode, 0)
