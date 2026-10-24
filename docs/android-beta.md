# Android 3.3 Beta preparation

**Not published yet.** Use the actual Android release page only after signing and native acceptance are complete. Actions artifacts labeled test-only or fixture are not public release builds.

The 3.3 candidate requires Android 7.0/API 24 or later and ARM64. x86_64 is included for emulator testing; this does not establish phone compatibility. Package: `io.github.styayur.lgxt_assistant_mobile`; versionName: `3.3.0`; versionCode: `4`.

1. Open the release tagged `v3.3.0-android` once it exists, verify it says **Pre-release / Beta**, and download only its Android APK, guide, notices and SHA256SUMS.
2. Compare the APK's SHA-256 with that release's checksum. For maintainers, run Android SDK `apksigner verify --print-certs` and compare the published durable certificate fingerprint.
3. Allow installation from your chosen file manager. Keep a backup of local notes. Do not uninstall an older installation to bypass a signature mismatch without understanding that app-private data may be deleted.
4. Launch the app. HTTP authentication is blocked by default because platform HTTPS is still unverified. Explicit compatibility mode transmits credentials and grades in plaintext; the warning remains visible throughout navigation. The app does not make HTTP safe.
5. Select a course, assignment and question. Inspect/zoom the original image, correct the LaTeX source, and save the question/solution to local materials. The save timestamp confirms a completed local write.
6. AI analysis sends the current question/context and, optionally, its image to the endpoint you configure. Confirm model vision support before image recognition. Keys stay in session memory. Review provider privacy/cost policies. Stopping local reception does not guarantee cancellation of billing.
7. Use **本地资料** or **离线打开本地资料** to read saved notes without logging in. Use **导出备份** before uninstalling. **导入备份 / 恢复** validates a schema-1 JSON backup and asks before replacing matching documents. A previous revision is retained.

Mobile displays editable LaTeX/Markdown source; it does not include the desktop rich editor, image cropper, Word/PDF export or native equation typesetting. Save edits before navigating away or terminating the process. No claim is made about live LGXT login/grade operations, paid provider compatibility or OCR accuracy.

Historical 3.2.1 APK certificate SHA-256: `26c318acad5518ef0344e68e54bfb976a9ea23ab1d26a324f1c88c024ee86f49`. Its original private key has not been located. A new release identity would require reinstalling historical installations; this decision has not been silently made.

See [research and decisions](research/ANDROID_LIMITATIONS.md), [security policy](../SECURITY.md) and [executed verification](VERIFICATION.md). Application license: AGPL-3.0-only; preserve accompanying third-party notices.
