# Canonical architecture and channel boundaries

**Android publication, 25 October 2026:** [v3.3.0-android Beta](https://github.com/styayur/LGXT-Assistant/releases/tag/v3.3.0-android) is published with a durable signing identity and a reinstall-required migration from historical 3.2.1. [Exact signed-APK/native acceptance](https://github.com/styayur/LGXT-Assistant/actions/runs/40167960538) and fresh draft/published asset verification passed. Source `e402b78e558cc763b0e1fad87991674bb8bc831f`. This status supersedes historical preparation/blocker statements below. See [installation/data migration](android-beta.md) and [signing custody](android-signing.md).

LGXT Assistant is one product with several clients sharing Python domain behavior. This document defines the architecture to prevent new work from accumulating across legacy and current paths.

## Current channels

| Channel | Entrypoint | UI boundary | Release status |
| --- | --- | --- | --- |
| Windows desktop | `default.pyw` | `desktop/` bridge + built `frontend/` React UI | Current supported desktop channel |
| Windows web | `web_app.py` | built `frontend/` served by the local Python process | Current supported Windows web channel |
| Android | `mobile/src/main.py` | Flet client | Published 3.3.0 Beta; historical 3.2.1 requires reinstall |
| Legacy Tk | `default.pyw --legacy` | `ui/` package | Compatibility support; not the target for new product work |

Android 3.3 Beta retains Flet/Python. The app imports the shared transport, provider and document modules directly from `mobile/src`; no Windows binary dependency is shipped to Android. The Android build compiles its own Pillow 13 wheel using the pinned source recipe in `scripts/build_android_wheels.sh`, supplied through `PIP_FIND_LINKS`. The recipe disables unused font/TIFF extensions and preserves PNG/JPEG/WebP decoding. Desktop requirements remain platform-compatible.

Mobile work captures session/view generations so stale worker completions cannot navigate a newer page. Navigation and background lifecycle events stop local AI reception. A separate fixture entry is copied only into a test APK; the ordinary APK keeps the production entry. Emulator reruns may reuse a candidate only after app/dependency source comparison.

Local notes use schema-1 app-private JSON, bounded to 32 MiB. Writes flush then atomically replace; the current document and previous revision commit together. The offline library and validated backup import/export do not require a platform login. Corrupt/future data is preserved rather than silently reset. See [Android research](research/ANDROID_LIMITATIONS.md) for limits and [Android guide](android-beta.md) for backup behavior.

## Core domain

`api.py`, `tasks.py`, `exporter.py`, `config.py`, and the desktop storage/service modules own platform login, course/assignment retrieval, export orchestration, preferences, and local persistence. UI clients should call these boundaries instead of duplicating remote protocol or storage behavior.

## UI boundary

- `frontend/src/` is the React UI source for desktop and web.
- `desktop/bridge.py` is the trust boundary between the local web view and Python.
- `mobile/src/main.py` owns Android navigation and mobile-specific rendering.
- `ui/` owns the legacy Tk interface and should receive compatibility fixes only unless a migration is explicitly planned.

## Persistence boundary

Desktop data lives under `%APPDATA%\LGXT-Assistant`. Credentials use the operating-system credential store, not plain project files. Web mode must not silently create a second competing source of truth; shared storage behavior must be explicit and documented.

## External service boundary

The LGXT platform is accessed through the user's own account. AI requests go only to the provider configured by the user, using that provider's endpoint and key. The local web service binds to loopback by default and is not a public server.

## Extension points

- New AI providers should use the existing provider abstraction rather than branching in every React component.
- New export formats belong behind the exporter/service boundary.
- New channels must document storage, credential, packaging, and release-version behavior before implementation.
- New legacy features must not bypass the current desktop/web bridge.

## Release boundary

Channel versions may differ. Release asset names must identify platform and channel, and release notes must state known limitations. No workflow may publish a build from an untagged or unverified source state.


## Assignment document upgrade (schema 1)

`mobile/src/lgxt_transport.py`, `model_transport.py` and `question_documents.py` are the canonical portable Python modules. Root `api.py` / `question_documents.py` and `desktop/models.py` re-export them, so Flet packaging contains the same transport, provider and document validation as Windows. They do not depend on desktop storage or Tk. `tasks.py` owns sampling, batch planning and the sequential executor; `desktop/bridge.py` owns one-use confirmations, job cancellation, provider serialization and atomic Store integration.

React keeps its existing course/source navigation, workspace files and chat. `QuestionDocument.jsx` adds an original/corrected/solution/AI boundary inside the assignment page. `SolutionEditor.jsx` uses MIT Tiptap and local KaTeX math nodes; Markdown is the canonical recoverable representation. Flet keeps its own controls and mobile notes UI, using the shared modules rather than embedding a second HTTP implementation.

Question files are keyed by SHA-256 of course/work/question IDs. Schema 1 records source image/text, recognition, corrections, solution Markdown, explicitly selected source excerpts, platform answer and timestamps. Saves are atomic with a previous-version copy. Unsupported versions are refused without overwriting. Existing workspace/conversation files are unchanged. Source references name only actual supplied context; no retrieval/citation service or vector database is implied.

See SECURITY.md for HTTP compatibility and trust boundaries, docs/editor-decision.md for conversion/extension trade-offs, and docs/user-guide.md for user-facing operations. Platform success acknowledgment is distinct from independent final-grade verification, which is not available.

Flet 1.0 migration uses current Button/BoxFit/dialog APIs and a bounded atomic `mobile/src/local_store.py` under the durable FLET_APP_STORAGE_DATA directory. Legacy SharedPreferences migration reads only the saved username and removes the old password; no credential is written there.
