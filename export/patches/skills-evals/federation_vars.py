"""C12: eval.yml's Anthropic federation ids come from repository variables.

The source's two "Mint OIDC token and exchange for Anthropic access token"
steps wrote its own workload identity federation set-up into the exchange
body: one federation rule, organization, service account and workspace id,
all four specific to the source's Anthropic account (the header comment
named them too). An adopter's exchange must name its own, so each step now
reads them from four repository variables, which bootstrap's
create-environments.sh sets from fleet.env (REPO_VARIABLES, the
`federation` group) and docs/evals-and-loop.md's "Workload identity
federation" section explains how to create. Each value is checked by shape
before use and passed to jq with --arg, never spliced into the program.

A failed exchange printed the whole response body (`cat "$xresp"`); on a
public repo that log is public. It now prints the HTTP status and the
error type only, the type limited to a short token, else `unknown`.

Federation is optional (docs/evals-and-loop.md), but the `roster` job mints
on every dispatch, `roster_only` included, and roster-refresh.yml
dispatches that weekly. So the roster job's mint (the first of the two, id
`federation`) exits 0 with a ::notice:: and `federation=off` when all four
variables are empty, and "Refresh the model roster" then publishes no roster
and says so; one set without the others, or a malformed value, still fails.
The eval job's mint keeps failing on an unset variable: an eval leg cannot
run without the token.

skill-coverage.yml's "Mint the Anthropic bearer for the adversarial review"
step (skills-evals#917) named the same four ids. It reads the same four
variables and checks them by shape the same way; the step is under
continue-on-error, so an unset or malformed variable only means the review
has no bearer and auto removal is not allowed that run.

The ids are matched here by their lexical shape (a prefix and an id
token), so this file spells none of them. Runs on the substituted tree.
"""

from __future__ import annotations

import re
from pathlib import Path

REL = ".github/workflows/eval.yml"

ENV = (
    "        env:\n"
    "          # The workload identity federation set-up (docs/evals-and-loop.md,\n"
    "          # \"Workload identity federation\"); set by bootstrap from fleet.env.\n"
    "          FEDERATION_RULE_ID: ${{ vars.ANTHROPIC_FEDERATION_RULE_ID }}\n"
    "          ORGANIZATION_ID: ${{ vars.ANTHROPIC_ORGANIZATION_ID }}\n"
    "          SERVICE_ACCOUNT_ID: ${{ vars.ANTHROPIC_SERVICE_ACCOUNT_ID }}\n"
    "          WORKSPACE_ID: ${{ vars.ANTHROPIC_WORKSPACE_ID }}\n"
)

CHECKS = (
    "          [[ \"$FEDERATION_RULE_ID\" =~ ^fdrl_[A-Za-z0-9]{8,64}$ ]] || { echo \"::error::repository variable ANTHROPIC_FEDERATION_RULE_ID is unset or not an fdrl_ id\"; exit 1; }\n"
    "          [[ \"$ORGANIZATION_ID\" =~ ^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$ ]] || { echo \"::error::repository variable ANTHROPIC_ORGANIZATION_ID is unset or not an organization uuid\"; exit 1; }\n"
    "          [[ \"$SERVICE_ACCOUNT_ID\" =~ ^svac_[A-Za-z0-9]{8,64}$ ]] || { echo \"::error::repository variable ANTHROPIC_SERVICE_ACCOUNT_ID is unset or not an svac_ id\"; exit 1; }\n"
    "          [[ \"$WORKSPACE_ID\" =~ ^wrkspc_[A-Za-z0-9]{8,64}$ ]] || { echo \"::error::repository variable ANTHROPIC_WORKSPACE_ID is unset or not a wrkspc_ id\"; exit 1; }\n"
)

STEP_HEAD = ("      - name: Mint OIDC token and exchange for Anthropic access token\n"
             "        run: |\n")

BODY_OLD = re.compile(
    r'          body=\$\(jq -n --rawfile jwt "\$RUNNER_TEMP/anthropic-oidc\.jwt" \'\{\n'
    r'            grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",\n'
    r'            assertion: \(\$jwt \| rtrimstr\("\\n"\)\),\n'
    r'            federation_rule_id: "fdrl_[A-Za-z0-9]+",\n'
    r'            organization_id: "[0-9a-f-]{36}",\n'
    r'            service_account_id: "svac_[A-Za-z0-9]+",\n'
    r'            workspace_id: "wrkspc_[A-Za-z0-9]+"\n'
    r"          \}'\)\n")

BODY_NEW = (
    '          body=$(jq -n --rawfile jwt "$RUNNER_TEMP/anthropic-oidc.jwt" \\\n'
    '            --arg rule "$FEDERATION_RULE_ID" --arg org "$ORGANIZATION_ID" \\\n'
    '            --arg svac "$SERVICE_ACCOUNT_ID" --arg wrkspc "$WORKSPACE_ID" \'{\n'
    '            grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",\n'
    '            assertion: ($jwt | rtrimstr("\\n")),\n'
    '            federation_rule_id: $rule,\n'
    '            organization_id: $org,\n'
    '            service_account_id: $svac,\n'
    '            workspace_id: $wrkspc\n'
    "          }')\n")

FAIL_OLD = ('            echo "token exchange failed: HTTP $code"\n'
            '            cat "$xresp"\n'
            '            exit 1\n')
FAIL_NEW = (
    '            # The status and the error type only: the body is not logged.\n'
    '            etype=$(jq -r \'(.error.type? // .error? // empty) | strings\' < "$xresp" 2>/dev/null) || etype=""\n'
    '            [[ "$etype" =~ ^[A-Za-z0-9_.-]{1,64}$ ]] || etype=unknown\n'
    '            rm -f "$xresp"\n'
    '            echo "token exchange failed: HTTP $code, error type $etype"\n'
    '            exit 1\n')

HEADER_OLD = re.compile(
    r"#   to https://api\.anthropic\.com/v1/oauth/token against federation rule\n"
    r"#   fdrl_[A-Za-z0-9]+ / org [0-9a-f-]{36}\n"
    r"#   / service account svac_[A-Za-z0-9]+, with the exchange body\n"
    r"#   pinned to workspace_id wrkspc_[A-Za-z0-9]+ \(the spend-capped\n"
    r"#   skills-evals-ci workspace\) explicitly,")
HEADER_NEW = (
    "#   to https://api.anthropic.com/v1/oauth/token against the federation\n"
    "#   rule, organization and service account in the repository variables\n"
    "#   ANTHROPIC_FEDERATION_RULE_ID, ANTHROPIC_ORGANIZATION_ID and\n"
    "#   ANTHROPIC_SERVICE_ACCOUNT_ID, with the exchange body pinned to the\n"
    "#   workspace in ANTHROPIC_WORKSPACE_ID (a spend-capped workspace)\n"
    "#   explicitly,")


ROSTER_MINT = ("      # no fixture-controlled input is consumed by this exchange.\n"
               "      - name: Mint OIDC token and exchange for Anthropic access token\n")
ROSTER_SKIP = (
    "          # Optional: with all four variables empty, no token is minted, the\n"
    "          # roster step below publishes no roster, and the job stays green\n"
    "          # (roster-refresh.yml dispatches it weekly). A partial or\n"
    "          # malformed set still fails on the checks that follow.\n"
    "          if [ -z \"${FEDERATION_RULE_ID}${ORGANIZATION_ID}${SERVICE_ACCOUNT_ID}${WORKSPACE_ID}\" ]; then\n"
    "            echo \"::notice::Anthropic workload identity federation is not configured (repository variables ANTHROPIC_FEDERATION_RULE_ID, ANTHROPIC_ORGANIZATION_ID, ANTHROPIC_SERVICE_ACCOUNT_ID and ANTHROPIC_WORKSPACE_ID are unset): no token is minted and the model roster is not refreshed this run\"\n"
    "            echo \"federation=off\" >> \"$GITHUB_OUTPUT\"\n"
    "            exit 0\n"
    "          fi\n")
ROSTER_DONE_OLD = ("          printf '%s' \"$tok\" > \"$RUNNER_TEMP/anthropic-bearer\"\n"
                   "\n      # Model roster (#67, redesigned in #147).")
ROSTER_DONE_NEW = ("          printf '%s' \"$tok\" > \"$RUNNER_TEMP/anthropic-bearer\"\n"
                   "          echo \"federation=on\" >> \"$GITHUB_OUTPUT\"\n"
                   "\n      # Model roster (#67, redesigned in #147).")
REFRESH_OLD = ("      - name: Refresh the model roster\n"
               "        working-directory: skills-evals\n"
               "        run: |\n"
               "          set -uo pipefail\n")
REFRESH_NEW = (
    "      - name: Refresh the model roster\n"
    "        working-directory: skills-evals\n"
    "        env:\n"
    "          FEDERATION: ${{ steps.federation.outputs.federation }}\n"
    "        run: |\n"
    "          set -uo pipefail\n"
    "          # Federation not configured (the mint step above said so): there is\n"
    "          # no token for the Models API, so no roster is computed or proposed.\n"
    "          if [ \"${FEDERATION:-}\" = off ]; then\n"
    "            echo \"::notice::model roster not refreshed: Anthropic workload identity federation is not configured\"\n"
    "            {\n"
    "              echo \"### Model roster\"\n"
    "              echo\n"
    "              echo \"**The roster was not refreshed this run:** Anthropic workload identity federation is not configured, so there is no token for the Models API. No roster is published and no proposal is made.\"\n"
    "            } >> \"$GITHUB_STEP_SUMMARY\"\n"
    "            exit 0\n"
    "          fi\n")


def _sub(text: str, pattern, new: str, want: int, what: str) -> str:
    if isinstance(pattern, str):
        n = text.count(pattern)
        out = text.replace(pattern, new)
    else:
        out, n = pattern.subn(lambda _m: new, text)
    if n != want:
        raise RuntimeError(f"{REL}: expected {want} {what}, found {n}")
    return out


def apply(root: Path, ctx) -> None:
    path = root / REL
    text = path.read_text(encoding="utf-8")
    text = _sub(text, HEADER_OLD, HEADER_NEW, 1, "header federation comment")
    text = _sub(text, STEP_HEAD,
                STEP_HEAD.replace("        run: |\n", ENV + "        run: |\n") + CHECKS,
                2, "mint steps")
    text = _sub(text, BODY_OLD, BODY_NEW, 2, "exchange bodies")
    text = _sub(text, FAIL_OLD, FAIL_NEW, 2, "exchange failure branches")
    # The roster job's mint (the first, the only one after ROSTER_MINT's
    # comment) gets an id and the all-unset skip ahead of the checks.
    head = ROSTER_MINT + ENV + "        run: |\n"
    text = _sub(text, head, ROSTER_MINT.replace(
        "      - name: Mint OIDC token and exchange for Anthropic access token\n",
        "      - name: Mint OIDC token and exchange for Anthropic access token\n"
        "        id: federation\n") + ENV + "        run: |\n" + ROSTER_SKIP, 1, "roster mint step")
    text = _sub(text, ROSTER_DONE_OLD, ROSTER_DONE_NEW, 1, "roster mint end")
    text = _sub(text, REFRESH_OLD, REFRESH_NEW, 1, "roster refresh step head")
    _no_ids_left(text, REL)
    path.write_text(text, encoding="utf-8")
    _review_bearer(root)


def _no_ids_left(text: str, rel: str) -> None:
    for prefix in ("fdrl_", "svac_", "wrkspc_"):
        if re.search(rf"\b{prefix}(?!EXAMPLE)[A-Za-z0-9]{{8,}}", text):
            raise RuntimeError(f"{rel}: a {prefix} id is left")
    if re.search(r'organization_id: "[0-9a-f-]{36}"', text):
        raise RuntimeError(f"{rel}: an organization id is left")


REVIEW_REL = ".github/workflows/skill-coverage.yml"
REVIEW_HEAD = ("      - name: Mint the Anthropic bearer for the adversarial review\n"
               "        id: review-bearer\n")
REVIEW_RUN = ("        continue-on-error: true\n"
              "        run: |\n"
              "          set -euo pipefail\n")
REVIEW_BODY_OLD = re.compile(
    r"          body=\$\(jq -n --arg jwt \"\$jwt\" '\{\n"
    r'            grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",\n'
    r"            assertion: \$jwt,\n"
    r'            federation_rule_id: "fdrl_[A-Za-z0-9]+",\n'
    r'            organization_id: "[0-9a-f-]{36}",\n'
    r'            service_account_id: "svac_[A-Za-z0-9]+",\n'
    r'            workspace_id: "wrkspc_[A-Za-z0-9]+"\n'
    r"          \}'\)\n")
REVIEW_BODY_NEW = (
    '          body=$(jq -n --arg jwt "$jwt" \\\n'
    '            --arg rule "$FEDERATION_RULE_ID" --arg org "$ORGANIZATION_ID" \\\n'
    '            --arg svac "$SERVICE_ACCOUNT_ID" --arg wrkspc "$WORKSPACE_ID" \'{\n'
    '            grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",\n'
    '            assertion: $jwt,\n'
    '            federation_rule_id: $rule,\n'
    '            organization_id: $org,\n'
    '            service_account_id: $svac,\n'
    '            workspace_id: $wrkspc\n'
    "          }')\n")


def _review_bearer(root: Path) -> None:
    path = root / REVIEW_REL
    text = path.read_text(encoding="utf-8")
    i = text.find(REVIEW_HEAD)
    if i < 0 or text.count(REVIEW_HEAD) != 1:
        raise RuntimeError(f"{REVIEW_REL}: expected 1 review bearer step")
    # The step's own run block: the next one after its head, before the
    # step's `if:` line ends and its body starts.
    j = text.find(REVIEW_RUN, i)
    if j < 0 or text.find("      - name:", i + len(REVIEW_HEAD)) < j:
        raise RuntimeError(f"{REVIEW_REL}: expected 1 review bearer run block")
    text = text[:j] + "        continue-on-error: true\n" + ENV + "        run: |\n" \
        + "          set -euo pipefail\n" + CHECKS + text[j + len(REVIEW_RUN):]
    text, n = REVIEW_BODY_OLD.subn(lambda _m: REVIEW_BODY_NEW, text)
    if n != 1:
        raise RuntimeError(f"{REVIEW_REL}: expected 1 review exchange body, found {n}")
    _no_ids_left(text, REVIEW_REL)
    path.write_text(text, encoding="utf-8")
