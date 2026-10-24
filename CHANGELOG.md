# Changelog

## Android 3.3.0 Beta preparation (not published)

- Build Pillow 13.0.0 Android ARM64/x86_64 wheels from hash-verified source with pinned NDK, CPython support and build constraints; retain full PNG/JPEG/WebP validation without a vulnerable downgrade.
- Fully decode accepted images and enforce response MIME equality. Validate vision capability/images on every provider request path and bound streamed events before parsing.
- Fix cancelled login, late view updates, duplicate submissions and Android lifecycle handling; keep HTTP warnings outside scrolling content.
- Add offline local materials, atomic document/revision saves, visible save state, bounded backup import/export and recovery of damaged stores. Keys remain in session memory; insecure login does not save credentials.
- Add actual APK metadata/signature checks, native Android emulator acceptance, separate synthetic fixture APKs and a twelve-input mock OCR regression corpus.
- Record historical signing fingerprint and the missing upgrade identity. Do not publish test/debug keys or claim an Android 3.3 release before final gates.

## Release verification follow-up

- Resolve draft releases through the supported GitHub CLI lookup and verify source, bytes, checksums, metadata and channel before publication.
- Add a maintainer finalizer that downloads and launches the immutable tagged assets, without overwriting tags or historical assets.
- Record the Android patched-wheel/signing/device blockers and align bilingual channel links.

## 4.1.0 desktop / 4.2.0-web / 3.3.0-android source candidates

- Add assignment-bound original-image, corrected LaTeX, rich solution and source-oriented AI workflows.
- Preserve 一键满分 with scoped preview, confirmation, sequential progress, cancellation and unknown-outcome handling.
- Block default plaintext authentication; isolate and bound trusted image retrieval; prohibit redirects and automatic write replay.
- Add recoverable schema-1 documents and Markdown/Word/PDF exports with explicit source-math limitations.
- Improve the separate Flet Android UI, image zoom, saved notes and explicit contextual recognition/AI.
- Patch Pillow/KaTeX dependencies and document the editor/license decision and channel release gates.
- Android production artifact withheld pending signing and device verification. Published Windows state is recorded in docs/VERIFICATION.md.

## Earlier governance work

- Document canonical architecture and release-channel boundaries.
- Standardize repository governance, issue forms, dependency automation, and
  Windows/frontend CI.
- Preserve the project-specific licensing notice separately while restoring a
  machine-recognizable GPL-3.0 license file.

## 4.1.0-web

- Add the Windows local browser channel with shared course, workspace, AI chat,
  export, and session recovery behavior.

## 4.0.1

- Add the modern Three-column desktop UI, startup recovery, WebView2 guidance,
  streaming AI responses, session tools, and export compatibility.

## 3.2.1

- Stabilize Android login and the mobile course/assignment flow.
- Modernize the legacy desktop visual system and packaging.
