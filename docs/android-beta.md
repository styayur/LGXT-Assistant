# Android 3.3 Beta — reinstall required

**Reinstall required for historical 3.2.1 installations.** The maintainer approved a new durable signing identity. Download only from the actual `v3.3.0-android` GitHub page once it is published as Pre-release / Beta. Actions artifacts labeled test-only or fixture are not release builds.

The 3.3 candidate requires Android 7.0/API 24 or later and ARM64. x86_64 is included for emulator testing; this does not establish phone compatibility. Package: `io.github.styayur.lgxt_assistant_mobile`; versionName: `3.3.0`; versionCode: `4`.

1. Open the release tagged `v3.3.0-android` once it exists, verify it says **Pre-release / Beta**, and download only its Android APK, guide, notices and SHA256SUMS.
2. Compare the APK's SHA-256 with that release's checksum. For maintainers, run Android SDK `apksigner verify --print-certs` and compare the published durable certificate fingerprint.
3. Before replacing any older installation, follow the backup and reinstall steps below. Uninstalling deletes app-private data and preferences. Allow installation from your chosen file manager only after protecting your data.
4. Launch the app. HTTP authentication is blocked by default because platform HTTPS is still unverified. Explicit compatibility mode transmits credentials and grades in plaintext; the warning remains visible throughout navigation. The app does not make HTTP safe.
5. Select a course, assignment and question. Inspect/zoom the original image, correct the LaTeX source, and save the question/solution to local materials. The save timestamp confirms a completed local write.
6. AI analysis sends the current question/context and, optionally, its image to the endpoint you configure. Confirm model vision support before image recognition. Keys stay in session memory. Review provider privacy/cost policies. Stopping local reception does not guarantee cancellation of billing.
7. Use **本地资料** or **离线打开本地资料** to read saved notes without logging in. Use **导出备份** before uninstalling. **导入备份 / 恢复** validates a schema-1 JSON backup and asks before replacing matching documents. A previous revision is retained.

Mobile displays editable LaTeX/Markdown source; it does not include the desktop rich editor, image cropper, Word/PDF export or native equation typesetting. Save edits before navigating away or terminating the process. No claim is made about live LGXT login/grade operations, paid provider compatibility or OCR accuracy.

Historical 3.2.1 APK certificate SHA-256: `26c318acad5518ef0344e68e54bfb976a9ea23ab1d26a324f1c88c024ee86f49`. Its original private key has not been located. The approved durable Beta certificate SHA-256 is `0ec0084b65aff166d379206ca244ea54904511e95573b15fd2159bd4bd604114`. These are different identities; Android will reject an in-place update from 3.2.1. VersionCode 4 does not bypass signature checking.

See [research and decisions](research/ANDROID_LIMITATIONS.md), [security policy](../SECURITY.md) and [executed verification](VERIFICATION.md). Application license: AGPL-3.0-only; preserve accompanying third-party notices.

## Back up, verify, reinstall and restore

1. In an installed build that supports question documents, use **本地资料 → 导出备份** before uninstalling. Open the exported JSON independently, confirm it has `schemaVersion: 1` and the expected `documents`, and inspect representative question/solution contents. An empty/malformed file is not a verified backup.
2. Keep that file outside app-private storage (for example, Downloads plus another protected copy). Question-document exports include supported question/solution/source/image fields; they do **not** include usernames, passwords, API keys, every preference or all application state.
3. Only after verifying the external backup, uninstall the old application. Uninstalling deletes its private notes/data/preferences; reinstalling cannot recover an absent backup.
4. Install the signed `v3.3.0-android` Beta, verify its certificate/checksum, open **离线打开本地资料**, then **导入备份 / 恢复** and confirm replacement.
5. Open restored documents and compare their text, formulas and any embedded images with your backup. Retain the external backup until restoration is confirmed.

The original 3.2.1 source predates question-document storage and the JSON backup feature; it does not contain an export button. Do not assume this guide adds one to an old installation. If a modified/intermediate build contains valuable notes but has no export facility, preserve them through that build's existing export/device backup facilities or manual copies before uninstalling. Do not uninstall while the data is unverified. Historical saved login preferences are not migrated or exported.

See [signing custody and release gates](android-signing.md) for the public identity and maintainer procedure.
