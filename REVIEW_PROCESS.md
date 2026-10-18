# Community preset review

## Submission and approval

1. Contributor uses ShortcutManager > Submit to Community. The app prepares a ZIP containing a single preset.json, but does not upload it.
2. Contributor opens a public GitHub issue, provides a meaningful description, attaches the ZIP and checks the four privacy/publication consent boxes.
3. GitHub Actions reads the ZIP as untrusted data, verifies format, action types, size, nesting and machine-specific paths. It never extracts or executes the ZIP.
4. A bot comment and one of two technical statuses record the outcome: **changes-requested** (problems found) or **pending-review** (no automatic blockers; not approved).
5. An independent human/AI reviewer evaluates every target, URL, full launch argument, suggested hotkey, author intention, privacy, portability and abuse potential.
6. Only the maintainer (Daishi11) explicitly authorizes publication. After approval, the checked JSON is added under presets/, index.json is updated with a unique ID, version, metadata and the exact SHA-256, and catalog CI must pass.
7. After merge, mark the issue **published** and link the catalog entry. An **approved** issue is not necessarily published.

The workflow never grants itself approval, merges pull requests, publishes JSON or changes the private application source.

## Trigger or rerun

- New/edited/reopened issues run the automated review.
- The repository owner can comment **/review** on an old issue to rerun checks.
- Alternatively use Actions > Review community submissions > Run workflow with the issue number.
- The bot updates its own previous review comment rather than appending duplicate reports.

## Security and portability rules

- Only the trusted default-branch reviewer runs. Untrusted ZIP contents are **never executed**, imported into Python, or extracted to the filesystem.
- ZIP input is limited to 1 MiB, and decompressed preset.json to 512 KiB, with a strict one-file allowlist and duplicate JSON field checks.
- The reviewer has contents:read and issues:write only; it cannot publish preset changes.
- URLs referring to local services, suspicious credential parameters, non-portable absolute Windows paths and executable command arguments cause flags or change requests.
- Community submission now supports strict package v2 `portable_app` identities: `steam`, `discord` or `custom` with an EXE basename and a `launch_app` / `focus_or_launch` behavior. The importing app resolves Steam and Discord from the recipient machine, while custom identities require manual executable mapping. Absolute v1 EXE paths remain nonportable and are flagged. Steam game IDs and wider installed-app detection are future improvements.
- All issue descriptions and attachments are public. Never upload private app configuration or personal installation paths. A successful schema or SHA-256 check is not a security guarantee.
- Suggested hotkeys still require explicit opt-in when imported; review must include the exact target and arguments.
- Final acceptance always requires explicit maintainer approval.

## Local checks

Run from the public repository:

```powershell
python verify_catalog.py
python -m unittest discover -s tests -v
```

Technical review and manual content review are separate; passing either alone is insufficient for publication.
