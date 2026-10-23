# Security policy

Current application license: AGPL-3.0-only. Report vulnerabilities privately through [GitHub security advisories](https://github.com/styayur/LGXT-Assistant/security/advisories/new). Never include passwords, tokens, AI keys, student identifiers, private course content or unredacted conversations in public issues.

## Platform transport evidence (24 October 2026, Singapore)

Credential-free `HEAD http://lgxt.wutp.com.cn/api` returned 302 to the same HTTP endpoint with a trailing slash. `HEAD https://lgxt.wutp.com.cn/api` failed during TLS handshake (Windows curl/Schannel error 35). Browser retrieval did not establish a usable HTTPS API. This proves neither universal HTTPS unavailability nor a working secure replacement. No username/password or token was sent during investigation.

The known official HTTP base remains accurately recorded. Every HTTP API operation is blocked unless the user explicitly opts into insecure compatibility for the login. No HTTPS-to-HTTP fallback exists. A verified HTTPS base may be configured by the operator; certificates are always validated normally. Redirects on authentication, reads, writes, images and model generation are disabled. Error messages do not echo exception URLs or arbitrary platform responses.

In insecure mode the React, legacy Tk and Flet interfaces display persistent warnings. Platform credentials are not saved; Android removes historical plaintext saved passwords and holds AI keys only in memory. Logout clears tokens, cookies/cache, pending batch previews and the saved platform credential. AI keys on Windows remain in the OS credential store. These controls cannot make HTTP confidential: users who opt in accept interception/tampering risk.

## Image and editor boundaries

- Only HTTP(S), exact configured platform hostname, default ports, no userinfo/fragment, and globally routable DNS results are permitted. Plain HTTP requires the same explicit opt-in. No arbitrary external image hosts are trusted.
- An isolated image session sends no LGXT Authorization, cookies, ambient proxy or netrc credentials. No redirects are followed. DNS destinations are checked; the trusted platform DNS itself remains an infrastructure trust assumption.
- Stream responses with finite connect/read timeouts, 8 MB encoded-byte limit, 20 million decoded pixels and one frame. Decode/verify PNG/JPEG/WebP with patched Pillow; reject SVG and non-image responses. Failures do not include sensitive URLs.
- AI image attachments are base64-decoded with strict MIME/content/size checks before provider serialization. Text fields, source lists, model output and document versions are bounded and validated.
- Markdown does not execute raw HTML. KaTeX uses `trust:false`, `maxExpand:1000`, `maxSize:20`. Automatic remote chat images are blocked. Rich editor imports escape raw HTML, reject remote image links and strip pasted HTML images. Model output is untrusted; recognition accepts exactly `text` and `latex` strings.
- File imports are explicit, bounded and local. Export IDs/names are cleaned to prevent path traversal. PDF markup escapes external question names and answers. Exports never fetch model-supplied image URLs.

## Request and batch semantics

Read-only POST endpoints are explicitly enumerated; they have at most two retries by default, configurable 0–3, exponential delay with jitter and bounded Retry-After handling. When Retry-After exceeds the supported waiting budget, return the rate limit without retrying early. Short-lived list caches suppress repeat requests. Question retrieval is sampling, not documented pagination; sequential collection is bounded and never promises a complete question bank.

Writes and paid AI generation are never automatically replayed. Submission timeout, connection loss, malformed confirmation, redirect or 5xx produces `verification_required`. A platform acknowledgment is `succeeded`, not independent verification of final grade. No reliable verification endpoint or idempotency support has been established. Check the platform before repeating ambiguous writes.

Batch previews list exact affected assignments and target score. A five-minute, one-use preview token gates React batch execution. Legacy uses the same domain plan and executor with an explicit confirmation. Writes are sequential (one in flight); cancellation stops future writes and does not roll back committed changes. The Windows audit retains at most 500 timestamp/hashed-item/status/score entries and stores no account names, credentials or response text.

## Local service

The browser server remains bound to `127.0.0.1`, uses a random per-run credential, checks Host and exact Origin and accepts only a fixed RPC allowlist. Browser launch credentials are moved from the fragment into sessionStorage and removed from the address bar. They are not kept in localStorage. No LAN exposure, permissive CORS or credential logging was added. Remote AI HTTP is rejected except explicit loopback model services.

## Supported artifacts and limitations

New Windows releases require source tests, UI checks, dependency/security scans, exact-tag builds and real packaged startup checks. Historical binaries do not acquire these fixes. Android source checks are separate from signing/device verification; without those gates, no production Android release is published. See [verification](docs/VERIFICATION.md) and [channel policy](docs/release-channels.md).

Android dependency blocker: the pinned Flet 0.25.2 runtime requires oauthlib <4, while PYSEC-2026-4114 is fixed in oauthlib 4.0.0. Flet 0.28.3 has the same cap; current Flet 1.0.5 changes the client API and needs a separately validated migration. The Android dependency audit remains a hard failing Android gate, with no ignored advisory or continue-on-error. Windows runtime requirements do not include Flet/oauthlib; its audit and publication are independent. No Android APK will be published from this state.
