# ShortcutManager Community Presets

Public, reviewed community preset catalog for the **private** ShortcutManager desktop application. The app itself remains in a separate, private repository.

## Browse

The published catalog is available without signing in:

- Catalog manifest: https://raw.githubusercontent.com/Daishi11/shortcutmanager-presets/main/index.json
- Presets: see the `presets/` folder and `index.json` manifest.
- In ShortcutManager, use **Community Presets** to browse, review and import entries.

Downloads verify each preset against the SHA-256 in `index.json`. The digest checks integrity relative to the catalog manifest; it is **not** a safety signature. Review all targets and optional hotkeys before importing.

## Submit a preset

1. In ShortcutManager, select one or more shortcut actions or folders.
2. Use **Submit to Community**, enter a collection name (if needed), author and description, and review the exact generated JSON.
3. The app creates a ZIP containing one `preset.json` and opens the submission form. Nothing is uploaded automatically. A GitHub account is currently required to post the issue.
4. Attach the ZIP, replace the placeholder description and check all four publication/privacy confirmations.
5. The automatic reviewer checks the data and posts an issue report with `pending-review` or `changes-requested`. These are **technical** statuses and do not authorize publication.
6. A maintainer reviews every target, security impact, metadata and hotkey proposal and must expressly approve publication. Only then may the JSON and updated catalog manifest be merged.

Submission form: https://github.com/Daishi11/shortcutmanager-presets/issues/new?template=preset-submission.md

The full process, status definitions and threat model are documented in [REVIEW_PROCESS.md](REVIEW_PROCESS.md).

## Portable application presets

The application supports **preset package v2** for portable app identities. Community submissions can represent Steam/Discord and generic Win32 programs without exposing the creator’s absolute installation paths. Steam and Discord are resolved on the importing Windows PC using known local registrations; generic programs require explicit local executable mapping. Suggested hotkeys remain opt-in.

Legacy v1 package files remain readable; absolute application paths in a community contribution are not portable and will be flagged by review. Existing AppsFolder/AUMID actions can preserve their stable identifiers. Steam **game IDs**, broad installed-application auto-detection and partial unresolved imports are not yet implemented.

## Validation

The public catalog uses an `index.json` manifest with unique entries and exact SHA-256 digests. Every `presets/*.json` file must be indexed, the allowed action types and nested structures must pass strict validation, and published metadata must match the manifest.

Run locally:

```powershell
python verify_catalog.py
python -m unittest discover -s tests -v
```

Pull requests and pushes run the read-only catalog validation. The separate submission-review workflow parses ZIP attachments as untrusted **data**, with capped sizes, no extraction, no execution and no permission to publish catalog changes. Contributors must not include scripts, command execution, credentials, secrets, private local paths or sensitive personal information.

The maintainer reviews the result manually before publication. Contributors can also fork this repository and propose content via pull request.

## Maintenance

- Keep JSON line endings as LF (see `.gitattributes`) because exact bytes are hashed.
- Recalculate each updated preset SHA-256 and update the corresponding `index.json` entry.
- Never change the private ShortcutManager application repository visibility to publish a preset.
- Keep `main` protected and require explicit maintainer approval; a green CI build is not a safety guarantee.

