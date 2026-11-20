# Flutter 3.47.9 autofill privacy backport

The exact SDK revision `c197ca5199e9ee5661e865596c9c07294dfab51c` omits
`enableIMEPersonalizedLearning` while copying a field configuration into an
AutofillScope configuration. Its default `true` silently replaces the app's
requested `false`. The source-identical API35 synthetic fixture observed password
`imeOptions=0x02000006`, without the requested `0x01000000` privacy bit.

This local backport forwards only that one field. AutofillGroup, password masking,
reveal support, no-suggestion options and the strict native assertion remain.
It does not attribute the separate computer bulk-input anomaly to this defect.

Provenance: [issue192340](https://github.com/flutter/flutter/issues/192340) and
[PR192480](https://github.com/flutter/flutter/pull/192480), reviewed at head
`4de1d59b2cb705ff0e8a22e40ff0b5f751240580`. The PR was OPEN and unmerged when
reviewed; this is not a claim that the released SDK includes its fix. This patch
does not import the rest of that PR's configuration changes.

`autofill-backport.json` pins the original revision, Git blob and original/patched
SHA-256. The installer refuses a different revision, changed baseline, unrelated
framework edits or a changed license; applying the exact patch twice is safe.
The upstream source header remains intact. Flutter's BSD-3-Clause terms are
retained in `LICENSE.flutter` and normal APK notices.

CI runs the existing Flutter autofill tests plus a platform-channel regression
for both requested values before building. The native matrix independently
requires the emitted privacy bit; a passing Python property assertion is not a
substitute. Existing signed release assets are immutable and are not patched.
