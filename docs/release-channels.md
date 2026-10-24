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

Candidate minor versions: v4.1.0 desktop, v4.2.0-web web, v3.3.0-android Android. Independent feature additions justify each minor increment; Android source metadata does not establish APK readiness. Beta releases are marked prerelease in GitHub, not labeled stable from CI alone. Android publication is blocked on durable signing provenance and the historical-upgrade decision; Android 15 x86_64 emulator acceptance is recorded in VERIFICATION.md.

Before tagging: merge a reviewed PR by squash after Verify, CodeForge regression, dependency/security, CodeQL and packaging checks pass. Dispatch release builds with a validated existing tag, checkout its exact commit, verify that metadata matches, run source/UI checks and packaged launch. Produce channel-named assets and SHA256SUMS.txt. Create a draft first, verify uploaded asset names/digests, then publish only verified channels. Never overwrite an existing tag or historical assets. See docs/VERIFICATION.md for actual outcomes.

The Android OAuthlib audit blocker was resolved by migrating to Flet 1.0.5 and requiring OAuthlib >=4,<5. The mobile control flows and atomic local notes store are regression-tested; no advisory is ignored. Android release signing remains unresolved; native candidate acceptance is tracked in docs/VERIFICATION.md. No Android 3.3 release is published.

Android candidate build evidence: [run 40000566710](https://github.com/styayur/LGXT-Assistant/actions/runs/40000566710) reached arm64 dependency packaging, but Flet’s wheel index offers Pillow 12.2/12.3 and no security-required Pillow >=13 wheel. No insecure downgrade was used. That historical binary-dependency failure is superseded by the source-built Pillow 13 candidates in the Android preparation record. Native Android 15 x86_64 acceptance passed (run 40095767034); durable signing and the historical-upgrade decision still gate publication.

## Android 3.3 preparation update — 2026-10-24

Pillow 13.0.0 Android ARM64/x86_64 wheels and test APKs now build from verified source, using pinned build constraints. Images are fully decoded after structural verification and checked against MIME, byte/pixel/frame limits. Provider request paths enforce vision/image validation and bounded stream events. Mobile adds an offline materials library, atomic document/revision storage, explicit bounded backup import/export and session/view cancellation. Its text preview never loads Markdown image URLs.

Historical Android 3.2.1 has debug certificate SHA-256 `26c318acad5518ef0344e68e54bfb976a9ea23ab1d26a324f1c88c024ee86f49`; its key has not been located. Temporary CI signatures are test-only. A new durable identity for the same package requires explicit acceptance of reinstall/data-backup implications. Build number 4 and source version 3.3.0 do not establish a public release. See [Android research](https://github.com/styayur/LGXT-Assistant/blob/main/docs/research/ANDROID_LIMITATIONS.md), [guide](https://github.com/styayur/LGXT-Assistant/blob/main/docs/android-beta.md) and [verification](https://github.com/styayur/LGXT-Assistant/blob/main/docs/VERIFICATION.md).

Android durable signing and the reinstall requirement were approved on 25 October 2026. The workflow is dispatched on main with `release_signing=true`; an immutable tag is created only after signed-artifact and native acceptance gates pass. See [signing maintenance](android-signing.md). Approval is not a publication result.
