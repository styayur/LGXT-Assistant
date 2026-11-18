# picomatch 4.0.7 local security backport

GHSA-fc5q-39xc-vjpf has no published fixed version at the 2026-11-18 review.
The vulnerable path is Vite → tinyglobby/fdir → picomatch, a development dependency;
it is not bundled in the Android APK. No Windows feature work is added.

Adopted the conservative wildcard-in-repeated-extglob literalization patch from
styayur/gitpad-plus, with its source and installed-file SHA-256 bindings. Original
picomatch is MIT licensed; npm installs its LICENSE unchanged and the verifier
checks that license's digest. Package name/version remain unchanged.

`npm ci` postinstall applies only the exact reviewed patch to the exact upstream
bytes. Every installed parser copy is independently checked. Risky ambiguous globs
are treated literally; ordinary globs retain their semantics. Bounded child-process
tests cover exploit rejection, literal behavior, ordinary glob compatibility,
tampering rejection and the original parser's reproducible timeout.

`npm run audit:security` retains `npm-audit.raw.json` and permits only this exact
advisory in the verified development graph with the installed patch and tests.
New advisories, missing inventory, changed executable bytes or runtime reachability
fail closed. The workflow uploads the raw report, so this is not an upstream fix,
alert dismissal or an assertion that npm audit reports zero vulnerabilities.
