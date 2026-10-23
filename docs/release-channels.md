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


## Assignment upgrade baseline and candidate versions

Audited 24 October 2026: published desktop v4.0.1, web v4.1.0-web, Android historical v3.2.1. The old web release also contains a historical Android APK; do not move/delete it. New releases must never mix channels.

Candidate minor versions: v4.1.0 desktop, v4.2.0-web web, v3.3.0-android Android. Independent feature additions justify each minor increment; Android source metadata does not establish APK readiness. Beta releases are marked prerelease in GitHub, not labeled stable from CI alone. Android publication is blocked until signing provenance and device/emulator checks are available.

Before tagging: merge a reviewed PR by squash after Verify, CodeForge regression, dependency/security, CodeQL and packaging checks pass. Dispatch release builds with a validated existing tag, checkout its exact commit, verify that metadata matches, run source/UI checks and packaged launch. Produce channel-named assets and SHA256SUMS.txt. Create a draft first, verify uploaded asset names/digests, then publish only verified channels. Never overwrite an existing tag or historical assets. See docs/VERIFICATION.md for actual outcomes.
