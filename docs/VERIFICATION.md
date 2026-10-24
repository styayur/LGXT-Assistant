# Verification record

The Android preparation record below supersedes older Android blocker statements. Historical Windows/assignment evidence is retained afterward.

## Durable signing preparation — 25 October 2026

The maintainer explicitly approved the new identity and reinstall requirement. Baseline `8e3b9d6f960f55e779561a9d20301bc2615e85b7` and all its main/PR checks passed; the application/dependency source still equals the accepted candidate. Public durable certificate: `0ec0084b65aff166d379206ca244ea54904511e95573b15fd2159bd4bd604114`. Independent encrypted-backup recovery and restored-key SDK signing passed; full custody details are in [android-signing.md](android-signing.md), without secret values. Local updated Python suite: **126 passed**, including missing/mismatched credentials, non-main signing, synthetic APK, SDK/debuggable manifest, ABI and release metadata rejection. The local signing smoke result is not a release build. Final main workflow/native/publication outcomes will be recorded separately after execution. The older Android section below describes the pre-authorization state.

## Android 3.3 Beta preparation — 24 October 2026

**Not published.** PR [#24](https://github.com/styayur/LGXT-Assistant/pull/24) prepares the Android Beta; no `v3.3.0-android` tag or GitHub Release exists. Development started from clean `main` at `b4c02a7ec2a4d158bf8980a1e116929b819be1e6`, on a separate Android branch. No unrelated PR or historical release was changed.

### Build, artifact and security evidence

- [Candidate run 40093464655](https://github.com/styayur/LGXT-Assistant/actions/runs/40093464655): the **build-apk job passed**, producing ordinary and separately marked synthetic fixture APKs. The overall run failed on the earlier native UI driver; it is not recorded as an overall pass. The final app source is `f44d146dca14aa9183322bf5650660edfabcd1e0`. Later acceptance runs require a zero diff across app, dependency, native recipe and fixture-entry source before reusing its exact bytes.
- Ordinary APK SHA-256: `54dd2ebad9a1f77aecbd46b852bf8157e1a33b710fd0c4f83193e3d119465b07`. Local Android SDK signature verification and all six manifest checksums passed on the downloaded artifact. Package `io.github.styayur.lgxt_assistant_mobile`, versionName `3.3.0`, versionCode `4`, min SDK 24, target SDK 36, ABIs `arm64-v8a` and `x86_64`.
- Temporary **test-only** certificate SHA-256: `89b63bb74ad0f9462e63488bef860e67325c0ae88af4b76f10e1bbcf3dcbb1b8`. A valid cryptographic signature does not make this a permitted publication identity. Fixture APKs and temporary-key APKs must never be release assets.
- Pillow 13.0.0 built from hash-verified upstream source with pinned Forge/Crossenv/CPython/NDK inputs. Actual wheel ELF headers, platform tags, metadata and required decoder modules verified locally for ARM64 (machine 183) and x86_64 (machine 62). Wheel SHA-256: ARM64 `5405f51bd900ddf4bf3baaadd1dda03e2d9170df299db01776ef0cb9a61c82e3`; x86_64 `aaea5d4e9e32741cba7d6ef1b90b86a9f3fe616c71955b5dd110a2ebe96b3b55`. Build logs, constraints, recipe/diff, input/output hashes and environment freeze are retained in the Actions wheel-evidence artifact. This is a repeatable recipe, not a bit-for-bit reproducibility claim.
- Local Python 3.13: **121 passed**. Tests cover full decode/MIME/resource limits, storage atomicity/corruption/import, provider serialization/cancel/redirect/stream bounds, stale auth and submission callbacks, lifecycle enums, and release-identity rejection. Targeted Bandit: zero findings, with no suppressions. Root/mobile pip-audit, npm audit, CodeQL and CodeForge 0.2.1 passed on the acceptance-driver commit ([checks](https://github.com/styayur/LGXT-Assistant/pull/24/checks)); final documentation commits must also satisfy the required checks; CodeForge baseline is unchanged. A local root pip-audit query timed out contacting PyPI; successful CI audits provide the dependency result. Native-library CVE coverage remains separate; the build audit explicitly reports source-only Mobile Forge as unindexed.
- Real Flet browser-renderer fixture regression passed after the final app changes. Control tests cover 390×844, 360×740 and 390×480; browser screenshots clearly display the fixture banner. Browser checks do not establish native Android acceptance.
- OCR corpus: 12 self-authored rendered samples, mock responses only; 11/12 schema parse, 8/12 normalized exact match, 10/12 render, 4/12 require correction. **Zero live OCR calls; no measured model accuracy.**

### Native Android acceptance

Ordinary candidate installed and launched in Android 15/API 35 x86_64 emulation, with default HTTP rejection using dummy inputs, offline library, background resume and force-stop restart. Historical 3.2.1 installed in the disposable emulator; attempting the new candidate correctly returned `INSTALL_FAILED_UPDATE_INCOMPATIBLE`. Native fixture decoder self-checks passed all 18 cases (PNG/JPEG/WebP, malformed/truncated/corrupt/oversize/bomb/multiframe rejection, repeated decode, HTTP tripwire, notes restart, password persistence refusal and corrupt-store fail closed).

[Native acceptance run 40095767034](https://github.com/styayur/LGXT-Assistant/actions/runs/40095767034) **passed** after its source-equality gate. Both ordinary and isolated fixture APKs installed and launched. Fixture paths passed course/assignment/question navigation, submission cancellation/confirmation without a server, note editing/saving, unconfirmed vision rejection before a provider request, note restoration after process termination, system Back, background resume and native file-picker export/import. The backup test exports a note, modifies and saves it, then imports and verifies the original exact value. It does not rely on a transient success notification. No native/Python crash was present in the acceptance logs.

The earlier import-driver failure was corrected by waiting for settled Flutter dialog bounds after returning from the Android picker; no app validation/confirmation gate was removed. Earlier native runs also exposed a real Flet lifecycle enum mismatch, now fixed and covered against every runtime enum member. Historical failed runs remain visible.

Compact reports: [ordinary APK](evidence/android-3.3/device-acceptance.json), [synthetic fixture APK](evidence/android-3.3/device-fixture-acceptance.json). Native screenshots: [login](screenshots/android-native-login.png), [HTTP rejected](screenshots/android-native-http-blocked.png), [fixture with actual Android keyboard](screenshots/android-native-keyboard-fixture.png), [fixture saved status](screenshots/android-native-saved-fixture.png). Fixture screenshots display a synthetic-data banner; they are not real courses. Full logs/XML/actions/screenshots are in the native acceptance artifact. Native image decoding is covered by the 18 self-checks; image zoom gestures, live image networking and vendor-specific layout are not established by this small flow.

### Signing and remaining limits

Historical 3.2.1 APK SHA-256 `6a9ec5a4113a1a24a4bfad29068158544aa526f892ffa972b590d53a7e29487d`; verified certificate SHA-256 `26c318acad5518ef0344e68e54bfb976a9ea23ab1d26a324f1c88c024ee86f49` (Android Debug DN). Historical workflow supplied no persistent key. Repository Secrets names are empty; no key is tracked; the standard local debug certificate differs. No private key values were read into reports and no broad disk search was performed. The original signing key has not been located. A new durable identity would require reinstalling existing installations and backing up notes first; publication needs the maintainer’s explicit decision. No new release key has been created.

No physical ARM64 device, real LGXT login/grade write, live paid provider, OCR accuracy, provider billing cancellation, vendor-specific keyboard or all-Android-version coverage is claimed. Native offline recovery is not a cloud-sync or encryption claim. Slow-network/429/5xx/timeout/cancel boundaries use synthetic transport/control tests rather than a live platform. HTTPS remains unverified after credential-free HTTP HEAD and failed TLS negotiation. Word/PDF equations remain LaTeX source. Detailed sources, dates, decisions and follow-ups: [Android limitations](research/ANDROID_LIMITATIONS.md), [OCR #25](https://github.com/styayur/LGXT-Assistant/issues/25), [equation export #26](https://github.com/styayur/LGXT-Assistant/issues/26).

## Historical assignment upgrade verification

Date: 24 October 2026 (Asia/Singapore). This record separates executed checks from release gates still in progress. Earlier historical evidence follows below.

## Audit baseline

- Clean original checkout on `codeforge/regression-ci-v0.2.1`; fetched current `origin/main` at `8d7be85` before creating `feat/assignment-workspace-security`. No pre-existing tracked changes were discarded.
- Published releases: desktop v4.0.1, Windows web v4.1.0-web, Android historical v3.2.1. Open PR #20 is an unrelated dependency update and was not modified.
- Baseline Python 3.13 suite: 51 passed. Baseline npm build passed; npm audit found four transitive KaTeX findings. Default shell Python 3.14 lacked pytest, so actual checks used installed Python 3.13.
- Recent main workflows passed. Historical failures included a loopback test timeout on a dependency branch and CodeForge regression findings; they were inspected and are not attributed to this change. Main rules require PR+squash, CodeForge regression, python and frontend checks; zero approving reviews are required.
- No credentials were sent to LGXT. HTTP HEAD responded, HTTPS handshake failed. This is an environment observation; secure API availability remains unverified.

## Executed during implementation

| Check | Evidence / limits |
| --- | --- |
| Python | 103 passed after shared transport/document, export, batch and Flet tests; later changes require rerun before release |
| React production build | Passed with npm lockfile; assignment/editor chunk is lazy-loaded |
| Existing browser checks | Passed themes, recovery, command palette, streaming/stop/regeneration, course pagination, confirmation and five viewport sizes |
| Assignment browser checks | Passed all three batch scopes, no writes before confirmation, cancellation, original image, recognition correction, rich math/table/source round trips, safe HTML, saved document and question AI context; 390×844 and 390×480 layouts |
| Flet controls | Synthetic login/course/assignment/document/save and confirmed single submission at 390×844, 360×740 and 390×480; no actual platform writes |
| Dependencies | npm audit zero findings after KaTeX deduplication. pip-audit zero findings for updated desktop requirements. Mobile audit is separately recorded by CI |
| Static security | Targeted Bandit on changed network/provider/document/bridge/storage/export/batch/local-server boundaries: zero findings after repairs; does not certify every historical line |
| Export | Word reopened with two embedded images and a table, LaTeX source retained. PDF rendered with Poppler for visual review; native mathematical typesetting is not claimed |

`docs/screenshots/assignment-*-fixture.png` are captures of the actual built React UI with synthetic course/model responses. Existing `modern-*.png` are browser UI captures, not native Android images. Software-keyboard behavior is approximated by reduced height; it is not a real Android IME test.

## Packaging and external gates

Windows local builds and exact-tag GitHub build/startup workflows are being verified. A build command alone is not acceptance; both actual desktop EXEs and the Web EXE must pass their smoke checks. No merge/tag/release is claimed by this interim record.

Android signing secrets are absent (`gh secret list` returned no secrets). No new signed APK, physical-device check or production Android release is claimed. Flet browser preview required compatible flet-web/FastAPI versions and stalled at its loading screen in this environment. `flet-runtime-loading-390.png` records only that loading state, not the updated Android interface. No Android visual acceptance is claimed.

No real platform login, grade submission, paid model generation, live OCR accuracy benchmark, handwriting/diagram study, LAN deployment or independent final-grade verification was executed. Fixture tests do not establish real-provider compatibility or platform permission.

## Repeatable commands

```powershell
py -3.13 -m pytest -q
py -3.13 -m compileall -q api.py tasks.py question_documents.py exporter.py desktop ui mobile/src web_app.py
npm ci --prefix frontend
npm run build --prefix frontend
py -3.13 scripts/check_frontend.py
py -3.13 scripts/check_assignment.py
py -3.13 scripts/check_web.py
py -3.13 -m pip_audit -r requirements.txt
py -3.13 -m pip_audit -r mobile/requirements.txt
py -3.13 -m bandit -r desktop/bridge.py desktop/storage.py mobile/src tasks.py exporter.py web_app.py
# After builds finish, without concurrent frontend rebuilds:
py -3.13 scripts/check_package.py
py -3.13 scripts/check_web.py --exe dist/LGXT-Assistant-Web.exe
```

See the GitHub PR and workflow links in the final delivery record for post-commit results. Published assets, if any, are independently checked by `scripts/verify_release.py` against SHA256SUMS and GitHub asset digests. Historical releases are unchanged.

The Android OAuthlib audit blocker was resolved by migrating to Flet 1.0.5 and requiring OAuthlib >=4,<5. The mobile control flows and atomic local notes store are regression-tested; no advisory is ignored. Android signing and device acceptance remain unavailable, so no APK is published.

Flet migration verification: 1.0.5 (Apache-2.0), OAuthlib 4.0.0; mobile audit and control tests pass. Durable mobile notes use FLET_APP_STORAGE_DATA with atomic schema-1 writes, unsupported-version backups and no password persistence. Legacy username migration and password removal use the asynchronous SharedPreferences service. Flet 1.0.5 selects Flutter 3.44.8 for candidate builds. No signed APK/device result is implied.

Local interim desktop packaging was rejected: a frontend rebuild occurred during artifact collection, and the portable smoke check failed. Those interim files were not published. Exact-tag release jobs build without concurrent edits and must pass fresh ZIP extraction plus both EXE startup checks. The separate local Web EXE passed real Chromium launch, RPC/session, persistence, export and layout checks.

Actual Flet 1.0 browser-renderer fixture flow passed: keyboard login, dashboard, course, assignment and question document at 390×844; reduced-height capture at 390×480. `android-flet-*-fixture.png` contain synthetic data from the isolated FixtureClient. These are genuine Flet browser renders, not native Android APK screenshots. The earlier loading-only capture documents the superseded 0.25 runtime failure.

The historical Windows loopback test timeout was reproduced with Tk Variable destruction on a server worker. The legacy startup test now destroys and collects its Tk callback cycles on the owning thread and asserts the app is released, without increasing HTTP timeouts or removing origin checks. A candidate Android build was also attempted; the first attempt exposed an interactive Flutter installation prompt. The workflow now pins the Flet-matched Flutter 3.44.8 and uses its supported --yes option. Signing/device acceptance still gate publication.


## Exact-tag Windows publication

PR #22 was squash-merged at `15b849cbf024e36d16e6b49abe46967435fbab13`. The immutable desktop `v4.1.0` and web `v4.2.0-web` tags resolve to that same verified application tree. [Required PR verification](https://github.com/styayur/LGXT-Assistant/actions/runs/40000574032), [CodeForge](https://github.com/styayur/LGXT-Assistant/actions/runs/40000574033), [CodeQL](https://github.com/styayur/LGXT-Assistant/actions/runs/40000566025), [security](https://github.com/styayur/LGXT-Assistant/actions/runs/40000574072) and [mobile dependency audit](https://github.com/styayur/LGXT-Assistant/actions/runs/40000574126) passed. Application regression count: 103; the later draft-verification tooling adds five tests (108 total).

The [desktop tagged build](https://github.com/styayur/LGXT-Assistant/actions/runs/40001560971) passed source, UI and both EXE startup checks, including a fresh portable extraction. The [web tagged build](https://github.com/styayur/LGXT-Assistant/actions/runs/40001566407) passed the actual uploaded EXE's browser checks. Both stopped safely at draft metadata verification: REST `releases/tags` returns 404 for drafts. Assets remain in their original drafts, not overwritten.

The corrected verifier uses `gh release view`, compares local SHA256SUMS, actual downloaded bytes, GitHub digests, exact asset set, channel, beta status and source commit. `finalize-release.yml` downloads those existing exact-tag artifacts, launches them again, and publishes only after all gates pass, then rechecks the published record. Publication status and finalizer evidence are authoritative on the [desktop release](https://github.com/styayur/LGXT-Assistant/releases/tag/v4.1.0) and [web release](https://github.com/styayur/LGXT-Assistant/releases/tag/v4.2.0-web). No tag or historical asset is rewritten.

Android candidate [build 40000566710](https://github.com/styayur/LGXT-Assistant/actions/runs/40000566710) fails at `Pillow>=13` for Android arm64: upstream provides only 12.2/12.3 wheels. The patched dependency was retained; no APK or Android tag is published. Signing credentials and device acceptance are also unavailable.
