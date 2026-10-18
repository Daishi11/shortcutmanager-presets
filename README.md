# ShortcutManager Community Presets

This folder is a **publication template** for a separate **public** GitHub
repository named `Daishi11/shortcutmanager-presets`. It is **not** the
private ShortcutManager application source repository.

## Publish the first public catalog

1. **First create the repository in GitHub's web UI** at
   https://github.com/new — owner `Daishi11`, exact repository name
   `shortcutmanager-presets`, **Public**, default branch `main`.
   It can be empty: do not initialize a README, license or .gitignore.
   **Do not change the private ShortcutManager application repository.**
   Until the new repository exists, `git clone` will return
   **Repository not found**. No follow-up copy/git command can succeed.
2. From the **private ShortcutManager project folder**, pull the latest
   changes and run the fail-safe publishing helper:

   ```powershell
   git pull
   .\scripts\publish_community_catalog.ps1
   ```

   The helper checks that the new repository exists and is public
   **before cloning or copying**, uses a fresh sibling directory named
   `shortcutmanager-presets-public`, refuses to overwrite an existing
   destination, copies hidden `.gitattributes` and GitHub Actions
   files, runs `verify_catalog.py`, and only then commits and pushes
   the reviewed starter files to `main`.
   In case that directory already exists, choose a different empty path:
   `.\scripts\publish_community_catalog.ps1 -Destination E:\git\shortcutmanager-presets-new`.
3. Check that the manifest is public from an incognito browser window
   (no GitHub login required):
   `https://raw.githubusercontent.com/Daishi11/shortcutmanager-presets/main/index.json`
4. Start ShortcutManager and open **Community Presets**. The sample
   collection should be listed. **Review and import** reuses the same
   action/target preview and individually opt-in hotkeys as local import.

**Recovery from an earlier failed clone:** If `git clone` failed,
`E:\git\shortcutmanager-presets` is not a valid checkout. The previous
wildcard-based `Copy-Item` command may have placed partial files there.
Do not run `git add` in it or delete unknown files blindly. The publishing
helper deliberately uses a **different** fresh folder, so the failed
local destination can remain untouched until you inspect it.

The sample contains only public example URLs. The `sha256` field in
`index.json` is calculated from the **exact bytes**, including the final
newline, of the sample JSON. To check it on Windows:

```powershell
(Get-FileHash -Algorithm SHA256 .\presets\example-url-collection.json).Hash.ToLowerInvariant()
```

Run `python verify_catalog.py` before publishing. The included
read-only GitHub Actions workflow validates every pull request and push
without any app credentials or deployment secrets. Public branch
protection and manual review are still required: contributors can modify
the validator in their own pull requests, and a checksum is not a
signature. `.gitattributes` forces LF for JSON files so Windows Git
checkouts preserve the bytes used by SHA-256.

For additional presets, export a shareable JSON preset using ShortcutManager,
review it for sensitive/local paths, place it under `presets/` with a safe
filename, and add an entry to `index.json` with a unique lowercase
hyphenated ID, version, identical display metadata and SHA-256.
All contents of this repository, including any private paths someone
accidentally puts in a preset, are **public**.

## Safety and contributions

- Reading the public catalog requires no login, API key, token or write
  permission. The client accepts HTTPS `raw.githubusercontent.com` URLs
  only and never executes catalog data.
- New contributors should **fork this repo and open a pull request**.
  The maintainer reviews every action type, launch target, suggested
  hotkey, description and any OS-specific path before merging.
- The JSON parser rejects scripts, command execution actions and
  unsupported fields. However, launching an application can still have
  consequences when a user subsequently assigns and presses its hotkey.
- Never commit private ShortcutManager config files, Discord/GitHub tokens,
  personal API keys, secrets, local user paths, or binaries. Never place a
  GitHub PAT inside the ShortcutManager desktop app.
- Protect the main branch; require code review for incoming PRs. A
  SHA-256 checks accidental or unauthorized file changes against the
  catalog manifest, but it is **not** a signature or trust guarantee
  against a compromised manifest/repository.
- Automatic preset updates and resolving user overrides are intentionally
  not part of this first read-only implementation.
