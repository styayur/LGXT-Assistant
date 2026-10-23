# Assignment upgrade verification

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
