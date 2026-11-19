# picomatch 4.0.7 local security backport

GHSA-fc5q-39xc-vjpf has no published fixed version at the 2026-11-18 review.
The vulnerable path is Vite → tinyglobby/fdir → picomatch, a development dependency;
it is not bundled in the Android APK. No Windows feature work is added.

Originally adopted the wildcard-in-repeated-extglob patch from styayur/gitpad-plus.
On 2026-11-19 independently reproduced its residual nested-wrapper timeout at
`+(@(*(a)))` with 96 `a` characters and `!`. The LGXT revision now literalizes
ambiguous nested extglobs inside repeats, preserving only the upstream proven
direct-star-to-character-class simplification. Ordinary wildcards, bracket
classes and escaped/quoted literals remain compatible. This deliberately narrows
uncommon nested extglob semantics in development tooling. Patch SHA-256 is
`133baaaf9c5e6e74203a28b779349876d672fa43da8a144bed7ee3128bd26585` and parser
SHA-256 is `f4736cb51806f4a23ee4b2cb6b7a711c82a9ac6ab4274b14087d21d93ba31e0a`.
Original
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
