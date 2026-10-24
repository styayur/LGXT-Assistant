# Assignment upgrade release notes

Channel candidates: Windows desktop **4.1.0**, Windows web **4.2.0-web**, Android **3.3.0-android**. These are beta feature releases; passing CI does not establish stable maturity. Availability is recorded in [verification](docs/VERIFICATION.md) and on each GitHub release page.

The minor increments reflect additive assignment documents, contextual AI and recognition workflows. Desktop advances from 4.0.1 to 4.1.0; web from 4.1.0-web to 4.2.0-web; Android source from historical 3.2.1 to 3.3.0-android. Old workspace/chat files remain usable. Requiring explicit HTTP compatibility is an intentional security behavior change.

- Assignment workspace with original image, corrected question, LaTeX preview, Tiptap solution and source-selected question AI.
- Whole-image or percentage-crop recognition; edit and approve text/math before applying. Provider-neutral serialization and conservative, user-confirmed vision capability.
- “一键满分” retained with assignment/course/all scope, counted preview, explicit confirmation, sequential progress, cancellation and truthful unknown outcomes.
- HTTP access blocked by default, no downgrade or write replay, isolated image fetches, destination/content/resource checks and patched image/math dependencies.
- Recoverable schema-1 question files, previous-version backup and Markdown/Word/PDF export. Equations in Word/PDF are source; validated embedded editor raster images are also included.
- Separate Android visual/input improvements, zoomable original images, saved notes, contextual AI and recognition; no desktop rich editor/crop/Word/PDF parity claim.

The official HTTP endpoint responds; HTTPS was not verified. Insecure compatibility transmits passwords/tokens/grades in plaintext and shows a persistent warning. No real account login, grade writes, paid model requests or live OCR accuracy study was performed. Automated model and platform workflows use synthetic fixtures. Unknown models require capability confirmation. No vector retrieval, invented citations, comprehensive OCR, handwriting or diagram guarantee.

A durable Android signing identity is unavailable. Emulator candidate outcomes are recorded separately; no physical ARM64 device acceptance is claimed. The release remains unpublished until its gates pass. Windows packaging and publication require checks against the exact intended source/tag; checksums are meaningful only for the assets actually attached to that release. Historical releases and tags are not rewritten.

Application license remains AGPL-3.0-only. Tiptap/ProseMirror MIT notices are distributed; prior attribution remains in NOTICE.md.

The Android OAuthlib audit blocker was resolved by migrating to Flet 1.0.5 and requiring OAuthlib >=4,<5. The mobile control flows and atomic local notes store are regression-tested; no advisory is ignored. Android release signing remains unresolved; native candidate acceptance is tracked in docs/VERIFICATION.md. No Android 3.3 release is published.

Android candidate build evidence: [run 40000566710](https://github.com/styayur/LGXT-Assistant/actions/runs/40000566710) reached arm64 dependency packaging, but Flet’s wheel index offers Pillow 12.2/12.3 and no security-required Pillow >=13 wheel. No insecure downgrade was used. That historical binary-dependency failure is superseded by the source-built Pillow 13 candidates in the Android preparation record. Native Android 15 x86_64 acceptance passed (run 40095767034); durable signing and the historical-upgrade decision still gate publication.

## Android 3.3 preparation update — 2026-10-24

Pillow 13.0.0 Android ARM64/x86_64 wheels and test APKs now build from verified source, using pinned build constraints. Images are fully decoded after structural verification and checked against MIME, byte/pixel/frame limits. Provider request paths enforce vision/image validation and bounded stream events. Mobile adds an offline materials library, atomic document/revision storage, explicit bounded backup import/export and session/view cancellation. Its text preview never loads Markdown image URLs.

Historical Android 3.2.1 has debug certificate SHA-256 `26c318acad5518ef0344e68e54bfb976a9ea23ab1d26a324f1c88c024ee86f49`; its key has not been located. Temporary CI signatures are test-only. A new durable identity for the same package requires explicit acceptance of reinstall/data-backup implications. Build number 4 and source version 3.3.0 do not establish a public release. See [Android research](https://github.com/styayur/LGXT-Assistant/blob/main/docs/research/ANDROID_LIMITATIONS.md), [guide](https://github.com/styayur/LGXT-Assistant/blob/main/docs/android-beta.md) and [verification](https://github.com/styayur/LGXT-Assistant/blob/main/docs/VERIFICATION.md).
