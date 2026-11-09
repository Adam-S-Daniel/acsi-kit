## Security

- Validate anything crossing a trust boundary — user input, API responses,
  file contents.
- **Escape or encode untrusted data for each context it reaches**, just
  before it is placed there, with a well-established library or built-in
  (else a thoroughly vetted algorithm): HTML text or attribute, URL, YAML,
  SQL (parameterized queries), shell (arrays). Rejecting or stripping
  characters does not replace it.
- Never commit secrets, credentials or `.env` files, or disable TLS
  verification, authentication or CSRF protection.
- **Automation authenticates as a scoped GitHub App, not a PAT.**
