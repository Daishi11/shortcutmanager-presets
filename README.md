# ShortcutManager Community Presets

Public, reviewed preset catalog for the Windows application **ShortcutManager**.
This public repository is separate from the private ShortcutManager application source code.

## Browse and import

ShortcutManager > **Community Presets** reads this public catalog without a GitHub account.
Import has a read-only action/target preview. Suggested global hotkeys are opt-in; local config is not overwritten.

- Catalog: [index.json](index.json)
- Community review policy: [REVIEW_PROCESS.md](REVIEW_PROCESS.md)
- Submit your own collection: [New submission issue](https://github.com/Daishi11/shortcutmanager-presets/issues/new?template=preset-submission.md)

## Submit a preset

1. Select a folder or actions in ShortcutManager and click **Submit to Community**.
2. Enter a public author name and description. The app prepares a local ZIP containing exactly one preset.json; it does **not** upload it automatically.
3. Open the submission issue linked from the app. Attach the ZIP, write a meaningful description and check all four public-sharing/security confirmations.
4. GitHub Actions runs a data-only review. An issue receives **changes-requested** or **pending-review**; the bot never approves or publishes anything.
5. A human/AI reviewer checks the contents and makes a recommendation. **Daishi11 must explicitly authorize publication** before the preset is added.

The current v1 format cannot port arbitrary local EXE paths across PCs. Do not share absolute installed-application paths, private URLs, usernames, passwords, or access tokens. Discord/Steam may be installed in different locations on each machine; these need a future portable application identity resolver.

All submission issues and attachments are **public**. Only submit collections you intend to share.

## Contribute directly with a pull request

Fork the repository, add a validated preset file under presets/, and update index.json with a unique ID, version, public name/author/description, path and exact SHA-256 digest of the file bytes.

```powershell
python verify_catalog.py
python -m unittest discover -s tests -v
```

The CI workflow validates each pull request. All submissions remain subject to maintainer review; passing CI is **not** a safety guarantee.

Do not commit private ShortcutManager configs, API keys, local personal paths or executables. Published preset JSON is treated as untrusted data, and no script or uploaded ZIP content is executed in CI.

## Current status

- Public read-only catalog: available and tested.
- Issue-based submission: available, requires GitHub login.
- GitHub Actions automated ZIP technical review: enabled.
- Maintainer-approved publication: manual; no automatic merges.
- Portable imported app identities, account-free submissions, likes and download counting: not yet implemented.
