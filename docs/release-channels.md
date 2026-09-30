# Release channels

LGXT Assistant uses channel-specific releases because desktop, Windows web, and Android do not share a version cadence.

| Channel | Tag pattern | Example assets |
| --- | --- | --- |
| Windows web | `vX.Y.Z-web` | `LGXT-Assistant-Windows-Web-vX.Y.Z.exe`, `SHA256SUMS.txt` |
| Windows desktop | `vX.Y.Z` | `LGXT-Assistant-Windows-Desktop-vX.Y.Z.exe`, `LGXT-Assistant-Windows-Desktop-vX.Y.Z-portable.zip` |
| Android | `vX.Y.Z-android` | `LGXT-Assistant-Android-vX.Y.Z.apk` |

Rules:

- Tags use SemVer and identify the affected channel.
- Stable assets are machine-parseable and URL-safe.
- Releases are built from an exact tag or a maintainer-controlled dispatch tied to that tag.
- SHA256SUMS accompanies distributable assets.
- Release notes list supported platforms and known limitations.
- Historical compatibility names may remain attached to older releases, but new automation should use the channel pattern above.
- No release is published automatically merely because `main` changed.
