# Android 3.3 Beta: evidence and decisions

Research date: **2026-10-24 (Asia/Singapore)**. This is a release-preparation record, not a claim that a 3.3 Android release exists. Application license: AGPL-3.0-only. No real LGXT credentials, grades, paid model calls or private course material were used.

## 1. Patched image decoder and packaging (release critical)

**Problem / impact.** Flet packaging installs platform wheels, rather than compiling a desktop wheel for Android. The previous [candidate 40000566710](https://github.com/styayur/LGXT-Assistant/actions/runs/40000566710) could not resolve Pillow >=13 for Android ARM64. Desktop/manylinux ARM wheels are not Android wheels.

**Sources, checked 2026-10-24.** [Flet Android packaging](https://flet.dev/docs/publish/android/), [official binary index](https://pypi.flet.dev/pillow/), [binary-package inventory](https://flet.dev/docs/reference/binary-packages-android-ios/), [Pillow 13.0.0 release notes, 2026-10-16](https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html), [PyPI source metadata](https://pypi.org/pypi/Pillow/13.0.0/json). The index offers 12.2/12.3 for cp314 Android, but no 13.0.0 wheel at research time. Pillow's notes identify critical JPEG decoding/storage fixes, including GHSA-5x8w-8jj5-q52h and GHSA-v9pv-5gc8-w2m6. These are relevant to untrusted raster input; a header-only check or a downgrade is not an equivalent mitigation. Advisory identifiers here come from upstream, not inferred CVE assignments.

**Decision A: official compatible wheel unavailable.** Do not lower the security requirement. Recheck the official index during subsequent maintenance; prefer an audited official wheel once available.

**Decision B: source build implemented.** `scripts/build_android_wheels.sh` pins:

| Input | Identity / verification |
| --- | --- |
| Mobile Forge | [b38989fa3954c8a491347bdce4196dedeacae399](https://github.com/flet-dev/mobile-forge/tree/b38989fa3954c8a491347bdce4196dedeacae399), upstream build recipes, BSD license |
| Crossenv helper | [e5e615651f794d060d9484eab463861fef2a2019](https://github.com/flet-dev/crossenv/tree/e5e615651f794d060d9484eab463861fef2a2019), pinned commit |
| CPython support | Flet python-build release 20260921, Python 3.14.7; archive SHA-256 `57ff6e122d7c05523c1704f4ea2118445c38a80e13a533ab3d0e143e3d6545fc` |
| Pillow source | 13.0.0, PyPI sdist SHA-256 `cdcd1ba258178f7356d74170c9a81ba4eab6a5d55748bc402a5a2a6fe6be3510` |
| Android compilation | NDK 27.3.13750724, API 24, cp314, arm64-v8a and x86_64 |
| App shell | Flet CLI/runtime 1.0.5, Flutter 3.44.8, JDK 17, uv 0.13.5 |

The local patch changes compiler search paths and disables unused TIFF/font extensions; it does not remove Pillow security fixes. The minimal Android recipe retains Flet's exact JPEG/WebP native dependencies (flet-libjpeg 3.0.90 and flet-libwebp 1.6.0). These come from Flet's official index; their wheel metadata/licenses are part of dependency provenance. Build tools update the upstream Jinja2 3.1.3 and wheel 0.43 pins to 3.1.6 and 0.48.0, with a separate pip-audit gate. Build-environment freeze, recipe, source patch, compiler logs and wheel SHA256SUMS accompany Actions artifacts. A procedure can be reproduced; wheel bytes are **not claimed bit-for-bit deterministic** across rebuilds.

The first experiment [40070916276](https://github.com/styayur/LGXT-Assistant/actions/runs/40070916276) failed because the old setup patch did not match Pillow 13. The adapted patch produced both wheels and an APK in [40071085261](https://github.com/styayur/LGXT-Assistant/actions/runs/40071085261). The subsequent reduced-dependency build [40071692435](https://github.com/styayur/LGXT-Assistant/actions/runs/40071692435) also succeeded. These are test candidates, not public releases. Later exact-source verification is recorded in [VERIFICATION](../VERIFICATION.md).

**Decision C: native Android adapter not selected.** [ImageDecoder](https://developer.android.com/reference/android/graphics/ImageDecoder) offers actual platform decoding and header callbacks (API 28+). Flet does not currently expose an equivalent synchronous Python validation interface in this project. A replacement would require a maintained Dart/Android bridge, bounded full decode, animation rejection, resource-release tests and a policy for API 24–27. Inspecting magic bytes or downsampling alone would weaken the present contract. Confidence: high for API availability; equivalence of a hypothetical adapter remains unproven.

**Validation boundary.** 8 MiB input, 20 million pixels, one frame, PNG/JPEG/WebP only; verify structure, reopen and fully decode, enforce actual MIME equality. `Image.verify()` alone is insufficient for JPEG scanlines. Tests cover truncated JPEG, corrupt PNG, bogus data, SVG, forged MIME, byte/pixel limits, tiny decompression-bomb headers, APNG/WebP animation and repeated decode. The native fixture entry runs the same decoder checks in Android. A small acceptance suite is not a fuzzing proof or a guarantee against all future vulnerabilities. Windows keeps its compatible Pillow dependency and shares the stronger validator.

**Status / follow-up.** Build blocker solved experimentally and encoded in CI; maintain this small source recipe until upstream wheel availability is verified. Audit native dependencies as well as Python packages; pip-audit does not establish a complete native CVE inventory. The build-environment audit reports the pinned, source-only `mobile-forge==2023.0.0` as unindexed and skips advisory lookup for that package; its source/recipe is reviewed separately. This is an audit coverage gap, not a zero-vulnerability assertion or an ignored advisory. Native ABI validation requires runtime acceptance, not merely an ELF filename.

## 2. Signing identity and upgrades (release critical)

**Evidence.** Downloaded historical `LGXT-Assistant-3.2.1-android.apk`, SHA-256 `6a9ec5a4113a1a24a4bfad29068158544aa526f892ffa972b590d53a7e29487d`. Android SDK apksigner verifies it. Certificate DN is `C=US, O=Android, CN=Android Debug`; public certificate SHA-256:

`26c318acad5518ef0344e68e54bfb976a9ea23ab1d26a324f1c88c024ee86f49`

Historical package `io.github.styayur.lgxt_assistant_mobile`, versionName 3.2.1, versionCode 3, minimum SDK 23, target SDK 34. The historical workflow supplied no keystore; [Flet documents debug signing as the fallback](https://flet.dev/docs/publish/android/#signing-an-android-bundle). Current repository Secrets list is empty. No keystore is tracked in the repository. The standard local Android debug keystore has a **different** certificate (`6769913b62a209863fe921ebfe7b1c82e96cf15eaa8b7dbdcde3a7c3c4031532`). Only these targeted locations and public certificate metadata were inspected; there was no disk-wide key search and no private key was logged.

**Conclusion / impact.** The historical signing key has not been located. A fresh CI debug key cannot provide a sustainable release identity. A new long-lived key for the same package will prevent in-place upgrades of historical installations; versionCode 4 alone does not solve this. [Android's signing documentation](https://developer.android.com/studio/publish/app-signing) explains the signing identity requirement. Confidence: high for inspected certificates; unknown whether the maintainer has an external backup.

**Status / recommendation.** Preserve package identity and increment build number to 4. CI explicitly labels temporary signatures test-only. Publication must pin and verify an enduring certificate and preserve its key in protected CI Secrets plus an independent encrypted backup. Do not recreate a lookalike debug identity or publish the test key. If the original key cannot be supplied, the final maintainer decision is whether to permit a reinstall-required Beta. Uninstall can destroy app-private notes/preferences; export a backup first where the installed version supports it. No historical APK/tag is replaced.

## 3. HTTPS and authentication (high)

**Reproduction.** Two credential-free checks on 2026-10-24: `curl --head --max-time 15 http://lgxt.wutp.com.cn/api` returns HTTP 302 to the HTTP trailing-slash URL; the same path over HTTPS fails Windows Schannel handshake with curl error 35. No certificate chain was established, so chain validity and an operational HTTPS API remain **unverified**. A network-specific failure is not proof that HTTPS is universally unsupported. No other official HTTPS base has been verified.

**Implementation / parity.** The same Python transport serves Windows and Android: default HTTP rejection before network, explicit per-login opt-in, normal TLS verification, no downgrade, no redirects, bounded read retries, and no grade-write replay. Mobile warning is outside the scrolling content so normal navigation/scrolling cannot hide it. Password fields clear when a request begins; insecure mode does not persist a username/password. A cancelled or timed-out login cannot restore authentication. Logout invalidates the session/view generation before background cleanup. Python objects cannot promise secure memory erasure; keys are not deliberately serialized to disk or logs.

**Status / recommendation.** Source and synthetic tests cover the default boundary. Real LGXT login/submission remains untested. Platform-operated TLS deployment or a verifiable official HTTPS endpoint is the appropriate fix; do not introduce an untrusted forwarding service. TLS negotiation must be retested with certificate validation and a documented API path when the operator supplies it.

## 4. OCR and image-to-LaTeX (quality unknown)

**Current path.** A user selects the current question, inspects its original image, confirms model vision support and explicitly invokes recognition. The prompt requests JSON containing exactly two string fields, `text` and `latex`, without solving. The shared parser bounds output to 64,000 characters, each field to 30,000, rejects malformed structure, and requires manual correction/application. Model output is not an authoritative answer.

**Reproducible corpus.** Run `py -3.13 scripts/benchmark_ocr.py` after `npm ci` and installing Playwright Chromium. [ocr-fixtures/results.json](ocr-fixtures/results.json) and twelve self-authored PNGs cover powers/subscripts, fractions, radicals, Greek letters, matrices, integrals, derivatives and engineering expressions, plus low resolution, blur, crop and lined background. These are project-owned synthetic fixtures, not student work. Rendering uses the project's KaTeX with trust disabled and bounded expansion. Mock responses deliberately include wrong formulas, malformed JSON and unsupported/untrusted commands.

| Measurement | Actual local MOCK result | Interpretation |
| --- | --- | --- |
| JSON/schema parse | 11/12 | Parser regression only |
| Whitespace-normalized exact LaTeX match | 8/12 | Known fixture responses; not mathematical equivalence |
| KaTeX render | 10/12 | Syntactically renderable can still be wrong |
| Manual correction required | 4/12 | Deliberately injected problems |
| Real model requests | 0 | No measured OCR accuracy |
| Diagram/context understanding | Not measured | Formula transcription does not demonstrate reasoning |

**Status / next step.** Corpus and parser/render regression executed locally. No provider benchmark, handwriting assessment, independent labels or confidence intervals exist. Before an accuracy claim, collect a larger licensed corpus with independent ground truth, fix a model/version and cost budget, compare exact/semantic/render results separately, and review every engineering diagram manually. No model key is required for this release's mock regression.

Tracked acceptance: [OCR benchmark issue #25](https://github.com/styayur/LGXT-Assistant/issues/25).

## 5. Provider formats, privacy and cancellation (medium/high)

**Sources.** [OpenAI image input](https://developers.openai.com/api/docs/guides/images-vision), [OpenAI data controls](https://developers.openai.com/api/docs/guides/your-data), [Claude vision](https://platform.claude.com/docs/en/build-with-claude/vision), [Gemini OpenAI compatibility](https://ai.google.dev/gemini-api/docs/openai), [Gemini terms](https://ai.google.dev/gemini-api/terms). These are current, mostly undated documentation pages, retrieved 2026-10-24; their service policies can change. They document formats and provider-specific handling, not LGXT app certification.

**Observed implementation.** Shared transport supports OpenAI/Gemini-compatible `image_url` data URLs and Claude base64 `image` blocks. Mobile exposes the compatible endpoint only; Windows exposes the broader provider selector. Every request path now enforces explicit vision confirmation and revalidates decoded bytes. Changing the mobile endpoint/model resets confirmation. Text-only analysis is available without vision. Non-loopback providers require HTTPS, generation redirects are rejected, and paid generation is never retried. Synthetic tests cover compatible/Claude serialization, malformed images, status errors, cancellation and stream closure. Live service compatibility remains unverified.

**Data boundary.** Explicit analysis sends the question text/corrections, selected source excerpts, existing solution/context and optionally the original image to the configured endpoint. Recognition always needs the image. Embedded solution images are not silently converted into extra attachments. Mobile now uses inert text previews, so model/Markdown HTML and image links cannot trigger remote preview fetches. An API key stays in session fields/request memory; endpoint errors do not echo the key. Stopping generation/closing its response cancels local receiving, not necessarily provider computation or billing. Connect/read timeouts are finite (10/60 seconds); an already-blocked network operation may take time to unwind.

**Policy conclusion.** OpenAI documents API data controls and possible abuse-monitoring retention; Gemini terms distinguish service tiers; Claude has its own service policies. Do not generalize a training/retention promise to custom compatible endpoints. Users must review the actual endpoint operator's policy and limits before sending private notes. Requests may return 429 or 5xx; the UI reports failure rather than replaying a billable call.

## 6. Word/PDF formulas (deferred; no Android export claim)

**Evidence.** `exporter.export_question_document` returns `equations: latex-source`. Current Word paragraphs and PDF text contain LaTeX source alongside existing headings, tables, code and validated raster images. They do not contain Word `m:oMath` objects or typeset PDF equations. Earlier export tests inspect the document structure; React's KaTeX preview does not change exported formats.

| Option | Benefit | Cost / licensing / decision |
| --- | --- | --- |
| Keep source + Markdown sidecar | Recoverable and editable source; current behavior | Implemented; document plainly |
| KaTeX/browser raster capture | Predictable visual equation in Word/PDF | MIT KaTeX, Apache-2.0 Playwright; browser/font packaging, sizing and accessibility need tests; equation becomes a bitmap |
| MathJax SVG then export adapter | Scalable equation appearance | [MathJax SVG documentation](https://docs.mathjax.org/en/latest/output/svg.html), Apache-2.0 project; SVG sanitization/conversion and font embedding add a pipeline |
| LaTeX/MathML to OMML | Native editable Word mathematics | [Microsoft Office math documentation](https://learn.microsoft.com/en-us/office/math/) confirms OMML storage; conversion subset and Word/LibreOffice round trips need an independent acceptance corpus |
| Dedicated TeX PDF engine | Full mathematical typesetting | External engine/distribution, sandboxing, macro/file-access restrictions, font licensing and substantial packaging cost |

**Status / recommendation.** Do not add a new renderer/converter in a release whose critical path is Android packaging. First implement optional, bounded offline equation images with source retained; evaluate OMML separately against matrix/fraction/multiline fixtures and existing text/image/table/code exports. No new conversion dependency or license has been introduced in this round.

Tracked acceptance: [equation export issue #26](https://github.com/styayur/LGXT-Assistant/issues/26).

## 7. Offline storage and recovery (high data integrity)

**Evidence / fixes.** `LocalStore` uses Flet's app-private data directory, schema 1, a 32 MiB ceiling, deep-copy reads/writes and same-directory atomic replacement after flushing. The previous setter retained the caller's object reference; subsequent mutation could change memory without updating disk. That is fixed. Document and previous revision now commit in one transaction; failed replacement preserves the existing main file and in-memory state. A last-good snapshot and corruption/unknown-version recovery copy are preserved. Unknown schema never silently overwrites data.

**User behavior.** Login offers offline local materials. The library opens saved question documents without platform access and offers explicit JSON export/import. Export contains question documents only, not username, passwords or API keys. Import bounds size, validates every document and hashed ID, confirms replacement, preserves prior revisions, and can recover a damaged store. Successful saves show timestamps; failure keeps editor contents visible. Notes are saved explicitly, not continuously: force termination before saving can lose edits. Back up before uninstalling or changing signing identity.

**Status / limits.** Unit tests execute restart, caller mutation, failed-replace, version refusal and corrupted-store import recovery. Android 15 x86_64 native fixture acceptance passed export, post-export edit, confirmed import and exact restored content in run 40095767034; native self-checks also passed corrupted-store fail-closed behavior. Physical/vendor-device recovery remains unverified. There is no cloud sync or encryption-at-rest layer added here; app-private storage is not a substitute for a protected external backup. Large embedded images count toward the total storage cap. Test actual Android file-picker permissions/backup restore across representative vendor devices before broader maturity claims.

## 8. Runtime and release support (medium)

**Sources / confidence.** [Pinned Mobile Forge source](https://github.com/flet-dev/mobile-forge/tree/b38989fa3954c8a491347bdce4196dedeacae399), [Flet 1.0.5](https://pypi.org/project/flet/1.0.5/), [Flet Python support release](https://github.com/flet-dev/python-build/releases/tag/20260921), [Flet Android packaging](https://flet.dev/docs/publish/android/). Official code/build logs establish cp314 Android wheel use and support for the selected ABIs. A community suggestion or an open upstream issue is not an upstream delivery commitment. No promised Pillow-wheel publication date was found or assumed.

**Compatibility.** The candidate targets ARM64 phones and x86_64 emulation, Android API 24+. Historical 32-bit/Android 6 support is not retained by this candidate toolchain. The package name stays unchanged and build number increases from 3 to 4. A successful x86_64 emulator run cannot establish physical ARM64 compatibility, vendor keyboard/safe-area behavior or all Android versions.

**Release controls.** Candidate workflow has read-only repository permissions; it uploads test artifacts rather than publishing a Release. Metadata verification checks signature, package, versionCode/name, ABIs, ZIP integrity and SHA-256. Debug certificates require an explicit test-only flag; publication verification requires the durable certificate fingerprint. Fixture APKs are built separately and never release assets. No `v3.3.0-android` tag or public release is created until signing and native acceptance gates are satisfied. Exact final outcomes and remaining gaps belong in [VERIFICATION](../VERIFICATION.md).
