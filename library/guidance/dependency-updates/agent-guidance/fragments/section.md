## Dependency updates

Dependabot `cooldown`: `default-days: 7`, `semver-major-days: 30` (not
`github-actions`); advisories and own actions (`exclude` `example-adopter/*`,
`example-adopter-two/*`) skip it; unset waits 3 days; leave
`semver-minor-days`/`-patch-days` undefined. Action bumps auto-merge once it
passes. **By hand**: newest release past 7 days
(`npm view <pkg> time --json`), pinned exact. **Harness CLIs are unpinned**
(Claude Code, Codex; not `uses:` or SDKs): a run installs npm `latest`;
record the version and models.
