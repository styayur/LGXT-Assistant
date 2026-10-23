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

Android signing secrets and physical-device/emulator acceptance are unavailable. Its release must remain unpublished. Windows packaging and publication require checks against the exact intended source/tag; checksums are meaningful only for the assets actually attached to that release. Historical releases and tags are not rewritten.

Application license remains AGPL-3.0-only. Tiptap/ProseMirror MIT notices are distributed; prior attribution remains in NOTICE.md.
